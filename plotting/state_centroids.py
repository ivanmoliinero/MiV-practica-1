"""
Geographical coordinates and state mappings for the 2026 US Senate map visualization.

Contains:
- STATE_TO_ABBREV and ABBREV_TO_STATE mappings.
- STATE_LOWER_RIGHT_COORDS: Strict south-east coordinates for state postal abbreviations.
- SEAT_SYMBOL_COORDS: Verified coordinates for all 100 Senate seats (left/right halves).
- get_seat_symbol_coord: Dynamic coordinate resolver function.
"""

from typing import Dict, Optional, Tuple

STATE_TO_ABBREV: Dict[str, str] = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
}

ABBREV_TO_STATE: Dict[str, str] = {v: k for k, v in STATE_TO_ABBREV.items()}

# State lower-right coordinates (latitude, longitude) strictly positioned in the SE area inside each state polygon
STATE_LOWER_RIGHT_COORDS: Dict[str, Tuple[float, float]] = {
    "AL": (31.6, -85.6),
    "AK": (62.2, -148.5),
    "AZ": (32.3, -109.8),
    "AR": (33.5, -91.5),
    "CA": (34.0, -116.5),
    "CO": (37.8, -103.5),
    "CT": (41.4, -72.2),
    "DE": (38.7, -75.3),
    "FL": (27.2, -81.2),
    "GA": (31.5, -82.2),
    "HI": (19.6, -155.4),
    "ID": (42.8, -112.5),
    "IL": (38.5, -88.7),
    "IN": (39.0, -85.7),
    "IA": (41.2, -92.0),
    "KS": (37.5, -95.5),
    "KY": (37.1, -84.0),
    "LA": (30.2, -90.5),
    "ME": (44.8, -68.5),
    "MD": (38.5, -76.0),
    "MA": (41.9, -70.9),
    "MI": (42.5, -83.5),
    "MN": (44.5, -92.8),
    "MS": (31.2, -89.3),
    "MO": (37.0, -90.5),
    "MT": (45.8, -106.0),
    "NE": (40.6, -97.0),
    "NV": (37.2, -115.5),
    "NH": (43.2, -71.2),
    "NJ": (39.8, -74.4),
    "NM": (32.8, -104.5),
    "NY": (42.2, -74.3),
    "NC": (35.2, -77.0),
    "ND": (46.5, -98.0),
    "OH": (39.8, -81.8),
    "OK": (34.6, -95.5),
    "OR": (43.0, -118.5),
    "PA": (40.3, -76.2),
    "RI": (41.6, -71.5),
    "SC": (33.5, -80.3),
    "SD": (43.5, -98.0),
    "TN": (35.5, -85.0),
    "TX": (29.5, -96.0),
    "UT": (38.0, -110.5),
    "VT": (43.6, -72.5),
    "VA": (37.1, -77.2),
    "WA": (46.6, -118.5),
    "WV": (38.3, -80.6),
    "WI": (43.5, -88.8),
    "WY": (41.8, -105.5),
}

