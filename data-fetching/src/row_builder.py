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
    )
except ImportError:
    from config import YEAR, COLUMNS_ORDER
    from utils import (
        clean_text_field,
        clean_pct_series,
        col_matches_candidate,
        find_matching_col,
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
) -> list[dict]:
    """
    Builds structured CSV rows for a given state race, aligning candidate names
    with REP/DEM columns, extracting pollster sources and fieldwork dates,
    and filtering phantom rows where neither candidate has percentages.
    """
    cand1, party1 = meta.get("candidate_1"), meta.get("party_1")
    cand2, party2 = meta.get("candidate_2"), meta.get("party_2")

    if not cand1 and not cand2:
        return [create_fallback_row(state, incumbent_info, meta, "Candidates/nominees not yet identified on Wikipedia")]

    if not poll_tables:
        return [create_fallback_row(state, incumbent_info, meta, "No general election polling data found on page")]

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
    for df in poll_tables:
        rep_col = next((c for c in df.columns if col_matches_candidate(c, rep_name)), None) if rep_name else None
        dem_col = next((c for c in df.columns if col_matches_candidate(c, dem_name)), None) if dem_name else None
        unk_col = find_matching_col(df, ["undecided", "don't know", "dk", "other/undecided", "other"])
        src_col = find_matching_col(df, ["poll source", "source of poll", "pollster", "firm", "surveyor", "source"], exclude=["date"])
        date_col = find_matching_col(df, ["date(s) administered", "dates administered", "date administered", "dates", "date"], exclude=["update"])

        rep_pct = clean_pct_series(df[rep_col]) if rep_col else pd.Series([None] * len(df))
        dem_pct = clean_pct_series(df[dem_col]) if dem_col else pd.Series([None] * len(df))
        unk_pct = clean_pct_series(df[unk_col]) if unk_col else pd.Series([None] * len(df))

        for i in range(len(df)):
            rep_v = rep_pct.iloc[i] if (rep_col and i < len(rep_pct)) else None
            dem_v = dem_pct.iloc[i] if (dem_col and i < len(dem_pct)) else None
            unk_v = unk_pct.iloc[i] if (unk_col and i < len(unk_pct)) else None
            src_v = clean_text_field(df[src_col].iloc[i]) if (src_col and i < len(df)) else None
            date_v = clean_text_field(df[date_col].iloc[i]) if (date_col and i < len(df)) else None

            # Discard phantom rows where neither major party percentage exists
            if pd.isna(rep_v) and pd.isna(dem_v):
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
                "indecision": unk_v if pd.notna(unk_v) else None,
                "error": None,
            })

    if not rows:
        return [create_fallback_row(state, incumbent_info, meta, "Polling tables found but could not extract candidate percentages")]

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
