"""
Export script for the 2026 US Senate interactive web visualization.

Preprocesses polling, composition, and geospatial data into static JSON assets
stored in plotting/web/data/, allowing the web visualization to run directly
via standard HTTP servers (e.g. python3 -m http.server) without runtime Python dependencies.
"""

import json
from pathlib import Path
from typing import List

import pandas as pd

from data_loader import (
    COLOR_CATEGORIES,
    COLOR_PALETTE,
    get_balance_of_power_summary,
    get_flip_records,
    load_all_senators_data,
)
from geo_splitter import generate_split_geojson, generate_state_outlines_geojson
from state_centroids import (
    STATE_LOWER_RIGHT_COORDS,
    STATE_TO_ABBREV,
    get_seat_symbol_coord,
)
from state_vep import STATE_VEP

MODULE_DIR = Path(__file__).resolve().parent
WEB_DATA_DIR = MODULE_DIR / "web" / "data"


def _generate_flip_badge_records(flips: List[dict]) -> List[dict]:
    """Construct seat transfer badge records for Plotly Scattergeo markers."""
    records = []
    for f in flips:
        coord = get_seat_symbol_coord(f["feature_id"])
        color = COLOR_PALETTE["DEM"] if f["flip_incoming_party"] == "DEM" else COLOR_PALETTE["REP"]
        margin_str = f"+{f['poll_margin']:.1f} pp" if f["poll_margin"] is not None else "Lead"
        records.append({
            "lat": coord[0],
            "lon": coord[1],
            "color": color,
            "text": "⇄",
            "tooltip": (
                f"<b>⚡ SEAT FLIP: {f['state']} ({f['abbrev']})</b><br>"
                f"Incumbent Party: {f['party']}<br>"
                f"2026 Poll Leader: {f['poll_leader']} ({margin_str})<br>"
                f"Polls Analyzed: {f['n_polls']}"
            ),
        })
    return records


