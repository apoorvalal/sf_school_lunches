#!/usr/bin/env python3
"""
Generate site-level summary tables for ACS and CDE allocations.
"""

import csv
from pathlib import Path
from collections import defaultdict


def read_csv(path: Path):
    """Read CSV and yield rows as dicts."""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def generate_site_summary_table(allocation_csv_path: Path, output_format="markdown"):
    """
    Generate a summary table of optimal allocations by site (aggregated across days/scenarios).
    """
    site_totals = defaultdict(lambda: {"name": "", "total_optimal": 0.0})
    
    for row in read_csv(allocation_csv_path):
        site_id = row["site_id"].strip()
        site_name = row["site_name"].strip()
        optimal_meals = float(row["optimal_meals"])
        
        if site_id not in site_totals:
            site_totals[site_id]["name"] = site_name
        site_totals[site_id]["total_optimal"] += optimal_meals
    
    # Sort by total optimal meals descending
    sorted_sites = sorted(
        site_totals.items(),
        key=lambda x: x[1]["total_optimal"],
        reverse=True
    )
    
    if output_format == "markdown":
        lines = [
            "| Site ID | Site Name | Total Optimal Meals (All Days/Scenarios) |",
            "|:---|:---|---:|",
        ]
        for site_id, data in sorted_sites:
            lines.append(
                f"| {site_id} | {data['name'][:50]} | {data['total_optimal']:.1f} |"
            )
        return "\n".join(lines)
    else:
        return sorted_sites


def main():
    acs_allocation = Path("data/processed/site_day_allocation_comparison.csv")
    cde_allocation = Path("data/processed/site_day_allocation_comparison_cde.csv")
    
    print("=== ACS-Based Model: Site-Level Allocations ===\n")
    acs_table = generate_site_summary_table(acs_allocation, "markdown")
    print(acs_table)
    
    print("\n\n=== CDE FRPM-Based Model: Site-Level Allocations ===\n")
    cde_table = generate_site_summary_table(cde_allocation, "markdown")
    print(cde_table)
    
    # Write to file for easy insertion into report
    with open("outputs/site_allocation_tables.txt", "w") as f:
        f.write("## ACS-Based Model: Site-Level Allocations\n\n")
        f.write(acs_table)
        f.write("\n\n## CDE FRPM-Based Model: Site-Level Allocations\n\n")
        f.write(cde_table)
    
    print("\n\nWrote tables to outputs/site_allocation_tables.txt")


if __name__ == "__main__":
    main()
