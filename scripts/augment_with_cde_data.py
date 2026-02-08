#!/usr/bin/env python3
"""Augment tract demand using California unduplicated student counts (CDE).

Produces a tract-level child population CSV with unduplicated student counts
assigned to the nearest tract centroid, and a small comparison summary
versus the existing ACS-based tract child population.

Usage:
  python scripts/augment_with_cde_data.py --cde-csv <path-or-url> [--count-col Unduplicated] 

If the CDE file lacks lat/lon, the script will attempt to match school names
to `data/processed/site_locations.csv` to inherit coordinates.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import urllib.request
from pathlib import Path
from difflib import get_close_matches


def haversine_miles(lat1, lon1, lat2, lon2):
    # returns distance in miles
    R = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def download_if_url(path: str) -> Path:
    p = Path(path)
    if p.exists():
        return p
    # try download
    url = path
    tmp = Path("/tmp/cde_download.csv")
    try:
        urllib.request.urlretrieve(url, tmp)
        return tmp
    except Exception as e:
        raise RuntimeError(f"Couldn't read or download {path}: {e}")


def read_csv_path(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_site_locations(path: Path) -> dict[str, dict]:
    rows = read_csv_path(path)
    out = {}
    for r in rows:
        out[r.get("site_name", r.get("site_id", ""))] = r
    return out


def find_nearest_tract(lat, lon, tract_centroids):
    best = None
    best_d = float("inf")
    for t in tract_centroids:
        d = haversine_miles(lat, lon, float(t["centroid_lat"]), float(t["centroid_lon"]))
        if d < best_d:
            best_d = d
            best = t
    return best, best_d


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cde-csv", required=True, help="Path or URL to CDE CSV")
    parser.add_argument("--count-col", default="unduplicated", help="Column name with unduplicated student counts (case-insensitive substring match)")
    parser.add_argument("--site-locations", default="data/processed/site_locations.csv")
    parser.add_argument("--tract-centroids", default="data/processed/tract_centroids.csv")
    parser.add_argument("--output-tract-child", default="data/processed/tract_child_population_cde.csv")
    parser.add_argument("--comparison-out", default="data/processed/demand_comparison_summary.csv")
    args = parser.parse_args()

    cde_path = Path(download_if_url(args.cde_csv))
    cde_rows = read_csv_path(cde_path)
    if not cde_rows:
        print("No rows in CDE file", file=sys.stderr)
        sys.exit(1)

    # load tract centroids
    tracts = read_csv_path(Path(args.tract_centroids))
    tract_map = {t["tract_geoid"]: t for t in tracts}

    # load site locations for fallback geocoding
    sites = load_site_locations(Path(args.site_locations))
    site_names = list(sites.keys())

    # detect count column heuristically
    header = list(cde_rows[0].keys())
    count_col = None
    lower = [h.lower() for h in header]
    target = args.count_col.lower()
    for h, lh in zip(header, lower):
        if target in lh or "unduplicated" in lh or "free" in lh or "reduced" in lh or "frpm" in lh:
            count_col = h
            break
    if count_col is None:
        print("Couldn't detect count column -- available columns:", header, file=sys.stderr)
        sys.exit(1)

    # detect lat/lon columns
    lat_col = None
    lon_col = None
    for h in header:
        lh = h.lower()
        if "lat" in lh and lat_col is None:
            lat_col = h
        if "lon" in lh or "long" in lh or "longitude" in lh:
            lon_col = h

    tract_counts: dict[str, float] = {t["tract_geoid"]: 0.0 for t in tracts}

    for r in cde_rows:
        try:
            count = float(r.get(count_col, "0") or 0)
        except Exception:
            count = 0.0
        lat = None
        lon = None
        if lat_col and lon_col and r.get(lat_col) and r.get(lon_col):
            try:
                lat = float(r[lat_col])
                lon = float(r[lon_col])
            except Exception:
                lat = lon = None
        # fallback: try to match school name to site locations
        if lat is None or lon is None:
            name = r.get("School Name") or r.get("school_name") or r.get("SCH_NAME") or r.get("School")
            if not name:
                # try any plausible field
                for cand in ["Name", "LEA_NAME", "SCHOOL", "school"]:
                    if cand in r and r[cand]:
                        name = r[cand]
                        break
            if name:
                matches = get_close_matches(name, site_names, n=1, cutoff=0.6)
                if matches:
                    s = sites[matches[0]]
                    try:
                        lat = float(s.get("lat"))
                        lon = float(s.get("lon"))
                    except Exception:
                        lat = lon = None

        if lat is None or lon is None:
            # couldn't locate this school; skip (counts may be lost)
            continue

        nearest, d = find_nearest_tract(lat, lon, tracts)
        if nearest is None:
            continue
        tract_counts[nearest["tract_geoid"]] += count

    # produce tract-level CSV with same header as existing ACS file
    # header: acs_year,state_fips,county_fips,tract_fips,tract_geoid,tract_name,male_under18,female_under18,child_pop_u18
    out_rows = []
    for t in tracts:
        geoid = t["tract_geoid"]
        state_fips = t.get("state_fips", "06")
        county_fips = t.get("county_fips", "075")
        tract_fips = t.get("tract_fips", "")
        tract_name = t.get("tract_name", "")
        total = tract_counts.get(geoid, 0.0)
        out_rows.append(
            {
                "acs_year": "2024",
                "state_fips": state_fips,
                "county_fips": county_fips,
                "tract_fips": tract_fips,
                "tract_geoid": geoid,
                "tract_name": tract_name,
                "male_under18": "",
                "female_under18": "",
                "child_pop_u18": int(round(total)),
            }
        )

    write_csv(Path(args.output_tract_child), out_rows, [
        "acs_year",
        "state_fips",
        "county_fips",
        "tract_fips",
        "tract_geoid",
        "tract_name",
        "male_under18",
        "female_under18",
        "child_pop_u18",
    ])

    # produce simple comparison summary for participation rates
    # read original ACS totals
    orig = read_csv_path(Path("data/processed/tract_child_population.csv"))
    orig_total = sum(int(r.get("child_pop_u18") or 0) for r in orig)
    cde_total = sum(int(r.get("child_pop_u18") or 0) for r in out_rows)

    rates = [0.2, 0.3, 0.4]
    comp_rows = []
    for rate in rates:
        comp_rows.append(
            {
                "participation_rate": rate,
                "total_demand_census": int(round(orig_total * rate)),
                "total_demand_cde": int(round(cde_total * rate)),
                "abs_diff": int(round((cde_total - orig_total) * rate)),
                "pct_diff": "{:.1f}".format(100.0 * (cde_total - orig_total) / max(1, orig_total)),
            }
        )

    write_csv(Path(args.comparison_out), comp_rows, [
        "participation_rate",
        "total_demand_census",
        "total_demand_cde",
        "abs_diff",
        "pct_diff",
    ])

    print(f"Wrote tract-level CDE child counts to {args.output_tract_child}")
    print(f"Wrote comparison summary to {args.comparison_out}")


if __name__ == "__main__":
    main()
