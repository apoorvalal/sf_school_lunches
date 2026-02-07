#!/usr/bin/env python3
"""Build tract-by-day demand table from tract child population."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def parse_csv_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def parse_float_list(raw: str) -> list[float]:
    values = [float(item.strip()) for item in raw.split(",") if item.strip()]
    if not values:
        raise ValueError("At least one participation rate is required.")
    for value in values:
        if value < 0:
            raise ValueError(f"Participation rate must be non-negative: {value}")
    return values


def apply_rounding(value: float, mode: str) -> float | int:
    if mode == "none":
        return round(value, 6)
    if mode == "round":
        return int(round(value))
    if mode == "floor":
        return int(math.floor(value))
    if mode == "ceil":
        return int(math.ceil(value))
    raise ValueError(f"Unknown rounding mode: {mode}")


def scenario_id(rate: float) -> str:
    return f"pr_{str(rate).replace('.', 'p')}"


def build_demand_rows(
    input_rows: list[dict[str, str]],
    days: list[str],
    meal_types: list[str],
    participation_rates: list[float],
    rounding: str,
) -> list[dict[str, str | int | float]]:
    rows: list[dict[str, str | int | float]] = []
    for rate in participation_rates:
        scen = scenario_id(rate)
        for tract in input_rows:
            child_pop = int(tract["child_pop_u18"])
            for day in days:
                for meal_type in meal_types:
                    expected = child_pop * rate
                    rows.append(
                        {
                            "scenario_id": scen,
                            "participation_rate": rate,
                            "distribution_date": day,
                            "meal_type": meal_type,
                            "tract_geoid": tract["tract_geoid"],
                            "tract_name": tract["tract_name"],
                            "child_pop_u18": child_pop,
                            "expected_demand": apply_rounding(expected, rounding),
                        }
                    )
    rows.sort(
        key=lambda r: (
            str(r["scenario_id"]),
            str(r["distribution_date"]),
            str(r["meal_type"]),
            str(r["tract_geoid"]),
        )
    )
    return rows


def write_csv(rows: list[dict[str, str | int | float]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scenario_id",
        "participation_rate",
        "distribution_date",
        "meal_type",
        "tract_geoid",
        "tract_name",
        "child_pop_u18",
        "expected_demand",
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
        default=Path("data/processed/tract_child_population.csv"),
        help="Tract child population CSV.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/tract_day_demand.csv"),
        help="Output demand CSV.",
    )
    parser.add_argument(
        "--days",
        type=str,
        default="2026-02-09,2026-02-10",
        help="Comma-separated list of demand days.",
    )
    parser.add_argument(
        "--meal-types",
        type=str,
        default="lunch",
        help="Comma-separated list of meal types.",
    )
    parser.add_argument(
        "--participation-rates",
        type=str,
        default="0.2,0.3,0.4",
        help="Comma-separated participation rates.",
    )
    parser.add_argument(
        "--rounding",
        choices=["none", "round", "floor", "ceil"],
        default="none",
        help="Rounding mode for expected_demand.",
    )
    args = parser.parse_args()

    days = parse_csv_list(args.days)
    meal_types = parse_csv_list(args.meal_types)
    rates = parse_float_list(args.participation_rates)
    if not days:
        raise ValueError("At least one day is required.")
    if not meal_types:
        raise ValueError("At least one meal type is required.")

    with args.input_csv.open(newline="", encoding="utf-8") as f:
        input_rows = list(csv.DictReader(f))
    if not input_rows:
        raise ValueError(f"No rows found in {args.input_csv}")

    rows = build_demand_rows(
        input_rows=input_rows,
        days=days,
        meal_types=meal_types,
        participation_rates=rates,
        rounding=args.rounding,
    )
    write_csv(rows, args.output_csv)
    print(
        f"Wrote {len(rows)} rows to {args.output_csv} "
        f"for {len(input_rows)} tracts, {len(days)} day(s), "
        f"{len(meal_types)} meal type(s), {len(rates)} scenario(s)."
    )


if __name__ == "__main__":
    main()
