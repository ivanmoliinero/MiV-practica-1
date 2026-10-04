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
    debug_mode: str = "none",
) -> str:
    """
    Generate the hybrid static dashboard for the 2026 US Senate representation (Option B):
    - Left column: 50-state Albers split map with 2026 poll predictions,
      solid black state borders, white internal senator dividers,
      dashed white border overlay on the 35 contested seats, state postal abbreviations,
      and Style 2 circular flip badges (⇄) on the 7 battlegrounds where a party flip is projected.
    - Right column: Static Majority 50 Threshold Bar & Battleground Flip Ledger,
      displaying the 100-seat distribution, the 50-seat majority threshold line,
      the tally scoreboard (52 DEM majority vs 48 REP minority), and the 7 flips with margins.
    """
    polls_z = df["code_combined"].tolist()
    tooltips = df["tooltip"].tolist()
    locs = df["feature_id"].tolist()
    contested_locs = df[df["is_contested_2026"]]["feature_id"].tolist()
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

    # Build Flip Ledger HTML rows
    dem_flips_html = ""
    rep_flips_html = ""
    for f in flips:
        st_name = f["state"]
        ab = f["abbrev"]
        inc = f["party"]
        leader = f["poll_leader"]
        margin = f["poll_margin"]
        margin_str = f"+{margin:.1f} pp" if margin and margin > 0 else (f"{margin:.1f} pp" if margin else "N/A")

        row_html = f"""
            <div class="flip-card {'dem-card' if leader == 'DEM' else 'rep-card'}">
              <span class="flip-icon {'dem-icon' if leader == 'DEM' else 'rep-icon'}">⇄</span>
              <div class="flip-info">
                <span class="flip-name"><b>{st_name}</b> <span class="flip-abbrev">{ab}</span></span>
                <span class="flip-shift">{inc} → <b>{leader}</b></span>
              </div>
              <span class="flip-lead {'dem-lead' if leader == 'DEM' else 'rep-lead'}"><b>{margin_str}</b></span>
            </div>"""
        if leader == "DEM":
            dem_flips_html += row_html
        else:
            rep_flips_html += row_html

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
    body {{
      margin: 0;
      padding: 0;
      background: transparent;
      color: #F8FAFC;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 1.35fr 1fr;
      gap: 18px;
      height: 675px;
    }}
    #map-container {{
      width: 100%;
      height: 100%;
      background: rgba(15, 23, 42, 0.65);
      border: 1px solid #334155;
      border-radius: 12px;
      overflow: hidden;
      position: relative;
    }}
    #balance-panel {{
      width: 100%;
      height: 100%;
      background: #0F172A;
      border: 1px solid #334155;
      border-radius: 12px;
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
      overflow-y: auto;
    }}

    /* Panel Header */
    .panel-header {{
      border-bottom: 1px solid #1E293B;
      padding-bottom: 8px;
      margin-bottom: 10px;
    }}
    .panel-title {{
      font-size: 1.12rem;
      font-weight: 700;
      color: #F8FAFC;
      letter-spacing: -0.01em;
    }}
    .panel-subtitle {{
      font-size: 0.82rem;
      color: #94A3B8;
      margin-top: 2px;
    }}

    /* Tally Scoreboard */
    .tally-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .tally-box {{
      background: #1E293B;
      border-radius: 8px;
      padding: 9px 12px;
      border-left: 4px solid #64748B;
    }}
    .tally-box.dem-box {{
      border-left-color: #38BDF8;
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(14, 116, 144, 0.25));
    }}
    .tally-box.rep-box {{
      border-left-color: #F87171;
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(185, 28, 28, 0.20));
    }}
    .tally-header-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }}
    .party-title {{
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .party-title.dem-title {{ color: #7DD3FC; }}
    .party-title.rep-title {{ color: #FCA5A5; }}
    .tally-tag {{
      font-size: 0.70rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 9999px;
    }}
    .tally-tag.win-tag {{
      background: rgba(56, 189, 248, 0.20);
      color: #38BDF8;
      border: 1px solid rgba(56, 189, 248, 0.40);
    }}
    .tally-tag.loss-tag {{
      background: rgba(248, 113, 113, 0.15);
      color: #F87171;
      border: 1px solid rgba(248, 113, 113, 0.35);
    }}
    .tally-big {{
      font-size: 1.85rem;
      font-weight: 800;
      line-height: 1.1;
      color: #FFFFFF;
    }}
    .tally-total {{
      font-size: 0.90rem;
      font-weight: 500;
      color: #94A3B8;
    }}
    .tally-desc {{
      font-size: 0.72rem;
      color: #94A3B8;
      margin-top: 3px;
    }}

    /* Majority 50 Threshold Bar */
    .bar-section {{
      background: #1E293B;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 10px;
    }}
    .bar-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.80rem;
      margin-bottom: 14px;
      color: #E2E8F0;
    }}
    .bar-wrapper {{
      position: relative;
      width: 100%;
      height: 30px;
      background: #0B1120;
      border-radius: 6px;
      overflow: visible;
      margin-bottom: 8px;
    }}
    .bar-track {{
      display: flex;
      width: 100%;
      height: 100%;
      border-radius: 6px;
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
      top: -10px;
      bottom: -10px;
      width: 2.5px;
      background: #F8FAFC;
      box-shadow: 0 0 8px rgba(255, 255, 255, 0.9);
      z-index: 10;
      pointer-events: none;
    }}
    .majority-label-pin {{
      position: absolute;
      top: -22px;
      left: 50%;
      transform: translateX(-50%);
      background: #F8FAFC;
      color: #0F172A;
      font-size: 0.68rem;
      font-weight: 800;
      padding: 1px 6px;
      border-radius: 4px;
      white-space: nowrap;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.4);
      z-index: 11;
    }}
    .bar-sublegend {{
      display: flex;
      justify-content: space-between;
      font-size: 0.72rem;
      color: #94A3B8;
      margin-top: 4px;
    }}

    /* Flip Ledger Section */
    .ledger-section {{
      flex: 1;
      display: flex;
      flex-direction: column;
    }}
    .ledger-title {{
      font-size: 0.82rem;
      font-weight: 700;
      color: #F8FAFC;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .ledger-grid {{
      display: grid;
      grid-template-columns: 1.25fr 1fr;
      gap: 10px;
    }}
    .flip-col-header {{
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 5px;
    }}
    .flip-col-header.dem-head {{ color: #38BDF8; }}
    .flip-col-header.rep-head {{ color: #F87171; }}

    .flip-card {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #1E293B;
      border-radius: 6px;
      padding: 4px 8px;
      margin-bottom: 3.5px;
      font-size: 0.75rem;
      border: 1px solid #334155;
    }}
    .flip-card.dem-card {{ border-left: 3px solid #38BDF8; }}
    .flip-card.rep-card {{ border-left: 3px solid #F87171; }}

    .flip-icon {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      font-size: 0.70rem;
      font-weight: 900;
      color: #FFFFFF;
      margin-right: 6px;
      flex-shrink: 0;
    }}
    .flip-icon.dem-icon {{ background: #2563EB; }}
    .flip-icon.rep-icon {{ background: #DC2626; }}
    .flip-info {{
      display: flex;
      flex-direction: column;
      flex: 1;
    }}
    .flip-name {{
      color: #F8FAFC;
      line-height: 1.1;
    }}
    .flip-abbrev {{
      font-size: 0.70rem;
      color: #94A3B8;
      font-weight: 600;
    }}
    .flip-shift {{
      font-size: 0.68rem;
      color: #94A3B8;
    }}
    .flip-lead.dem-lead {{ color: #38BDF8; font-size: 0.78rem; }}
    .flip-lead.rep-lead {{ color: #F87171; font-size: 0.78rem; }}

    .net-summary-box {{
      background: linear-gradient(135deg, rgba(30, 41, 59, 0.9), rgba(14, 116, 144, 0.3));
      border: 1px solid #0284C7;
      border-radius: 8px;
      padding: 10px 12px;
      margin-top: 6px;
    }}
    .net-box-title {{
      font-size: 0.72rem;
      font-weight: 800;
      color: #38BDF8;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .net-box-val {{
      font-size: 1.05rem;
      font-weight: 800;
      color: #FFFFFF;
      margin: 2px 0;
    }}
    .net-box-desc {{
      font-size: 0.72rem;
      color: #CBD5E1;
      line-height: 1.3;
    }}

    /* Map styling */
    path.choroplethlocation {{
      transition: fill 0.3s ease !important;
    }}
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
  </style>
</head>
<body>
  <div class="dashboard-grid">
    <!-- Map Container -->
    <div id="map-container"></div>

    <!-- Balance of Power & Flip Ledger Panel -->
    <div id="balance-panel">
      <!-- Header -->
      <div class="panel-header">
        <div class="panel-title">🏛️ 2026 US Senate Balance of Power</div>
        <div class="panel-subtitle">100 Seats Total • <b>50 Seats</b> Threshold for Chamber Majority</div>
      </div>

      <!-- Tally Scoreboard -->
      <div class="tally-grid">
        <div class="tally-box dem-box">
          <div class="tally-header-row">
            <span class="party-title dem-title">DEMOCRATIC COALITION</span>
            <span class="tally-tag win-tag">+5 MAJORITY</span>
          </div>
          <div class="tally-big">{summary['projected_dem_total']} <span class="tally-total">/ 100</span></div>
          <div class="tally-desc">47 Poll Leads + 2 IND + 3 Safe Unpolled</div>
        </div>

        <div class="tally-box rep-box">
          <div class="tally-header-row">
            <span class="party-title rep-title">REPUBLICAN PARTY</span>
            <span class="tally-tag loss-tag">-5 MINORITY</span>
          </div>
          <div class="tally-big">{summary['projected_rep_total']} <span class="tally-total">/ 100</span></div>
          <div class="tally-desc">46 Poll Leads + 2 Safe Unpolled</div>
        </div>
      </div>

      <!-- Majority 50 Threshold Bar -->
      <div class="bar-section">
        <div class="bar-header">
          <span><b>Seat Balance Bar (0 to 100):</b></span>
          <span style="color: #38BDF8; font-weight: 700;">DEM crosses 50-Seat Mark</span>
        </div>

        <div class="bar-wrapper">
          <div class="majority-label-pin">50 Majority</div>
          <div class="majority-line"></div>
          <div class="bar-track">
            <div class="bar-seg seg-dem-safe" style="width: {summary['safe_dem_ind']}%;" title="{summary['safe_dem_ind']} Safe Democratic & Independent Seats">{summary['safe_dem_ind']} Safe</div>
            <div class="bar-seg seg-dem-holds" style="width: {summary['dem_holds']}%;" title="{summary['dem_holds']} Democratic Poll Holds">{summary['dem_holds']}</div>
            <div class="bar-seg seg-dem-flips" style="width: {summary['dem_flips']}%;" title="{summary['dem_flips']} Democratic Flips from GOP (AK, KY, ME, NE, NC, OH)">★ +6</div>
            <div class="bar-seg seg-unpolled" style="width: {summary['unpolled']}%;" title="{summary['unpolled']} Seats with No General Election Polls (3 DEM safe, 2 REP safe)">5</div>
            <div class="bar-seg seg-rep-flips" style="width: {summary['rep_flips']}%;" title="{summary['rep_flips']} Republican Flip from DEM (MI)">★ +1</div>
            <div class="bar-seg seg-rep-holds" style="width: {summary['rep_holds']}%;" title="{summary['rep_holds']} Republican Poll Holds">{summary['rep_holds']}</div>
            <div class="bar-seg seg-rep-safe" style="width: {summary['safe_rep']}%;" title="{summary['safe_rep']} Safe Republican Seats">{summary['safe_rep']} Safe</div>
          </div>
        </div>

        <div class="bar-sublegend">
          <span>🔵 <b>49</b> Direct Leads/Safe</span>
          <span>⚪ <b>5</b> Unpolled (3 DEM safe)</span>
          <span>🔴 <b>46</b> Direct Leads/Safe</span>
        </div>
      </div>

      <!-- Flip Ledger -->
      <div class="ledger-section">
        <div class="ledger-title">
          <span>⚡ 7 Decisive Battleground Flips (Poll Predictions) {debug_badge_tag}</span>
        </div>
        <div class="ledger-grid">
          <div>
            <div class="flip-col-header dem-head">🔵 Flips to Democrat (+6 Seats)</div>
            {dem_flips_html}
          </div>
          <div>
            <div class="flip-col-header rep-head">🔴 Flip to Republican (+1 Seat)</div>
            {rep_flips_html}

            <div class="net-summary-box">
              <div class="net-box-title">🏁 Net Projection</div>
              <div class="net-box-val">+5 Seats to Democrats</div>
              <div class="net-box-desc">
                Democrats overcome the 53-47 Republican majority, flipping the chamber to <b>52 DEM vs. 48 REP</b>.
              </div>
            </div>
          </div>
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
    const contestedLocs = {json.dumps(contested_locs)};
    const contestedSet = new Set(contestedLocs);
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
      geo: {{
        scope: 'usa',
        projection: {{ type: 'albers usa' }},
        showsubunits: false,
        showland: false,
        showlakes: false,
        showocean: false,
        showrivers: false,
        showcountries: false,
        bgcolor: 'rgba(0,0,0,0)'
      }},
      margin: {{ l: 0, r: 0, t: 0, b: 0 }},
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      hoverlabel: {{
        bgcolor: '#0F172A',
        font: {{ size: 13, color: '#F8FAFC' }},
        bordercolor: '#334155'
      }},
      showlegend: false
    }};

    Plotly.newPlot('map-container', [mapTraceHalves, mapTraceOutlines, mapTraceText, mapTraceFlips], mapLayout, {{ responsive: true, displayModeBar: false }});

    // Dedicated top-level overlay layer for contested seats' dashed borders (visible over both black and white borders)
    function updateContestedOverlay() {{
      const choroplethGroup = document.querySelector('#map-container .choropleth') || 
                              document.querySelector('#map-container .geolayer');
      if (!choroplethGroup) return;

      let overlayGroup = document.getElementById('contested-stroke-overlay');
      if (!overlayGroup) {{
        overlayGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        overlayGroup.setAttribute('id', 'contested-stroke-overlay');
        overlayGroup.style.pointerEvents = 'none';
        choroplethGroup.appendChild(overlayGroup);
      }}

      // Populate overlay paths
      if (overlayGroup.children.length === 0) {{
        const allPaths = document.querySelectorAll('#map-container path.choroplethlocation');
        const numHalves = Math.min(locs.length, allPaths.length);
        for (let idx = 0; idx < numHalves; idx++) {{
          const p = allPaths[idx];
          const d = p.__data__;
          let loc = null;
          if (d) {{
            loc = d.id || (d.properties && d.properties.id) || (d.properties && (d.properties.state + '_' + d.properties.side));
          }}
          if (!loc) {{
            loc = locs[idx];
          }}
          if (contestedSet.has(loc)) {{
            const overlayPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            overlayPath.setAttribute('d', p.getAttribute('d'));
            overlayPath.setAttribute('class', 'contested-seat-border');
            overlayPath.style.fill = 'none';
            overlayPath.style.stroke = '#FFFFFF';
            overlayPath.style.strokeWidth = '2.6px';
            overlayPath.style.strokeDasharray = '5, 3.5';
            overlayPath.style.strokeLinecap = 'round';
            overlayPath.style.filter = 'drop-shadow(0 0 1.2px #000000) drop-shadow(0 0 2px rgba(255, 255, 255, 0.5))';
            overlayPath.style.pointerEvents = 'none';
            overlayGroup.appendChild(overlayPath);
          }}
        }}
      }}
      overlayGroup.style.opacity = '1';
    }}

    // Ensure state abbreviation text labels and flip badges stay strictly on the top-most visual layer
    function bringTextToFront() {{
      const geoContainer = document.querySelector('#map-container .geo') || 
                           document.querySelector('#map-container .geolayer');
      const scatterGroups = document.querySelectorAll('#map-container .scattergeo, #map-container g.trace.scattergeo');
      const overlayGroup = document.getElementById('contested-stroke-overlay');

      if (geoContainer) {{
        if (overlayGroup && overlayGroup.parentNode === geoContainer) {{
          geoContainer.appendChild(overlayGroup);
        }}
        scatterGroups.forEach(sg => geoContainer.appendChild(sg));
      }}
    }}

    // Initialize stroke hierarchy and text layers on load
    setTimeout(() => {{
      updateContestedOverlay();
      bringTextToFront();
    }}, 200);
  </script>
</body>
</html>
"""
    return html

