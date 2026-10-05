"""
Map and chart construction module for the 2026 US Senate interactive visualization.

Features:
1. Map: 100 split half-state polygons with white internal dividers and black state perimeters.
   When viewing 2026 poll predictions, the 35 contested seats in election are marked
   with a distinct, subtle dashed white border (stroke-dasharray) that instantly identifies
   the races in play without distracting from the color fills.
2. Pie Chart: 100-seat (or 35-seat isolated) pie chart without center text or legend clutter.
   Displays slice numbers and locks party sectors consistently (REP on right, DEM on left).
3. Interactive client-side dashboard with:
   - Single hover button (enter for 2026 Polls, leave for Current Senate, click to lock).
   - Checkbox to isolate 2026 poll results (mutes safe seats).
   - Dynamic 60fps color gradient transitions via hardware-accelerated CSS.
"""

import json
from typing import List, Tuple
import pandas as pd
import plotly.graph_objects as go

from data_loader import (
    COLOR_CATEGORIES,
    COLOR_PALETTE,
    get_balance_of_power_summary,
    get_flip_records,
)
from state_centroids import (
    SEAT_SYMBOL_COORDS,
    STATE_LOWER_RIGHT_COORDS,
    STATE_TO_ABBREV,
    get_seat_symbol_coord,
)


def _create_discrete_colorscale() -> Tuple[List[List], float, float]:
    """
    Construct a discrete Plotly colorscale mapping integer category indices to exact hex colors.
    """
    k = len(COLOR_CATEGORIES)
    colorscale = []
    for i, cat in enumerate(COLOR_CATEGORIES):
        color = COLOR_PALETTE[cat]
        colorscale.append([i / k, color])
        colorscale.append([(i + 1) / k, color])
    zmin = -0.5
    zmax = k - 0.5
    return colorscale, zmin, zmax


def _generate_badge_records(
    df: pd.DataFrame, flips: List[dict], debug_mode: str = "none"
) -> List[dict]:
    """
    Construct seat transfer badge records for Plotly Scattergeo markers.

    Modes:
    - 'none' (default): Only the 7 actual projected party flips from 2026 polling.
    - 'all_50': Render 50 symbols, one for each state (placed in the East/Right seat).
    - 'all_100': Render 100 symbols across every Senate seat (both West and East halves).
    """
    records = []
    if debug_mode == "all_100":
        for _, row in df.iterrows():
            fid = row["feature_id"]
            coord = get_seat_symbol_coord(fid)
            color = COLOR_PALETTE["DEM"] if row["side"] == "left" else COLOR_PALETTE["REP"]
            records.append({
                "lat": coord[0],
                "lon": coord[1],
                "color": color,
                "text": "⇄",
                "tooltip": (
                    f"<b>🛠️ DEBUG: {row['state']} ({row['side'].upper()})</b><br>"
                    f"Feature: {fid}<br>"
                    f"Party: {row['party']}<br>"
                    f"Coord: ({coord[0]:.3f}, {coord[1]:.3f})"
                ),
            })
    elif debug_mode in ("all_50", "right_50"):
        for _, row in df[df["side"] == "right"].iterrows():
            fid = row["feature_id"]
            coord = get_seat_symbol_coord(fid)
            color = COLOR_PALETTE["DEM"] if row["party"] == "REP" else COLOR_PALETTE["REP"]
            records.append({
                "lat": coord[0],
                "lon": coord[1],
                "color": color,
                "text": "⇄",
                "tooltip": (
                    f"<b>🛠️ DEBUG: {row['state']} (RIGHT SEAT)</b><br>"
                    f"Feature: {fid}<br>"
                    f"Incumbent: {row['party']}<br>"
                    f"Coord: ({coord[0]:.3f}, {coord[1]:.3f})"
                ),
            })
    else:
        for f in flips:
            coord = get_seat_symbol_coord(f["feature_id"])
            records.append({
                "lat": coord[0],
                "lon": coord[1],
                "color": COLOR_PALETTE["DEM"] if f["flip_incoming_party"] == "DEM" else COLOR_PALETTE["REP"],
                "text": "⇄",
                "tooltip": (
                    f"<b>⚡ SEAT FLIP: {f['state']} ({f['abbrev']})</b><br>"
                    f"Incumbent Party: {f['party']}<br>"
                    f"2026 Poll Leader: {f['poll_leader']} ({'+' if (f['poll_margin'] or 0) > 0 else ''}{f['poll_margin']} pp)<br>"
                    f"Polls Analyzed: {f['n_polls']}"
                ),
            })
    return records


