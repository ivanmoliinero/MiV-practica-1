"""
Map construction module for the 2026 US Senate interactive visualization.

Renders each state divided into two geographic halves representing the 100 US Senators.
Applies a dual-stroke hierarchy:
- Outer state perimeter: Solid black border (#000000, width=2.0) separating states.
- Internal state divider: Crisp white border (#FFFFFF, width=1.5) dividing each state into 2 halves.
"""

from typing import List, Tuple
import pandas as pd
import plotly.graph_objects as go

from data_loader import COLOR_CATEGORIES, COLOR_PALETTE


def _create_discrete_colorscale() -> Tuple[List[List], float, float]:
    """
    Construct a discrete Plotly colorscale mapping integer category indices to exact hex colors.

    Using [i/K, (i+1)/K] intervals with zmin=-0.5 and zmax=K-0.5 ensures each integer
    index lands strictly within its designated color step, avoiding boundary interpolation.
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
    Build the Plotly US Senate map with 100 split half-state polygons and crisp state boundaries.

    Args:
        df: 100-row DataFrame with all senator records and feature IDs.
        split_geojson: 100-feature GeoJSON FeatureCollection (2 halves per state).
        outlines_geojson: 50-feature GeoJSON FeatureCollection (merged state perimeters).
        view: "combined" (Default: Safe seats + 2026 poll predictions),
              "composition" (Current incumbent party for all 100 seats),
              "polls_only" (2026 contested races highlighted against muted safe seats).

    Returns:
        go.Figure: The complete, interactive Plotly figure.
    """
    colorscale, zmin, zmax = _create_discrete_colorscale()

    # Select the code column based on the active view
    if view == "composition":
        z_col = "code_composition"
    elif view == "polls_only":
        z_col = "code_polls_only"
    else:
        # Default: combined view
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
        showsubunits=False,  # Replaced by custom pixel-perfect black outlines
        showlakes=True,
        lakecolor="#E0F2FE",  # Subtle light blue lake fill
        showland=True,
        landcolor="#F8FAFC",
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        height=640,
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
