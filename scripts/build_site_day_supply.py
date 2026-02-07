#!/usr/bin/env python3
"""Build LP-ready site/day/meal supply table from raw meal-site rows."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


def build_supply(input_csv: Path, output_csv: Path) -> None:
    with input_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    grouped: dict[tuple[str, str, str], dict[str, str | int]] = {}
    total_by_key = defaultdict(int)

    for row in rows:
        key = (row["site_id"], row["distribution_date"], row["meal_type"])
        total_by_key[key] += int(row["meals_available"])

        if key not in grouped:
            grouped[key] = {
                "site_id": row["site_id"],
                "site_name": row["site_name"],
                "address": row["address"],
                "distribution_date": row["distribution_date"],
                "day": row["day"],
                "meal_type": row["meal_type"],
                "meals_available": 0,
            }

    for key, total in total_by_key.items():
        grouped[key]["meals_available"] = total

    out_rows = sorted(
        grouped.values(),
        key=lambda r: (
            str(r["site_id"]),
            str(r["distribution_date"]),
            str(r["meal_type"]),
        ),
    )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "site_id",
        "site_name",
        "address",
        "distribution_date",
        "day",
        "meal_type",
        "meals_available",
    ]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"Wrote {len(out_rows)} rows to {output_csv}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=Path("data/raw/meal_sites_manual.csv"),
        help="Raw meal-site CSV path",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/site_day_supply.csv"),
        help="Output processed CSV path",
    )
    args = parser.parse_args()

    build_supply(args.input_csv, args.output_csv)


if __name__ == "__main__":
    main()