def build_figure(
    df: pd.DataFrame,
    split_geojson: dict,
    outlines_geojson: dict,
    view: str = "combined",
    debug_mode: str = "none",
) -> go.Figure:
    """
    Build the Plotly US Senate map with 100 split half-state polygons,
    crisp black state boundaries, state abbreviations, and transfer flip badges.
    """
    colorscale, zmin, zmax = _create_discrete_colorscale()

    if view == "composition":
        z_col = "code_composition"
    elif view == "polls_only":
        z_col = "code_polls_only"
    else:
        z_col = "code_combined"

    # Layer 1: 100 half-state polygons with white internal division lines
    halves_trace = go.Choropleth(
        geojson=split_geojson,
        locations=df["feature_id"],
        featureidkey="id",
        z=df[z_col],
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        showscale=False,
        hoverinfo="text",
        hovertext=df["tooltip"],
        marker=dict(
            line=dict(color="#FFFFFF", width=1.5),
            opacity=0.95,
        ),
        name="US Senate Seats",
    )

    # Layer 2: 50 full state perimeter outlines with solid black borders
    state_names = [f["id"] for f in outlines_geojson["features"]]
    outlines_trace = go.Choropleth(
        geojson=outlines_geojson,
        locations=state_names,
        featureidkey="id",
        z=[0] * len(state_names),
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
        showscale=False,
        hoverinfo="skip",
        marker=dict(
            line=dict(color="#000000", width=2.0),
        ),
        name="State Boundaries",
    )

    # Layer 3: 50 state abbreviation labels in the lower-right corner of each state
    abbrev_lats = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][0] for s in state_names]
    abbrev_lons = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][1] for s in state_names]
    abbrev_texts = [STATE_TO_ABBREV[s] for s in state_names]

    text_trace = go.Scattergeo(
        locationmode="USA-states",
        lon=abbrev_lons,
        lat=abbrev_lats,
        mode="text",
        text=abbrev_texts,
        textfont=dict(
            family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
            size=10,
            color="#FFFFFF",
        ),
        hoverinfo="skip",
        name="State Abbreviations",
    )

    # Layer 4: Seat flip transfer badges (Style 2: transfer icon ⇄ inside circular markers)
    flips = get_flip_records(df)
    badge_records = _generate_badge_records(df, flips, debug_mode)
    flip_lats = [b["lat"] for b in badge_records]
    flip_lons = [b["lon"] for b in badge_records]
    flip_colors = [b["color"] for b in badge_records]
    flip_texts = [b["text"] for b in badge_records]
    flip_tooltips = [b["tooltip"] for b in badge_records]

    flips_trace = go.Scattergeo(
        locationmode="USA-states",
        lon=flip_lons,
        lat=flip_lats,
        mode="markers+text",
        text=flip_texts,
        textposition="middle center",
        textfont=dict(
            family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
            size=13,
            color="#FFFFFF",
        ),
        marker=dict(
            size=22,
            color=flip_colors,
            line=dict(color="#FFFFFF", width=2.0),
            opacity=1.0,
        ),
        hoverinfo="text",
        hovertext=flip_tooltips,
        name="Seat Flips",
    )

    fig = go.Figure(data=[halves_trace, outlines_trace, text_trace, flips_trace])


    fig.update_geos(
        scope="usa",
        projection_type="albers usa",
        showsubunits=False,
        showland=False,
        showlakes=False,
        showocean=False,
        showrivers=False,
        showcountries=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        height=580,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(
            bgcolor="#0F172A",
            font_size=13,
            font_family="sans-serif",
            font_color="#F8FAFC",
            bordercolor="#334155",
        ),
    )

    return fig


