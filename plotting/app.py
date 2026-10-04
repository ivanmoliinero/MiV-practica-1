"""
Streamlit application for the interactive 2026 US Senate Election Map.

Each US state is geographically divided into two halves representing its two US Senators:
- State borders: Solid black line delineates state boundaries.
- Internal division: Crisp white line divides each state into two senator seats.
- Left / West half: Safe seat not up for election in 2026 (or Senator 1).
- Right / East half: Seat up for election in 2026 (or Senator 2).
- Controls:
  - Single hover button to preview 2026 Poll Predictions with a dynamic gradient transition (move away to return).
  - Checkbox to isolate the 35 contested races in play (muting general safe seats).
- Accompanied by a synchronized Pie Chart with consistently anchored party sectors.
"""

import streamlit as st
import streamlit.components.v1 as components

from data_loader import load_all_senators_data
from geo_splitter import generate_split_geojson, generate_state_outlines_geojson
from map_builder import build_interactive_dashboard_html


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
            margin-top: 10px;
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
        page_title="US Senate 2026 — Geographic Seat Map & Composition",
        page_icon="🗳️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    set_custom_styles()

    # Title and concise description
    st.title("🗳️ US Senate 2026 — Interactive Geographic Representation & Balance")
    st.caption(
        "Each state is bounded by a black border and divided internally by a white line into two halves "
        "representing its two US Senators. Hover over the button above the map to transition between "
        "Current Senate and 2026 Poll Predictions with a dynamic gradient. Use the checkbox to isolate the 35 races in play."
    )

    # Load data and GeoJSON collections
    senators_df = load_all_senators_data()
    split_geojson = generate_split_geojson()
    outlines_geojson = generate_state_outlines_geojson()

    # Render interactive client-side dashboard (Map + Pie Chart with hover gradient transition)
    dashboard_html = build_interactive_dashboard_html(senators_df, split_geojson, outlines_geojson)
    components.html(dashboard_html, height=660, scrolling=False)

    # Clean Visual Legend
    leg_col1, leg_col2 = st.columns(2)

    with leg_col1:
        st.markdown(
            """
            <div class="legend-card">
                <b>🎨 Color Legend:</b><br>
                <div><span class="color-badge" style="background-color: #2563EB;"></span> <b>Solid Blue:</b> Democratic Incumbent / Solid Democrat Lead (> 2 pp)</div>
                <div><span class="color-badge" style="background-color: #93C5FD;"></span> <b>Light Blue:</b> Toss-Up Race — Slight Democrat Lead (≤ 2 pp)</div>
                <div><span class="color-badge" style="background-color: #DC2626;"></span> <b>Solid Red:</b> Republican Incumbent / Solid Republican Lead (> 2 pp)</div>
                <div><span class="color-badge" style="background-color: #FCA5A5;"></span> <b>Light Red:</b> Toss-Up Race — Slight Republican Lead (≤ 2 pp)</div>
                <div><span class="color-badge" style="background-color: #EAB308;"></span> <b>Golden Yellow:</b> Independent Senator</div>
                <div><span class="color-badge" style="background-color: #64748B;"></span> <b>Slate Gray:</b> Contested seat with no poll data yet</div>
                <div><span class="color-badge" style="background-color: #1E293B;"></span> <b>Dark Slate:</b> Safe seat unpainted (in isolated view)</div>
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
                • <b>Interactivity:</b> Hover over the button to view 2026 Polls (move cursor away to return to Current Senate). Check the box to isolate only the 35 contested races.
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
