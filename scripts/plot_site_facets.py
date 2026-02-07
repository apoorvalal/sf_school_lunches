#!/usr/bin/env python3
"""Plot 8x5 site facet grid comparing status quo vs optimal allocations."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparison-csv",
        type=Path,
        default=Path("data/processed/site_day_allocation_comparison.csv"),
        help="Site-day status vs optimal allocation table.",
    )
    parser.add_argument(
        "--site-locations-csv",
        type=Path,
        default=Path("data/processed/site_locations.csv"),
        help="Site location metadata table with addresses.",
    )
    parser.add_argument(
        "--output-png",
        type=Path,
        default=Path("outputs/figures/site_allocation_facets_8x5.png"),
        help="Output PNG path.",
    )
    args = parser.parse_args()

    comp_rows = read_csv(args.comparison_csv)
    site_rows = read_csv(args.site_locations_csv)

    site_meta = {
        row["site_id"]: {
            "site_name": row["site_name"],
            "address": row["address"],
        }
        for row in site_rows
    }

    # Aggregate each site's total two-day meals by scenario.
    # key: (site_id, participation_rate) -> [status_sum, optimal_sum]
    agg: dict[tuple[str, float], list[float]] = defaultdict(lambda: [0.0, 0.0])
    for row in comp_rows:
        site_id = row["site_id"]
        rate = float(row["participation_rate"])
        agg[(site_id, rate)][0] += float(row["status_quo_meals"])
        agg[(site_id, rate)][1] += float(row["optimal_meals"])

    site_ids = sorted(site_meta.keys())
    rates = sorted({float(row["participation_rate"]) for row in comp_rows})

    nrows, ncols = 8, 5
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(22, 30), sharex=True, sharey=True)
    axes_flat = axes.flatten()

    y_max = 0.0
    for site_id in site_ids:
        for rate in rates:
            status, optimal = agg[(site_id, rate)]
            y_max = max(y_max, status, optimal)
    y_max = y_max * 1.08 if y_max > 0 else 1.0

    for idx, site_id in enumerate(site_ids):
        ax = axes_flat[idx]
        ys_status = [agg[(site_id, rate)][0] for rate in rates]
        ys_opt = [agg[(site_id, rate)][1] for rate in rates]

        ax.plot(rates, ys_status, marker="o", linewidth=1.2, markersize=3.8, label="Status Quo")
        ax.plot(rates, ys_opt, marker="s", linewidth=1.2, markersize=3.8, label="Optimal")
        ax.set_ylim(0, y_max)
        ax.grid(alpha=0.25, linewidth=0.5)

        meta = site_meta[site_id]
        ax.set_title(f"{meta['site_name']}\n{meta['address']}", fontsize=8)

    for idx in range(len(site_ids), len(axes_flat)):
        axes_flat[idx].axis("off")

    for ax in axes_flat:
        ax.set_xlabel("Participation Rate", fontsize=8)
        ax.set_ylabel("Two-Day Meals", fontsize=8)
        ax.tick_params(axis="both", labelsize=7)

    handles, labels = axes_flat[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.006),
        ncol=2,
        frameon=False,
        fontsize=11,
    )
    fig.suptitle("Status Quo vs Optimal Reallocation by Site (8 x 5 facets)", fontsize=16, y=0.995)
    fig.tight_layout(rect=(0, 0.03, 1, 0.982))

    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_png, dpi=300)
    plt.close(fig)
    print(f"Wrote facet plot to {args.output_png}")


if __name__ == "__main__":
    main()
