#!/usr/bin/env python3
"""Extract San Francisco school-level unduplicated counts from CDE Excel.
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path


def main():
    p = Path('data/raw/cupc2425-k12.xlsx')
    if not p.exists():
        raise SystemExit(f"Missing {p}; download first")
    df = pd.read_excel(p, sheet_name='School-Level CALPADS UPC Data', header=1, engine='openpyxl')
    cols = df.columns.tolist()
    county_col = None
    school_col = None
    undup_col = None
    for c in cols:
        lc = str(c).lower()
        if 'county code' in lc:
            county_col = c
        if 'school name' in lc:
            school_col = c
        if 'unduplicated' in lc and 'pupil' in lc:
            undup_col = c
    if county_col is None or school_col is None or undup_col is None:
        print('Could not detect necessary columns; available columns:')
        for c in cols:
            print(' -', repr(str(c)))
        raise SystemExit('Aborting')
    subset = df[df[county_col].astype(str).str.zfill(2).isin(['075','75'])]
    out = subset[[school_col, county_col, undup_col]].copy()
    out.columns = ['School Name', 'County Code', 'Unduplicated']
    out_path = Path('data/raw/cupc2425_schoollevel_sf.csv')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print('Wrote', out_path, 'rows:', len(out))


if __name__ == '__main__':
    main()
