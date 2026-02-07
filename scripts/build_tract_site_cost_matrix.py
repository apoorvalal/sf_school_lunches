#!/usr/bin/env python3
"""Build tract-to-site distance matrix for LP transport cost c_{i,j}."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


EARTH_RADIUS_KM = 6371.0088
KM_TO_MILES = 0.621371192


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1r = math.radians(lat1)
    lon1r = math.radians(lon1)
    lat2r = math.radians(lat2)
    lon2r = math.radians(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, str | float]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tract_geoid",
        "site_id",
        "distance_km",
        "distance_miles",
        "c_ij",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tract-centroids-csv",
        type=Path,
        default=Path("data/processed/tract_centroids.csv"),
        help="Input tract centroids CSV.",
    )
    parser.add_argument(
        "--site-locations-csv",
        type=Path,
        default=Path("data/processed/site_locations.csv"),
        help="Input geocoded site locations CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/tract_site_cost_matrix.csv"),
        help="Output cost matrix CSV.",
    )
    args = parser.parse_args()

    tracts = read_csv(args.tract_centroids_csv)
    site_rows = read_csv(args.site_locations_csv)
    sites = [row for row in site_rows if str(row.get("matched", "")).lower() in {"true", "1"}]
    if not sites:
        raise RuntimeError("No matched sites available to build cost matrix.")

    rows: list[dict[str, str | float]] = []
    for tract in tracts:
        t_lat = float(tract["centroid_lat"])
        t_lon = float(tract["centroid_lon"])
        t_geoid = tract["tract_geoid"]
        for site in sites:
            s_lat = float(site["lat"])
            s_lon = float(site["lon"])
            km = haversine_km(t_lat, t_lon, s_lat, s_lon)
            miles = km * KM_TO_MILES
            rows.append(
                {
                    "tract_geoid": t_geoid,
                    "site_id": site["site_id"],
                    "distance_km": round(km, 6),
                    "distance_miles": round(miles, 6),
                    "c_ij": round(miles, 6),
                }
            )

    rows.sort(key=lambda r: (str(r["tract_geoid"]), str(r["site_id"])))
    write_csv(rows, args.output_csv)
    print(
        f"Wrote {len(rows)} tract-site pairs to {args.output_csv} "
        f"({len(tracts)} tracts x {len(sites)} matched sites)."
    )


if __name__ == "__main__":
    main()
