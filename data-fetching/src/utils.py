"""
utils.py
--------
Pure text cleaning, regex parsing, party normalization, and DataFrame
column matching utilities without external network dependencies.
"""

import re
import pandas as pd

try:
    from .config import PARTY_ALIASES
except ImportError:
    from config import PARTY_ALIASES


def normalize_party(raw: str | None) -> str | None:
    """
    Maps a raw party string (from Wikipedia infoboxes or tables) to a
    standard short code (DEM, REP, IND, LIB, GRN, or OTH).
    """
    if not raw:
        return None
    lowered = raw.strip().lower()
    for key, label in PARTY_ALIASES.items():
        if key in lowered:
            return label
    return "OTH"


def clean_candidate_name(val: str | None) -> str | None:
    """
    Removes HTML comments, <ref> citations, wikitext links [[...]],
    and parenthetical annotations from candidate names.
    """
    if not val:
        return None
    val = re.sub(r"<!--.*?-->", "", val, flags=re.DOTALL)
    val = re.sub(r"<ref.*?(?:/>|</ref>)", "", val, flags=re.DOTALL)
    val = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", val)
    val = re.sub(r"\s*\([^)]*\)", "", val)
    val = val.strip()
    return val if val else None


def clean_text_field(val: any) -> str | None:
    """
    Strips Wikipedia reference footnotes (e.g. '[1]', '[b]') and excess
    whitespace from table cells. Returns None for NaN or blank values.
    """
    if val is None or pd.isna(val):
        return None
    text = str(val).strip()
    text = re.sub(r"\[.*?\]", "", text).strip()
    return text if text else None


def clean_pct_series(series: pd.Series) -> pd.Series:
    """
    Cleans a pandas Series representing polling percentages by stripping
    footnote brackets, '%', en-dashes, and em-dashes, then converts to float.
    """
    return pd.to_numeric(
        series.astype(str)
              .str.replace(r"\[.*?\]", "", regex=True)
              .str.replace("%", "", regex=False)
              .str.replace("–", "", regex=False)
              .str.replace("—", "", regex=False)
              .str.strip(),
        errors="coerce",
    )


def col_matches_candidate(col_name: str, full_name: str | None) -> bool:
    """
    Checks if a table column header matches a candidate's name or surname.
    Case-insensitive matching supporting single surnames and full names.
    """
    if not full_name:
        return False
    col_lower = str(col_name).lower()
    full_lower = full_name.lower().strip()
    parts = full_lower.split()
    surname = parts[-1] if parts else ""
    first = parts[0] if len(parts) > 1 else ""

    return (
        full_lower in col_lower
        or (surname and surname in col_lower)
        or (first and surname and first in col_lower and surname in col_lower)
    )


def find_matching_col(
    df: pd.DataFrame,
    keywords: list[str],
    exclude: list[str] | None = None,
) -> str | None:
    """
    Finds the first column in the DataFrame whose name contains any of the
    target keywords while excluding columns containing any forbidden tokens.
    """
    exclude = exclude or []
    for col in df.columns:
        c_lower = str(col).lower()
        if any(kw in c_lower for kw in keywords) and not any(ex in c_lower for ex in exclude):
            return col
    return None


def find_all_matching_cols(
    df: pd.DataFrame,
    keywords: list[str],
    exclude: list[str] | None = None,
) -> list[str]:
    """
    Finds all distinct columns in the DataFrame whose names contain any of the
    target keywords while excluding columns containing any forbidden tokens.
    """
    exclude = exclude or []
    matches = []
    for col in df.columns:
        c_lower = str(col).lower()
        if any(kw in c_lower for kw in keywords) and not any(ex.lower() in c_lower for ex in exclude if ex):
            if col not in matches:
                matches.append(col)
    return matches

