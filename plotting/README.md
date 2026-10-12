# US Senate 2026 — Balance of Power & Seat Flip Dashboard

A static, publication-grade data visualization communicating the 2026 US Senate election balance of power and projected seat flips based on empirical polling data.

---

## Architecture & Key Components

- **`export_data.py`**: Preprocessing and serialization pipeline that merges polling data with incumbent Senate composition, saving static JSON payloads and GeoJSONs to `web/data/`.
- **`web/`**: Standalone web application:
  - **`index.html`**: HTML5 layout markup, SVG pattern defs, containers, interactive controls, and balance panel.
  - **`dashboard.css`**: Pure CSS stylesheet for modern dark-theme presentation.
  - **`dashboard.js`**: Client-side controller that fetches data, initializes Plotly choropleth halves, and handles responsive layout and interactive toggles.
- **`state_centroids.py`**: Geographical configuration containing:
  - `STATE_LOWER_RIGHT_COORDS`: Strict south-east polygon coordinates for postal abbreviations.
  - `SEAT_SYMBOL_COORDS`: Dedicated `(lat, lon)` coordinates for all 100 individual Senate seats (`<State>_left` and `<State>_right`), mathematically verified to fall strictly within half-state polygons.
  - `get_seat_symbol_coord`: Dynamic coordinate resolver for any state name, abbreviation, or feature ID.
- **`data_loader.py`**: Data pipeline merging incumbent Senate composition with aggregated 2026 general election polls, calculating party flips and balance of power metrics.
- **`geo_splitter.py`**: Divides state boundary polygons along their geometric bounding box bisector into West (`_left`) and East (`_right`) senator halves, with automated caching (`_us_states_split.geojson` and `_us_states_outlines.geojson`).

---

## How to Run

From the repository root or project directory (`practica-1`):

### 1. Preprocess & Export Data
```bash
python plotting/export_data.py
```

### 2. Launch Local HTTP Server (Zero Node.js dependency)
```bash
python3 -m http.server 8000 --directory plotting/web
```

The application will launch locally at **`http://localhost:8000/`**.