def build_pie_figure(df: pd.DataFrame, view: str = "combined") -> go.Figure:
    """
    Build the matching pie chart for the Senate seats based on active view.
    Zero center text, no legend, sectors anchored consistently (REP on right, DEM on left).
    """
    if view == "composition":
        labels = ["Republicans", "Independents", "Democrats"]
        values = [53, 2, 45]
        colors = ["#DC2626", "#EAB308", "#2563EB"]
        text_colors = ["#FFFFFF", "#0F172A", "#FFFFFF"]
    elif view == "polls_only":
        labels = [
            "Solid Republican (> 2 pp)",
            "Toss-Up (Lean REP ≤ 2 pp)",
            "No Poll Data",
            "Toss-Up (Lean DEM ≤ 2 pp)",
            "Solid Democrat (> 2 pp)",
        ]
        values = [12, 3, 5, 3, 12]
        colors = ["#DC2626", "#FCA5A5", "#64748B", "#93C5FD", "#2563EB"]
        text_colors = ["#FFFFFF", "#0F172A", "#FFFFFF", "#0F172A", "#FFFFFF"]
    else:
        labels = [
            "Solid Republican (> 2 pp)",
            "Toss-Up (Lean REP ≤ 2 pp)",
            "Independent",
            "No Poll Data",
            "Toss-Up (Lean DEM ≤ 2 pp)",
            "Solid Democrat (> 2 pp)",
        ]
        values = [43, 3, 2, 5, 3, 44]
        colors = ["#DC2626", "#FCA5A5", "#EAB308", "#64748B", "#93C5FD", "#2563EB"]
        text_colors = ["#FFFFFF", "#0F172A", "#0F172A", "#FFFFFF", "#0F172A", "#FFFFFF"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0,
                rotation=0,
                direction="clockwise",
                sort=False,
                marker=dict(colors=colors, line=dict(color="#0F172A", width=1.5)),
                textinfo="value",
                textposition="auto",
                hoverinfo="skip",
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=15, r=15, t=25, b=25),
        height=580,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        annotations=[],
    )

    return fig


