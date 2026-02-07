#!/usr/bin/env python3
"""Solve status-quo vs optimal-reallocation lunch allocation LPs and plot comparison."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import linprog


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, Any]], output_csv: Path, fieldnames: list[str]) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def solve_status_quo(
    costs: np.ndarray,
    demand: np.ndarray,
    supply: np.ndarray,
    unmet_penalty: float,
) -> dict[str, Any]:
    n_i, n_j = costs.shape
    n_x = n_i * n_j
    n_u = n_i
    n_vars = n_x + n_u

    c = np.zeros(n_vars)
    c[:n_x] = costs.reshape(-1)
    c[n_x:] = unmet_penalty

    # Site capacity: sum_i x_ij <= supply_j
    a_ub = np.zeros((n_j, n_vars))
    b_ub = supply.copy()
    for j in range(n_j):
        for i in range(n_i):
            a_ub[j, i * n_j + j] = 1.0

    # Demand balance: sum_j x_ij + u_i = demand_i
    a_eq = np.zeros((n_i, n_vars))
    b_eq = demand.copy()
    for i in range(n_i):
        row = i
        for j in range(n_j):
            a_eq[row, i * n_j + j] = 1.0
        a_eq[row, n_x + i] = 1.0

    bounds = [(0, None)] * n_vars
    res = linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f"Status quo LP failed: {res.message}")

    z = res.x
    x = z[:n_x].reshape((n_i, n_j))
    u = z[n_x:]
    return {
        "x": x,
        "u": u,
        "y": supply.copy(),  # fixed
        "objective": float(res.fun),
    }


def solve_optimal_reallocation(
    costs: np.ndarray,
    demand: np.ndarray,
    status_supply: np.ndarray,
    unmet_penalty: float,
    reallocation_cap_multiplier: float,
) -> dict[str, Any]:
    n_i, n_j = costs.shape
    n_x = n_i * n_j
    n_u = n_i
    n_y = n_j
    n_vars = n_x + n_u + n_y

    c = np.zeros(n_vars)
    c[:n_x] = costs.reshape(-1)
    c[n_x : n_x + n_u] = unmet_penalty

    # 1) Link x to y: sum_i x_ij - y_j <= 0
    # 2) y upper bound: y_j <= cap_multiplier * status_supply_j
    a_ub = np.zeros((2 * n_j, n_vars))
    b_ub = np.zeros(2 * n_j)
    for j in range(n_j):
        # link
        for i in range(n_i):
            a_ub[j, i * n_j + j] = 1.0
        a_ub[j, n_x + n_u + j] = -1.0
        b_ub[j] = 0.0

        # upper bound
        a_ub[n_j + j, n_x + n_u + j] = 1.0
        b_ub[n_j + j] = reallocation_cap_multiplier * status_supply[j]

    # 1) Demand balance: sum_j x_ij + u_i = demand_i
    # 2) Daily total supply conservation: sum_j y_j = sum_j status_supply_j
    a_eq = np.zeros((n_i + 1, n_vars))
    b_eq = np.zeros(n_i + 1)
    for i in range(n_i):
        for j in range(n_j):
            a_eq[i, i * n_j + j] = 1.0
        a_eq[i, n_x + i] = 1.0
        b_eq[i] = demand[i]
    a_eq[n_i, n_x + n_u : n_x + n_u + n_j] = 1.0
    b_eq[n_i] = float(np.sum(status_supply))

    bounds = [(0, None)] * n_vars
    res = linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")
    if not res.success:
        raise RuntimeError(f"Optimal-reallocation LP failed: {res.message}")

    z = res.x
    x = z[:n_x].reshape((n_i, n_j))
    u = z[n_x : n_x + n_u]
    y = z[n_x + n_u :]
    return {
        "x": x,
        "u": u,
        "y": y,
        "objective": float(res.fun),
    }


def build_cost_lookup(cost_rows: list[dict[str, str]]) -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for row in cost_rows:
        lookup[(row["tract_geoid"], row["site_id"])] = float(row["c_ij"])
    return lookup


def plot_site_day_comparison(
    site_rows: list[dict[str, Any]],
    out_png: Path,
) -> None:
    by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rate_by_scenario: dict[str, float] = {}
    for row in site_rows:
        by_scenario[row["scenario_id"]].append(row)
        rate_by_scenario[row["scenario_id"]] = float(row["participation_rate"])

    scenarios = sorted(by_scenario.keys(), key=lambda s: rate_by_scenario[s])
    n = len(scenarios)
    fig, axes = plt.subplots(1, n, figsize=(5 * n, 4), sharex=True, sharey=True)
    if n == 1:
        axes = [axes]

    for ax, scenario in zip(axes, scenarios):
        rows = by_scenario[scenario]
        xs = [float(r["status_quo_meals"]) for r in rows]
        ys = [float(r["optimal_meals"]) for r in rows]
        max_val = max(xs + ys) if rows else 1.0
        ax.scatter(xs, ys, alpha=0.8, s=32)
        ax.plot([0, max_val], [0, max_val], linestyle="--", linewidth=1.2)
        ax.set_title(f"{scenario} (rate={rate_by_scenario[scenario]:.2f})")
        ax.set_xlabel("Status Quo Meals (site-day)")
        ax.set_ylabel("Optimal Meals (site-day)")

    fig.suptitle("Status Quo vs Optimal Site-Day Lunch Allocations")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--supply-csv",
        type=Path,
        default=Path("data/processed/site_day_supply.csv"),
        help="Site/day supply CSV.",
    )
    parser.add_argument(
        "--demand-csv",
        type=Path,
        default=Path("data/processed/tract_day_demand.csv"),
        help="Tract/day demand CSV with scenarios.",
    )
    parser.add_argument(
        "--cost-csv",
        type=Path,
        default=Path("data/processed/tract_site_cost_matrix.csv"),
        help="Tract-site c_ij matrix CSV.",
    )
    parser.add_argument(
        "--meal-type",
        type=str,
        default="lunch",
        help="Meal type to solve.",
    )
    parser.add_argument(
        "--unmet-penalty",
        type=float,
        default=100.0,
        help="Penalty for unmet demand (must exceed typical distance cost).",
    )
    parser.add_argument(
        "--reallocation-cap-multiplier",
        type=float,
        default=2.0,
        help="Upper bound multiplier on site-day meals vs status quo for optimal reallocation.",
    )
    parser.add_argument(
        "--summary-out",
        type=Path,
        default=Path("data/processed/allocation_comparison_summary.csv"),
        help="Scenario summary output CSV.",
    )
    parser.add_argument(
        "--site-comparison-out",
        type=Path,
        default=Path("data/processed/site_day_allocation_comparison.csv"),
        help="Site-day comparison output CSV.",
    )
    parser.add_argument(
        "--figure-out",
        type=Path,
        default=Path("outputs/figures/status_quo_vs_optimal_allocations.png"),
        help="Output figure path.",
    )
    args = parser.parse_args()

    supply_rows = [
        row
        for row in read_csv(args.supply_csv)
        if row["meal_type"].strip().lower() == args.meal_type.lower()
    ]
    demand_rows = [
        row
        for row in read_csv(args.demand_csv)
        if row["meal_type"].strip().lower() == args.meal_type.lower()
    ]
    cost_rows = read_csv(args.cost_csv)
    cost_lookup = build_cost_lookup(cost_rows)

    if not supply_rows:
        raise ValueError(f"No supply rows for meal_type={args.meal_type}")
    if not demand_rows:
        raise ValueError(f"No demand rows for meal_type={args.meal_type}")

    site_name_lookup = {row["site_id"]: row["site_name"] for row in supply_rows}

    supply_by_day: dict[str, dict[str, float]] = defaultdict(dict)
    for row in supply_rows:
        day = row["distribution_date"]
        supply_by_day[day][row["site_id"]] = float(row["meals_available"])

    demand_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in demand_rows:
        key = (row["scenario_id"], row["distribution_date"])
        demand_by_key[key].append(row)

    scenario_rates: dict[str, float] = {}
    for row in demand_rows:
        scenario_rates[row["scenario_id"]] = float(row["participation_rate"])

    summary_rows: list[dict[str, Any]] = []
    site_comp_rows: list[dict[str, Any]] = []

    for scenario_id in sorted(scenario_rates, key=lambda s: scenario_rates[s]):
        rate = scenario_rates[scenario_id]

        totals = {
            "demand": 0.0,
            "supply": 0.0,
            "served_status": 0.0,
            "served_optimal": 0.0,
            "unmet_status": 0.0,
            "unmet_optimal": 0.0,
            "dist_status": 0.0,
            "dist_optimal": 0.0,
            "l1_shift": 0.0,
        }

        for day in sorted(supply_by_day.keys()):
            day_supply_map = supply_by_day[day]
            sites = sorted(day_supply_map.keys())
            demand_key = (scenario_id, day)
            day_demand_rows = demand_by_key.get(demand_key, [])
            if not day_demand_rows:
                continue
            tracts = sorted(row["tract_geoid"] for row in day_demand_rows)
            demand_lookup = {row["tract_geoid"]: float(row["expected_demand"]) for row in day_demand_rows}

            n_i = len(tracts)
            n_j = len(sites)
            costs = np.zeros((n_i, n_j))
            for i, tract in enumerate(tracts):
                for j, site in enumerate(sites):
                    key = (tract, site)
                    if key not in cost_lookup:
                        raise KeyError(f"Missing c_ij for tract={tract}, site={site}")
                    costs[i, j] = cost_lookup[key]

            demand_vec = np.array([demand_lookup[tract] for tract in tracts], dtype=float)
            status_supply_vec = np.array([day_supply_map[site] for site in sites], dtype=float)

            status = solve_status_quo(
                costs=costs,
                demand=demand_vec,
                supply=status_supply_vec,
                unmet_penalty=args.unmet_penalty,
            )
            optimal = solve_optimal_reallocation(
                costs=costs,
                demand=demand_vec,
                status_supply=status_supply_vec,
                unmet_penalty=args.unmet_penalty,
                reallocation_cap_multiplier=args.reallocation_cap_multiplier,
            )

            served_status = float(np.sum(status["x"]))
            served_optimal = float(np.sum(optimal["x"]))
            unmet_status = float(np.sum(status["u"]))
            unmet_optimal = float(np.sum(optimal["u"]))
            dist_status = float(np.sum(costs * status["x"]))
            dist_optimal = float(np.sum(costs * optimal["x"]))

            totals["demand"] += float(np.sum(demand_vec))
            totals["supply"] += float(np.sum(status_supply_vec))
            totals["served_status"] += served_status
            totals["served_optimal"] += served_optimal
            totals["unmet_status"] += unmet_status
            totals["unmet_optimal"] += unmet_optimal
            totals["dist_status"] += dist_status
            totals["dist_optimal"] += dist_optimal
            totals["l1_shift"] += float(np.sum(np.abs(optimal["y"] - status_supply_vec)))

            for j, site_id in enumerate(sites):
                status_meals = float(status_supply_vec[j])
                optimal_meals = float(optimal["y"][j])
                site_comp_rows.append(
                    {
                        "scenario_id": scenario_id,
                        "participation_rate": rate,
                        "distribution_date": day,
                        "site_id": site_id,
                        "site_name": site_name_lookup.get(site_id, ""),
                        "status_quo_meals": round(status_meals, 6),
                        "optimal_meals": round(optimal_meals, 6),
                        "delta_meals": round(optimal_meals - status_meals, 6),
                    }
                )

        served_status = totals["served_status"]
        served_optimal = totals["served_optimal"]
        demand_total = totals["demand"]

        summary_rows.append(
            {
                "scenario_id": scenario_id,
                "participation_rate": rate,
                "meal_type": args.meal_type,
                "model_status_quo_served": round(served_status, 6),
                "model_optimal_served": round(served_optimal, 6),
                "total_demand": round(demand_total, 6),
                "total_supply": round(totals["supply"], 6),
                "status_quo_unmet": round(totals["unmet_status"], 6),
                "optimal_unmet": round(totals["unmet_optimal"], 6),
                "status_quo_coverage_rate": round(served_status / demand_total, 6) if demand_total else 0.0,
                "optimal_coverage_rate": round(served_optimal / demand_total, 6) if demand_total else 0.0,
                "status_quo_avg_distance_miles": round(totals["dist_status"] / served_status, 6)
                if served_status
                else 0.0,
                "optimal_avg_distance_miles": round(totals["dist_optimal"] / served_optimal, 6)
                if served_optimal
                else 0.0,
                "total_l1_reallocation": round(totals["l1_shift"], 6),
                "implied_meals_moved": round(0.5 * totals["l1_shift"], 6),
                "unmet_penalty": args.unmet_penalty,
                "reallocation_cap_multiplier": args.reallocation_cap_multiplier,
            }
        )

    write_csv(
        summary_rows,
        args.summary_out,
        [
            "scenario_id",
            "participation_rate",
            "meal_type",
            "model_status_quo_served",
            "model_optimal_served",
            "total_demand",
            "total_supply",
            "status_quo_unmet",
            "optimal_unmet",
            "status_quo_coverage_rate",
            "optimal_coverage_rate",
            "status_quo_avg_distance_miles",
            "optimal_avg_distance_miles",
            "total_l1_reallocation",
            "implied_meals_moved",
            "unmet_penalty",
            "reallocation_cap_multiplier",
        ],
    )
    write_csv(
        site_comp_rows,
        args.site_comparison_out,
        [
            "scenario_id",
            "participation_rate",
            "distribution_date",
            "site_id",
            "site_name",
            "status_quo_meals",
            "optimal_meals",
            "delta_meals",
        ],
    )
    plot_site_day_comparison(site_comp_rows, args.figure_out)

    print(f"Wrote summary: {args.summary_out}")
    print(f"Wrote site-day comparison: {args.site_comparison_out}")
    print(f"Wrote figure: {args.figure_out}")


if __name__ == "__main__":
    main()
