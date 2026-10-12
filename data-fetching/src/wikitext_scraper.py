"""
wikitext_scraper.py
-------------------
Extracts candidate nominations and party affiliations from Wikipedia infoboxes
via the MediaWiki Action API (parse action with wikitext prop).
"""

import re
import logging
import requests

try:
    from .client import fetch_with_backoff
    from .utils import clean_candidate_name, normalize_party
except ImportError:
    from client import fetch_with_backoff
    from utils import clean_candidate_name, normalize_party

log = logging.getLogger("senate_scraper")


def get_candidates_from_wikitext(session: requests.Session, page_title: str) -> dict:
    """
    Calls the MediaWiki Action API to retrieve page wikitext and extracts candidate
    and party metadata from infobox fields (nominee1/2, candidate1/2, incumbent,
    before_election, party1/2, before_party).
    """
    api_url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": page_title,
        "prop": "wikitext",
        "format": "json",
    }
    response = fetch_with_backoff(session, api_url, params=params)
    data = response.json()
    if "parse" not in data or "wikitext" not in data["parse"]:
        return {
            "candidate_1": None,
            "party_1": None,
            "candidate_2": None,
            "party_2": None,
        } # error processing, return None
    wikitext = data["parse"]["wikitext"]["*"]

    def extract_field(pattern: str) -> str | None:
        match = re.search(pattern, wikitext)
        return clean_candidate_name(match.group(1)) if match else None

    # Candidate 1 and Party 1
    nominee1 = extract_field(r"\|\s*nominee1\s*=\s*([^\n\r]+)")
    if not nominee1:
        nominee1 = extract_field(r"\|\s*candidate1\s*=\s*([^\n\r]+)")
    if not nominee1:
        nominee1 = extract_field(r"\|\s*incumbent\s*=\s*([^\n\r]+)")
    if not nominee1:
        nominee1 = extract_field(r"\|\s*before_election\s*=\s*([^\n\r]+)")

    party1_raw = extract_field(r"\|\s*party1\s*=\s*([^\n\r]+)")
    if not party1_raw:
        party1_raw = extract_field(r"\|\s*before_party\s*=\s*([^\n\r]+)")

    # Candidate 2 and Party 2
    nominee2 = extract_field(r"\|\s*nominee2\s*=\s*([^\n\r]+)")
    if not nominee2:
        nominee2 = extract_field(r"\|\s*candidate2\s*=\s*([^\n\r]+)")

    party2_raw = extract_field(r"\|\s*party2\s*=\s*([^\n\r]+)")

    return {
        "candidate_1": nominee1,
        "party_1": normalize_party(party1_raw) if nominee1 else None,
        "candidate_2": nominee2,
        "party_2": normalize_party(party2_raw) if nominee2 else None,
    }