def build_interactive_dashboard_html(
    df: pd.DataFrame,
    split_geojson: dict,
    outlines_geojson: dict,
    view: str = "combined",
    debug_mode: str = "none",
) -> str:
    """
    Generate the hybrid static dashboard for the 2026 US Senate representation (Option B):
    - Top section: 50-state Albers split map with 2026 poll predictions,
      solid black state borders, white internal senator dividers,
      diagonal stripe patterns and crisp white borders on the 35 contested seats, state postal abbreviations,
      and Style 2 circular flip badges (⇄) on the 7 battlegrounds where a party flip is projected.
    - Bottom section: Majority 50 Threshold Bar & Chamber Balance Ledger,
      displaying the 100-seat distribution, the 50-seat majority threshold line,
      the tally scoreboard (52 DEM majority vs 48 REP minority), and segment key.
    """
    if view == "polls_only":
        z_col = "code_polls_only"
        cat_col = "cat_polls_only"
    elif view == "composition":
        z_col = "code_composition"
        cat_col = "cat_composition"
    else:
        z_col = "code_combined"
        cat_col = "cat_combined"

    polls_z = df[z_col].tolist()
    tooltips = df["tooltip"].tolist()
    locs = df["feature_id"].tolist()
    contested_locs = df[df["is_contested_2026"]]["feature_id"].tolist()
    contested_patterns = {
        row["feature_id"]: f"hatch-{row[cat_col].lower()}"
        for _, row in df[df["is_contested_2026"]].iterrows()
    }
    state_names = [f["id"] for f in outlines_geojson["features"]]
    abbrev_lats = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][0] for s in state_names]
    abbrev_lons = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][1] for s in state_names]
    abbrev_texts = [STATE_TO_ABBREV[s] for s in state_names]

    # Flip badge coordinates and properties (Style 2: geometric circular badge with ⇄)
    flips = get_flip_records(df)
    summary = get_balance_of_power_summary(df)

    badge_records = _generate_badge_records(df, flips, debug_mode)
    flip_lats = [b["lat"] for b in badge_records]
    flip_lons = [b["lon"] for b in badge_records]
    flip_colors = [b["color"] for b in badge_records]
    flip_texts = [b["text"] for b in badge_records]
    flip_tooltips = [b["tooltip"] for b in badge_records]

    colorscale_items = []
    k = len(COLOR_CATEGORIES)
    for i, cat in enumerate(COLOR_CATEGORIES):
        color = COLOR_PALETTE[cat]
        colorscale_items.append([i / k, color])
        colorscale_items.append([(i + 1) / k, color])

    if view == "polls_only":
        legend_colors_html = """
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <span>Unpolled (5 seats)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#1E293B; border: 1px solid #475569;"></span> <span>Safe / Muted (65 seats)</span></div>
        """
    else:
        legend_colors_html = """
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#EAB308;"></span> <span>Independent</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <span>Unpolled</span></div>
        """

    debug_badge_tag = (
        f'<span style="font-size:0.70rem; background:#D97706; color:#FFFFFF; padding:2px 7px; border-radius:4px; margin-left:8px; font-weight:700; vertical-align:middle;">'
        f'DEBUG: {len(badge_records)} Symbols Active</span>'
        if debug_mode != "none"
        else ""
    )

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      height: 100%;
      width: 100%;
      margin: 0;
      padding: 0;
      overflow: hidden;
      background: transparent;
      color: #F8FAFC;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .dashboard-layout {{
      height: 100%;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    #map-container {{
      flex: 1 1 auto;
      min-height: 280px;
      width: 100%;
      background: #0F172A;
      border: 1px solid #334155;
      border-radius: 12px;
      overflow: hidden;
      position: relative;
      display: flex;
      flex-direction: column;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
    }}
    #map-plot {{
      flex: 1 1 auto;
      width: 100%;
      height: 100%;
      min-height: 220px;
      position: relative;
      overflow: hidden !important;
    }}
    #map-legend-bar {{
      position: relative !important;
      z-index: 20 !important;
      flex-shrink: 0;
      background: #0B1120 !important;
      border-top: 1px solid #1E293B;
      padding: 6px 14px;
      display: flex;
      flex-direction: column;
      gap: 3px;
      box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.4);
    }}
    .legend-row {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      font-size: 0.72rem;
    }}
    .structure-pill {{
      display: inline-flex;
      border: 1px solid rgba(255, 255, 255, 0.45);
      border-radius: 4px;
      overflow: hidden;
      font-size: 0.66rem;
      font-weight: 800;
      line-height: 15px;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
    }}
    .pill-half {{
      padding: 1px 7px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.95), 0 0 3px #000000;
      white-space: nowrap;
    }}
    .pill-left {{
      background: #2563EB;
      color: #FFFFFF;
      border-right: 1.5px solid #FFFFFF;
    }}
    .pill-right {{
      background-color: #DC2626;
      color: #FFFFFF;
    }}
    .legend-divider {{
      width: 1px;
      height: 14px;
      background: #334155;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 0.72rem;
      color: #CBD5E1;
      white-space: nowrap;
    }}
    .legend-swatch-pair {{
      display: inline-flex;
      align-items: center;
      gap: 3px;
    }}
    .legend-swatch {{
      width: 12px;
      height: 12px;
      border-radius: 3px;
      flex-shrink: 0;
      border: 1px solid rgba(255, 255, 255, 0.2);
    }}
    .legend-swatch-hatch {{
      width: 13px;
      height: 13px;
      border-radius: 3px;
      flex-shrink: 0;
      border: 1px solid #FFFFFF;
      background-image: repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(255,255,255,0.8) 2px, rgba(255,255,255,0.8) 3.5px);
    }}
    .legend-swatch-hatch.hatch-dem {{
      background-color: #2563EB;
    }}
    .legend-swatch-hatch.hatch-rep {{
      background-color: #DC2626;
    }}
    .legend-swatch-flip {{
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 1.5px solid #FFFFFF;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.62rem;
      color: #FFFFFF;
      font-weight: 700;
      line-height: 1;
    }}
    .legend-swatch-flip.flip-dem {{
      background-color: #0284C7;
    }}
    .legend-swatch-flip.flip-rep {{
      background-color: #DC2626;
    }}

    /* Balance of Power Panel */
    #balance-panel {{
      flex-shrink: 0;
      width: 100%;
      background: #0F172A;
      border: 1px solid #334155;
      border-radius: 10px;
      padding: 7px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
    }}
    .panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      border-bottom: 1px solid #1E293B;
      padding-bottom: 4px;
    }}
    .panel-title {{
      font-size: 0.96rem;
      font-weight: 700;
      color: #F8FAFC;
      letter-spacing: -0.01em;
    }}
    .panel-subtitle {{
      font-size: 0.74rem;
      color: #94A3B8;
      margin: 0;
    }}

    /* Majority 50 Threshold Bar Section */
    .bar-section {{
      background: #1E293B;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 6px 12px;
    }}
    .bar-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.76rem;
      margin-bottom: 12px;
      color: #E2E8F0;
    }}
    .bar-wrapper {{
      position: relative;
      width: 100%;
      height: 26px;
      background: #0B1120;
      border-radius: 5px;
      overflow: visible;
      margin-bottom: 4px;
    }}
    .bar-track {{
      display: flex;
      width: 100%;
      height: 100%;
      border-radius: 5px;
      overflow: hidden;
    }}
    .bar-seg {{
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.70rem;
      font-weight: 700;
      color: #FFFFFF;
      text-shadow: 0 1px 2px rgba(0,0,0,0.8);
      white-space: nowrap;
      overflow: hidden;
    }}
    .seg-dem-safe {{ background: #1E40AF; }}
    .seg-dem-holds {{ background: #2563EB; }}
    .seg-dem-flips {{
      background: #0284C7;
      border-top: 2px solid #38BDF8;
      border-bottom: 2px solid #38BDF8;
      box-shadow: inset 0 0 6px rgba(56, 189, 248, 0.6);
    }}
    .seg-unpolled {{ background: #64748B; }}
    .seg-rep-flips {{ background: #F87171; }}
    .seg-rep-holds {{ background: #DC2626; }}
    .seg-rep-safe {{ background: #991B1B; }}

    /* Majority threshold vertical line at 50% */
    .majority-line {{
      position: absolute;
      left: 50%;
      top: -8px;
      bottom: -8px;
      width: 2px;
      background: #F8FAFC;
      box-shadow: 0 0 6px rgba(255, 255, 255, 0.9);
      z-index: 10;
      pointer-events: none;
    }}
    .majority-label-pin {{
      position: absolute;
      top: -18px;
      left: 50%;
      transform: translateX(-50%);
      background: #F8FAFC;
      color: #0F172A;
      font-size: 0.64rem;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 3px;
      white-space: nowrap;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);
      z-index: 11;
    }}
    .bar-sublegend {{
      display: flex;
      justify-content: space-between;
      font-size: 0.74rem;
      color: #94A3B8;
      margin-top: 4px;
    }}

    /* Segment Color Key */
    .bar-legend-card {{
      background: #1E293B;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 5px 10px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: nowrap;
    }}
    .legend-card-title {{
      font-size: 0.68rem;
      font-weight: 700;
      color: #94A3B8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      white-space: nowrap;
    }}
    .bar-legend-grid {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 4px 14px;
      font-size: 0.72rem;
      color: #E2E8F0;
    }}

    /* Scattergeo labels styling */
    .scattergeo, .textpoint, .textpoint text {{
      visibility: visible !important;
      opacity: 1 !important;
      font-weight: 700 !important;
      font-size: 10px !important;
      fill: #FFFFFF !important;
      paint-order: stroke fill !important;
      stroke: rgba(15, 23, 42, 0.95) !important;
      stroke-width: 2.4px !important;
      stroke-linecap: round !important;
      stroke-linejoin: round !important;
      pointer-events: none !important;
      user-select: none !important;
    }}
    /* Style 2 transfer flip badge SVG styling */
    .scattergeo .point path {{
      filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.75)) !important;
    }}

    /* Eliminate artificial SVG clipping rects while strictly containing map inside map-plot */
    #map-plot .plot-container,
    #map-plot .svg-container,
    #map-plot svg.main-svg {{
      width: 100% !important;
      height: 100% !important;
      overflow: hidden !important;
    }}
    #map-plot .geolayer,
    #map-plot .geosubplot,
    #map-plot g.geo {{
      clip-path: none !important;
    }}

    /* Direct SVG pattern and border styling on native Plotly choropleth paths */
    path.choroplethlocation.contested-seat {{
      stroke: #FFFFFF !important;
      stroke-width: 2.2px !important;
      stroke-linecap: round !important;
      stroke-linejoin: round !important;
      paint-order: fill stroke !important;
    }}
    path.choroplethlocation.hatch-dem {{
      fill: url(#hatch-dem) !important;
    }}
    path.choroplethlocation.hatch-dem_lean {{
      fill: url(#hatch-dem_lean) !important;
    }}
    path.choroplethlocation.hatch-rep {{
      fill: url(#hatch-rep) !important;
    }}
    path.choroplethlocation.hatch-rep_lean {{
      fill: url(#hatch-rep_lean) !important;
    }}
    path.choroplethlocation.hatch-ind {{
      fill: url(#hatch-ind) !important;
    }}
    path.choroplethlocation.hatch-no_data {{
      fill: url(#hatch-no_data) !important;
    }}
    path.choroplethlocation.hatch-tie {{
      fill: url(#hatch-tie) !important;
    }}
  </style>
</head>
<body>
  <!-- Static SVG Pattern Definitions for 2026 Contested Races -->
  <svg style="position: absolute; width: 0; height: 0; overflow: hidden; pointer-events: none;" aria-hidden="true">
    <defs>
      <!-- Solid Democrat Pattern -->
      <pattern id="hatch-dem" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#2563EB" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#000000" stroke-width="2.2" stroke-opacity="0.35" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#FFFFFF" stroke-width="1.4" stroke-opacity="0.85" />
      </pattern>

      <!-- Lean Dem Toss-Up Pattern -->
      <pattern id="hatch-dem_lean" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#93C5FD" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#1E3A8A" stroke-width="2.2" stroke-opacity="0.45" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#FFFFFF" stroke-width="1.4" stroke-opacity="0.9" />
      </pattern>

      <!-- Solid Republican Pattern -->
      <pattern id="hatch-rep" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#DC2626" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#000000" stroke-width="2.2" stroke-opacity="0.35" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#FFFFFF" stroke-width="1.4" stroke-opacity="0.85" />
      </pattern>

      <!-- Lean Rep Toss-Up Pattern -->
      <pattern id="hatch-rep_lean" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#FCA5A5" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#7F1D1D" stroke-width="2.2" stroke-opacity="0.45" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#FFFFFF" stroke-width="1.4" stroke-opacity="0.9" />
      </pattern>

      <!-- Independent Pattern -->
      <pattern id="hatch-ind" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#EAB308" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#000000" stroke-width="2.2" stroke-opacity="0.35" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#FFFFFF" stroke-width="1.4" stroke-opacity="0.85" />
      </pattern>

      <!-- Unpolled / No Data Pattern -->
      <pattern id="hatch-no_data" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#64748B" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#000000" stroke-width="2.2" stroke-opacity="0.35" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#FFFFFF" stroke-width="1.4" stroke-opacity="0.85" />
      </pattern>

      <!-- Tie Pattern -->
      <pattern id="hatch-tie" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
        <rect width="8" height="8" fill="#C084FC" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#000000" stroke-width="2.2" stroke-opacity="0.35" />
        <line x1="4" y1="0" x2="4" y2="8" stroke="#FFFFFF" stroke-width="1.4" stroke-opacity="0.85" />
      </pattern>
    </defs>
  </svg>

  <div class="dashboard-layout">
    <!-- Map Container with integrated Gestalt Legend -->
    <div id="map-container">
      <div id="map-plot"></div>
      <div id="map-legend-bar">
        <div class="legend-row">
          <span class="structure-pill">
            <span class="pill-half pill-left">Senate Seat 1</span>
            <span class="pill-half pill-right">Senate Seat 2</span>
          </span>
          <div class="legend-divider"></div>
          <div class="legend-item">
            <span class="legend-swatch-pair">
              <span class="legend-swatch-hatch hatch-dem"></span>
              <span class="legend-swatch-hatch hatch-rep"></span>
            </span>
            <span>2026 Race in Play</span>
          </div>
          <div class="legend-item">
            <span class="legend-swatch-pair">
              <span class="legend-swatch-flip flip-dem">⇄</span>
              <span class="legend-swatch-flip flip-rep">⇄</span>
            </span>
            <span>Projected Party Flip</span>
          </div>
        </div>
        <div class="legend-row legend-colors">
          {legend_colors_html}
        </div>
      </div>
    </div>

    <!-- Balance of Power Seat Balance Panel -->
    <div id="balance-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="panel-title">🏛️ 2026 US Senate Seat Balance {debug_badge_tag}</div>
        <div class="panel-subtitle">100 Seats Total • <b>50 Seats</b> Threshold for Chamber Majority</div>
      </div>

      <!-- Majority 50 Threshold Bar Section -->
      <div class="bar-section">
        <div class="bar-header">
          <span><b>Seat Balance Bar (0 to 100):</b></span>
          <span style="color: #38BDF8; font-weight: 700; font-size: 0.88rem;">DEM crosses 50-Seat Mark (52 DEM vs. 48 REP)</span>
        </div>

        <div class="bar-wrapper">
          <div class="majority-label-pin">50 Majority</div>
          <div class="majority-line"></div>
          <div class="bar-track">
            <div class="bar-seg seg-dem-safe" style="width: {summary['safe_dem_ind']}%;" title="{summary['safe_dem_ind']} Safe Democratic & Independent Seats">{summary['safe_dem_ind']} Safe</div>
            <div class="bar-seg seg-dem-holds" style="width: {summary['dem_holds']}%;" title="{summary['dem_holds']} Democratic Poll Holds">{summary['dem_holds']} Holds</div>
            <div class="bar-seg seg-dem-flips" style="width: {summary['dem_flips']}%;" title="{summary['dem_flips']} Democratic Flips from GOP (AK, KY, ME, NE, NC, OH)">+6★</div>
            <div class="bar-seg seg-unpolled" style="width: {summary['unpolled']}%;" title="{summary['unpolled']} Seats with No General Election Polls (3 DEM safe, 2 REP safe)">5</div>
            <div class="bar-seg seg-rep-flips" style="width: {summary['rep_flips']}%;" title="{summary['rep_flips']} Republican Flip from DEM (MI)"></div>
            <div class="bar-seg seg-rep-holds" style="width: {summary['rep_holds']}%;" title="{summary['rep_holds']} Republican Poll Holds">{summary['rep_holds']} Holds</div>
            <div class="bar-seg seg-rep-safe" style="width: {summary['safe_rep']}%;" title="{summary['safe_rep']} Safe Republican Seats">{summary['safe_rep']} Safe</div>
          </div>
        </div>

        <div class="bar-sublegend">
          <span>🔵 <b>{summary['projected_dem_total']} DEM Coalition</b> (34 Safe + 9 Holds + 6 Flips + 3 Unpolled)</span>
          <span>🔴 <b>{summary['projected_rep_total']} Republican Party</b> (31 Safe + 14 Holds + 1 Flip + 2 Unpolled)</span>
        </div>
      </div>

      <!-- Segment Color Key -->
      <div class="bar-legend-card">
        <div class="legend-card-title">Seat Composition Key</div>
        <div class="bar-legend-grid">
          <div class="legend-item"><span class="legend-swatch" style="background:#1E40AF;"></span> <b>34</b> Safe DEM & IND</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <b>9</b> DEM Holds</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#0284C7; border: 1px solid #38BDF8;"></span> <b>+6</b> DEM Flips (Gain)</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <b>5</b> Unpolled Seats</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#F87171;"></span> <b>+1</b> REP Flip (Gain)</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <b>14</b> REP Holds</div>
          <div class="legend-item"><span class="legend-swatch" style="background:#991B1B;"></span> <b>31</b> Safe REP</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    const splitGeojson = {json.dumps(split_geojson)};
    const outlinesGeojson = {json.dumps(outlines_geojson)};
    const locs = {json.dumps(locs)};
    const pollsZ = {json.dumps(polls_z)};
    const tooltips = {json.dumps(tooltips)};
    const stateNames = {json.dumps(state_names)};
    const colorscale = {json.dumps(colorscale_items)};
    const contestedPatterns = {json.dumps(contested_patterns)};
    const abbrevLons = {json.dumps(abbrev_lons)};
    const abbrevLats = {json.dumps(abbrev_lats)};
    const abbrevTexts = {json.dumps(abbrev_texts)};

    const flipLons = {json.dumps(flip_lons)};
    const flipLats = {json.dumps(flip_lats)};
    const flipColors = {json.dumps(flip_colors)};
    const flipTexts = {json.dumps(flip_texts)};
    const flipTooltips = {json.dumps(flip_tooltips)};

    // Map traces definition
    const mapTraceHalves = {{
      type: 'choropleth',
      geojson: splitGeojson,
      locations: locs,
      featureidkey: 'id',
      z: pollsZ,
      colorscale: colorscale,
      zmin: -0.5,
      zmax: {k} - 0.5,
      showscale: false,
      hoverinfo: 'text',
      hovertext: tooltips,
      marker: {{
        line: {{ color: '#FFFFFF', width: 1.5 }},
        opacity: 0.95
      }}
    }};

    const mapTraceOutlines = {{
      type: 'choropleth',
      geojson: outlinesGeojson,
      locations: stateNames,
      featureidkey: 'id',
      z: new Array(stateNames.length).fill(0),
      colorscale: [[0, 'rgba(0,0,0,0)'], [1, 'rgba(0,0,0,0)']],
      showscale: false,
      hoverinfo: 'skip',
      marker: {{
        line: {{ color: '#000000', width: 2.0 }}
      }}
    }};

    const mapTraceText = {{
      type: 'scattergeo',
      locationmode: 'USA-states',
      lon: abbrevLons,
      lat: abbrevLats,
      mode: 'text',
      text: abbrevTexts,
      textfont: {{
        family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
        size: 10,
        color: '#FFFFFF'
      }},
      showlegend: false,
      hoverinfo: 'skip'
    }};

    // Style 2 Flip transfer badges: bold circular badge with ⇄ icon in incoming party color
    const mapTraceFlips = {{
      type: 'scattergeo',
      locationmode: 'USA-states',
      lon: flipLons,
      lat: flipLats,
      mode: 'markers+text',
      text: flipTexts,
      textposition: 'middle center',
      textfont: {{
        family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif',
        size: 13,
        color: '#FFFFFF'
      }},
      marker: {{
        size: 22,
        color: flipColors,
        line: {{ color: '#FFFFFF', width: 2.0 }},
        opacity: 1.0
      }},
      showlegend: false,
      hoverinfo: 'text',
      hovertext: flipTooltips,
      name: 'Seat Flips'
    }};

    const mapLayout = {{
      autosize: true,
      geo: {{
        scope: 'usa',
        projection: {{ type: 'albers usa' }},
        showsubunits: false,
        showland: false,
        showlakes: false,
        showocean: false,
        showrivers: false,
        showcountries: false,
        bgcolor: 'rgba(0,0,0,0)',
        domain: {{ x: [0, 1], y: [0, 1] }}
      }},
      margin: {{ l: 0, r: 0, t: 0, b: 0 }},
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      hoverlabel: {{
        bgcolor: '#0F172A',
        font: {{ size: 13, color: '#F8FAFC' }},
        bordercolor: '#334155'
      }},
      dragmode: 'pan',
      showlegend: false
    }};

    // Apply diagonal hatch patterns and crisp white borders directly to Trace 0 paths
    function applyContestedStyles() {{
      const choroplethTraces = document.querySelectorAll('#map-plot g.trace.choropleth, #map-plot g.choropleth');
      if (!choroplethTraces || choroplethTraces.length === 0) return;
      const baseTrace = choroplethTraces[0];
      const halfPaths = baseTrace.querySelectorAll('path.choroplethlocation');
      if (!halfPaths || halfPaths.length === 0) return;

      for (let idx = 0; idx < halfPaths.length; idx++) {{
        const p = halfPaths[idx];
        let loc = null;
        const d = p.__data__;
        if (d) {{
          loc = d.id || (d.properties && d.properties.id) || (d.properties && (d.properties.state + '_' + d.properties.side));
        }}
        if (!loc && idx < locs.length) {{
          loc = locs[idx];
        }}
        const patternClass = contestedPatterns[loc];
        if (patternClass) {{
          if (!p.classList.contains(patternClass)) {{
            p.classList.add('contested-seat', patternClass);
          }}
        }}
      }}
    }}

    // Initial render with interactive pan and zoom
    Plotly.newPlot('map-plot', [mapTraceHalves, mapTraceOutlines, mapTraceText, mapTraceFlips], mapLayout, {{
      responsive: true,
      displayModeBar: false,
      scrollZoom: true
    }}).then(() => {{
      applyContestedStyles();
    }});

    // Reliable autosize relayout without fragile mutex locks
    function resizeMap() {{
      const el = document.getElementById('map-plot');
      if (!el || !el.data) return;
      try {{
        Plotly.relayout(el, {{ autosize: true }}).then(() => {{
          applyContestedStyles();
        }}).catch(() => {{
          applyContestedStyles();
        }});
      }} catch (err) {{
        applyContestedStyles();
      }}
    }}

    let resizeTimer = null;
    function debouncedResize() {{
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resizeMap, 80);
    }}

    window.addEventListener('resize', debouncedResize);

    // Hook Plotly redraw events safely to re-apply pattern classes without mutating the DOM tree
    const mapDiv = document.getElementById('map-plot');
    if (mapDiv && mapDiv.on) {{
      mapDiv.on('plotly_afterplot', () => {{
        applyContestedStyles();
      }});
      mapDiv.on('plotly_relayout', () => {{
        applyContestedStyles();
      }});
    }}

    // ResizeObserver on the container to detect flexbox layout updates
    const ro = new ResizeObserver(() => {{
      debouncedResize();
    }});
    const mapPlot = document.getElementById('map-plot');
    if (mapPlot) {{
      ro.observe(mapPlot);
    }}
  </script>
</body>
</html>
"""
    return html

