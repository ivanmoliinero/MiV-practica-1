"""
polling_scraper.py
------------------
HTML extraction, section traversal, heuristic filtering, and DataFrame
conversion for Wikipedia Senate election polling tables.
"""

import io
import logging
import requests
import pandas as pd
from bs4 import BeautifulSoup

try:
    from .client import fetch_with_backoff
except ImportError:
    from client import fetch_with_backoff

log = logging.getLogger("senate_scraper")


def is_polling_table(df: pd.DataFrame) -> bool:
    """
    Identifies genuine polling tables by requiring poll-specific metadata
    (poll source, sample size, margin of error, dates) and rejecting non-polling
    tables like campaign finance, debate schedules, and election summaries.
    """
    if len(df.columns) < 4 or len(df) < 1:
        return False

    cols_str = " ".join(str(c).lower() for c in df.columns)

    exclude_keywords = [
        "campaign finance", "cash on hand", "raised", "spent",
        "moderator", "participant", "debates", "endorsements",
        "primary results", "general election results",
    ]
    if any(kw in cols_str for kw in exclude_keywords):
        return False

    has_poll = any(
        kw in cols_str
        for kw in ["poll", "sample", "margin of error", "survey", "dates updated"]
    )
    has_date = any(
        kw in cols_str
        for kw in ["date", "administered", "dates"]
    )

    return has_poll and has_date


def get_polling_tables_from_page(session: requests.Session, url: str) -> list[pd.DataFrame]:
    """
    Downloads the state election Wikipedia page and extracts genuine general
    election polling tables by locating 'Polling' headings and inspecting wikitables.
    """
    response = fetch_with_backoff(session, url)
    soup = BeautifulSoup(response.text, "lxml")

    poll_tables_html = []
    inside_poll_section = False

    for tag in soup.find_all(["h2", "h3", "table"]):
        if tag.name in ("h2", "h3"):
            text = tag.get_text(strip=True).lower()
            if any(kw in text for kw in ["polling", "general election poll"]):
                inside_poll_section = True
            elif tag.name == "h2" and inside_poll_section:
                inside_poll_section = False
        elif tag.name == "table" and inside_poll_section:
            poll_tables_html.append(str(tag))

    result = []
    for html_fragment in poll_tables_html:
        try:
            dfs = pd.read_html(io.StringIO(html_fragment), flavor="lxml")
            for df in dfs:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [" ".join(str(c) for c in col).strip() for col in df.columns]
                if is_polling_table(df):
                    result.append(df)
        except Exception:
            continue

    # Fallback: scan all wikitables on the page if section-based extraction yielded nothing
    if not result:
        try:
            all_tables = pd.read_html(io.StringIO(response.text), flavor="lxml", attrs={"class": "wikitable"})
            for df in all_tables:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [" ".join(str(c) for c in col).strip() for col in df.columns]
                if is_polling_table(df):
                    result.append(df)
        except Exception:
            pass

    return result
