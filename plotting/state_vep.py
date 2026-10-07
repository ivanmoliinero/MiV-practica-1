"""
Voting Eligible Population (VEP) dataset loader and verification module.

Source: University of Florida Election Lab (directed by Dr. Michael McDonald, formerly US Elections Project)
Dataset: Turnout_2024G_v0.4.csv (May 2026 release)
Official Portal: https://election.lab.ufl.edu/2024-general-election-turnout/
Direct CSV URL: https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv

Data is loaded dynamically from the official fetched CSV at:
  data-fetching/results/state_vep_2024.csv
If the local file is not found, it is automatically retrieved from the official URL.
"""

import csv
import os
from pathlib import Path
from typing import Dict, Optional

MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
RESULTS_CSV_PATH = PROJECT_ROOT / "data-fetching" / "results" / "state_vep_2024.csv"
SENATORS_CSV_PATH = PROJECT_ROOT / "data-fetching" / "results" / "senate_current_composition.csv"
OFFICIAL_SOURCE_URL = "https://election.lab.ufl.edu/data-downloads/turnoutdata/Turnout_2024G_v0.4.csv"


def load_state_vep(csv_path: Optional[Path] = None) -> Dict[str, int]:
    """
    Load official state VEP values from the local CSV, or fetch from the source if missing.
    Returns a dictionary mapping state name to integer VEP.
    """
    target = csv_path or RESULTS_CSV_PATH

    if not target.exists():
        # Fallback to fetching directly if results file is missing
        try:
            import requests

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            }
            resp = requests.get(OFFICIAL_SOURCE_URL, headers=headers, timeout=30)
            resp.raise_for_status()

            target.parent.mkdir(parents=True, exist_ok=True)
            lines = [l for l in resp.text.splitlines() if l.strip()]
            reader = csv.DictReader(lines)

            vep_map: Dict[str, int] = {}
            for r in reader:
                st = r.get("STATE", "").strip()
                val_raw = r.get("VEP", "").replace(",", "").strip()
                if st and st not in ("United States", "District of Columbia") and val_raw:
                    try:
                        vep_map[st] = int(val_raw)
                    except ValueError:
                        continue

            # Cache to target path
            with target.open("w", encoding="utf-8", newline="") as f_out:
                writer = csv.writer(f_out)
                writer.writerow(["state", "vep"])
                for s, v in sorted(vep_map.items()):
                    writer.writerow([s, v])

            return vep_map
        except Exception as exc:
            raise FileNotFoundError(
                f"VEP dataset not found at {target} and auto-download failed: {exc}"
            ) from exc

    # Load from existing clean CSV
    vep_dict: Dict[str, int] = {}
    with target.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            st = row.get("state", "").strip()
            val = row.get("vep", "").replace(",", "").strip()
            if st and val:
                try:
                    vep_dict[st] = int(val)
                except ValueError:
                    continue

    return vep_dict


def verify_senate_voters() -> dict:
    """
    Verify alignment between the 50 US States with Senate representation and the official source.
    """
    vep_dict = load_state_vep()

    # Load Senate composition states
    senate_states = []
    if SENATORS_CSV_PATH.exists():
        import pandas as pd
        df = pd.read_csv(SENATORS_CSV_PATH)
        senate_states = sorted(df["estado"].unique())

    all_50_states = sorted(vep_dict.keys())
    states_match = (senate_states == all_50_states) if senate_states else (len(all_50_states) == 50)
    total_50_states_vep = sum(vep_dict.values())

    return {
        "states_count": len(all_50_states),
        "matches_senate_composition": states_match,
        "total_50_states_vep": total_50_states_vep,
        "sample_states": {s: vep_dict[s] for s in all_50_states[:5]},
    }


# Exported mapping populated dynamically from the official dataset
STATE_VEP: Dict[str, int] = load_state_vep()


if __name__ == "__main__":
    report = verify_senate_voters()
    print("==================================================")
    print("US SENATE VOTING-ELIGIBLE POPULATION VERIFICATION")
    print("==================================================")
    print(f"States loaded: {report['states_count']} / 50")
    print(f"Matches Senate Composition (100 Senators): {report['matches_senate_composition']}")
    print(f"Total Senate Electorate (50 States VEP): {report['total_50_states_vep']:,}")
    print("\nTop 5 sample states:")
    for st, v in report["sample_states"].items():
        print(f"  {st:15s}: {v:10,d}")
    print("==================================================")
