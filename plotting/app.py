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
    st.title("🗳️ US Senate 2026 — Static Flip Analysis & Chamber Balance of Power")
    st.caption(
        "A strictly static, non-interactive visual representation communicating the projected balance of power "
        "and seat flips under current 2026 polling. States are bounded by black borders and divided internally by white lines "
        "into their two US Senators. Circular transfer badges (⇄) mark the 7 decisive battlegrounds where polls project a party flip, "
        "accompanied by the 100-seat Majority Threshold Bar showing the path to 52 seats."
    )

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

    # Render static client-side dashboard (Map + Majority 50 Threshold Bar & Flip Ledger)
    dashboard_html = build_interactive_dashboard_html(
        senators_df, split_geojson, outlines_geojson, debug_mode=debug_mode
    )
    components.html(dashboard_html, height=710, scrolling=False)

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
                <div><span class="color-badge" style="background-color: #EAB308;"></span> <b>Golden Yellow:</b> Independent Senator (caucusing with DEM)</div>
                <div><span class="color-badge" style="background-color: #64748B;"></span> <b>Slate Gray:</b> Contested seat with no general election poll data yet</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with leg_col2:
        st.markdown(
            """
            <div class="legend-card">
                <b>🏛️ Representation & Seat Flips (2 Senators per State):</b><br>
                • <b>Outer Black Border:</b> Clearly separates each of the 50 US states.<br>
                • <b>Inner White Line:</b> Divides each state into its two Senate seats (West = Safe, East = 2026 Race).<br>
                • <b>Contested Races Border:</b> All 35 seats up for election in 2026 are highlighted with a crisp dashed white border.<br>
                • <b>⇄ Transfer Badges (Style 2):</b> Bold circular badges mark the 7 battlegrounds projecting a party flip:<br>
                  &nbsp;&nbsp;🔵 <b>Blue Badge (⇄):</b> Republican seat flipping to Democrat (AK, KY, ME, NE, NC, OH).<br>
                  &nbsp;&nbsp;🔴 <b>Red Badge (⇄):</b> Democratic seat flipping to Republican (MI).<br>
                • <b>Majority Bar:</b> Displays the 100-seat distribution across the 50-seat threshold (projecting 52 DEM vs 48 REP).
            </div>
            """,
            unsafe_allow_html=True,
        )



if __name__ == "__main__":
    main()
