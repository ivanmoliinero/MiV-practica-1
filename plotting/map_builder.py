"""
Map and chart construction module for the 2026 US Senate interactive visualization.

Renders:
1. Map: 100 split half-state polygons with white internal dividers and black state perimeters.
   No text abbreviation clutter and zero white background/lake artifacts.
2. Pie Chart: 100-seat pie chart without center text or legend clutter, displaying slice numbers.
   Sectors are consistently anchored across views (Republicans on right, Democrats on left).
3. Interactive client-side dashboard with dynamic color gradient transitions on hover.
"""

import json
from typing import List, Tuple
import pandas as pd
import plotly.graph_objects as go

from data_loader import COLOR_CATEGORIES, COLOR_PALETTE


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

    fig = go.Figure(data=[halves_trace, outlines_trace])

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
    Build the matching pie chart for the 100 Senate seats based on active view.
    Zero center text, no legend, sectors anchored consistently (REP on right, DEM on left).
    """
    if view == "composition":
        labels = ["Republicans", "Independents", "Democrats"]
        values = [53, 2, 45]
        colors = ["#DC2626", "#EAB308", "#2563EB"]
        text_colors = ["#FFFFFF", "#0F172A", "#FFFFFF"]
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
                textfont=dict(size=14, color=text_colors),
                hoverinfo="label+value+percent",
                hovertemplate="<b>%{label}</b><br>Seats: %{value} (%{percent})<extra></extra>",
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
    Both the Map and Pie Chart dynamically adapt between views with hardware-accelerated transitions:
    - View 1: Current Senate Composition (53 REP, 45 DEM, 2 IND)
    - View 2: 2026 Poll Predictions (43 REP + 3 Lean REP | 2 IND | 5 No Data | 3 Lean DEM + 44 DEM)
    Party sectors remain strictly locked in the same position (Republicans on right, Democrats on left).
    """
    comp_z = df["code_composition"].tolist()
    polls_z = df["code_combined"].tolist()
    tooltips = df["tooltip"].tolist()
    locs = df["feature_id"].tolist()
    state_names = [f["id"] for f in outlines_geojson["features"]]

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
    .dashboard-header {{
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
      margin-bottom: 12px;
    }}
    .hover-pill {{
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 18px;
      border-radius: 9999px;
      background: #1E293B;
      border: 1.5px solid #334155;
      color: #94A3B8;
      font-size: 0.88rem;
      cursor: pointer;
      transition: all 0.3s ease;
      user-select: none;
    }}
    .hover-pill:hover, .hover-pill.active {{
      background: #0F172A;
      border-color: #38BDF8;
      color: #F8FAFC;
      box-shadow: 0 0 14px rgba(56, 189, 248, 0.3);
    }}
    .pill-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      display: inline-block;
    }}
    .hover-divider {{
      font-size: 0.8rem;
      color: #64748B;
      letter-spacing: 0.05em;
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
  </style>
</head>
<body>
  <div class="dashboard-header">
    <div id="pill-comp" class="hover-pill active" title="Hover to view Current Senate Composition">
      <span class="pill-dot" style="background: #DC2626;"></span>
      <b>🏛️ Current Senate Composition</b> (53 REP · 45 DEM · 2 IND)
    </div>
    <span class="hover-divider">⟵ Hover to transition with dynamic gradient ⟶</span>
    <div id="pill-polls" class="hover-pill" title="Hover to view 2026 Poll Predictions">
      <span class="pill-dot" style="background: #2563EB;"></span>
      <b>📊 2026 Poll Predictions</b> (44 DEM · 43 REP · 6 Toss-Up)
    </div>
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
    const tooltips = {json.dumps(tooltips)};
    const stateNames = {json.dumps(state_names)};
    const colorscale = {json.dumps(colorscale_items)};

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

    Plotly.newPlot('map-container', [mapTraceHalves, mapTraceOutlines], mapLayout, {{ responsive: true, displayModeBar: false }});

    // Pie chart dataset 1: Current Senate Composition (Anchored: REP on right, IND in middle, DEM on left)
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
      hovertemplate: '<b>%{{label}}</b><br>Seats: %{{value}} (%{{percent}})<extra></extra>'
    }};

    // Pie chart dataset 2: 2026 Poll Predictions (Identical spatial anchoring: REP -> IND -> NO_DATA -> DEM)
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
      hovertemplate: '<b>%{{label}}</b><br>Seats: %{{value}} (%{{percent}})<extra></extra>'
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

    // Dynamic Hover Transition Logic
    let currentView = 'composition';
    let isPinned = false;

    function setView(view, pinned = false) {{
      if (isPinned && !pinned) return;
      if (pinned) isPinned = true;
      if (view === currentView) return;
      currentView = view;

      document.getElementById('pill-comp').classList.toggle('active', view === 'composition');
      document.getElementById('pill-polls').classList.toggle('active', view === 'polls');

      // Update Map: CSS transition on path.choroplethlocation smoothly animates fill gradient
      const targetZ = view === 'composition' ? compZ : pollsZ;
      Plotly.restyle('map-container', {{ z: [targetZ] }}, [0]);

      // Update Pie Chart dynamically using Plotly.react
      const targetPie = view === 'composition' ? pieCompData : piePollsData;
      Plotly.react('pie-container', [targetPie], pieLayout);
    }}

    // Pill Hover Listeners
    const pillComp = document.getElementById('pill-comp');
    const pillPolls = document.getElementById('pill-polls');

    pillComp.addEventListener('mouseenter', () => setView('composition'));
    pillPolls.addEventListener('mouseenter', () => setView('polls'));

    pillComp.addEventListener('click', () => {{ isPinned = true; setView('composition', true); }});
    pillPolls.addEventListener('click', () => {{ isPinned = true; setView('polls', true); }});

    // Map Hover Listeners: Hovering over map transitions to polls view, leaving returns to composition
    const mapDiv = document.getElementById('map-container');
    mapDiv.addEventListener('mouseenter', () => {{
      if (!isPinned) setView('polls');
    }});
    mapDiv.addEventListener('mouseleave', () => {{
      if (!isPinned) setView('composition');
    }});
  </script>
</body>
</html>
"""
    return html
