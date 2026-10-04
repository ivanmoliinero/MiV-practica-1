"""
Data loading and preprocessing module for the 2026 US Senate Election Map.

Loads the current Senate composition (100 senators) and 2026 polling data,
mapping each senator to a geographic half-state feature ('<State>_left' or '<State>_right').
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

try:
    import streamlit as st
    cache_data_decorator = st.cache_data
except ImportError:
    def cache_data_decorator(func):
        return func

# Standard categories and corresponding hex colors for the discrete colorscale
COLOR_CATEGORIES: List[str] = [
    "DEM",         # 0: Democrat Blue
    "REP",         # 1: Republican Red
    "IND",         # 2: Independent Purple
    "TOSS_UP",     # 3: Poll Toss-Up Amber
    "NO_DATA",     # 4: No Poll Data Slate
    "SAFE_MUTED",  # 5: Muted background for non-contested seats
]

COLOR_PALETTE: Dict[str, str] = {
    "DEM": "#2563EB",         # Strong Democrat Blue
    "REP": "#DC2626",         # Strong Republican Red
    "IND": "#7C3AED",         # Purple for Independents
    "TOSS_UP": "#F59E0B",     # Amber / Yellow-Orange
    "NO_DATA": "#64748B",     # Slate Gray
    "SAFE_MUTED": "#E2E8F0",  # Light gray-slate
}

CATEGORY_TO_INT: Dict[str, int] = {cat: i for i, cat in enumerate(COLOR_CATEGORIES)}

# Dataset file locations
BASE_DIR = Path(__file__).resolve().parent.parent / "data-fetching" / "results"
COMPOSITION_CSV = BASE_DIR / "senate_current_composition.csv"
POLLS_CSV = BASE_DIR / "senate_2026_polls.csv"

# Standard 2-letter state abbreviations
STATE_TO_ABBREV: Dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
    "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
    "Wisconsin": "WI", "Wyoming": "WY",
}


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
    Compute poll aggregates (leader, margin, DEM %, REP %, count) for a given state.
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

    clean_polls = valid_polls.dropna(
        subset=["porc_republicano_sillon_en_juego", "porc_democrata_sillon_en_juego"],
        how="all",
    )

    # Prefer individual polls if available; fallback to all valid rows
    individual = clean_polls[clean_polls["fuente_encuesta"] != "Average"]
    to_use = (
        individual
        if not individual.empty and individual[
            ["porc_republicano_sillon_en_juego", "porc_democrata_sillon_en_juego"]
        ].notna().any().any()
        else clean_polls
    )

    if not to_use.empty:
        mean_rep = to_use["porc_republicano_sillon_en_juego"].mean()
        mean_dem = to_use["porc_democrata_sillon_en_juego"].mean()
        n_polls = len(to_use)
    else:
        mean_rep = None
        mean_dem = None
        n_polls = 0

    if mean_dem is not None and mean_rep is not None and pd.notna(mean_dem) and pd.notna(mean_rep):
        margin = round(mean_dem - mean_rep, 1)
        if margin > 2.0:
            leader = "DEM"
        elif margin < -2.0:
            leader = "REP"
        else:
            leader = "TOSS_UP"
    elif mean_dem is not None and pd.notna(mean_dem):
        margin = None
        leader = "DEM"
    elif mean_rep is not None and pd.notna(mean_rep):
        margin = None
        leader = "REP"
    else:
        margin = None
        leader = "NO_DATA"

    return {
        "leader": leader,
        "margin": margin,
        "mean_dem": mean_dem,
        "mean_rep": mean_rep,
        "n_polls": n_polls,
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
            margin = poll_data["margin"]
            n_polls = poll_data["n_polls"]
            dem_avg = f"{poll_data['mean_dem']:.1f}%" if poll_data["mean_dem"] is not None and pd.notna(poll_data["mean_dem"]) else "N/A"
            rep_avg = f"{poll_data['mean_rep']:.1f}%" if poll_data["mean_rep"] is not None and pd.notna(poll_data["mean_rep"]) else "N/A"

            if leader == "DEM":
                leader_str = "Democrat Leading"
            elif leader == "REP":
                leader_str = "Republican Leading"
            elif leader == "TOSS_UP":
                leader_str = "Toss-Up Race (≤ ±2 pp)"
            else:
                leader_str = "No Poll Data Available"

            margin_str = f"DEM +{margin:.1f} pp" if (margin is not None and margin > 0) else (
                f"REP +{abs(margin):.1f} pp" if (margin is not None and margin < 0) else (
                    "Tied (0.0 pp)" if margin == 0 else "N/A"
                )
            )

            lines.append(f"<b>📊 2026 Poll Forecast:</b> {leader_str}")
            if leader != "NO_DATA":
                lines.append(f"<b>Poll Margin:</b> {margin_str}")
                lines.append(f"<b>Averages:</b> DEM {dem_avg} | REP {rep_avg}")
                lines.append(f"<b>Polls Analyzed:</b> {n_polls}")
            else:
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

        contested_mask = state_rows["en_juego_2026"].astype(str).str.lower() == "true"
        contested_rows = state_rows[contested_mask]
        stable_rows = state_rows[~contested_mask]

        has_race = len(contested_rows) > 0

        if has_race:
            # 1 seat is safe (left), 1 seat is up for election in 2026 (right)
            row_left = stable_rows.iloc[0]
            row_right = contested_rows.iloc[0]
            left_is_contested = False
            right_is_contested = True
        else:
            # No race in 2026: both seats are safe, sorted deterministically
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

            # Category 1: Composition (incumbent party)
            cat_composition = party

            # Category 2: Combined (Default view: safe seats = party, contested seats = poll result)
            if is_contested and poll_info:
                cat_combined = poll_info["leader"]
            else:
                cat_combined = party

            # Category 3: Polls only (safe seats = muted, contested = poll result)
            if is_contested and poll_info:
                cat_polls_only = poll_info["leader"]
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
                "poll_margin": poll_info["margin"] if (is_contested and poll_info) else None,
                "mean_dem": poll_info["mean_dem"] if (is_contested and poll_info) else None,
                "mean_rep": poll_info["mean_rep"] if (is_contested and poll_info) else None,
                "n_polls": poll_info["n_polls"] if (is_contested and poll_info) else 0,
                "cat_composition": cat_composition,
                "cat_combined": cat_combined,
                "cat_polls_only": cat_polls_only,
                "code_composition": CATEGORY_TO_INT.get(cat_composition, 0),
                "code_combined": CATEGORY_TO_INT.get(cat_combined, 0),
                "code_polls_only": CATEGORY_TO_INT.get(cat_polls_only, 5),
                "tooltip": tooltip,
            })

    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = load_all_senators_data()
    print(f"Loaded {len(df)} senator half-state records.")
    print("Sample feature IDs:", df["feature_id"].head(6).tolist())
