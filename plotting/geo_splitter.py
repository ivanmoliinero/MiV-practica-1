"""
Geographic geometry splitting module for the 2026 US Senate Election Map.

Splits each of the 50 US state polygons into two distinct geographic halves
(left/west = stable senator or senator A, right/east = contested senator or senator B).
Each of the 100 US Senators is represented by exactly one GeoJSON feature.
Also generates merged 50-state perimeter outlines for high-contrast state borders.
"""

from collections import defaultdict
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from shapely import make_valid, unary_union
from shapely.geometry import box, mapping, shape

# Source URL for official US states GeoJSON (Census / Cartographic boundary)
STATES_GEOJSON_URL = (
    "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json"
)

MODULE_DIR = Path(__file__).resolve().parent
WEB_DATA_DIR = MODULE_DIR / "web" / "data"
RAW_CACHE_PATH = WEB_DATA_DIR / "_us_states_cache.geojson"
SPLIT_CACHE_PATH = WEB_DATA_DIR / "_us_states_split.geojson"
OUTLINES_CACHE_PATH = WEB_DATA_DIR / "_us_states_outlines.geojson"


def fetch_raw_states_geojson() -> dict:
    """Load or download the raw 50-state GeoJSON."""
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if RAW_CACHE_PATH.exists():
        with RAW_CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)

    response = requests.get(STATES_GEOJSON_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    with RAW_CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f)

    return data


def _extract_polygons(geom):
    """
    Extract only Polygon and MultiPolygon geometries from Shapely results.

    Discards any degenerate 0D (Point) or 1D (LineString) slivers created along the cut line.
    """
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    if geom.geom_type == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            return None
        return unary_union(polys)
    return None


def _split_state_geometry(geom, state_name: str) -> Tuple[object, object]:
    """
    Split a state geometry vertically into two halves (west and east).

    Applies topological validation and antimeridian clipping for Alaska.
    """
    if not geom.is_valid:
        geom = make_valid(geom)

    # For Alaska: clip uninhabited islands past the antimeridian (-180 longitude)
    # to avoid D3 Albers USA composite projection wraparound errors.
    if state_name == "Alaska":
        geom = geom.intersection(box(-180.0, 50.0, -120.0, 75.0))
        if not geom.is_valid:
            geom = make_valid(geom)

    minx, miny, maxx, maxy = geom.bounds
    midx = (minx + maxx) / 2.0
    eps = 0.005

    left_box = box(minx - eps, miny - eps, midx, maxy + eps)
    right_box = box(midx, miny - eps, maxx + eps, maxy + eps)

    left_cut = _extract_polygons(geom.intersection(left_box))
    right_cut = _extract_polygons(geom.intersection(right_box))

    # Fallback to original geometry if split resulted in empty slice
    if left_cut is None or left_cut.is_empty:
        left_cut = geom
    if right_cut is None or right_cut.is_empty:
        right_cut = geom

    return left_cut, right_cut


def generate_split_geojson(force_rebuild: bool = False) -> dict:
    """
    Generate or load the 100-feature split GeoJSON collection (2 features per state).

    Feature IDs follow the format:
    - '<StateName>_left' for the western half (stable seat in contested states).
    - '<StateName>_right' for the eastern half (seat up for election in 2026).
    """
    if not force_rebuild and SPLIT_CACHE_PATH.exists():
        with SPLIT_CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)

    raw_data = fetch_raw_states_geojson()
    features = []

    for feature in raw_data["features"]:
        state_name = feature["properties"]["name"]
        raw_geom = shape(feature["geometry"])

        left_geom, right_geom = _split_state_geometry(raw_geom, state_name)

        features.append({
            "type": "Feature",
            "id": f"{state_name}_left",
            "geometry": mapping(left_geom),
            "properties": {
                "state": state_name,
                "side": "left",
                "seat_role": "stable",
            },
        })

        features.append({
            "type": "Feature",
            "id": f"{state_name}_right",
            "geometry": mapping(right_geom),
            "properties": {
                "state": state_name,
                "side": "right",
                "seat_role": "contested",
            },
        })

    collection = {"type": "FeatureCollection", "features": features}

    with SPLIT_CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(collection, f)

    return collection


def generate_state_outlines_geojson(force_rebuild: bool = False) -> dict:
    """
    Generate or load the 50-feature state perimeter GeoJSON collection.

    Dissolves the two half-state geometries for each state into a single unified
    polygon, ensuring mathematically identical outer boundaries that can be drawn
    with a solid black stroke to clearly delineate states from one another.
    """
    if not force_rebuild and OUTLINES_CACHE_PATH.exists():
        with OUTLINES_CACHE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)

    split_fc = generate_split_geojson(force_rebuild=force_rebuild)

    state_parts = defaultdict(list)
    for feat in split_fc["features"]:
        state_name = feat["properties"]["state"]
        state_parts[state_name].append(shape(feat["geometry"]))

    outline_features = []
    for state_name, geoms in state_parts.items():
        merged = unary_union(geoms)
        outline_features.append({
            "type": "Feature",
            "id": state_name,
            "geometry": mapping(merged),
            "properties": {"name": state_name},
        })

    outlines_fc = {"type": "FeatureCollection", "features": outline_features}

    with OUTLINES_CACHE_PATH.open("w", encoding="utf-8") as f:
        json.dump(outlines_fc, f)

    return outlines_fc


if __name__ == "__main__":
    split_fc = generate_split_geojson(force_rebuild=True)
    outlines_fc = generate_state_outlines_geojson(force_rebuild=True)
    print(f"Generated split GeoJSON with {len(split_fc['features'])} features.")
    print(f"Generated outlines GeoJSON with {len(outlines_fc['features'])} features.")
