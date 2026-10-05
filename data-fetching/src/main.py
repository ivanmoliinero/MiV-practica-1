"""
main.py
-------
Pipeline entrypoint for the Wikipedia US Senate 2026 election scraper.
Coordinates current senator baseline generation, candidate infobox parsing,
general election polling table extraction, and dataset serialization.
"""

import json
import time
import requests

try:
    from .config import JSON_PATH, OUTPUT_CSV, REQUEST_DELAY, setup_logging
    from .client import create_session
    from .current_senate import fetch_and_save_current_senators
    from .wikitext_scraper import get_candidates_from_wikitext
    from .polling_scraper import extract_page_election_data
    from .row_builder import build_rows_for_state, create_fallback_row, save_polling_csv
except ImportError:
    from config import JSON_PATH, OUTPUT_CSV, REQUEST_DELAY, setup_logging
    from client import create_session
    from current_senate import fetch_and_save_current_senators
    from wikitext_scraper import get_candidates_from_wikitext
    from polling_scraper import extract_page_election_data
    from row_builder import build_rows_for_state, create_fallback_row, save_polling_csv

log = setup_logging()


def load_sources(json_path: str) -> dict[str, str]:
    """
    Loads and flattens the JSON configuration mapping state names to their
    respective Wikipedia election article URLs (Class II regular + specials).
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    states = {}
    states.update(data.get("class_ii_regular_elections", {}))
    states.update(data.get("special_elections", {}))
    return states


def process_state(
    session: requests.Session,
    state: str,
    url: str,
    incumbent_info: dict | None,
) -> list[dict]:
    """
    Processes an individual state election race:
    1. Extracts candidate names and parties from Wikipedia infobox wikitext.
    2. Downloads and parses polling tables and forecaster predictions.
    3. Aligns polling figures or prediction ratings with the project dataset schema.
    """
    log.info("Processing: %s", state)
    page_title = url.split("/wiki/")[-1]

    try:
        meta = get_candidates_from_wikitext(session, page_title)
        log.info(
            "  Candidates: %s (%s) vs %s (%s)",
            meta["candidate_1"],
            meta["party_1"],
            meta["candidate_2"],
            meta["party_2"],
        )
        time.sleep(REQUEST_DELAY)

        poll_tables, predictions = extract_page_election_data(session, url)
        log.info(
            "  Polling tables found: %d | Predictions found: %d",
            len(poll_tables),
            len(predictions),
        )
        time.sleep(REQUEST_DELAY)

        rows = build_rows_for_state(
            state, meta, poll_tables, incumbent_info, predictions=predictions
        )
        log.info("  Rows added: %d", len(rows))
        return rows
    except Exception as exc:
        log.error("  FAILED for %s: %s", state, exc)
        return [create_fallback_row(state, incumbent_info, error_msg=f"Fetch error: {exc}")]


def main():
    """
    Main orchestration function:
    1. Initializes an HTTP session with retries.
    2. Scrapes the 100 current senators and exports senate_current_composition.csv.
    3. Loads the 35 target state URLs.
    4. Iteratively scrapes and processes polling tables with polite throttling.
    5. Exports the complete polling dataset to senate_2026_polls.csv.
    """
    session = create_session()

    # Step 1: Baseline current senators and in-play seats identification
    seats_in_play = fetch_and_save_current_senators(session)
    time.sleep(REQUEST_DELAY)

    # Step 2: Load target race URLs
    all_states = load_sources(JSON_PATH)
    log.info("Loaded %d states to process from %s", len(all_states), JSON_PATH)

    # Step 3: Scrape polls for each race in play
    all_rows = []
    for state, url in all_states.items():
        state_rows = process_state(session, state, url, seats_in_play.get(state))
        all_rows.extend(state_rows)

    # Step 4: Export final polling dataset
    save_polling_csv(all_rows, OUTPUT_CSV)
    log.info("All states completed successfully.")


if __name__ == "__main__":
    main()
