"""
Export script for the 2026 US Senate interactive web visualization.

Preprocesses polling, composition, and geospatial data into static JSON assets
stored in plotting/web/data/, allowing the web visualization to run directly
via standard HTTP servers (e.g. python3 -m http.server) without runtime Python dependencies.
"""

import json
from pathlib import Path
from typing import List

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

MODULE_DIR = Path(__file__).resolve().parent
WEB_DATA_DIR = MODULE_DIR / "web" / "data"


def _generate_flip_badge_records(flips: List[dict]) -> List[dict]:
    """Construct seat transfer badge records for Plotly Scattergeo markers."""
    records = []
    for f in flips:
        coord = get_seat_symbol_coord(f["feature_id"])
        color = COLOR_PALETTE["DEM"] if f["flip_incoming_party"] == "DEM" else COLOR_PALETTE["REP"]
        records.append({
            "lat": coord[0],
            "lon": coord[1],
            "color": color,
            "text": "⇄",
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
        }
    }

    # Discrete colorscale for seat status
    k = len(COLOR_CATEGORIES)
    colorscale_items = []
    for i, cat in enumerate(COLOR_CATEGORIES):
        color = COLOR_PALETTE[cat]
        colorscale_items.append([i / k, color])
        colorscale_items.append([(i + 1) / k, color])

    legend_colors_combined_html = """
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#EAB308;"></span> <span>Independent</span></div>
    """

    legend_colors_polls_only_html = """
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#EAB308;"></span> <span>Independent / Other</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#1E293B; border: 1px solid #475569;"></span> <span>Safe / Muted (65 seats)</span></div>
    """

    dem_flip_states = ", ".join(f["abbrev"] for f in flips if f["flip_incoming_party"] == "DEM")
    rep_flip_states = ", ".join(f["abbrev"] for f in flips if f["flip_incoming_party"] == "REP")
    ind_flip_states = ", ".join(f["abbrev"] for f in flips if f["flip_incoming_party"] == "IND")

    summary["dem_flip_states"] = dem_flip_states
    summary["rep_flip_states"] = rep_flip_states
    summary["ind_flip_states"] = ind_flip_states

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
        "legendColorsCombinedHtml": legend_colors_combined_html,
        "legendColorsPollsOnlyHtml": legend_colors_polls_only_html,
    }

    out_file = WEB_DATA_DIR / "senate_data.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Exported dashboard data to {out_file} ({out_file.stat().st_size:,d} bytes)")
    print(f"Chamber projection: {summary['projected_dem_total']} DEM vs {summary['projected_rep_total']} REP")


if __name__ == "__main__":
    export_all()
