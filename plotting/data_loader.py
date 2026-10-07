"""
Data loading and preprocessing module for the 2026 US Senate Election Map.

Loads the current Senate composition (100 senators) and 2026 polling data,
mapping each senator to a geographic half-state feature ('<State>_left' or '<State>_right').
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd

from state_centroids import STATE_TO_ABBREV
from state_vep import STATE_VEP

from functools import lru_cache

cache_data_decorator = lru_cache(maxsize=None)

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
    Compute poll aggregates (leader, sub_category, margin, DEM %, REP %, count) for a given state.

    Categorization:
    - DEM lead > 2.0 pp -> 'DEM' (Solid Blue)
    - DEM lead <= 2.0 pp -> 'DEM_LEAN' (Soft Light Blue)
    - REP lead > 2.0 pp -> 'REP' (Solid Red)
    - REP lead <= 2.0 pp -> 'REP_LEAN' (Soft Light Red)
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

    # Require both candidate percentages for genuine head-to-head general election matchups
    clean_polls = valid_polls.dropna(
        subset=["porc_republicano_sillon_en_juego", "porc_democrata_sillon_en_juego"],
        how="any",
    )

    # Prefer individual polls if available; fallback to all valid rows
    individual = clean_polls[clean_polls["fuente_encuesta"] != "Average"]
    to_use = individual if not individual.empty else clean_polls

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
            "mean_dem": mean_dem,
            "mean_rep": mean_rep,
            "n_polls": n_polls,
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
            "mean_dem": None,
            "mean_rep": None,
            "n_polls": len(pred_rows),
            "is_prediction": True,
            "consensus_rating": most_frequent,
        }

    return {
        "leader": "NO_DATA",
        "sub_category": "NO_DATA",
        "margin": None,
        "mean_dem": None,
        "mean_rep": None,
        "n_polls": 0,
        "is_prediction": False,
        "consensus_rating": None,
    }


# Estimated DEM polling percentage derived from the prediction margin proxies used in aggregate_state_polls().
# These are the same fixed values assigned when converting rating strings to numeric scores:
# Safe D / Solid D => margin=+15.0 => ~73% DEM share assuming average 2-party split
# Likely D         => margin=+7.0  => ~62% DEM
# Lean D           => margin=+2.0  => ~51% DEM
# Toss-Up          => margin=0.0   => ~50% each
# Lean R           => margin=-2.0  => ~49% DEM / ~51% REP
# Likely R         => margin=-7.0  => ~38% DEM / ~62% REP
# Safe R / Solid R => margin=-15.0 => ~27% DEM / ~73% REP
_MARGIN_TO_DEM_PCT: dict[float, float] = {
    15.0: 73.0,
    7.0:  62.0,
    2.0:  51.0,
    0.0:  50.0,
   -2.0:  49.0,
   -7.0:  38.0,
  -15.0:  27.0,
}


def compute_voter_weights(state: str, poll_info: Optional[dict]) -> tuple[Optional[float], Optional[float]]:
    """
    Estimate the absolute number of voters supporting each leading candidate:
      dem_weight = VEP(state) * mean_dem_pct / 100
      rep_weight = VEP(state) * mean_rep_pct / 100

    For numeric-poll states:  uses real mean_dem / mean_rep values.
    For prediction-only states: uses a fixed percentage derived from the margin proxy
                                (see _MARGIN_TO_DEM_PCT mapping above).
    Returns (dem_weight, rep_weight) or (None, None) if insufficient data.
    """
    if poll_info is None:
        return None, None

    vep = STATE_VEP.get(state)
    if vep is None:
        return None, None

    if not poll_info.get("is_prediction", False):
        # Real numeric polling: use mean_dem / mean_rep directly
        mean_dem = poll_info.get("mean_dem")
        mean_rep = poll_info.get("mean_rep")
        if mean_dem is None or mean_rep is None or pd.isna(mean_dem) or pd.isna(mean_rep):
            return None, None
        return round(vep * mean_dem / 100), round(vep * mean_rep / 100)
    else:
        # Prediction-only: derive pct from the margin proxy
        margin = poll_info.get("margin")
        if margin is None:
            return None, None
        dem_pct = _MARGIN_TO_DEM_PCT.get(float(margin), 50.0 + float(margin) / 2)
        rep_pct = 100.0 - dem_pct
        return round(vep * dem_pct / 100), round(vep * rep_pct / 100)


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
    dem_weight: Optional[float] = None,
    rep_weight: Optional[float] = None,
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
                dem_avg = f"{poll_data['mean_dem']:.1f}%" if poll_data["mean_dem"] is not None and pd.notna(poll_data["mean_dem"]) else "N/A"
                rep_avg = f"{poll_data['mean_rep']:.1f}%" if poll_data["mean_rep"] is not None and pd.notna(poll_data["mean_rep"]) else "N/A"

                if sub_cat == "DEM":
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

                margin_str = f"DEM +{margin:.1f} pp" if (margin is not None and margin > 0) else (
                    f"REP +{abs(margin):.1f} pp" if (margin is not None and margin < 0) else (
                        "Tied (0.0 pp)" if margin == 0 else "N/A"
                    )
                )

                lines.append(f"<b>📊 2026 Poll Forecast:</b> {forecast_desc}")
                lines.append(f"<b>Poll Margin:</b> {margin_str}")
                lines.append(f"<b>Averages:</b> DEM {dem_avg} | REP {rep_avg}")
                lines.append(f"<b>Polls Analyzed:</b> {n_polls}")
            else:
                lines.append("<b>📊 2026 Poll Forecast:</b> No Poll Data Available")
                lines.append("<i>No general election polls found yet</i>")

        # Append voter weight approximation if available
        if dem_weight is not None and rep_weight is not None:
            is_pred = poll_data.get("is_prediction", False) if poll_data else False
            approx_note = " (estimated from forecast rating)" if is_pred else ""
            lines.append("─────────────────────────────")
            lines.append(f"<b>👥 Voter Weight{approx_note}:</b>")
            lines.append(f"<b>DEM supporters:</b> ~{dem_weight:,.0f}")
            lines.append(f"<b>REP supporters:</b> ~{rep_weight:,.0f}")
            lines.append(f"<i>Based on 2024 VEP × polling %</i>")
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

            # Category 1: Composition (incumbent party)
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

            # Compute voter weights for contested seats only
            if is_contested and poll_info:
                dem_weight, rep_weight = compute_voter_weights(state, poll_info)
            else:
                dem_weight, rep_weight = None, None

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
                dem_weight=dem_weight if is_contested else None,
                rep_weight=rep_weight if is_contested else None,
            )

            # Flip evaluation
            is_flip = False
            flip_type = None
            flip_incoming_party = None
            if is_contested and poll_info and poll_info["leader"] in ["DEM", "REP"]:
                if party == "REP" and poll_info["leader"] == "DEM":
                    is_flip = True
                    flip_type = "REP_TO_DEM"
                    flip_incoming_party = "DEM"
                elif party == "DEM" and poll_info["leader"] == "REP":
                    is_flip = True
                    flip_type = "DEM_TO_REP"
                    flip_incoming_party = "REP"

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
                "dem_voter_weight": dem_weight,
                "rep_voter_weight": rep_weight,
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
    - safe_dem_ind: 34 seats (32 DEM + 2 IND)
    - dem_holds: 9 seats
    - dem_flips: 6 seats (from GOP)
    - unpolled: 5 seats (3 DEM incumbent, 2 REP incumbent)
    - rep_flips: 1 seat (from DEM)
    - rep_holds: 14 seats
    - safe_rep: 31 seats
    - projected_dem_total: 52 seats
    - projected_rep_total: 48 seats
    - net_dem_gain: 5 seats
    """
    safe_seats = df[~df["is_contested_2026"]]
    contested_seats = df[df["is_contested_2026"]]

    safe_dem_ind = len(safe_seats[safe_seats["party"].isin(["DEM", "IND"])])
    safe_rep = len(safe_seats[safe_seats["party"] == "REP"])

    dem_holds = len(contested_seats[(contested_seats["party"] == "DEM") & (contested_seats["poll_leader"] == "DEM")])
    rep_holds = len(contested_seats[(contested_seats["party"] == "REP") & (contested_seats["poll_leader"] == "REP")])

    dem_flips = len(contested_seats[contested_seats["flip_type"] == "REP_TO_DEM"])
    rep_flips = len(contested_seats[contested_seats["flip_type"] == "DEM_TO_REP"])

    unpolled = len(contested_seats[contested_seats["poll_leader"] == "NO_DATA"])
    unpolled_dem = len(contested_seats[(contested_seats["poll_leader"] == "NO_DATA") & (contested_seats["party"] == "DEM")])
    unpolled_rep = len(contested_seats[(contested_seats["poll_leader"] == "NO_DATA") & (contested_seats["party"] == "REP")])

    projected_dem = safe_dem_ind + dem_holds + dem_flips + unpolled_dem
    projected_rep = safe_rep + rep_holds + rep_flips + unpolled_rep

    return {
        "safe_dem_ind": safe_dem_ind,
        "dem_holds": dem_holds,
        "dem_flips": dem_flips,
        "unpolled": unpolled,
        "unpolled_dem": unpolled_dem,
        "unpolled_rep": unpolled_rep,
        "rep_flips": rep_flips,
        "rep_holds": rep_holds,
        "safe_rep": safe_rep,
        "projected_dem_total": projected_dem,
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

