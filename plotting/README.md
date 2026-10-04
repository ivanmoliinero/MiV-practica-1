# US Senate 2026 — Balance of Power & Seat Flip Dashboard

A static, publication-grade data visualization communicating the 2026 US Senate election balance of power and projected seat flips based on empirical polling data.

---

## Architecture & Key Components

- **`app.py`**: Streamlit application entry point. Coordinates layout, query parameters, sidebar controls, and the embedded client-side dashboard component.
- **`map_builder.py`**: Constructs the synchronized client-side dashboard:
  - 50-state Albers split map (100 half-state polygons representing individual Senate seats).
  - Dashed white border overlays around all 35 seats up for election in 2026.
  - Circular transfer badges (`⇄`) marking battleground seats projected to flip party control.
  - 50-Seat Majority Threshold Bar (0 to 100 seats) and 7-seat battleground flip ledger.
- **`state_centroids.py`**: Geographical configuration containing:
  - `STATE_CENTROIDS`: Geographical center for state labels.
  - `STATE_LOWER_RIGHT_COORDS`: Strict south-east polygon coordinates for postal abbreviations.
  - `SEAT_SYMBOL_COORDS`: Dedicated `(lat, lon)` coordinates for all 100 individual Senate seats (`<State>_left` and `<State>_right`), mathematically verified to fall strictly within half-state polygons.
  - `get_seat_symbol_coord`: Dynamic coordinate resolver for any state name, abbreviation, or feature ID.
- **`data_loader.py`**: Data pipeline merging incumbent Senate composition (`data/senate_composition_2026.csv`) with aggregated 2026 general election polls (`data/us_senate_polls_2026.csv`), calculating party flips and balance of power metrics.
- **`geo_splitter.py`**: Divides state boundary polygons along their geometric bounding box bisector into West (`_left`) and East (`_right`) senator halves, with automated caching (`_us_states_split.geojson` and `_us_states_outlines.geojson`).

---

## How to Run

From the repository root or project directory (`practica-1`):

```bash
uv run streamlit run plotting/app.py
```

The application will launch locally at `http://localhost:8501/`.

---

## Seat Symbol Debug Mode

### Purpose of Debug Mode
In standard production mode, the transfer badge (`⇄`) is only rendered on seats where 2026 polling projects a party flip (the 7 decisive battlegrounds: **AK, KY, ME, NE, NC, OH** flipping to DEM, and **MI** flipping to REP).

Debug mode allows developers and cartographers to render transfer symbols across **all 50 states** or **all 100 seats simultaneously**. This is used to:
1. Verify coordinate accuracy and polygon containment for all seats.
2. Inspect spatial clearances and ensure no symbol collides with state borders or postal abbreviation labels.
3. Test hypothetical scenarios where party flips happen in non-battleground states or micro-states.

---

### How to Activate Debug Mode

Debug mode can be enabled through either the **UI Sidebar** or **URL Query Parameters**:

#### Method 1: Using the Streamlit Sidebar
1. Open the app in your browser (`http://localhost:8501/`).
2. Click the sidebar arrow (`>`) in the top-left corner to expand the sidebar.
3. Under **Display & Debug Settings**, select one of the debug options:
   - **`Debug: All 50 States (Right Halves)`**: Renders 50 transfer symbols (one on each state's East/contested seat).
   - **`Debug: All 100 Seats (Both Halves)`**: Renders 100 transfer symbols across every Senate seat in the country.
4. When active, an informative amber tag appears in the ledger header (`[DEBUG: X Symbols Active]`), and an info banner is displayed at the top of the app.

#### Method 2: Using URL Query Parameters
You can activate debug mode directly via the browser address bar:

- **50 States (Right Seats):**
  ```text
  http://localhost:8501/?debug=50
  ```
- **All 100 Senate Seats (Both Halves):**
  ```text
  http://localhost:8501/?debug=100
  ```

---

### How to Deactivate Debug Mode

By default, the application starts with debug mode **completely deactivated** (`initial_sidebar_state="collapsed"`, default selection = `"Normal: 7 Battleground Flips"`).

To return to standard production mode from an active debug session:

1. **Via UI Sidebar:** Select **`Normal: 7 Battleground Flips`** in the radio control.
2. **Via URL:** Remove the `?debug=...` parameter from the address bar (or navigate to `http://localhost:8501/?debug=none`).

In normal mode:
- Only the 7 actual toss-up flip badges (`⇄`) are rendered on the map.
- The sidebar remains collapsed by default for a clean presentation.
- No debug banners or indicator tags are displayed.
