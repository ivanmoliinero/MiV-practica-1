"""
row_builder.py
--------------
Dataset record construction, candidate percentage alignment, pollster
source/date matching, phantom row filtering, and CSV export.
"""

import os
import logging
import pandas as pd

try:
    from .config import YEAR, COLUMNS_ORDER
    from .utils import (
        clean_text_field,
        clean_pct_series,
        col_matches_candidate,
        find_matching_col,
        find_all_matching_cols,
    )
except ImportError:
    from config import YEAR, COLUMNS_ORDER
    from utils import (
        clean_text_field,
        clean_pct_series,
        col_matches_candidate,
        find_matching_col,
        find_all_matching_cols,
    )

log = logging.getLogger("senate_scraper")


def create_fallback_row(
    state: str,
    incumbent_info: dict | None = None,
    meta: dict | None = None,
    error_msg: str | None = None,
) -> dict:
    """
    Builds a fallback/error dictionary row when no polling data or candidate
    information is available for a race.
    """
    meta = meta or {}
    incumbent_info = incumbent_info or {}
    cand1, party1 = meta.get("candidate_1"), meta.get("party_1")
    cand2, party2 = meta.get("candidate_2"), meta.get("party_2")

    return {
        "estado": state,
        "año": YEAR,
        "titular_actual_sillon": incumbent_info.get("titular_actual_sillon"),
        "partido_titular_sillon": incumbent_info.get("partido_titular_sillon"),
        "partido_candidato_actual_1": party1 if cand1 else None,
        "candidato_actual_1": cand1,
        "partido_candidato_actual_2": party2 if cand2 else None,
        "candidato_actual_2": cand2,
        "fuente_encuesta": None,
        "fecha_encuesta": None,
        "porc_republicano_sillon_en_juego": None,
        "porc_democrata_sillon_en_juego": None,
        "indecision": None,
        "error": error_msg,
    }


def build_rows_for_state(
    state: str,
    meta: dict,
    poll_tables: list[pd.DataFrame],
    incumbent_info: dict | None = None,
    predictions: list[dict] | None = None,
) -> list[dict]:
    """
    Builds structured CSV rows for a given state race, aligning candidate names
    with REP/DEM columns, extracting pollster sources and fieldwork dates,
    and filtering phantom rows where neither candidate has percentages.
    "meta" contains metadata from Wikitext, whereas "poll_tables" contains the 
    analyzed tables from Wikipedia links for each state with the polls.
    If no head-to-head polling rows are found, falls back to qualitative
    forecaster prediction ratings.
    """
    cand1, party1 = meta.get("candidate_1"), meta.get("party_1")
    cand2, party2 = meta.get("candidate_2"), meta.get("party_2")

    incumbent_name = incumbent_info.get("titular_actual_sillon") if incumbent_info else None
    incumbent_party = incumbent_info.get("partido_titular_sillon") if incumbent_info else None

    # Determine candidate party assignments
    if party1 == "REP":
        rep_name, dem_name = cand1, cand2
    elif party2 == "REP":
        rep_name, dem_name = cand2, cand1
    else:
        rep_name, dem_name = cand1, cand2

    rows = []
    if poll_tables:
        for df in poll_tables:
            rep_col = next((c for c in df.columns if col_matches_candidate(c, rep_name)), None) if rep_name else None
            dem_col = next((c for c in df.columns if col_matches_candidate(c, dem_name)), None) if dem_name else None
            cand_cols = [c for c in [rep_col, dem_col] if c]
            unk_cols = find_all_matching_cols(
                df,
                ["undecided", "don't know", "dk", "other/undecided", "other", "neither"],
                exclude=["date", "margin", "sample", "poll", "source"] + cand_cols,
            )
            src_col = find_matching_col(df, ["poll source", "source of poll", "pollster", "firm", "surveyor", "source"], exclude=["date"])
            date_col = find_matching_col(df, ["date(s) administered", "dates administered", "date administered", "dates", "date"], exclude=["update"])

            rep_pct = clean_pct_series(df[rep_col]) if rep_col else pd.Series([None] * len(df))
            dem_pct = clean_pct_series(df[dem_col]) if dem_col else pd.Series([None] * len(df))

            # Clean and verify numeric percentages for all undecided/other columns, then aggregate
            valid_unk_series = []
            for c in unk_cols:
                s = clean_pct_series(df[c])
                if s.notna().any():
                    valid_unk_series.append(s)

            if valid_unk_series:
                unk_pct = pd.concat(valid_unk_series, axis=1).sum(axis=1, min_count=1).round(2)
            else:
                unk_pct = pd.Series([None] * len(df))

            for i in range(len(df)):
                rep_v = rep_pct.iloc[i] if (rep_col and i < len(rep_pct)) else None
                dem_v = dem_pct.iloc[i] if (dem_col and i < len(dem_pct)) else None
                unk_v = unk_pct.iloc[i] if i < len(unk_pct) else None
                src_v = clean_text_field(df[src_col].iloc[i]) if (src_col and i < len(df)) else None
                date_v = clean_text_field(df[date_col].iloc[i]) if (date_col and i < len(df)) else None

                # Discard rows that are not head-to-head general election matchups
                if pd.isna(rep_v) or pd.isna(dem_v):
                    continue

                rows.append({
                    "estado": state,
                    "año": YEAR,
                    "titular_actual_sillon": incumbent_name,
                    "partido_titular_sillon": incumbent_party,
                    "partido_candidato_actual_1": party1,
                    "candidato_actual_1": cand1,
                    "partido_candidato_actual_2": party2,
                    "candidato_actual_2": cand2,
                    "fuente_encuesta": src_v,
                    "fecha_encuesta": date_v,
                    "porc_republicano_sillon_en_juego": rep_v if pd.notna(rep_v) else None,
                    "porc_democrata_sillon_en_juego": dem_v if pd.notna(dem_v) else None,
                    "indecision": round(float(unk_v), 2) if (unk_v is not None and pd.notna(unk_v)) else None,
                    "error": None,
                })

    # If no head-to-head numerical polls were extracted, fall back to forecaster predictions
    if not rows and predictions:
        for pred in predictions:
            rows.append({
                "estado": state,
                "año": YEAR,
                "titular_actual_sillon": incumbent_name,
                "partido_titular_sillon": incumbent_party,
                "partido_candidato_actual_1": party1,
                "candidato_actual_1": cand1,
                "partido_candidato_actual_2": party2,
                "candidato_actual_2": cand2,
                "fuente_encuesta": pred["source"],
                "fecha_encuesta": pred.get("date"),
                "porc_republicano_sillon_en_juego": None,
                "porc_democrata_sillon_en_juego": None,
                "indecision": None,
                "error": f"Prediction: {pred['ranking']}",
            })

    if not rows:
        return [create_fallback_row(state, incumbent_info, meta, "No general election polling data or predictions found on page")]

    return rows


def save_polling_csv(rows: list[dict], output_csv: str) -> None:
    """
    Formats the assembled rows into a pandas DataFrame adhering strictly to
    the project schema (COLUMNS_ORDER) and saves as a UTF-8 CSV.
    """
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df = pd.DataFrame(rows)
    for col in COLUMNS_ORDER:
        if col not in df.columns:
            df[col] = None
    df = df[COLUMNS_ORDER]
    df.to_csv(output_csv, index=False, encoding="utf-8")
    log.info(
        "Polling CSV written to %s (%d rows, %d columns)",
        output_csv,
        len(df),
        len(df.columns),
    )
