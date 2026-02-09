#!/usr/bin/env python3
"""Parse downloaded CDE school directory Excel into a CSV of school lat/lon.

Writes `data/processed/cde_school_locations.csv` with columns: site_name,lat,lon
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


def find_col(cols, keywords):
    for k in keywords:
        for c in cols:
            if k in str(c).lower():
                return c
    return None


def main():
    p = Path('data/raw/cupc2425-k12.xlsx')
    if not p.exists():
        p = Path('data/raw/cupc2425-k12.xlsx')
    if not p.exists():
        raise SystemExit('Excel not found at data/raw/cupc2425-k12.xlsx')

    # try a couple header rows to handle messy multi-line headers
    sheet = 'School-Level CALPADS UPC Data'
    df = None
    for header in (1, 2, 3, 4):
        try:
            df = pd.read_excel(p, sheet_name=sheet, header=header, engine='openpyxl')
            if df is not None and len(df.columns) > 5:
                break
        except Exception:
            continue
    if df is None:
        raise SystemExit('Failed to read sheet')

    cols = list(df.columns)
    school_col = find_col(cols, ['school name', 'school'])
    county_col = find_col(cols, ['county code', 'county'])
    lat_col = find_col(cols, ['latitude', 'lat'])
    lon_col = find_col(cols, ['longitude', 'lon', 'long'])

    if school_col is None or county_col is None or lat_col is None or lon_col is None:
        print('Detected columns:', cols)
        raise SystemExit('Could not detect necessary columns automatically')

    out = df[[school_col, county_col, lat_col, lon_col]].copy()
    out.columns = ['School Name', 'County Code', 'Latitude', 'Longitude']
    out = out.dropna(subset=['Latitude', 'Longitude'])
    # filter for SF county code 075 (or 75)
    out = out[out['County Code'].astype(str).str.zfill(2).isin(['075', '75'])]

    out_path = Path('data/processed/cde_school_locations.csv')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out[['School Name', 'Latitude', 'Longitude']].to_csv(out_path, index=False)
    print('Wrote', out_path, 'rows', len(out))


if __name__ == '__main__':
    main()
