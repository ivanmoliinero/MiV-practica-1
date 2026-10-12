"""
Voter weight heatmap generation module for the 2026 US Senate Election Map.

Computes estimated supporter voter weights (VEP × Polling Percentage) for
contested 2026 Senate races, continuous diverging color scales (REP red to DEM blue),
rich HTML tooltips for both split-halves and 50-state choropleths, and legend markup.
"""

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from state_vep import STATE_VEP
except ImportError:
    from .state_vep import STATE_VEP

# Continuous diverging color scale: Deep Republican Red -> Neutral Slate -> Deep Democrat Blue
HEATMAP_COLORSCALE = [
    [0.0, "#7F1D1D"],
    [0.20, "#991B1B"],
    [0.35, "#DC2626"],
    [0.45, "#FCA5A5"],
    [0.488, "#FEE2E2"],
    [0.495, "#1E293B"],
    [0.505, "#1E293B"],
    [0.512, "#DBEAFE"],
    [0.55, "#93C5FD"],
    [0.65, "#3B82F6"],
    [0.80, "#2563EB"],
    [1.0, "#1E3A8A"],
]


def _generate_state_heatmap_tooltip(
    state_name: str,
    cont_row: Optional[pd.Series],
    vep_val: int,
) -> Tuple[float, str]:
    """
    Calculate signed voter weight and construct rich HTML tooltip for a given state.

    Positive weight indicates Democratic lead; negative indicates Republican lead.
    Returns a tuple of (signed_weight, tooltip_html).
    """
    if cont_row is not None:
        leader = cont_row.get("poll_leader")
        dem_w = cont_row.get("dem_voter_weight")
        rep_w = cont_row.get("rep_voter_weight")
        senator_name = cont_row.get("senator_name", "")
        party_name = cont_row.get("party", "")

        if dem_w and leader == "DEM":
            w = float(dem_w)
            pct = (w / vep_val * 100.0) if vep_val else 0.0
            margin = cont_row.get("poll_margin")
            margin_str = f"DEM +{margin:.1f} pp" if margin is not None else "Projected DEM Lead"
            tip_html = (
                f"<b>🏛️ {state_name} — 2026 Voter Weight</b><br>"
                f"─────────────────────────────<br>"
                f"<b>Projected Winner:</b> Democrat ({margin_str})<br>"
                f"<b>👥 Estimated Supporters:</b> ~{int(w):,d} voters<br>"
                f"<b>State Eligible Population (VEP):</b> {vep_val:,d}<br>"
                f"<b>Projected Vote Share:</b> {pct:.1f}%<br>"
                f"<b>Contested Seat:</b> {senator_name} ({party_name})<br>"
                f"─────────────────────────────<br>"
                f"<i>Formula: 2024 VEP (UF Election Lab) × Polling %</i>"
            )
            return w, tip_html
        elif rep_w and leader == "REP":
            w = float(rep_w)
            pct = (w / vep_val * 100.0) if vep_val else 0.0
            margin = cont_row.get("poll_margin")
            margin_str = f"REP +{abs(margin):.1f} pp" if margin is not None else "Projected REP Lead"
            tip_html = (
                f"<b>🏛️ {state_name} — 2026 Voter Weight</b><br>"
                f"─────────────────────────────<br>"
                f"<b>Projected Winner:</b> Republican ({margin_str})<br>"
                f"<b>👥 Estimated Supporters:</b> ~{int(w):,d} voters<br>"
                f"<b>State Eligible Population (VEP):</b> {vep_val:,d}<br>"
                f"<b>Projected Vote Share:</b> {pct:.1f}%<br>"
                f"<b>Contested Seat:</b> {senator_name} ({party_name})<br>"
                f"─────────────────────────────<br>"
                f"<i>Formula: 2024 VEP (UF Election Lab) × Polling %</i>"
            )
            return -w, tip_html

    # Safe state without 2026 Senate election
    tip_html = (
        f"<b>🏛️ {state_name}</b><br>"
        f"─────────────────────────────<br>"
        f"🔒 <b>Safe State:</b> No Senate election in 2026"
    )
    return 0.0, tip_html