def export_all() -> None:
    """Preprocess data and generate all static web assets."""
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data and GeoJSON collections...")
    df = load_all_senators_data()
    split_geojson = generate_split_geojson()
    outlines_geojson = generate_state_outlines_geojson()


    # Prepare datasets for map traces
    polls_z_combined = df["code_combined"].tolist()
    polls_z_only = df["code_polls_only"].tolist()
    tooltips = df["tooltip"].tolist()
    locs = df["feature_id"].tolist()
    contested_patterns = {
        row["feature_id"]: f"hatch-{row['cat_combined'].lower()}"
        for _, row in df[df["is_contested_2026"]].iterrows()
    }

    state_names = [f["id"] for f in outlines_geojson["features"]]
    abbrev_lats = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][0] for s in state_names]
    abbrev_lons = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][1] for s in state_names]
    abbrev_texts = [STATE_TO_ABBREV[s] for s in state_names]

    # Flip records and chamber balance summary
    flips = get_flip_records(df)
    summary = get_balance_of_power_summary(df)

    # Generate transfer badge records for projected flips
    records = _generate_flip_badge_records(flips)
    badges_data = {
        "none": {
            "count": len(records),
            "lats": [b["lat"] for b in records],
            "lons": [b["lon"] for b in records],
            "colors": [b["color"] for b in records],
            "texts": [b["text"] for b in records],
            "tooltips": [b["tooltip"] for b in records],
        }
    }

    # Discrete colorscale for seat status
    k = len(COLOR_CATEGORIES)
    colorscale_items = []
    for i, cat in enumerate(COLOR_CATEGORIES):
        color = COLOR_PALETTE[cat]
        colorscale_items.append([i / k, color])
        colorscale_items.append([(i + 1) / k, color])

    # Voter-weight heatmap calculation
    heatmap_z = []
    heatmap_tooltips = []
    dem_weights = []
    rep_weights = []

    for _, row in df.iterrows():
        leader = row.get("poll_leader")
        dem_w = row.get("dem_voter_weight")
        rep_w = row.get("rep_voter_weight")
        is_cont = row.get("is_contested_2026", False)
        state_name = row["state"]
        side_lbl = "Senate Seat 1" if row["side"] == "left" else "Senate Seat 2"
        senator_name = row.get("senator_name", "")
        party_name = row.get("party", "")
        vep_val = STATE_VEP.get(state_name, 0)

        if is_cont and dem_w and leader == "DEM":
            w = float(dem_w)
            dem_weights.append(w)
            heatmap_z.append(w)
            pct = (w / vep_val * 100.0) if vep_val else 0.0
            margin = row.get("poll_margin")
            margin_str = f"DEM +{margin:.1f} pp" if margin is not None else "Projected DEM Lead"
            tip_html = (
                f"<b>🏛️ {state_name} ({side_lbl}) — 2026 Voter Weight</b><br>"
                f"─────────────────────────────<br>"
                f"<b>Projected Winner:</b> Democrat ({margin_str})<br>"
                f"<b>👥 Estimated Supporters:</b> ~{int(w):,d} voters<br>"
                f"<b>State Eligible Population (VEP):</b> {vep_val:,d}<br>"
                f"<b>Projected Vote Share:</b> {pct:.1f}%<br>"
                f"─────────────────────────────<br>"
                f"<i>Formula: 2024 VEP (UF Election Lab) × Polling %</i>"
            )
            heatmap_tooltips.append(tip_html)
        elif is_cont and rep_w and leader == "REP":
            w = float(rep_w)
            rep_weights.append(w)
            heatmap_z.append(-w)
            pct = (w / vep_val * 100.0) if vep_val else 0.0
            margin = row.get("poll_margin")
            margin_str = f"REP +{abs(margin):.1f} pp" if margin is not None else "Projected REP Lead"
            tip_html = (
                f"<b>🏛️ {state_name} ({side_lbl}) — 2026 Voter Weight</b><br>"
                f"─────────────────────────────<br>"
                f"<b>Projected Winner:</b> Republican ({margin_str})<br>"
                f"<b>👥 Estimated Supporters:</b> ~{int(w):,d} voters<br>"
                f"<b>State Eligible Population (VEP):</b> {vep_val:,d}<br>"
                f"<b>Projected Vote Share:</b> {pct:.1f}%<br>"
                f"─────────────────────────────<br>"
                f"<i>Formula: 2024 VEP (UF Election Lab) × Polling %</i>"
            )
            heatmap_tooltips.append(tip_html)
        else:
            heatmap_z.append(0.0)
            tip_html = (
                f"<b>🏛️ {state_name} ({side_lbl})</b><br>"
                f"─────────────────────────────<br>"
                f"<b>Senator:</b> {senator_name} ({party_name})<br>"
                f"🔒 <b>Safe Seat:</b> Not up for election in 2026"
            )
            heatmap_tooltips.append(tip_html)

    max_voter_weight = max(
        max(dem_weights) if dem_weights else 1.0,
        max(rep_weights) if rep_weights else 1.0,
    )

    heatmap_colorscale = [
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

    def _fmt_voters(val: float) -> str:
        if val >= 1_000_000:
            return f"~{val / 1_000_000:.1f}M"
        if val >= 1_000:
            return f"~{val / 1_000:.0f}K"
        return f"~{val:,.0f}"

    dem_min_lbl = _fmt_voters(min(dem_weights)) if dem_weights else "0"
    dem_max_lbl = _fmt_voters(max(dem_weights)) if dem_weights else "0"
    rep_min_lbl = _fmt_voters(min(rep_weights)) if rep_weights else "0"
    rep_max_lbl = _fmt_voters(max(rep_weights)) if rep_weights else "0"

    legend_colors_combined_html = """
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#EAB308;"></span> <span>Independent</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <span>Unpolled</span></div>
    """

    legend_colors_polls_only_html = f"""
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <span>Unpolled ({summary['unpolled']} seats)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#1E293B; border: 1px solid #475569;"></span> <span>Safe / Muted (65 seats)</span></div>
    """

    legend_colors_heatmap_html = f"""
          <div class="legend-item">
            <span class="legend-gradient-bar" style="background: linear-gradient(to right, #DBEAFE, #3B82F6, #1E3A8A);"></span>
            <span><b>DEM:</b> {dem_min_lbl} (light) → {dem_max_lbl} (deep)</span>
          </div>
          <div class="legend-item">
            <span class="legend-gradient-bar" style="background: linear-gradient(to right, #FEE2E2, #DC2626, #7F1D1D);"></span>
            <span><b>REP:</b> {rep_min_lbl} (light) → {rep_max_lbl} (deep)</span>
          </div>
          <div class="legend-item">
            <span class="legend-swatch" style="background: #1E293B; border: 1px solid #475569;"></span>
            <span>Uncontested / Safe Seat</span>
          </div>
          <div class="legend-item" style="font-size: 0.68rem; color: #94A3B8; font-style: italic;">
            Estimated = State VEP (UF Election Lab) × Polling %
          </div>
    """

    dem_flip_states = ", ".join(f["abbrev"] for f in flips if f["flip_incoming_party"] == "DEM")
    rep_flip_states = ", ".join(f["abbrev"] for f in flips if f["flip_incoming_party"] == "REP")

    summary["dem_flip_states"] = dem_flip_states
    summary["rep_flip_states"] = rep_flip_states

    payload = {
        "summary": summary,
        "badges": badges_data,
        "locs": locs,
        "pollsZCombined": polls_z_combined,
        "pollsZOnly": polls_z_only,
        "tooltips": tooltips,
        "stateNames": state_names,
        "colorscale": colorscale_items,
        "numCategories": k,
        "contestedPatterns": contested_patterns,
        "abbrevLons": abbrev_lons,
        "abbrevLats": abbrev_lats,
        "abbrevTexts": abbrev_texts,
        "heatmapZ": heatmap_z,
        "heatmapColorscale": heatmap_colorscale,
        "heatmapTooltips": heatmap_tooltips,
        "heatmapZmin": -round(max_voter_weight),
        "heatmapZmax": round(max_voter_weight),
        "legendColorsCombinedHtml": legend_colors_combined_html,
        "legendColorsPollsOnlyHtml": legend_colors_polls_only_html,
        "legendColorsHeatmapHtml": legend_colors_heatmap_html,
    }

    out_file = WEB_DATA_DIR / "senate_data.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Exported dashboard data to {out_file} ({out_file.stat().st_size:,d} bytes)")
    print(f"Chamber projection: {summary['projected_dem_total']} DEM vs {summary['projected_rep_total']} REP")


if __name__ == "__main__":
    export_all()
