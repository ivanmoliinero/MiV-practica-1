"""
current_senate.py
-----------------
Scrapes Wikipedia's 'List of current United States senators' to generate
the baseline dataset of all 100 senators and determine which seats are up
for election in 2026 (33 Class II seats + 2 special elections).
"""

import io
import os
import re
import logging
import requests
import pandas as pd

try:
    from .config import RESULTS_DIR, SENATORS_CSV
    from .client import fetch_with_backoff, create_session
    from .utils import normalize_party, clean_text_field
except ImportError:
    from config import RESULTS_DIR, SENATORS_CSV
    from client import fetch_with_backoff, create_session
    from utils import normalize_party, clean_text_field

log = logging.getLogger("senate_scraper")


def fetch_and_save_current_senators(session: requests.Session) -> dict[str, dict]:
    """
    Downloads the Wikipedia page for current US senators, generates the 100-senator
    CSV showing all current senators and which seats are in play for 2026,
    and returns a mapping {state: {'titular_actual_sillon': ..., 'partido_titular_sillon': ...}}
    for the 35 races in 2026.
    """
    url = "https://en.wikipedia.org/wiki/List_of_current_United_States_senators"
    log.info("Fetching current 100 US Senators from %s", url)
    response = fetch_with_backoff(session, url)
    tables = pd.read_html(io.StringIO(response.text), flavor="lxml")

    main_df = None
    for df in tables:
        if len(df) == 100 and "State" in df.columns and "Senator" in df.columns:
            main_df = df
            break

    if main_df is None:
        for df in tables:
            if len(df) >= 90 and "State" in df.columns:
                main_df = df
                break

    if main_df is None:
        log.error("Failed to extract current US Senators table.")
        return {}

    senators_rows = []
    seats_in_play = {}

    for _, row in main_df.iterrows():
        state = clean_text_field(row.get("State", ""))
        senator = clean_text_field(row.get("Senator", ""))
        party_raw = str(row.get("Party.1", row.get("Party", "")))
        party = normalize_party(party_raw)
        raw_class = str(row.get("Class", ""))
        assumed = clean_text_field(row.get("Assumed office", ""))

        m_class = re.search(r"Class\s*(\d)", raw_class)
        clase_num = int(m_class.group(1)) if m_class else None

        m_year = re.search(r"(202\d|203\d)", raw_class)
        next_year = int(m_year.group(1)) if m_year else None

        is_special = (state in ["Florida", "Ohio"] and clase_num == 3)
        is_in_play = (clase_num == 2) or is_special

        if is_special:
            election_type = "Special Election"
            seat_class_desc = f"Class {clase_num} (Special Election in 2026 • Term ends in 2028)"
            next_year = 2026
        elif clase_num == 2:
            election_type = "Regular Election"
            seat_class_desc = f"Class {clase_num} (Next Election: 2026 • Regular 6-Year Cycle)"
            next_year = 2026
        else:
            election_type = "Not applicable"
            target_year = next_year if next_year else (2030 if clase_num == 1 else 2028)
            seat_class_desc = f"Class {clase_num} (Next Election: {target_year})" if clase_num else raw_class
            next_year = target_year

        senators_rows.append({
            "estado": state,
            "senador": senator,
            "partido": party,
            "clase": seat_class_desc,
            "año_proxima_eleccion": next_year,
            "en_juego_2026": is_in_play,
            "tipo_eleccion_2026": election_type,
            "asumio_cargo": assumed,
        })

        if is_in_play:
            seats_in_play[state] = {
                "titular_actual_sillon": senator,
                "partido_titular_sillon": party,
                "tipo_eleccion": election_type,
            }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    sen_df = pd.DataFrame(senators_rows)
    sen_df.to_csv(SENATORS_CSV, index=False, encoding="utf-8")
    log.info(
        "Saved 100 current senators to %s (%d seats in play in 2026)",
        SENATORS_CSV,
        len(seats_in_play),
    )

    return seats_in_play


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    sess = create_session()
    fetch_and_save_current_senators(sess)