def _generate_heatmap_legend_html(max_voter_weight: float) -> str:
    """Construct HTML markup for the continuous voter-weight colorbar in the legend."""
    max_lbl = f"{max_voter_weight / 1_000_000:.1f}M"
    mid2_lbl = f"{round(max_voter_weight * 0.64024 / 1_000_000):.0f}M"
    mid1_lbl = f"{round(max_voter_weight * 0.32012 / 1_000_000):.0f}M"

    return f"""
          <div class="heatmap-compact-row">
            <div class="heatmap-bar-container">
              <div class="heatmap-continuous-bar"></div>
              <div class="heatmap-ticks-track">
                <div class="heatmap-tick" style="left: 0%;">
                  <span class="tick-val">{max_lbl}</span>
                </div>
                <div class="heatmap-tick" style="left: 18%;">
                  <span class="tick-val">{mid2_lbl}</span>
                </div>
                <div class="heatmap-tick" style="left: 34%;">
                  <span class="tick-val">{mid1_lbl}</span>
                </div>
                <div class="heatmap-tick tick-center" style="left: 50%;">
                  <span class="tick-val tick-val-center">0</span>
                </div>
                <div class="heatmap-tick" style="left: 66%;">
                  <span class="tick-val">{mid1_lbl}</span>
                </div>
                <div class="heatmap-tick" style="left: 82%;">
                  <span class="tick-val">{mid2_lbl}</span>
                </div>
                <div class="heatmap-tick" style="left: 100%;">
                  <span class="tick-val">{max_lbl}</span>
                </div>
              </div>
            </div>
            <div class="heatmap-subtext-formula">
              Formula: 2024 VEP (UF Election Lab) × Polling %
            </div>
          </div>
    """


def generate_heatmap_data(
    df: pd.DataFrame,
    state_names: List[str],
) -> Dict[str, Any]:
    """
    Generate all voter-weight heatmap metrics, arrays, tooltips, and legend assets.

    Parameters
    ----------
    df : pd.DataFrame
        The complete 100-senator dataset with polling calculations.
    state_names : List[str]
        List of 50 state names matching outlines GeoJSON features.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing:
        - heatmap_z: List[float] for the 100 split halves
        - heatmap_tooltips: List[str] for the 100 split halves
        - heatmap_state_z: List[float] for the 50 whole states
        - heatmap_state_tooltips: List[str] for the 50 whole states
        - heatmap_colorscale: List[List[Any]] continuous diverging scale
        - heatmap_zmin: int
        - heatmap_zmax: int
        - legend_colors_heatmap_html: str
    """
    # Map each state to its 2026 contested race data (if any)
    contested_by_state: Dict[str, pd.Series] = {}
    for _, row in df[df["is_contested_2026"]].iterrows():
        contested_by_state[row["state"]] = row

    dem_weights: List[float] = []
    rep_weights: List[float] = []

    # Calculate voter weights per contested state
    for _, cont_row in contested_by_state.items():
        leader = cont_row.get("poll_leader")
        dem_w = cont_row.get("dem_voter_weight")
        rep_w = cont_row.get("rep_voter_weight")
        if dem_w and leader == "DEM":
            dem_weights.append(float(dem_w))
        elif rep_w and leader == "REP":
            rep_weights.append(float(rep_w))

    max_voter_weight = max(
        max(dem_weights) if dem_weights else 1.0,
        max(rep_weights) if rep_weights else 1.0,
    )

    # 1. Split-halves dataset (100 features)
    heatmap_z: List[float] = []
    heatmap_tooltips: List[str] = []

    for _, row in df.iterrows():
        state_name = row["state"]
        vep_val = STATE_VEP.get(state_name, 0)
        cont_row = contested_by_state.get(state_name)
        val, tip = _generate_state_heatmap_tooltip(state_name, cont_row, vep_val)
        heatmap_z.append(val)
        heatmap_tooltips.append(tip)

    # 2. Whole-state perimeter dataset (50 features)
    heatmap_state_z: List[float] = []
    heatmap_state_tooltips: List[str] = []

    for s_name in state_names:
        vep_val = STATE_VEP.get(s_name, 0)
        cont_row = contested_by_state.get(s_name)
        val, tip = _generate_state_heatmap_tooltip(s_name, cont_row, vep_val)
        heatmap_state_z.append(val)
        heatmap_state_tooltips.append(tip)

    legend_colors_heatmap_html = _generate_heatmap_legend_html(max_voter_weight)

    return {
        "heatmap_z": heatmap_z,
        "heatmap_tooltips": heatmap_tooltips,
        "heatmap_state_z": heatmap_state_z,
        "heatmap_state_tooltips": heatmap_state_tooltips,
        "heatmap_colorscale": HEATMAP_COLORSCALE,
        "heatmap_zmin": -round(max_voter_weight),
        "heatmap_zmax": round(max_voter_weight),
        "legend_colors_heatmap_html": legend_colors_heatmap_html,
    }
