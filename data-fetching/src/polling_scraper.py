"""
polling_scraper.py
------------------
HTML extraction, section traversal, heuristic filtering, and DataFrame
conversion for Wikipedia Senate election polling tables.
"""

import io
import re
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


def parse_predictions_wikitable(table_tag) -> list[dict]:
    """
    Parses a Wikipedia predictions wikitable into clean records with
    forecaster sources, qualitative rankings (e.g. 'Solid D', 'Safe R'),
    and observation dates.
    """
    if table_tag is None:
        return []

    try:
        dfs = pd.read_html(io.StringIO(str(table_tag)), flavor="lxml")
        if not dfs or len(dfs[0].columns) < 2 or len(dfs[0]) < 1:
            return []

        pdf = dfs[0]
        src_col = pdf.columns[0]
        rank_col = pdf.columns[1]
        date_col = pdf.columns[2] if len(pdf.columns) > 2 else None

        predictions = []
        for i in range(len(pdf)):
            raw_src = pdf[src_col].iloc[i]
            raw_rank = pdf[rank_col].iloc[i]
            raw_date = pdf[date_col].iloc[i] if date_col is not None else None

            # Remove citation tags like [185] or [ac]
            clean_src = (
                re.sub(r"\[\d+\]|\[[a-z]+\]", "", str(raw_src)).strip()
                if pd.notna(raw_src)
                else None
            )
            clean_rank = (
                re.sub(r"\[\d+\]|\[[a-z]+\]", "", str(raw_rank)).strip()
                if pd.notna(raw_rank)
                else None
            )
            clean_date = (
                re.sub(r"\[\d+\]|\[[a-z]+\]", "", str(raw_date)).strip()
                if (date_col is not None and pd.notna(raw_date))
                else None
            )

            if clean_src and clean_rank and clean_rank.lower() != "ranking":
                predictions.append({
                    "source": clean_src,
                    "ranking": clean_rank,
                    "date": clean_date,
                })
        return predictions
    except Exception as exc:
        log.warning("Could not parse predictions table: %s", exc)
        return []


def extract_page_election_data(
    session: requests.Session, url: str
) -> tuple[list[pd.DataFrame], list[dict]]:
    """
    Fetches the state election Wikipedia page once and extracts both:
    1. Genuine general election head-to-head polling DataFrames.
    2. Qualitative forecaster prediction ratings (Source, Ranking, Date).
    """
    response = fetch_with_backoff(session, url)
    soup = BeautifulSoup(response.text, "lxml")

    poll_tables_html = []
    pred_table_tag = None

    inside_general_election = False
    inside_poll_section = False
    inside_pred_section = False

    # State machine for Polling and Prediction finding.
    # We need to check for tables under General election -> Polling or General election -> Predictions.
    # Our FSM guarantees that analysed tables are under those sections, to avoid obtaining data from incorrect
    # tables of the same Wikipedia page.
    for tag in soup.find_all(["h2", "h3", "h4", "table"]):
        if tag.name == "h2":
            text = tag.get_text(strip=True).lower()
            if "general election" in text:
                inside_general_election = True
            else:
                inside_general_election = False
            inside_poll_section = False
            inside_pred_section = False
        elif tag.name in ("h3", "h4") and inside_general_election:
            text = tag.get_text(strip=True).lower()
            if "polling" in text:
                inside_poll_section = True
                inside_pred_section = False
            elif "prediction" in text or "rating" in text:
                inside_pred_section = True
                inside_poll_section = False
            else:
                inside_poll_section = False
                inside_pred_section = False
        elif tag.name == "table" and inside_general_election:
            if inside_poll_section:
                poll_tables_html.append(str(tag))
            elif inside_pred_section and pred_table_tag is None:
                pred_table_tag = tag

    # Parse polling tables
    poll_dfs = []
    for html_fragment in poll_tables_html:
        try:
            dfs = pd.read_html(io.StringIO(html_fragment), flavor="lxml")
            for df in dfs:
                if is_polling_table(df):
                    poll_dfs.append(df)
        except Exception:
            continue

    # Parse predictions
    predictions = parse_predictions_wikitable(pred_table_tag)

    return poll_dfs, predictions


def get_polling_tables_from_page(session: requests.Session, url: str) -> list[pd.DataFrame]:
    """Compatibility wrapper returning only polling DataFrames."""
    polls, _ = extract_page_election_data(session, url)
    return polls


def get_predictions_from_page(session: requests.Session, url: str) -> list[dict]:
    """Compatibility wrapper returning only prediction records."""
    _, preds = extract_page_election_data(session, url)
    return preds

