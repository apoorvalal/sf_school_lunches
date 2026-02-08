#!/usr/bin/env python3
"""
Create scatterplot comparing ACS vs CDE meal assignments.
"""

import csv
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from collections import defaultdict


def read_csv(path: Path):
    """Read CSV and yield rows as dicts."""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def main():
    acs_path = Path("data/processed/site_day_allocation_comparison.csv")
    cde_path = Path("data/processed/site_day_allocation_comparison_cde.csv")
    output_path = Path("outputs/figures/acs_vs_cde_allocations_scatter.png")
    
    # Read both files
    acs_data = list(read_csv(acs_path))
    cde_data = list(read_csv(cde_path))
    
    # Index by (site_id, distribution_date, scenario_id)
    acs_index = {}
    for row in acs_data:
        key = (row["site_id"], row["distribution_date"], row["scenario_id"])
        acs_index[key] = float(row["optimal_meals"])
    
    cde_index = {}
    for row in cde_data:
        key = (row["site_id"], row["distribution_date"], row["scenario_id"])
        cde_index[key] = float(row["optimal_meals"])
    
    # Collect parallel data points
    acs_meals = []
    cde_meals = []
    scenarios = set()
    
    for key in acs_index:
        if key in cde_index:
            acs_meals.append(acs_index[key])
            cde_meals.append(cde_index[key])
            scenarios.add(key[2])  # scenario_id
    
    scenarios = sorted(scenarios, key=lambda s: float(s.split("_")[1].replace("p", ".")))
    
    # Create scatterplot
    fig, ax = plt.subplots(figsize=(10, 8))
    
    colors = {"pr_0p2": "#1f77b4", "pr_0p3": "#ff7f0e", "pr_0p4": "#2ca02c"}
    
    for scenario in scenarios:
        scenario_acs = []
        scenario_cde = []
        for key, acs_val in acs_index.items():
            if key[2] == scenario and key in cde_index:
                scenario_acs.append(acs_val)
                scenario_cde.append(cde_index[key])
        
        if scenario_acs:
            rate_str = scenario.split("_")[1]  # e.g., "0p2"
            rate_display = rate_str.replace("p", ".")
            label = f"Participation rate {rate_display}"
            ax.scatter(scenario_acs, scenario_cde, alpha=0.6, s=60, 
                      label=label, color=colors.get(scenario, "gray"))
    
    # Add diagonal line (perfect agreement)
    max_val = max(max(acs_meals), max(cde_meals))
    ax.plot([0, max_val], [0, max_val], "k--", alpha=0.3, linewidth=1, label="Perfect agreement")
    
    ax.set_xlabel("ACS Optimal Meals per Site-Day", fontsize=12, fontweight="bold")
    ax.set_ylabel("CDE Optimal Meals per Site-Day", fontsize=12, fontweight="bold")
    ax.set_title("Optimal Meal Allocation: ACS vs. CDE FRPM Demand", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Wrote scatterplot to {output_path}")
    plt.close()
    
    # Summary stats
    print(f"\nScatterplot summary:")
    print(f"  Total site-day-scenario combinations: {len(acs_meals)}")
    print(f"  ACS meals range: {min(acs_meals):.1f} - {max(acs_meals):.1f}")
    print(f"  CDE meals range: {min(cde_meals):.1f} - {max(cde_meals):.1f}")
    print(f"  Correlation: {np.corrcoef(acs_meals, cde_meals)[0, 1]:.3f}")


if __name__ == "__main__":
    main()
