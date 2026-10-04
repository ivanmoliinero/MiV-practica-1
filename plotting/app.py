"""
Streamlit application for the interactive 2026 US Senate Election Map.

Each US state is geographically divided into two halves representing its two US Senators:
- State borders: Solid black line delineates state boundaries.
- Internal division: Crisp white line divides each state into two senator seats.
- Left / West half: Safe seat not up for election in 2026 (or Senator 1).
- Right / East half: Seat up for election in 2026 (or Senator 2).
"""

import streamlit as st

from data_loader import load_all_senators_data
from geo_splitter import generate_split_geojson, generate_state_outlines_geojson
from map_builder import build_figure


def set_custom_styles() -> None:
    """Inject styling for clean typography, container sizing, and visual legend."""
    st.markdown(
        """
        <style>
        .legend-card {
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 18px;
            margin-top: 8px;
            font-size: 0.88rem;
            color: #1E293B;
            line-height: 1.6;
        }
        .color-badge {
            display: inline-block;
            width: 14px;
            height: 14px;
            border-radius: 3px;
            margin-right: 8px;
            vertical-align: middle;
            border: 1px solid rgba(0, 0, 0, 0.15);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="US Senate 2026 — Geographic Seat Map",
        page_icon="🗳️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    set_custom_styles()

    # Title and concise description
    st.title("🗳️ US Senate 2026 — Interactive Geographic Representation")
    st.caption(
        "Each state is clearly bounded by black borders and divided internally by a white line "
        "into two halves representing its two US Senators. The left (west) half depicts the safe seat "
        "not up for election, while the right (east) half depicts the seat up for election in 2026. "
        "Hover over any half for detailed senator and polling data."
    )

    # View Mode Selection Radio
    view_label = st.radio(
        "Select Map View Mode:",
        options=[
            "🏛️ Current Situation + 2026 Polls (Default: Safe Incumbents + Poll Predictions)",
            "📋 Current Senate Composition (All 100 Incumbent Senators)",
            "📊 2026 Contested Races Highlighted (Safe Seats Muted)",
        ],
        index=0,
        horizontal=True,
    )

    if "Current Situation" in view_label:
        active_view = "combined"
    elif "Current Senate Composition" in view_label:
        active_view = "composition"
    else:
        active_view = "polls_only"

    # Load data and GeoJSON collections
    senators_df = load_all_senators_data()
    split_geojson = generate_split_geojson()
    outlines_geojson = generate_state_outlines_geojson()

    # Render interactive Plotly choropleth
    fig = build_figure(senators_df, split_geojson, outlines_geojson, view=active_view)
    st.plotly_chart(fig, width="stretch")

    # Clean Visual Legend
    leg_col1, leg_col2 = st.columns(2)

    with leg_col1:
        st.markdown(
            """
            <div class="legend-card">
                <b>🎨 Color Legend:</b><br>
                <div><span class="color-badge" style="background-color: #2563EB;"></span> <b>Blue:</b> Democratic Party / Democrat Leading in Polls</div>
                <div><span class="color-badge" style="background-color: #DC2626;"></span> <b>Red:</b> Republican Party / Republican Leading in Polls</div>
                <div><span class="color-badge" style="background-color: #7C3AED;"></span> <b>Purple:</b> Independent Senator</div>
                <div><span class="color-badge" style="background-color: #F59E0B;"></span> <b>Amber:</b> Toss-Up Race (Poll margin ≤ ±2.0 pp)</div>
                <div><span class="color-badge" style="background-color: #64748B;"></span> <b>Slate Gray:</b> Contested seat with no poll data yet</div>
                <div><span class="color-badge" style="background-color: #E2E8F0;"></span> <b>Light Gray:</b> Safe seat (in contested-only view)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with leg_col2:
        st.markdown(
            """
            <div class="legend-card">
                <b>🏛️ Representation Structure (2 Senators per State):</b><br>
                • <b>Outer Black Border:</b> Clearly separates each of the 50 US states.<br>
                • <b>Inner White Line:</b> Divides each state into its two Senate seats.<br>
                • <b>Left (West) Half:</b> Safe senator not up for election in 2026.<br>
                • <b>Right (East) Half:</b> Contested seat up for election in 2026.<br>
                • <b>Interactivity:</b> Hover over either half of any state to inspect incumbent names, terms, vote margins, and poll averages.
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
