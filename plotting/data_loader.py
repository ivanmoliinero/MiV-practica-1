"""
Data loading and preprocessing module for the 2026 US Senate Election Map.

Loads the current Senate composition (100 senators) and 2026 polling data,
mapping each senator to a geographic half-state feature ('<State>_left' or '<State>_right').
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math
import re
import pandas as pd

from state_centroids import STATE_TO_ABBREV

from functools import lru_cache

cache_data_decorator = lru_cache(maxsize=None)

# Known poll aggregation sources
AGGREGATORS = [
    "270towin",
    "silver bulletin",
    "fiftyplusone",
    "realclearpolitics",
    "decision desk hq",
    "the hill",
    "race to the wh",
    "fivethirtyeight",
    "the texas tribune",
]

MONTHS_LIST = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
]
MONTH_MAP = {m: i for i, m in enumerate(MONTHS_LIST, 1)}

# Half-life for exponential temporal decay (28 days)
HALF_LIFE_DAYS = 28.0
DECAY_RATE_K = math.log(2.0) / HALF_LIFE_DAYS  # ~0.024755


def parse_poll_end_date(d_str: str | None) -> Optional[datetime]:
    """Extracts the fieldwork end date from standard polling date range strings."""
    if not isinstance(d_str, str) or not d_str.strip():
        return None
    s = d_str.strip().replace("–", "-").replace("—", "-")
    # 'through <Month> <day>, <year>'
    m = re.search(r"through\s+([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", s, re.I)
    if m and m.group(1).lower() in MONTH_MAP:
        return datetime(int(m.group(3)), MONTH_MAP[m.group(1).lower()], int(m.group(2)))
    # '<Month1> <day1> - <Month2> <day2>, <year>'
    m = re.search(r"([A-Za-z]+)\s+\d{1,2}\s*-\s*([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", s)
    if m and m.group(2).lower() in MONTH_MAP:
        return datetime(int(m.group(4)), MONTH_MAP[m.group(2).lower()], int(m.group(3)))
    # '<Month> <day1> - <day2>, <year>'
    m = re.search(r"([A-Za-z]+)\s+\d{1,2}\s*-\s*(\d{1,2}),?\s*(\d{4})", s)
    if m and m.group(1).lower() in MONTH_MAP:
        return datetime(int(m.group(3)), MONTH_MAP[m.group(1).lower()], int(m.group(2)))
    # '<Month> <day>, <year>'
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", s)
    if m and m.group(1).lower() in MONTH_MAP:
        return datetime(int(m.group(3)), MONTH_MAP[m.group(1).lower()], int(m.group(2)))
    # '<Month> <year>'
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", s)
    if m and m.group(1).lower() in MONTH_MAP:
        return datetime(int(m.group(2)), MONTH_MAP[m.group(1).lower()], 15)
    return None

# Standard categories and corresponding hex colors for the discrete colorscale
COLOR_CATEGORIES: List[str] = [
    "DEM",         # 0: Solid Democrat Blue
    "DEM_LEAN",    # 1: Soft Light Democrat Blue (Toss-Up <= 2.0 pp DEM lead)
    "REP",         # 2: Solid Republican Red
    "REP_LEAN",    # 3: Soft Light Republican Red (Toss-Up <= 2.0 pp REP lead)
    "TIE",         # 4: Soft Violet for exact ties (0.0 pp)
    "IND",         # 5: Golden Yellow for Independents
    "NO_DATA",     # 6: Slate Gray for contested races with no poll data yet
    "SAFE_MUTED",  # 7: Light Gray for safe seats in polls-only view
]

COLOR_PALETTE: Dict[str, str] = {
    "DEM": "#2563EB",         # Solid Democrat Blue
    "DEM_LEAN": "#93C5FD",    # Soft Light Democrat Blue (Lean / Toss-Up DEM <= 2.0 pp)
    "REP": "#DC2626",         # Solid Republican Red
    "REP_LEAN": "#FCA5A5",    # Soft Light Republican Red (Lean / Toss-Up REP <= 2.0 pp)
    "TIE": "#C084FC",         # Soft Violet for exact ties
    "IND": "#EAB308",         # Golden Yellow for Independents
    "NO_DATA": "#64748B",     # Slate Gray
    "SAFE_MUTED": "#1E293B",  # Dark slate neutral (unpainted safe seats in isolated view)
}

CATEGORY_TO_INT: Dict[str, int] = {cat: i for i, cat in enumerate(COLOR_CATEGORIES)}

# Dataset file locations
BASE_DIR = Path(__file__).resolve().parent.parent / "data-fetching" / "results"
COMPOSITION_CSV = BASE_DIR / "senate_current_composition.csv"
POLLS_CSV = BASE_DIR / "senate_2026_polls.csv"


def load_composition_csv(path: Optional[Path] = None) -> pd.DataFrame:
    """Load the current US Senate composition dataset (100 senators)."""
    target = path or COMPOSITION_CSV
    if not target.exists():
        raise FileNotFoundError(f"Composition dataset not found at: {target}")
    return pd.read_csv(target)


def load_polls_csv(path: Optional[Path] = None) -> pd.DataFrame:
    """Load the granular 2026 US Senate polling dataset."""
    target = path or POLLS_CSV
    if not target.exists():
        raise FileNotFoundError(f"Polling dataset not found at: {target}")
    return pd.read_csv(target)


def aggregate_state_polls(polls_df: pd.DataFrame, state: str) -> dict:
    """
    Compute poll aggregates (leader, sub_category, margin, DEM/REP/IND %, count) for a given state.

    Categorization:
    - DEM lead > 2.0 pp -> 'DEM' (Solid Blue)
    - DEM lead <= 2.0 pp -> 'DEM_LEAN' (Soft Light Blue)
    - REP lead > 2.0 pp -> 'REP' (Solid Red)
    - REP lead <= 2.0 pp -> 'REP_LEAN' (Soft Light Red)
    - IND lead -> 'IND' (Golden Yellow)
    - Exact 0.0 pp tie -> 'TIE' (Soft Violet)
    - No polling numbers -> 'NO_DATA' (Slate Gray)
    """
    state_polls = polls_df[polls_df["estado"] == state].copy()
    valid_polls = state_polls[
        state_polls["error"].isna() | (state_polls["error"].astype(str).str.strip() == "")
    ].copy()

    valid_polls["porc_republicano_sillon_en_juego"] = pd.to_numeric(
        valid_polls["porc_republicano_sillon_en_juego"], errors="coerce"
    )
    valid_polls["porc_democrata_sillon_en_juego"] = pd.to_numeric(
        valid_polls["porc_democrata_sillon_en_juego"], errors="coerce"
    )
    valid_polls["indecision"] = pd.to_numeric(
        valid_polls["indecision"], errors="coerce"
    )

    # Detect whether the main opponent running against the Republican candidate is DEM or IND
    cand_parties = set()
    if "partido_candidato_actual_1" in state_polls.columns:
        cand_parties.update(state_polls["partido_candidato_actual_1"].dropna().unique())
    if "partido_candidato_actual_2" in state_polls.columns:
        cand_parties.update(state_polls["partido_candidato_actual_2"].dropna().unique())

    has_ind_candidate = "IND" in cand_parties
    opponent_party = "IND" if has_ind_candidate else "DEM"

    # Require both candidate percentages for genuine head-to-head general election matchups
    clean_polls = valid_polls.dropna(
        subset=["porc_republicano_sillon_en_juego", "porc_democrata_sillon_en_juego"],
        how="any",
    )

    # Filter out any aggregate average summary rows
    to_use = clean_polls[~clean_polls["fuente_encuesta"].astype(str).str.strip().str.lower().isin(["average", "mean"])]

    # Hierarchy Pillar A & B:
    # 1. If aggregator polls exist in the state, use exclusively aggregators (unweighted mean).
    # 2. Otherwise, use individual polls with exponential time weighting (half-life 28d) and partisan bias shrinkage.
    is_agg_mask = pd.Series([False] * len(to_use), index=to_use.index)
    if "fuente_tipo" in to_use.columns and to_use["fuente_tipo"].notna().any():
        is_agg_mask = to_use["fuente_tipo"].astype(str).str.strip().str.lower() == "aggregator"
    else:
        is_agg_mask = to_use["fuente_encuesta"].astype(str).str.lower().apply(
            lambda s: any(agg in s for agg in AGGREGATORS)
        )

    agg_polls = to_use[is_agg_mask]

    if not agg_polls.empty:
        # Level 1: Use exclusively aggregators
        mean_rep = float(agg_polls["porc_republicano_sillon_en_juego"].mean())
        mean_opp = float(agg_polls["porc_democrata_sillon_en_juego"].mean())
        mean_other = (
            float(agg_polls["indecision"].mean())
            if "indecision" in agg_polls.columns and agg_polls["indecision"].notna().any()
            else None
        )
        n_polls = len(agg_polls)
        method_label = f"{n_polls} aggregator{'s' if n_polls > 1 else ''}"
    elif not to_use.empty:
        # Level 2 & 3: Individual polls with temporal decay and partisan shrinkage
        parsed_dates = to_use["fecha_encuesta"].apply(parse_poll_end_date)
        valid_dates = [d for d in parsed_dates if d is not None]
        ref_date = max(valid_dates) if valid_dates else datetime(2026, 10, 10)

        weights = []
        for idx, row in to_use.iterrows():
            d = parsed_dates.loc[idx]
            days_ago = max(0, (ref_date - d).days) if d is not None else 60
            tw = math.exp(-DECAY_RATE_K * days_ago)

            # Partisan bias shrinkage (50% weight for declared partisan sponsor: (D), (R), (I))
            st = str(row.get("fuente_tipo", "")).strip().lower()
            if st in ("individual_dem", "individual_rep", "individual_ind"):
                bw = 0.5
            else:
                bw = 1.0

            weights.append(tw * bw)

        weight_sum = sum(weights)
        if weight_sum > 0:
            mean_rep = float(sum(w * r for w, r in zip(weights, to_use["porc_republicano_sillon_en_juego"])) / weight_sum)
            mean_opp = float(sum(w * d for w, d in zip(weights, to_use["porc_democrata_sillon_en_juego"])) / weight_sum)
            valid_ind_mask = to_use["indecision"].notna() if "indecision" in to_use.columns else pd.Series([False] * len(to_use))
            if valid_ind_mask.any():
                w_ind_sum = sum(w for w, v in zip(weights, valid_ind_mask) if v)
                mean_other = float(sum(w * o for w, o, v in zip(weights, to_use["indecision"], valid_ind_mask) if v) / w_ind_sum) if w_ind_sum > 0 else None
            else:
                mean_other = None
        else:
            mean_rep = float(to_use["porc_republicano_sillon_en_juego"].mean())
            mean_opp = float(to_use["porc_democrata_sillon_en_juego"].mean())
            mean_other = float(to_use["indecision"].mean()) if "indecision" in to_use.columns else None

        n_polls = len(to_use)
        method_label = f"{n_polls} poll{'s' if n_polls > 1 else ''} (time-weighted)"
    else:
        mean_rep = None
        mean_opp = None
        mean_other = None
        n_polls = 0
        method_label = "0 polls"

    if opponent_party == "IND":
        mean_dem = None
        mean_ind = mean_opp
    else:
        mean_dem = mean_opp
        mean_ind = None

    if mean_opp is not None and mean_rep is not None and pd.notna(mean_opp) and pd.notna(mean_rep):
        # Check if other/undecided has a higher polling average than both major candidates
        has_other_lead = (
            mean_other is not None
            and pd.notna(mean_other)
            and mean_other > mean_opp
            and mean_other > mean_rep
        )

        if has_other_lead:
            leader = "IND"
            sub_category = "IND"
            margin = round(mean_other - max(mean_opp, mean_rep), 1)
        elif opponent_party == "IND":
            margin = round(mean_ind - mean_rep, 1)
            if margin > 2.0:
                leader = "IND"
                sub_category = "IND"
            elif 0 < margin <= 2.0:
                leader = "IND"
                sub_category = "IND"
            elif margin < -2.0:
                leader = "REP"
                sub_category = "REP"
            elif -2.0 <= margin < 0:
                leader = "REP"
                sub_category = "REP_LEAN"
            else:
                leader = "TIE"
                sub_category = "TIE"
        else:
            margin = round(mean_dem - mean_rep, 1)
            if margin > 2.0:
                leader = "DEM"
                sub_category = "DEM"
            elif 0 < margin <= 2.0:
                leader = "DEM"
                sub_category = "DEM_LEAN"
            elif margin < -2.0:
                leader = "REP"
                sub_category = "REP"
            elif -2.0 <= margin < 0:
                leader = "REP"
                sub_category = "REP_LEAN"
            else:
                leader = "TIE"
                sub_category = "TIE"

        return {
            "leader": leader,
            "sub_category": sub_category,
            "margin": margin,
            "opponent_party": opponent_party,
            "mean_dem": mean_dem,
            "mean_rep": mean_rep,
            "mean_ind": mean_ind,
            "mean_other": mean_other,
            "n_polls": n_polls,
            "method_label": method_label,
            "is_prediction": False,
            "consensus_rating": None,
        }

    # If no head-to-head numerical polls, evaluate forecaster predictions consensus
    pred_rows = state_polls[
        state_polls["error"].astype(str).str.startswith("Prediction:")
    ].copy()

    if not pred_rows.empty:
        raw_ratings = [
            str(err).replace("Prediction:", "").strip()
            for err in pred_rows["error"]
            if pd.notna(err)
        ]

        score = 0
        counts: dict[str, int] = {}
        for r in raw_ratings:
            counts[r] = counts.get(r, 0) + 1
            low = r.lower()
            if "solid d" in low or "safe d" in low:
                score += 3
            elif "likely d" in low:
                score += 2
            elif "lean d" in low or "tilt d" in low:
                score += 1
            elif "solid r" in low or "safe r" in low:
                score -= 3
            elif "likely r" in low:
                score -= 2
            elif "lean r" in low or "tilt r" in low:
                score -= 1

        most_frequent = max(counts, key=counts.get) if counts else "Safe"

        if score >= 4:
            leader = "DEM"
            sub_category = "DEM"
            margin = 15.0
        elif 2 <= score < 4:
            leader = "DEM"
            sub_category = "DEM"
            margin = 7.0
        elif 1 <= score < 2:
            leader = "DEM"
            sub_category = "DEM_LEAN"
            margin = 2.0
        elif -1 < score < 1:
            leader = "TIE"
            sub_category = "TIE"
            margin = 0.0
        elif -2 < score <= -1:
            leader = "REP"
            sub_category = "REP_LEAN"
            margin = -2.0
        elif -4 < score <= -2:
            leader = "REP"
            sub_category = "REP"
            margin = -7.0
        else:
            leader = "REP"
            sub_category = "REP"
            margin = -15.0

        return {
            "leader": leader,
            "sub_category": sub_category,
            "margin": margin,
            "opponent_party": opponent_party,
            "mean_dem": None,
            "mean_rep": None,
            "mean_ind": None,
            "mean_other": None,
            "n_polls": len(pred_rows),
            "is_prediction": True,
            "consensus_rating": most_frequent,
        }

    return {
        "leader": "NO_DATA",
        "sub_category": "NO_DATA",
        "margin": None,
        "opponent_party": opponent_party,
        "mean_dem": None,
        "mean_rep": None,
        "mean_ind": None,
        "mean_other": None,
        "n_polls": 0,
        "is_prediction": False,
        "consensus_rating": None,
    }


def _build_tooltip(
    state: str,
    side_label: str,
    senator: str,
    party: str,
    seat_class: str,
    asumio_cargo: str,
    is_contested: bool,
    election_type: str,
    poll_data: Optional[dict] = None,
) -> str:
    """Build a detailed HTML tooltip for a specific half-state polygon."""
    party_full = {"DEM": "Democrat", "REP": "Republican", "IND": "Independent"}.get(party, party)
    lines = [
        f"<b>🏛️ {state} ({side_label})</b>",
        "─────────────────────────────",
        f"<b>Senator:</b> {senator} ({party_full})",
        f"<b>Seat Class:</b> {seat_class}",
        f"<b>In office since:</b> {asumio_cargo}",
    ]

    if is_contested:
        lines.append("─────────────────────────────")
        lines.append(f"⚡ <b>2026 Senate Race:</b> {election_type}")
        if poll_data:
            leader = poll_data["leader"]
            sub_cat = poll_data["sub_category"]
            margin = poll_data["margin"]
            n_polls = poll_data["n_polls"]
            is_pred = poll_data.get("is_prediction", False)

            if is_pred:
                consensus_rating = poll_data.get("consensus_rating", "Safe")
                lines.append(f"<b>📊 Race Forecast:</b> Forecaster Consensus ({consensus_rating})")
                lines.append(f"<b>Forecasters Analyzed:</b> {n_polls} ratings (Cook, Sabato, Inside Elections, etc.)")
                lines.append("<i>Safe seat — Forecaster consensus rating used in place of direct polling</i>")
            elif leader != "NO_DATA":
                rep_avg = f"{poll_data['mean_rep']:.1f}%" if poll_data.get("mean_rep") is not None and pd.notna(poll_data["mean_rep"]) else "N/A"
                dem_avg = f"{poll_data['mean_dem']:.1f}%" if poll_data.get("mean_dem") is not None and pd.notna(poll_data["mean_dem"]) else None
                ind_avg = f"{poll_data['mean_ind']:.1f}%" if poll_data.get("mean_ind") is not None and pd.notna(poll_data["mean_ind"]) else None
                other_avg = f"{poll_data['mean_other']:.1f}%" if poll_data.get("mean_other") is not None and pd.notna(poll_data["mean_other"]) else "N/A"
                opponent_party = poll_data.get("opponent_party", "DEM")

                if sub_cat == "IND":
                    forecast_desc = "Independent Leading (> 2 pp)" if (margin is not None and margin > 2.0) else "Toss-Up / Slight Independent Lead (≤ 2 pp)"
                elif sub_cat == "DEM":
                    forecast_desc = "Democrat Leading (> 2 pp)"
                elif sub_cat == "DEM_LEAN":
                    forecast_desc = "Toss-Up / Slight Democrat Lead (≤ 2 pp)"
                elif sub_cat == "REP":
                    forecast_desc = "Republican Leading (> 2 pp)"
                elif sub_cat == "REP_LEAN":
                    forecast_desc = "Toss-Up / Slight Republican Lead (≤ 2 pp)"
                elif sub_cat == "TIE":
                    forecast_desc = "Dead Heat / Exactly Tied (0.0 pp)"
                else:
                    forecast_desc = "No Poll Data Available"

                if opponent_party == "IND":
                    if margin is not None and margin > 0:
                        margin_str = f"IND +{margin:.1f} pp"
                    elif margin is not None and margin < 0:
                        margin_str = f"REP +{abs(margin):.1f} pp"
                    elif margin == 0:
                        margin_str = "Tied (0.0 pp)"
                    else:
                        margin_str = "N/A"
                    averages_str = f"REP {rep_avg} | IND {ind_avg} | Other/Undecided {other_avg}"
                else:
                    if margin is not None and margin > 0:
                        margin_str = f"DEM +{margin:.1f} pp"
                    elif margin is not None and margin < 0:
                        margin_str = f"REP +{abs(margin):.1f} pp"
                    elif margin == 0:
                        margin_str = "Tied (0.0 pp)"
                    else:
                        margin_str = "N/A"
                    averages_str = f"DEM {dem_avg} | REP {rep_avg} | Other/Ind {other_avg}"

                lines.append(f"<b>📊 2026 Poll Forecast:</b> {forecast_desc}")
                lines.append(f"<b>Poll Margin:</b> {margin_str}")
                lines.append(f"<b>Averages:</b> {averages_str}")
                lines.append(f"<b>Polls Analyzed:</b> {poll_data.get('method_label', n_polls)}")
            else:
                lines.append("<b>📊 2026 Poll Forecast:</b> No Poll Data Available")
                lines.append("<i>No general election polls found yet</i>")
    else:
        lines.append("─────────────────────────────")
        lines.append("🔒 <b>Status:</b> Safe Seat (No election in 2026)")

    return "<br>".join(lines)


@cache_data_decorator
def load_all_senators_data() -> pd.DataFrame:
    """
    Construct the complete 100-row DataFrame (1 row per half-state polygon).

    Each state is split into:
    - '<State>_left': West half (safe senator if contested state; senator 1 if no race).
    - '<State>_right': East half (contested senator if contested state; senator 2 if no race).
    """
    comp_df = load_composition_csv()
    polls_df = load_polls_csv()

    rows = []
    unique_states = sorted(comp_df["estado"].unique())

    for state in unique_states:
        abbrev = STATE_TO_ABBREV.get(state, "")
        state_rows = comp_df[comp_df["estado"] == state].copy()

        # Mark state parts with elections in 2026.
        contested_mask = state_rows["en_juego_2026"].astype(str).str.lower() == "true"
        contested_rows = state_rows[contested_mask]
        stable_rows = state_rows[~contested_mask]

        has_race = len(contested_rows) > 0

        if has_race:
            row_left = stable_rows.iloc[0]
            row_right = contested_rows.iloc[0]
            left_is_contested = False
            right_is_contested = True
        else:
            sorted_rows = state_rows.sort_values(by="senador")
            row_left = sorted_rows.iloc[0]
            row_right = sorted_rows.iloc[1]
            left_is_contested = False
            right_is_contested = False

        poll_info = aggregate_state_polls(polls_df, state) if has_race else None

        for side, row_data, is_contested in [
            ("left", row_left, left_is_contested),
            ("right", row_right, right_is_contested),
        ]:
            senator_name = str(row_data["senador"])
            party = str(row_data["partido"])
            seat_class = str(row_data["clase"])
            election_type = str(row_data["tipo_eleccion_2026"])
            asumio_cargo = str(row_data["asumio_cargo"])

            feature_id = f"{state}_{side}"
            side_label = "West Half — Safe" if not is_contested else "East Half — 2026 Race"

            # Category 1: Actual party (incumbent)
            cat_composition = party

            # Category 2: Combined (Default view: safe seats = party, contested seats = poll result)
            if is_contested and poll_info:
                cat_combined = poll_info["sub_category"]
            else:
                cat_combined = party

            # Category 3: Polls only (safe seats = muted, contested = poll result)
            if is_contested and poll_info:
                cat_polls_only = poll_info["sub_category"]
            else:
                cat_polls_only = "SAFE_MUTED"

            tooltip = _build_tooltip(
                state=state,
                side_label=side_label,
                senator=senator_name,
                party=party,
                seat_class=seat_class,
                asumio_cargo=asumio_cargo,
                is_contested=is_contested,
                election_type=election_type,
                poll_data=poll_info if is_contested else None,
            )

            # Flip evaluation
            is_flip = False
            flip_type = None
            flip_incoming_party = None
            if is_contested and poll_info and poll_info["leader"] in ["DEM", "REP", "IND"]: # safe check
                if party != poll_info["leader"]: # check flip
                    is_flip = True
                    flip_type = f"{party}_TO_{poll_info['leader']}"
                    flip_incoming_party = poll_info["leader"]

            rows.append({
                "feature_id": feature_id,
                "state": state,
                "abbrev": abbrev,
                "side": side,
                "senator_name": senator_name,
                "party": party,
                "seat_class": seat_class,
                "is_contested_2026": is_contested,
                "election_type_2026": election_type,
                "asumio_cargo": asumio_cargo,
                "poll_leader": poll_info["leader"] if (is_contested and poll_info) else None,
                "poll_sub_category": poll_info["sub_category"] if (is_contested and poll_info) else None,
                "poll_margin": poll_info["margin"] if (is_contested and poll_info) else None,
                "mean_dem": poll_info["mean_dem"] if (is_contested and poll_info) else None,
                "mean_rep": poll_info["mean_rep"] if (is_contested and poll_info) else None,
                "mean_ind": poll_info.get("mean_ind") if (is_contested and poll_info) else None,
                "mean_other": poll_info["mean_other"] if (is_contested and poll_info) else None,
                "n_polls": poll_info["n_polls"] if (is_contested and poll_info) else 0,
                "cat_composition": cat_composition,
                "cat_combined": cat_combined,
                "cat_polls_only": cat_polls_only,
                "code_composition": CATEGORY_TO_INT.get(cat_composition, 0),
                "code_combined": CATEGORY_TO_INT.get(cat_combined, 0),
                "code_polls_only": CATEGORY_TO_INT.get(cat_polls_only, 7),
                "is_flip": is_flip,
                "flip_type": flip_type,
                "flip_incoming_party": flip_incoming_party,
                "tooltip": tooltip,
            })

    return pd.DataFrame(rows)


def get_flip_records(df: pd.DataFrame) -> List[dict]:
    """Return structured records for the 7 battleground flip seats."""
    flips_df = df[df["is_flip"]].copy()
    flips_df["abs_margin"] = flips_df["poll_margin"].abs()
    flips_df = flips_df.sort_values(by=["flip_incoming_party", "abs_margin"], ascending=[True, False])
    return flips_df.to_dict(orient="records")


def get_balance_of_power_summary(df: pd.DataFrame) -> dict:
    """
    Compute 100-seat balance of power summary metrics for the Majority Bar.

    Returns breakdown across:
    - safe_dem: 32 seats
    - safe_ind: 2 seats (Angus King in ME, Bernie Sanders in VT)
    - safe_rep: 31 seats
    - dem_holds: seats
    - dem_flips: seats (from GOP)
    - ind_holds: seats
    - ind_flips: seats
    - unpolled: seats (unpolled contested seats)
    - unpolled_dem: seats
    - unpolled_rep: seats
    - unpolled_ind: seats
    - rep_flips: seats (from DEM or IND)
    - rep_holds: seats
    - projected_dem_total: DEM caucus total
    - projected_ind_total: IND total
    - projected_rep_total: REP total
    - net_dem_gain: dem_flips - rep_flips
    """
    safe_seats = df[~df["is_contested_2026"]]
    contested_seats = df[df["is_contested_2026"]]

    safe_dem = len(safe_seats[safe_seats["party"] == "DEM"])
    safe_ind = len(safe_seats[safe_seats["party"] == "IND"])
    safe_rep = len(safe_seats[safe_seats["party"] == "REP"])

    dem_holds = len(contested_seats[(contested_seats["party"] == "DEM") & (contested_seats["poll_leader"] == "DEM")])
    rep_holds = len(contested_seats[(contested_seats["party"] == "REP") & (contested_seats["poll_leader"] == "REP")])
    ind_holds = len(contested_seats[(contested_seats["party"] == "IND") & (contested_seats["poll_leader"] == "IND")])

    dem_flips = len(contested_seats[contested_seats["flip_type"] == "REP_TO_DEM"])
    rep_flips = len(contested_seats[contested_seats["flip_type"] == "DEM_TO_REP"])
    ind_flips = len(contested_seats[contested_seats["flip_incoming_party"] == "IND"])

    unpolled_dem = len(contested_seats[(contested_seats["poll_leader"] == "NO_DATA") & (contested_seats["party"] == "DEM")])
    unpolled_rep = len(contested_seats[(contested_seats["poll_leader"] == "NO_DATA") & (contested_seats["party"] == "REP")])
    unpolled_ind = len(contested_seats[(contested_seats["poll_leader"] == "NO_DATA") & (contested_seats["party"] == "IND")])
    unpolled = unpolled_dem + unpolled_rep + unpolled_ind

    projected_dem = safe_dem + dem_holds + dem_flips + unpolled_dem
    projected_ind = safe_ind + ind_holds + ind_flips + unpolled_ind
    projected_rep = safe_rep + rep_holds + rep_flips + unpolled_rep

    return {
        "safe_dem": safe_dem,
        "safe_ind": safe_ind,
        "safe_rep": safe_rep,
        "safe_dem_ind": safe_dem + safe_ind,
        "dem_holds": dem_holds,
        "dem_flips": dem_flips,
        "ind_holds": ind_holds,
        "ind_flips": ind_flips,
        "unpolled": unpolled,
        "unpolled_dem": unpolled_dem,
        "unpolled_rep": unpolled_rep,
        "unpolled_ind": unpolled_ind,
        "rep_flips": rep_flips,
        "rep_holds": rep_holds,
        "projected_dem_total": projected_dem,
        "projected_ind_total": projected_ind,
        "projected_rep_total": projected_rep,
        "net_dem_gain": dem_flips - rep_flips,
    }


if __name__ == "__main__":
    df = load_all_senators_data()
    print(f"Loaded {len(df)} senator half-state records.")
    summary = get_balance_of_power_summary(df)
    print("Balance of power summary:", summary)
    flips = get_flip_records(df)
    print(f"Flips ({len(flips)}):", [(f['state'], f['party'], '->', f['poll_leader'], f['poll_margin']) for f in flips])

