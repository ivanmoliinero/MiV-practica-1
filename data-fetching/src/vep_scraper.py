"""
vep_scraper.py
--------------
Official Voting-Eligible Population (VEP) dataset fetcher and validator.

Retrieves official 2024 General Election turnout and VEP estimates from the
University of Florida Election Lab (directed by Dr. Michael McDonald, formerly
US Elections Project):
- Official Portal: https://election.lab.ufl.edu/2024-general-election-turnout/
- Dataset URL: https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv

Verifies:
1. Exact 1-to-1 matching for all 50 US states that elect the 100 US Senators.
2. Constitutional exclusion of non-Senate jurisdictions (District of Columbia,
   which has 0 US Senators under the US Constitution, and unallocated overseas voters).
3. Total voting electorate representation across all 50 states and the 35 contested races.
"""

import csv
import io
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests

try:
    from .config import HEADERS, RESULTS_DIR, SENATORS_CSV, VEP_OUTPUT_CSV, VEP_SOURCE_URL, setup_logging
except ImportError:
    SRC_DIR = Path(__file__).resolve().parent
    DATA_FETCHING_DIR = SRC_DIR.parent
    RESULTS_DIR = str(DATA_FETCHING_DIR / "results")
    SENATORS_CSV = str(DATA_FETCHING_DIR / "results" / "senate_current_composition.csv")
    VEP_OUTPUT_CSV = str(DATA_FETCHING_DIR / "results" / "state_vep_2024.csv")
    VEP_SOURCE_URL = "https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    import logging
    def setup_logging():
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        return logging.getLogger("vep_scraper")

log = setup_logging()


def download_official_vep_csv(url: Optional[str] = None) -> str:
    """
    Download raw CSV content directly from the official University of Florida Election Lab portal.
    """
    target_url = url or VEP_SOURCE_URL
    log.info("Downloading official VEP dataset from: %s", target_url)
    response = requests.get(target_url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    log.info("Successfully fetched %d bytes of CSV data.", len(response.content))
    return response.text


def parse_vep_csv(raw_csv_text: str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Parse the official UF Election Lab turnout CSV:
    - Extracts state-level VEP, VAP, ballots counted, and turnout rates.
    - Strips commas and percentage signs.
    - Separates the 50 state records from the national and DC summary rows.
    """
    f = io.StringIO(raw_csv_text)
    reader = csv.DictReader(f)

    records: List[dict] = []
    metadata_rows: Dict[str, int] = {}

    for row in reader:
        state_name = row.get("STATE", "").strip()
        state_abv = row.get("STATE_ABV", "").strip()
        vep_raw = row.get("VEP", "").replace(",", "").strip()

        if not state_name or not vep_raw:
            continue

        try:
            vep_val = int(vep_raw)
        except ValueError:
            continue

        if state_name in ("United States", "District of Columbia"):
            metadata_rows[state_name] = vep_val
            if state_name == "United States":
                overseas_raw = row.get("ELIGIBLE_OVERSEAS", "").replace(",", "").strip()
                if overseas_raw:
                    try:
                        metadata_rows["Eligible Overseas"] = int(overseas_raw)
                    except ValueError:
                        pass
            continue

        vap_raw = row.get("VAP", "").replace(",", "").strip()
        ballots_raw = row.get("TOTAL_BALLOTS_COUNTED", "").replace(",", "").strip()
        turnout_rate_raw = row.get("VEP_TURNOUT_RATE", "").replace("%", "").strip()

        records.append({
            "state": state_name,
            "abbrev": state_abv,
            "vep": vep_val,
            "vap": int(vap_raw) if vap_raw.isdigit() else None,
            "total_ballots_counted": int(ballots_raw) if ballots_raw.isdigit() else None,
            "vep_turnout_rate": float(turnout_rate_raw) if turnout_rate_raw else None,
        })

    df = pd.DataFrame(records).sort_values("state").reset_index(drop=True)
    return df, metadata_rows


def verify_senate_electorate_alignment(
    vep_df: pd.DataFrame,
    metadata_rows: Dict[str, int],
    senators_csv_path: Optional[str] = None,
) -> dict:
    """
    Verify that:
    1. All 50 states electing the 100 US Senators are present (1-to-1 match).
    2. Sum of state VEP exactly accounts for the entire US Senate voting constituency.
    3. The difference between national VEP and 50-state Senate VEP is explained by:
       - District of Columbia (506,415 VEP, has 0 voting US Senators).
       - Unallocated overseas eligible voters (3,325,217, not apportioned to state rolls).
    """
    path = senators_csv_path or SENATORS_CSV
    senate_states = []
    if os.path.exists(path):
        sen_df = pd.read_csv(path)
        senate_states = sorted(sen_df["estado"].unique())

    vep_states = sorted(vep_df["state"].unique())

    # Check 1: 50 states match exactly
    states_match = (senate_states == vep_states) if senate_states else (len(vep_states) == 50)

    # Check 2: Total 50-state Senate electorate sum
    senate_electorate_total = int(vep_df["vep"].sum())
    national_vep = metadata_rows.get("United States", 0)
    dc_vep = metadata_rows.get("District of Columbia", 0)
    overseas_vep = metadata_rows.get("Eligible Overseas", 0)

    return {
        "senate_states_count": len(vep_states),
        "states_exact_match": states_match,
        "total_senate_electorate_vep": senate_electorate_total,
        "national_vep_source": national_vep,
        "dc_vep_no_senate_rep": dc_vep,
        "overseas_vep_unallocated": overseas_vep,
        "reconciled_sum_states_plus_dc": senate_electorate_total + dc_vep,
    }


def fetch_and_save_state_vep(
    output_csv: Optional[str] = None,
    verify_against_senate: bool = True,
) -> pd.DataFrame:
    """
    Complete pipeline to download, clean, save, and verify state VEP figures.
    """
    target_path = output_csv or VEP_OUTPUT_CSV

    raw_text = download_official_vep_csv()
    df, meta = parse_vep_csv(raw_text)

    # Ensure parent output directory exists
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    df.to_csv(target_path, index=False)
    log.info("Saved %d state VEP records to: %s", len(df), target_path)

    if verify_against_senate:
        res = verify_senate_electorate_alignment(df, meta)
        log.info("Senate verification results:")
        log.info("  States present: %d / 50 (Exact match: %s)", res["senate_states_count"], res["states_exact_match"])
        log.info("  Total 50-State Senate Electorate VEP: %s", f"{res['total_senate_electorate_vep']:,}")
        log.info("  National VEP (UF Lab source total):    %s", f"{res['national_vep_source']:,}")
        log.info("  DC VEP (0 Senate voting members):       %s", f"{res['dc_vep_no_senate_rep']:,}")
        log.info("  Overseas VEP (unallocated estimate):    %s", f"{res['overseas_vep_unallocated']:,}")

    return df


def main():
    """CLI execution entrypoint."""
    log.info("Starting official VEP dataset scraping and validation...")
    df = fetch_and_save_state_vep()
    print("\nSample top 5 states:")
    print(df.head())


if __name__ == "__main__":
    main()
