#!/usr/bin/env python3
"""Build SF tract centroid coordinates from Census TIGER polygons."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import geopandas as gpd


STATE_FIPS = "06"
COUNTY_FIPS = "075"
CENTROID_CRS = "EPSG:3310"  # California Albers
WGS84 = "EPSG:4326"


def detect_tiger_year(population_csv: Path) -> int:
    with population_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"No rows in {population_csv}")
    years = sorted({int(row["acs_year"]) for row in rows})
    return years[-1]


def tiger_url(year: int) -> str:
    return f"zip+https://www2.census.gov/geo/tiger/TIGER{year}/TRACT/tl_{year}_{STATE_FIPS}_tract.zip"


def read_target_geoids(population_csv: Path) -> set[str]:
    with population_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {row["tract_geoid"] for row in rows}


def write_csv(rows: list[dict[str, str | float]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tract_geoid",
        "state_fips",
        "county_fips",
        "tract_fips",
        "tract_name",
        "centroid_lat",
        "centroid_lon",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--population-csv",
        type=Path,
        default=Path("data/processed/tract_child_population.csv"),
        help="Tract population CSV used to align geographies.",
    )
    parser.add_argument(
        "--tiger-year",
        type=int,
        default=None,
        help="TIGER vintage year. Defaults to acs_year from population CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/tract_centroids.csv"),
        help="Output centroid CSV.",
    )
    args = parser.parse_args()

    year = args.tiger_year or detect_tiger_year(args.population_csv)
    targets = read_target_geoids(args.population_csv)

    gdf = gpd.read_file(tiger_url(year))
    sf = gdf[(gdf["STATEFP"] == STATE_FIPS) & (gdf["COUNTYFP"] == COUNTY_FIPS)].copy()
    sf = sf[sf["GEOID"].isin(targets)].copy()
    if sf.empty:
        raise RuntimeError("No SF tracts found in TIGER data after filtering.")

    projected = sf.to_crs(CENTROID_CRS)
    centroids = projected.geometry.centroid
    centroid_points = gpd.GeoSeries(centroids, crs=CENTROID_CRS).to_crs(WGS84)

    rows: list[dict[str, str | float]] = []
    for (_, rec), point in zip(sf.iterrows(), centroid_points):
        rows.append(
            {
                "tract_geoid": rec["GEOID"],
                "state_fips": rec["STATEFP"],
                "county_fips": rec["COUNTYFP"],
                "tract_fips": rec["TRACTCE"],
                "tract_name": rec["NAMELSAD"],
                "centroid_lat": round(float(point.y), 8),
                "centroid_lon": round(float(point.x), 8),
            }
        )

    rows.sort(key=lambda r: str(r["tract_geoid"]))
    write_csv(rows, args.output_csv)
    print(
        f"Wrote {len(rows)} tract centroids to {args.output_csv} "
        f"using TIGER {year}."
    )


if __name__ == "__main__":
    main()
