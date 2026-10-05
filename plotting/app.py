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
    """Inject styling for clean container sizing and layout spacing."""
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="US Senate Elections Polls 2026",
        page_icon="🗳️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    set_custom_styles()

    # Title and concise description
    st.title("US Senate Elections Polls 2026")
    st.caption("2026 general election poll predictions and projected chamber balance of power.")

    # Check for debug mode via query parameter or sidebar control
    query_debug = st.query_params.get("debug", "").lower()
    default_idx = 0
    if query_debug in ("50", "all_50", "right"):
        default_idx = 1
    elif query_debug in ("100", "all_100", "all", "true"):
        default_idx = 2

    with st.sidebar:
        st.markdown("### 🛠️ Display & Debug Settings")
        debug_label = st.radio(
            "Seat Transfer Symbols (⇄) Display:",
            options=[
                "Normal: 7 Battleground Flips",
                "Debug: All 50 States (Right Halves)",
                "Debug: All 100 Seats (Both Halves)",
            ],
            index=default_idx,
            help=(
                "Render flip transfer badges (⇄) across all seats simultaneously to visually evaluate "
                "positioning, spatial clearance, and boundary alignment."
            ),
        )

    debug_mode_map = {
        "Normal: 7 Battleground Flips": "none",
        "Debug: All 50 States (Right Halves)": "all_50",
        "Debug: All 100 Seats (Both Halves)": "all_100",
    }
    debug_mode = debug_mode_map[debug_label]

    if debug_mode != "none":
        st.info(
            f"🛠️ **Debug Mode Active:** Visualizing seat symbols across "
            f"{'all 50 states (right half seats)' if debug_mode == 'all_50' else 'all 100 Senate seats (both halves)'}. "
            "Use the sidebar to switch modes or return to normal projection."
        )

    # Load data and GeoJSON collections
    senators_df = load_all_senators_data()
    split_geojson = generate_split_geojson()
    outlines_geojson = generate_state_outlines_geojson()

    # Render static client-side dashboard with integrated Gestalt map legend
    dashboard_html = build_interactive_dashboard_html(
        senators_df, split_geojson, outlines_geojson, debug_mode=debug_mode
    )
    components.html(dashboard_html, height=725, scrolling=False)


if __name__ == "__main__":
    main()
