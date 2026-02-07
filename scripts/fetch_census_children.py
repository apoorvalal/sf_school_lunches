#!/usr/bin/env python3
"""Fetch SF tract-level child population (age < 18) from Census ACS 5-year API.

By default this script auto-detects the latest available ACS5 year, then queries
all San Francisco County tracts (state 06, county 075) using B01001 age bins.
"""

from __future__ import annotations

import argparse
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


ACS_PATH = "acs/acs5"
STATE_FIPS = "06"   # California
COUNTY_FIPS = "075"  # San Francisco County
API_BASE = "https://api.census.gov/data"

# B01001 bins for ages under 18.
UNDER18_VARS = {
    "male_under_5": "B01001_003E",
    "male_5_9": "B01001_004E",
    "male_10_14": "B01001_005E",
    "male_15_17": "B01001_006E",
    "female_under_5": "B01001_027E",
    "female_5_9": "B01001_028E",
    "female_10_14": "B01001_029E",
    "female_15_17": "B01001_030E",
}


def _api_get(url: str, params: dict[str, str], timeout: int = 30) -> requests.Response:
    response = requests.get(url, params=params, timeout=timeout)
    return response


def detect_latest_acs5_year(
    *,
    api_key: str | None,
    max_year: int,
    min_year: int,
) -> int:
    probe_params = {"get": "NAME", "for": "us:1"}
    if api_key:
        probe_params["key"] = api_key

    for year in range(max_year, min_year - 1, -1):
        url = f"{API_BASE}/{year}/{ACS_PATH}"
        response = _api_get(url, probe_params, timeout=20)
        if response.status_code == 200:
            return year
    raise RuntimeError(
        f"Could not detect an available ACS5 year between {min_year} and {max_year}."
    )


def to_int(value: str) -> int:
    cleaned = value.strip()
    if cleaned in {"", "null", "None"}:
        return 0
    return int(cleaned)


def fetch_sf_tract_children(*, year: int, api_key: str | None) -> list[dict[str, Any]]:
    variable_names = list(UNDER18_VARS.values())
    get_fields = ["NAME", *variable_names]
    params = {
        "get": ",".join(get_fields),
        "for": "tract:*",
        "in": f"state:{STATE_FIPS} county:{COUNTY_FIPS}",
    }
    if api_key:
        params["key"] = api_key

    url = f"{API_BASE}/{year}/{ACS_PATH}"
    response = _api_get(url, params, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(
            f"Census API request failed ({response.status_code}): {response.text[:300]}"
        )

    payload = response.json()
    if not payload or len(payload) < 2:
        raise RuntimeError("Census API returned an empty result set.")

    header = payload[0]
    data_rows = payload[1:]
    idx = {name: pos for pos, name in enumerate(header)}

    output_rows: list[dict[str, Any]] = []
    for row in data_rows:
        male_under18 = sum(to_int(row[idx[var]]) for var in list(UNDER18_VARS.values())[:4])
        female_under18 = sum(to_int(row[idx[var]]) for var in list(UNDER18_VARS.values())[4:])
        child_pop_u18 = male_under18 + female_under18

        state = row[idx["state"]]
        county = row[idx["county"]]
        tract = row[idx["tract"]]

        output_rows.append(
            {
                "acs_year": year,
                "state_fips": state,
                "county_fips": county,
                "tract_fips": tract,
                "tract_geoid": f"{state}{county}{tract}",
                "tract_name": row[idx["NAME"]],
                "male_under18": male_under18,
                "female_under18": female_under18,
                "child_pop_u18": child_pop_u18,
            }
        )

    output_rows.sort(key=lambda r: str(r["tract_geoid"]))
    return output_rows


def write_csv(rows: list[dict[str, Any]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "acs_year",
        "state_fips",
        "county_fips",
        "tract_fips",
        "tract_geoid",
        "tract_name",
        "male_under18",
        "female_under18",
        "child_pop_u18",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="ACS5 year. If omitted, auto-detect latest available year.",
    )
    parser.add_argument(
        "--max-year",
        type=int,
        default=datetime.now().year,
        help="Upper bound for auto year detection (used when --year is omitted).",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=2010,
        help="Lower bound for auto year detection (used when --year is omitted).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Census API key; if omitted, falls back to CENSUS_API_KEY env var.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/tract_child_population.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("CENSUS_API_KEY")
    year = args.year
    if year is None:
        year = detect_latest_acs5_year(
            api_key=api_key,
            max_year=args.max_year,
            min_year=args.min_year,
        )

    rows = fetch_sf_tract_children(year=year, api_key=api_key)
    write_csv(rows, args.output_csv)

    total_children = sum(int(r["child_pop_u18"]) for r in rows)
    print(
        f"Wrote {len(rows)} tracts for ACS {year} to {args.output_csv}. "
        f"Total child_pop_u18={total_children}."
    )
    if api_key:
        print("API key used: yes")
    else:
        print("API key used: no (allowed for low-volume queries).")


if __name__ == "__main__":
    main()
