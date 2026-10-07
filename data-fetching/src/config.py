"""
config.py
---------
Configuration parameters, directory paths, HTTP headers, and schema definitions
for the Wikipedia Senate polling and composition scraper.
"""

import os
import logging

# ---------------------------------------------------------------------------
# Filesystem Paths
# ---------------------------------------------------------------------------

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FETCHING_DIR = os.path.dirname(SRC_DIR)
DATA_SOURCES_DIR = os.path.join(DATA_FETCHING_DIR, "data-sources")
RESULTS_DIR = os.path.join(DATA_FETCHING_DIR, "results")

JSON_PATH = os.path.join(DATA_SOURCES_DIR, "wikipedia-source-info.json")
OUTPUT_CSV = os.path.join(RESULTS_DIR, "senate_2026_polls.csv")
SENATORS_CSV = os.path.join(RESULTS_DIR, "senate_current_composition.csv")
VEP_OUTPUT_CSV = os.path.join(RESULTS_DIR, "state_vep_2024.csv")
VEP_SOURCE_URL = "https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv"

# ---------------------------------------------------------------------------
# Scraper & Network Parameters
# ---------------------------------------------------------------------------

YEAR = 2026
REQUEST_DELAY = 2.5  # Polite sleep interval (seconds) between Wikipedia calls

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AcademicScraper/1.0; "
        "university coursework - URV MiV practica-1)"
    )
}

# ---------------------------------------------------------------------------
# Dataset Schemas & Mappings
# ---------------------------------------------------------------------------

COLUMNS_ORDER = [
    "estado",
    "año",
    "titular_actual_sillon",
    "partido_titular_sillon",
    "partido_candidato_actual_1",
    "candidato_actual_1",
    "partido_candidato_actual_2",
    "candidato_actual_2",
    "fuente_encuesta",
    "fecha_encuesta",
    "porc_republicano_sillon_en_juego",
    "porc_democrata_sillon_en_juego",
    "indecision",
    "error",
]

PARTY_ALIASES = {
    "democratic": "DEM",
    "democrat": "DEM",
    "republican": "REP",
    "independent": "IND",
    "libertarian": "LIB",
    "green": "GRN",
}

# ---------------------------------------------------------------------------
# Logging Configuration Helper
# ---------------------------------------------------------------------------

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures and returns the standard project logger."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("senate_scraper")
