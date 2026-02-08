#!/usr/bin/env python3
"""
Parse CDE school directory and match schools in manual CSV to get coordinates,
then augment tract-level demand with CDE FRPM counts.
"""

import csv
import sys
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

import numpy as np


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two points in miles."""
    R = 3959  # Earth's radius in miles
    lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
    lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def read_csv(path: Path):
    """Read CSV and yield rows as dicts."""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def write_csv(rows, path: Path, fieldnames=None):
    """Write rows to CSV."""
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_cde_directory(directory_path: Path) -> dict[str, tuple[float, float]]:
    """
    Parse CDE school directory (tab-delimited) and extract school name -> (lat, lon).
    Returns dict mapping school name (lowercase) to (latitude, longitude).
    """
    school_coords = {}
    with open(directory_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            school_name = row.get("School", "").strip()
            try:
                lat = float(row.get("Latitude", ""))
                lon = float(row.get("Longitude", ""))
                if school_name and lat and lon:
                    # Normalize school name for matching
                    key = school_name.lower().strip()
                    school_coords[key] = (lat, lon)
            except (ValueError, TypeError):
                pass
    return school_coords


def fuzzy_match_name(name: str, candidates: dict[str, tuple[float, float]], threshold: float = 0.6) -> Optional[tuple[float, float]]:
    """
    Fuzzy match a school name to candidates and return (lat, lon) if found.
    """
    name_lower = name.lower().strip()
    best_match = None
    best_score = 0
    for cand_name in candidates:
        score = SequenceMatcher(None, name_lower, cand_name).ratio()
        if score > best_score:
            best_score = score
            best_match = cand_name
    if best_score >= threshold and best_match:
        return candidates[best_match]
    return None


def load_tract_centroids(path: Path) -> dict[str, tuple[float, float]]:
    """Load tract centroids: tract_geoid -> (lat, lon)."""
    centroids = {}
    for row in read_csv(path):
        tract_geoid = row["tract_geoid"].strip()
        try:
            lat = float(row["centroid_lat"])
            lon = float(row["centroid_lon"])
            centroids[tract_geoid] = (lat, lon)
        except (ValueError, KeyError):
            pass
    return centroids


def find_nearest_tract(lat: float, lon: float, centroids: dict[str, tuple[float, float]]) -> Optional[str]:
    """Find nearest tract centroid by Haversine distance."""
    if not centroids:
        return None
    best_tract = None
    best_dist = float("inf")
    for tract_geoid, (c_lat, c_lon) in centroids.items():
        dist = haversine_miles(lat, lon, c_lat, c_lon)
        if dist < best_dist:
            best_dist = dist
            best_tract = tract_geoid
    return best_tract if best_dist < 50 else None  # 50-mile cap


def augment_with_cde_from_directory(
    manual_csv: Path,
    cde_directory: Path,
    count_col: str,
    tract_centroids_path: Path,
    output_path: Path,
):
    """
    Match schools in manual CSV to CDE directory coordinates, assign to nearest tract,
    and write tract-level totals.
    """
    print(f"Parsing CDE directory from {cde_directory}...")
    school_coords = parse_cde_directory(cde_directory)
    print(f"Loaded {len(school_coords)} schools from directory.")

    print(f"Loading tract centroids from {tract_centroids_path}...")
    centroids = load_tract_centroids(tract_centroids_path)
    print(f"Loaded {len(centroids)} tract centroids.")

    print(f"Reading manual CDE CSV from {manual_csv}...")
    tract_counts = {}
    matched_count = 0
    unmatched_count = 0

    for row in read_csv(manual_csv):
        school_name = row.get("School Name", "").strip()
        try:
            count = float(row[count_col])
        except (ValueError, KeyError):
            count = 0

        if not school_name or count <= 0:
            continue

        # Fuzzy match school name to CDE directory
        coords = fuzzy_match_name(school_name, school_coords, threshold=0.6)
        if coords:
            lat, lon = coords
            nearest_tract = find_nearest_tract(lat, lon, centroids)
            if nearest_tract:
                tract_counts[nearest_tract] = tract_counts.get(nearest_tract, 0) + count
                matched_count += 1
            else:
                unmatched_count += 1
        else:
            unmatched_count += 1

    print(f"Matched {matched_count} schools; {unmatched_count} unmatched.")
    print(f"Assigned counts to {len(tract_counts)} tracts.")

    # Build output rows: replicate all tracts but fill in CDE counts where assigned
    print(f"Building tract-level CDE output...")
    output_rows = []
    for tract_geoid in sorted(centroids.keys()):
        cde_count = int(tract_counts.get(tract_geoid, 0))
        output_rows.append(
            {
                "acs_year": 2024,
                "state_fips": "06",
                "county_fips": "075",
                "tract_fips": tract_geoid[-6:],  # last 6 digits
                "tract_geoid": tract_geoid,
                "tract_name": f"Census Tract {tract_geoid[-6:].lstrip('0') or '0'}",
                "male_under18": "",
                "female_under18": "",
                "child_pop_u18": cde_count,
            }
        )

    write_csv(output_rows, output_path, fieldnames=[
        "acs_year", "state_fips", "county_fips", "tract_fips", "tract_geoid",
        "tract_name", "male_under18", "female_under18", "child_pop_u18"
    ])
    print(f"Wrote tract-level CDE child counts to {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Augment tract demand using CDE directory coordinates.")
    parser.add_argument("--manual-csv", type=Path, default=Path("data/raw/cupc2425-manual.csv"),
                        help="Manual CDE CSV with school counts.")
    parser.add_argument("--cde-directory", type=Path, default=Path("data/raw/cde_school_directory.txt"),
                        help="CDE school directory (tab-delimited).")
    parser.add_argument("--count-col", type=str, default="frpm", help="Column name for counts.")
    parser.add_argument("--tract-centroids", type=Path, default=Path("data/processed/tract_centroids.csv"),
                        help="Tract centroids for nearest-neighbor assignment.")
    parser.add_argument("--output-csv", type=Path, default=Path("data/processed/tract_child_population_cde.csv"),
                        help="Output tract-level CDE counts.")
    args = parser.parse_args()

    augment_with_cde_from_directory(
        manual_csv=args.manual_csv,
        cde_directory=args.cde_directory,
        count_col=args.count_col,
        tract_centroids_path=args.tract_centroids,
        output_path=args.output_csv,
    )
