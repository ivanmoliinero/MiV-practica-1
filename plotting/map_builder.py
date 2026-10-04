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

from data_loader import COLOR_CATEGORIES, COLOR_PALETTE
from state_centroids import STATE_LOWER_RIGHT_COORDS, STATE_TO_ABBREV


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


def build_figure(
    df: pd.DataFrame,
    split_geojson: dict,
    outlines_geojson: dict,
    view: str = "combined",
) -> go.Figure:
    """
    Build the Plotly US Senate map with 100 split half-state polygons
    and crisp black state boundaries (no text abbreviations, no white artifacts).
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

    fig = go.Figure(data=[halves_trace, outlines_trace, text_trace])

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
) -> str:
    """
    Generate an interactive client-side dashboard with the Map and Pie Chart side-by-side.
    Controls:
    - Single hover button: Hover over it to view 2026 Poll Predictions, move away to return to Current Senate.
      Clicking the button locks/pins the view.
    - Checkbox: Isolate 2026 poll races only (mutes safe seats and focuses pie chart on 35 contested races).
    - Subtle distinct dashed border on contested seats when poll predictions are active.
    """
    comp_z = df["code_composition"].tolist()
    polls_z = df["code_combined"].tolist()
    isolated_z = df["code_polls_only"].tolist()
    tooltips = df["tooltip"].tolist()
    locs = df["feature_id"].tolist()
    contested_locs = df[df["is_contested_2026"]]["feature_id"].tolist()
    state_names = [f["id"] for f in outlines_geojson["features"]]
    abbrev_lats = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][0] for s in state_names]
    abbrev_lons = [STATE_LOWER_RIGHT_COORDS[STATE_TO_ABBREV[s]][1] for s in state_names]
    abbrev_texts = [STATE_TO_ABBREV[s] for s in state_names]

    colorscale_items = []
    k = len(COLOR_CATEGORIES)
    for i, cat in enumerate(COLOR_CATEGORIES):
        color = COLOR_PALETTE[cat]
        colorscale_items.append([i / k, color])
        colorscale_items.append([(i + 1) / k, color])

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
    .controls-bar {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 20px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }}
    .hover-btn {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 9px 22px;
      border-radius: 9999px;
      background: #1E293B;
      border: 1.5px solid #334155;
      color: #F8FAFC;
      font-size: 0.90rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      user-select: none;
      box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25);
    }}
    .hover-btn:hover, .hover-btn.active {{
      background: #0F172A;
      border-color: #38BDF8;
      color: #38BDF8;
      box-shadow: 0 0 16px rgba(56, 189, 248, 0.35);
      transform: translateY(-1px);
    }}
    .hover-btn.pinned {{
      border-color: #F59E0B;
      color: #F59E0B;
      box-shadow: 0 0 16px rgba(245, 158, 11, 0.35);
    }}
    .checkbox-container {{
      display: inline-flex;
      align-items: center;
      gap: 9px;
      cursor: pointer;
      user-select: none;
      font-size: 0.88rem;
      color: #CBD5E1;
      background: #1E293B;
      padding: 8px 18px;
      border-radius: 9999px;
      border: 1.5px solid #334155;
      transition: all 0.25s ease;
    }}
    .checkbox-container:hover {{
      border-color: #64748B;
      color: #FFFFFF;
    }}
    .checkbox-container input {{
      cursor: pointer;
      accent-color: #38BDF8;
      width: 16px;
      height: 16px;
    }}
    .dashboard-grid {{
      display: grid;
      grid-template-columns: 1fr 340px;
      gap: 16px;
      height: 590px;
    }}
    #map-container {{
      width: 100%;
      height: 100%;
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid #334155;
      border-radius: 10px;
      overflow: hidden;
    }}
    #pie-container {{
      width: 100%;
      height: 100%;
      background: rgba(15, 23, 42, 0.5);
      border: 1px solid #334155;
      border-radius: 10px;
      overflow: hidden;
    }}
    /* Hardware-accelerated dynamic color gradient transition for all map polygon fills */
    path.choroplethlocation {{
      transition: fill 0.65s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    /* Clean readable styling for state abbreviation labels in the lower-right */
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
  </style>
</head>
<body>
  <div class="controls-bar">
    <!-- Single hover button -->
    <button id="hover-toggle-btn" class="hover-btn" title="Hover over this button to preview 2026 Polls. Move away to return to Current Senate. Click to lock.">
      <span id="btn-icon">⚡</span>
      <span id="btn-text">Hover for 2026 Poll Predictions</span>
    </button>

    <!-- Checkbox to isolate 2026 poll results -->
    <label class="checkbox-container">
      <input type="checkbox" id="isolate-chk">
      <span><b>Isolate 2026 Poll Races</b> (Mute safe seats)</span>
    </label>
  </div>

  <div class="dashboard-grid">
    <div id="map-container"></div>
    <div id="pie-container"></div>
  </div>

  <script>
    const splitGeojson = {json.dumps(split_geojson)};
    const outlinesGeojson = {json.dumps(outlines_geojson)};
    const locs = {json.dumps(locs)};
    const compZ = {json.dumps(comp_z)};
    const pollsZ = {json.dumps(polls_z)};
    const isolatedZ = {json.dumps(isolated_z)};
    const tooltips = {json.dumps(tooltips)};
    const stateNames = {json.dumps(state_names)};
    const colorscale = {json.dumps(colorscale_items)};
    const contestedLocs = {json.dumps(contested_locs)};
    const contestedSet = new Set(contestedLocs);
    const abbrevLons = {json.dumps(abbrev_lons)};
    const abbrevLats = {json.dumps(abbrev_lats)};
    const abbrevTexts = {json.dumps(abbrev_texts)};

    // Map traces definition
    const mapTraceHalves = {{
      type: 'choropleth',
      geojson: splitGeojson,
      locations: locs,
      featureidkey: 'id',
      z: compZ,
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
      hoverinfo: 'skip'
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
      }}
    }};

    Plotly.newPlot('map-container', [mapTraceHalves, mapTraceOutlines, mapTraceText], mapLayout, {{ responsive: true, displayModeBar: false }});

    // Pie chart dataset 1: Current Senate Composition (100 seats: REP on right, IND in middle, DEM on left)
    const pieCompData = {{
      type: 'pie',
      labels: ['Republicans', 'Independents', 'Democrats'],
      values: [53, 2, 45],
      hole: 0,
      rotation: 0,
      direction: 'clockwise',
      sort: false,
      marker: {{
        colors: ['#DC2626', '#EAB308', '#2563EB'],
        line: {{ color: '#0F172A', width: 1.5 }}
      }},
      textinfo: 'value',
      textposition: 'auto',
      textfont: {{
        size: 15,
        color: ['#FFFFFF', '#0F172A', '#FFFFFF']
      }},
      hoverinfo: 'skip'
    }};

    // Pie chart dataset 2: 2026 Poll Predictions (100 seats: identically anchored REP -> IND -> NO_DATA -> DEM)
    const piePollsData = {{
      type: 'pie',
      labels: [
        'Solid Republican (> 2 pp)',
        'Toss-Up (Lean REP ≤ 2 pp)',
        'Independent',
        'No Poll Data',
        'Toss-Up (Lean DEM ≤ 2 pp)',
        'Solid Democrat (> 2 pp)'
      ],
      values: [43, 3, 2, 5, 3, 44],
      hole: 0,
      rotation: 0,
      direction: 'clockwise',
      sort: false,
      marker: {{
        colors: ['#DC2626', '#FCA5A5', '#EAB308', '#64748B', '#93C5FD', '#2563EB'],
        line: {{ color: '#0F172A', width: 1.5 }}
      }},
      textinfo: 'value',
      textposition: 'auto',
      textfont: {{
        size: 14,
        color: ['#FFFFFF', '#0F172A', '#0F172A', '#FFFFFF', '#0F172A', '#FFFFFF']
      }},
      hoverinfo: 'skip'
    }};

    // Pie chart dataset 3: Isolated 2026 Poll Races (35 contested seats in election)
    const pieIsolatedData = {{
      type: 'pie',
      labels: [
        'Solid Republican (> 2 pp)',
        'Toss-Up (Lean REP ≤ 2 pp)',
        'No Poll Data',
        'Toss-Up (Lean DEM ≤ 2 pp)',
        'Solid Democrat (> 2 pp)'
      ],
      values: [12, 3, 5, 3, 12],
      hole: 0,
      rotation: 0,
      direction: 'clockwise',
      sort: false,
      marker: {{
        colors: ['#DC2626', '#FCA5A5', '#64748B', '#93C5FD', '#2563EB'],
        line: {{ color: '#0F172A', width: 1.5 }}
      }},
      textinfo: 'value',
      textposition: 'auto',
      textfont: {{
        size: 14,
        color: ['#FFFFFF', '#0F172A', '#FFFFFF', '#0F172A', '#FFFFFF']
      }},
      hoverinfo: 'skip'
    }};

    const pieLayout = {{
      margin: {{ l: 15, r: 15, t: 25, b: 25 }},
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      showlegend: false,
      annotations: []
    }};

    // Initial render of Pie Chart (clean full pie with numbers, zero center text, zero legend)
    Plotly.newPlot('pie-container', [pieCompData], pieLayout, {{ responsive: true, displayModeBar: false }});

    // Control Elements
    const hoverBtn = document.getElementById('hover-toggle-btn');
    const btnText = document.getElementById('btn-text');
    const isolateChk = document.getElementById('isolate-chk');

    let isButtonHovered = false;
    let isPinned = false;

    // Dedicated top-level overlay layer for contested seats' dashed borders (visible over both black and white borders)
    function updateContestedOverlay(showPolls) {{
      const choroplethGroup = document.querySelector('#map-container .choropleth') || 
                              document.querySelector('#map-container .geolayer');
      if (!choroplethGroup) return;

      let overlayGroup = document.getElementById('contested-stroke-overlay');
      if (!overlayGroup) {{
        overlayGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        overlayGroup.setAttribute('id', 'contested-stroke-overlay');
        overlayGroup.style.pointerEvents = 'none';
        overlayGroup.style.transition = 'opacity 0.35s cubic-bezier(0.4, 0, 0.2, 1)';
        choroplethGroup.appendChild(overlayGroup);
      }}

      // Populate overlay paths if empty
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
      }} else {{
        // Synchronize path geometry on update or resize
        const allPaths = document.querySelectorAll('#map-container path.choroplethlocation');
        let overlayIdx = 0;
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
          if (contestedSet.has(loc) && overlayIdx < overlayGroup.children.length) {{
            overlayGroup.children[overlayIdx].setAttribute('d', p.getAttribute('d'));
            overlayIdx++;
          }}
        }}
      }}

      overlayGroup.style.opacity = showPolls ? '1' : '0';
    }}

    // Ensure state abbreviation text labels stay strictly on the top-most visual layer
    function bringTextToFront() {{
      const geoContainer = document.querySelector('#map-container .geo') || 
                           document.querySelector('#map-container .geolayer');
      const scatterGroup = document.querySelector('#map-container .scattergeo') ||
                           document.querySelector('#map-container g.trace.scattergeo');
      const overlayGroup = document.getElementById('contested-stroke-overlay');

      if (geoContainer) {{
        // Ensure contested dashed overlay is above choropleth
        if (overlayGroup && overlayGroup.parentNode === geoContainer) {{
          geoContainer.appendChild(overlayGroup);
        }}
        // Ensure scattergeo text labels are above everything
        if (scatterGroup) {{
          geoContainer.appendChild(scatterGroup);
        }}
      }}
    }}

    function updateDashboard() {{
      const isIsolated = isolateChk.checked;
      const showPolls = isButtonHovered || isPinned || isIsolated;

      // Update button text and visual classes
      if (isPinned) {{
        hoverBtn.classList.add('pinned', 'active');
        btnText.textContent = '🔒 Locked on 2026 Polls (Click to unlock)';
      }} else if (isButtonHovered) {{
        hoverBtn.classList.add('active');
        hoverBtn.classList.remove('pinned');
        btnText.textContent = isIsolated
          ? '📊 Viewing 2026 Polls (Isolated)'
          : '📊 Viewing 2026 Polls (Move away for Current Senate)';
      }} else if (isIsolated) {{
        hoverBtn.classList.remove('pinned', 'active');
        btnText.textContent = '⚡ 2026 Races Isolated (35 Seats)';
      }} else {{
        hoverBtn.classList.remove('pinned', 'active');
        btnText.textContent = '⚡ Hover for 2026 Poll Predictions';
      }}

      // Select Map Z dataset
      let targetZ;
      if (isIsolated) {{
        targetZ = isolatedZ; // 35 contested seats colored by polls, 65 safe seats muted
      }} else if (showPolls) {{
        targetZ = pollsZ;    // 100 seats: safe seats with party, contested with polls
      }} else {{
        targetZ = compZ;     // 100 seats: incumbent party composition
      }}

      // Restyle Map: CSS handles smooth dynamic gradient transition on polygon fills
      Plotly.restyle('map-container', {{ z: [targetZ] }}, [0]).then(() => {{
        updateContestedOverlay(showPolls);
        bringTextToFront();
      }});
      // Apply immediately for instantaneous visual feedback
      updateContestedOverlay(showPolls);
      bringTextToFront();
      requestAnimationFrame(bringTextToFront);

      // Select Pie Chart dataset
      let targetPie;
      if (isIsolated) {{
        targetPie = pieIsolatedData;
      }} else if (showPolls) {{
        targetPie = piePollsData;
      }} else {{
        targetPie = pieCompData;
      }}

      // Update Pie Chart reactively
      Plotly.react('pie-container', [targetPie], pieLayout);
    }}

    // Single Button Hover Listeners
    hoverBtn.addEventListener('mouseenter', () => {{
      isButtonHovered = true;
      updateDashboard();
      bringTextToFront();
    }});

    hoverBtn.addEventListener('mouseleave', () => {{
      isButtonHovered = false;
      updateDashboard();
      bringTextToFront();
    }});

    hoverBtn.addEventListener('click', () => {{
      isPinned = !isPinned;
      updateDashboard();
      bringTextToFront();
    }});

    // Checkbox Change Listener
    isolateChk.addEventListener('change', () => {{
      updateDashboard();
      bringTextToFront();
    }});

    // Initialize stroke hierarchy and bring text to front on first load
    setTimeout(() => {{
      updateContestedOverlay(false);
      bringTextToFront();
    }}, 250);
  </script>
</body>
</html>
"""
    return html
