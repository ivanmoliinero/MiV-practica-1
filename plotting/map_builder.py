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
import os
from typing import List, Tuple
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import plotly.graph_objects as go

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_UI_DIR = os.path.join(_CURRENT_DIR, "ui")
_JINJA_ENV = Environment(
    loader=FileSystemLoader(_UI_DIR),
    autoescape=False,
)


def _load_ui_asset(filename: str) -> str:
    """Read a frontend asset (CSS, JS) from the ui directory."""
    path = os.path.join(_UI_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


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
from state_vep import STATE_VEP


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
    # Prepare both z datasets for seamless client-side filtering via Plotly.restyle
    polls_z_combined = df["code_combined"].tolist()
    polls_z_only = df["code_polls_only"].tolist()
    polls_z_initial = polls_z_only if view == "polls_only" else polls_z_combined

    tooltips = df["tooltip"].tolist()
    locs = df["feature_id"].tolist()
    contested_locs = df[df["is_contested_2026"]]["feature_id"].tolist()
    contested_patterns = {
        row["feature_id"]: f"hatch-{row['cat_combined'].lower()}"
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

    legend_colors_combined_html = """
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead / Safe</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#EAB308;"></span> <span>Independent</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <span>Unpolled</span></div>
    """

    dem_flip_states = ", ".join(f["abbrev"] for f in flips if f["flip_incoming_party"] == "DEM")
    rep_flip_states = ", ".join(f["abbrev"] for f in flips if f["flip_incoming_party"] == "REP")

    rep_flip_bar_html = (
        f'<div class="bar-seg seg-rep-flips" style="width: {summary["rep_flips"]}%;" title="{summary["rep_flips"]} Republican Flip from DEM ({rep_flip_states})">+{summary["rep_flips"]}★</div>'
        if summary["rep_flips"] > 0
        else ""
    )
    rep_flip_legend_html = (
        f'<div class="legend-item"><span class="legend-swatch" style="background:#F87171;"></span> <b>+{summary["rep_flips"]}</b> REP Flip (Gain)</div>'
        if summary["rep_flips"] > 0
        else ""
    )

    legend_colors_polls_only_html = f"""
          <div class="legend-item"><span class="legend-swatch" style="background:#2563EB;"></span> <span>Dem Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#93C5FD;"></span> <span>Dem Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#DC2626;"></span> <span>Rep Lead</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#FCA5A5;"></span> <span>Rep Toss-Up (≤2 pp)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#64748B;"></span> <span>Unpolled ({summary['unpolled']} seats)</span></div>
          <div class="legend-item"><span class="legend-swatch" style="background:#1E293B; border: 1px solid #475569;"></span> <span>Safe / Muted (65 seats)</span></div>
    """

    # ---------------------------------------------------------------------------
    # Voter-weight heatmap data preparation
    # ---------------------------------------------------------------------------
    # Each row in df corresponds 1-to-1 with 'locs' (100 feature_ids in same order).
    # DEM leading seats have positive z: +dem_voter_weight (blue intensity)
    # REP leading seats have negative z: -rep_voter_weight (red intensity)
    # Safe / Uncontested seats have z: 0.0 (dark slate neutral)

    heatmap_z: list = []
    heatmap_tooltips: list = []
    dem_weights: list = []
    rep_weights: list = []

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
            heatmap_z.append(-w)  # Negative z for Republican continuous gradient
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
        max(rep_weights) if rep_weights else 1.0
    )

    # Continuous diverging scale centered at 0:
    # 0.0 -> -max_voter_weight (Deep Red, max REP supporters)
    # ~0.485 -> min REP supporters (Light Red)
    # 0.495 to 0.505 -> z = 0 (Uncontested / Safe seats, Dark Slate Neutral)
    # ~0.515 -> min DEM supporters (Light Blue)
    # 1.0 -> +max_voter_weight (Deep Blue, max DEM supporters)
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

    legend_colors_initial_html = (
        legend_colors_polls_only_html if view == "polls_only" else legend_colors_combined_html
    )

    # Legend HTML for the voter-weight heatmap mode with explicit gradient swatches and numbers
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

    debug_badge_tag = (
        f'<span style="font-size:0.70rem; background:#D97706; color:#FFFFFF; padding:2px 7px; border-radius:4px; margin-left:8px; font-weight:700; vertical-align:middle;">'
        f'DEBUG: {len(badge_records)} Symbols Active</span>'
        if debug_mode != "none"
        else ""
    )

    config = {
        "splitGeojson": split_geojson,
        "outlinesGeojson": outlines_geojson,
        "locs": locs,
        "pollsZCombined": polls_z_combined,
        "pollsZOnly": polls_z_only,
        "legendColorsCombinedHtml": legend_colors_combined_html,
        "legendColorsPollsOnlyHtml": legend_colors_polls_only_html,
        "legendColorsHeatmapHtml": legend_colors_heatmap_html,
        "tooltips": tooltips,
        "stateNames": state_names,
        "colorscale": colorscale_items,
        "contestedPatterns": contested_patterns,
        "abbrevLons": abbrev_lons,
        "abbrevLats": abbrev_lats,
        "abbrevTexts": abbrev_texts,
        "flipLons": flip_lons,
        "flipLats": flip_lats,
        "flipColors": flip_colors,
        "flipTexts": flip_texts,
        "flipTooltips": flip_tooltips,
        "numCategories": k,
        "heatmapZ": heatmap_z,
        "heatmapColorscale": heatmap_colorscale,
        "heatmapTooltips": heatmap_tooltips,
        "heatmapZmin": -round(max_voter_weight),
        "heatmapZmax": round(max_voter_weight),
    }

    css_content = _load_ui_asset("dashboard.css")
    js_content = _load_ui_asset("dashboard.js")
    template = _JINJA_ENV.get_template("dashboard.html")

    return template.render(
        css_content=css_content,
        js_content=js_content,
        config_json=json.dumps(config),
        legend_colors_initial_html=legend_colors_initial_html,
        debug_badge_tag=debug_badge_tag,
        summary=summary,
        dem_flip_states=dem_flip_states,
        rep_flip_bar_html=rep_flip_bar_html,
        rep_flip_legend_html=rep_flip_legend_html,
    )

