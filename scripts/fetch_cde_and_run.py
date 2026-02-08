#!/usr/bin/env python3
"""Download CDE unduplicated pupil Excel, convert to CSV, and run augmentation pipeline.

Usage:
  python scripts/fetch_cde_and_run.py --url <xlsx_url>
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="URL to CDE Excel file")
    parser.add_argument("--out-csv", default="/tmp/cde_raw.csv", help="Temporary CSV path")
    args = parser.parse_args()

    try:
        import pandas as pd
    except Exception as e:
        print("pandas is required but not available:", e, file=sys.stderr)
        sys.exit(1)

    url = args.url
    out_csv = Path(args.out_csv)

    print("Downloading and reading Excel...")
    try:
        df = pd.read_excel(url, sheet_name=0, engine="openpyxl")
    except Exception:
        # try without engine
        df = pd.read_excel(url, sheet_name=0)

    print(f"Read sheet with {len(df)} rows and {len(df.columns)} columns")
    # write raw CSV
    df.to_csv(out_csv, index=False)
    print(f"Wrote CSV to {out_csv}")

    # run augment script
    print("Running augment_with_cde_data.py...")
    cmd = [sys.executable, "scripts/augment_with_cde_data.py", "--cde-csv", str(out_csv)]
    subprocess.check_call(cmd)

    # build tract day demand from CDE-derived tract child file
    print("Building tract day demand from CDE-derived file...")
    cmd2 = [sys.executable, "scripts/build_tract_day_demand.py", "--input-csv", "data/processed/tract_child_population_cde.csv", "--output-csv", "data/processed/tract_day_demand_cde.csv"]
    subprocess.check_call(cmd2)

    print("Done. You can now run `scripts/solve_allocation_lp.py` with the CDE demand CSV.")


if __name__ == "__main__":
    main()
