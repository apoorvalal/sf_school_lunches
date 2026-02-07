#!/usr/bin/env python3
"""Geocode unique meal supply sites using the U.S. Census geocoder API."""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Any

import requests


GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
BENCHMARK = "Public_AR_Current"


def unique_sites(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    seen: set[str] = set()
    sites: list[dict[str, str]] = []
    for row in rows:
        site_id = row["site_id"]
        if site_id in seen:
            continue
        seen.add(site_id)
        sites.append(
            {
                "site_id": site_id,
                "site_name": row["site_name"],
                "address": row["address"],
            }
        )
    sites.sort(key=lambda s: s["site_id"])
    return sites


def geocode_one(session: requests.Session, full_address: str) -> dict[str, Any]:
    params = {
        "address": full_address,
        "benchmark": BENCHMARK,
        "format": "json",
    }
    response = session.get(GEOCODER_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    matches = payload.get("result", {}).get("addressMatches", [])
    if not matches:
        return {
            "matched": False,
            "matched_address": "",
            "match_type": "",
            "lat": "",
            "lon": "",
            "tiger_line_id": "",
        }
    best = matches[0]
    coords = best.get("coordinates", {})
    tiger = best.get("tigerLine", {})
    return {
        "matched": True,
        "matched_address": best.get("matchedAddress", ""),
        "match_type": best.get("matchType", ""),
        "lat": coords.get("y", ""),
        "lon": coords.get("x", ""),
        "tiger_line_id": tiger.get("tigerLineId", ""),
    }


def write_csv(rows: list[dict[str, Any]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "site_id",
        "site_name",
        "address",
        "full_address_query",
        "matched",
        "matched_address",
        "match_type",
        "lat",
        "lon",
        "tiger_line_id",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/processed/site_day_supply.csv"),
        help="Input LP supply CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/site_locations.csv"),
        help="Output geocoded site CSV.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.05,
        help="Delay between API requests.",
    )
    args = parser.parse_args()

    sites = unique_sites(args.input_csv)
    results: list[dict[str, Any]] = []
    with requests.Session() as session:
        for idx, site in enumerate(sites, start=1):
            query = f"{site['address']}, San Francisco, CA"
            geocode = geocode_one(session, query)
            results.append(
                {
                    **site,
                    "full_address_query": query,
                    **geocode,
                }
            )
            if idx < len(sites):
                time.sleep(args.sleep_seconds)

    write_csv(results, args.output_csv)

    matched = sum(1 for row in results if row["matched"])
    print(
        f"Wrote {len(results)} site rows to {args.output_csv}. "
        f"Matched {matched}/{len(results)}."
    )


if __name__ == "__main__":
    main()