# Dedicated coordinates (lat, lon) for Senate seat symbols and badges across ALL 50 states and ALL 100 seats
# Keyed by feature_id ("<State>_left" for West half, "<State>_right" for East half)
# All coordinates are verified to lie strictly within their respective polygon boundaries.
SEAT_SYMBOL_COORDS: Dict[str, Tuple[float, float]] = {
    "Alabama_left": (32.739, -87.538),
    "Alabama_right": (32.852, -85.948),
    "Alaska_left": (64.109, -159.364),
    "Alaska_right": (65.467, -148.731),
    "Arizona_left": (34.428, -113.177),
    "Arizona_right": (34.188, -110.479),
    "Arkansas_left": (34.813, -93.299),
    "Arkansas_right": (35.014, -91.281),
    "California_left": (38.845, -121.419),
    "California_right": (35.027, -117.088),
    "Colorado_left": (39.0, -107.3),
    "Colorado_right": (38.999, -103.8),
    "Connecticut_left": (41.579, -73.178),
    "Connecticut_right": (41.919, -72.57),
    "Delaware_left": (39.105, -75.593),
    "Delaware_right": (38.925, -75.343),
    "Florida_left": (30.489, -85.584),
    "Florida_right": (28.171, -81.684),
    "Georgia_left": (32.947, -84.241),
    "Georgia_right": (32.237, -82.355),
    "Hawaii_left": (21.611, -158.03),
    "Hawaii_right": (20.88, -156.543),
    "Idaho_left": (44.919, -115.727),
    "Idaho_right": (43.407, -112.685),
    "Illinois_left": (40.241, -90.216),
    "Illinois_right": (39.956, -88.582),
    "Indiana_left": (39.717, -87.022),
    "Indiana_right": (40.071, -85.661),
    "Iowa_left": (42.12, -94.818),
    "Iowa_right": (42.027, -92.06),
    "Kansas_left": (38.501, -100.191),
    "Kansas_right": (38.467, -96.522),
    "Kentucky_left": (37.221, -87.211),
    "Kentucky_right": (38.1, -84.2),
    "Louisiana_left": (31.399, -92.68),
    "Louisiana_right": (32.405, -91.018),
    "Maine_left": (45.14, -69.929),
    "Maine_right": (45.9, -68.4),
    "Maryland_left": (39.534, -79.045),
    "Maryland_right": (39.45, -76.824),
    "Massachusetts_left": (42.372, -72.562),
    "Massachusetts_right": (42.679, -71.366),
    "Michigan_left": (46.257, -88.118),
    "Michigan_right": (43.3, -84.8),
    "Minnesota_left": (46.324, -95.114),
    "Minnesota_right": (46.302, -92.442),
    "Mississippi_left": (32.719, -90.511),
    "Mississippi_right": (32.771, -89.092),
    "Missouri_left": (38.676, -93.661),
    "Missouri_right": (38.033, -91.193),
    "Montana_left": (47.071, -112.608),
    "Montana_right": (47.001, -107.044),
    "Nebraska_left": (41.681, -101.653),
    "Nebraska_right": (41.8, -98.2),
    "Nevada_left": (39.923, -118.38),
    "Nevada_right": (38.972, -115.492),
    "New Hampshire_left": (43.427, -71.983),
    "New Hampshire_right": (43.867, -71.285),
    "New Jersey_left": (40.017, -74.996),
    "New Jersey_right": (41.018, -74.068),
    "New Mexico_left": (34.343, -107.571),
    "New Mexico_right": (34.506, -104.535),
    "New York_left": (42.715, -77.502),
    "New York_right": (43.061, -74.473),
    "North Carolina_left": (35.656, -81.637),
    "North Carolina_right": (35.7, -78.5),
    "North Dakota_left": (47.471, -102.174),
    "North Dakota_right": (47.418, -98.598),
    "Ohio_left": (40.227, -83.714),
    "Ohio_right": (40.8, -82.0),
    "Oklahoma_left": (35.997, -99.996),
    "Oklahoma_right": (35.431, -96.574),
    "Oregon_left": (43.872, -122.403),
    "Oregon_right": (44.003, -118.699),
    "Pennsylvania_left": (40.877, -79.075),
    "Pennsylvania_right": (41.659, -75.279),
    "Rhode Island_left": (41.677, -71.648),
    "Rhode Island_right": (41.92, -71.379),
    "South Carolina_left": (34.138, -81.775),
    "South Carolina_right": (34.644, -79.501),
    "South Dakota_left": (44.47, -102.149),
    "South Dakota_right": (44.403, -98.343),
    "Tennessee_left": (35.764, -87.893),
    "Tennessee_right": (35.943, -84.371),
    "Texas_left": (32.461, -102.144),
    "Texas_right": (30.802, -97.357),
    "Utah_left": (39.498, -112.796),
    "Utah_right": (39.119, -110.345),
    "Vermont_left": (43.905, -72.898),
    "Vermont_right": (44.462, -72.113),
    "Virginia_left": (37.121, -80.862),
    "Virginia_right": (37.693, -77.855),
    "Washington_left": (47.279, -122.339),
    "Washington_right": (47.452, -118.955),
    "West Virginia_left": (38.456, -81.173),
    "West Virginia_right": (39.059, -79.336),
    "Wisconsin_left": (44.948, -91.111),
    "Wisconsin_right": (44.303, -88.852),
    "Wyoming_left": (43.001, -109.301),
    "Wyoming_right": (43.0, -105.804),
}


def get_seat_symbol_coord(
    identifier: str, side: Optional[str] = None
) -> Tuple[float, float]:
    """
    Retrieve geographic (lat, lon) coordinates for placing a symbol or badge on a specific Senate seat.

    Accepts:
    - feature_id (e.g., 'North Carolina_right' or 'NC_right')
    - state name + side (e.g., identifier='North Carolina', side='right')
    - state postal code + side (e.g., identifier='NC', side='right')
    - state postal code or name alone (defaults to 'right' seat, the contested half in split maps)
    """
    if side is not None:
        state_name = ABBREV_TO_STATE.get(identifier, identifier)
        key = f"{state_name}_{side}"
        if key in SEAT_SYMBOL_COORDS:
            return SEAT_SYMBOL_COORDS[key]

    # Direct match with a feature_id (e.g. 'Alaska_right')
    if identifier in SEAT_SYMBOL_COORDS:
        return SEAT_SYMBOL_COORDS[identifier]

    # Match format '<ABBREV>_<side>' (e.g. 'AK_right')
    if "_" in identifier:
        prefix, s_side = identifier.rsplit("_", 1)
        state_name = ABBREV_TO_STATE.get(prefix, prefix)
        key = f"{state_name}_{s_side}"
        if key in SEAT_SYMBOL_COORDS:
            return SEAT_SYMBOL_COORDS[key]

    # State postal code or name without side specified: default to 'right' seat
    state_name = ABBREV_TO_STATE.get(identifier, identifier)
    key_right = f"{state_name}_right"
    if key_right in SEAT_SYMBOL_COORDS:
        return SEAT_SYMBOL_COORDS[key_right]

    # Fallback to state lower-right coordinate if no exact half-seat match is found
    abbrev = STATE_TO_ABBREV.get(identifier, identifier)
    if abbrev in STATE_LOWER_RIGHT_COORDS:
        return STATE_LOWER_RIGHT_COORDS[abbrev]

    raise KeyError(f"Seat coordinate not found for identifier: '{identifier}', side: '{side}'")

