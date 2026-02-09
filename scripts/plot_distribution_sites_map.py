#!/usr/bin/env python3
"""
Create a map of SF meal distribution sites with embedded bar charts
showing SFUSD planned vs ACS optimal vs CDE optimal allocations.
"""

import csv
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np
from pathlib import Path
from collections import defaultdict

try:
    import contextily as ctx
    HAS_CONTEXTILY = True
except ImportError:
    HAS_CONTEXTILY = False


def read_csv(path: Path):
    """Read CSV and yield rows as dicts."""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def load_site_locations(path: Path):
    """Load site locations: site_id -> (lat, lon, site_name)."""
    sites = {}
    for row in read_csv(path):
        site_id = row["site_id"].strip()
        try:
            lat = float(row.get("lat") or row.get("latitude", 0))
            lon = float(row.get("lon") or row.get("longitude", 0))
            name = row["site_name"].strip()
            if lat and lon:
                sites[site_id] = {"lat": lat, "lon": lon, "name": name}
        except (ValueError, KeyError):
            pass
    return sites


def load_supply(path: Path):
    """Load supply: site_id -> total meals (sum across days)."""
    supply = defaultdict(float)
    for row in read_csv(path):
        site_id = row["site_id"].strip()
        try:
            meals = float(row["meals_available"])
            supply[site_id] += meals
        except (ValueError, KeyError):
            pass
    return supply


def load_allocations(path: Path):
    """Load allocations: site_id -> total optimal meals (sum across days/scenarios)."""
    allocations = defaultdict(float)
    for row in read_csv(path):
        site_id = row["site_id"].strip()
        try:
            meals = float(row["optimal_meals"])
            allocations[site_id] += meals
        except (ValueError, KeyError):
            pass
    return allocations


def add_small_bar_chart(ax, x, y, values, colors, bar_width=0.002, max_height=0.004):
    """
    Add a small bar chart at position (x, y) on the map.
    values: list of [supply, acs, cde] meal counts
    colors: list of colors for bars
    bar_width: width of each bar (reduced 80% from original 0.01)
    max_height: maximum height of bar (reduced 80% from original 0.03)
    """
    # Normalize values to fit on the map
    if max(values) > 0:
        normalized = [v / max(values) * max_height for v in values]
    else:
        normalized = [0, 0, 0]
    
    bar_positions = [-bar_width, 0, bar_width]
    for i, (pos, val, color) in enumerate(zip(bar_positions, normalized, colors)):
        ax.bar(x + pos, val, width=bar_width * 0.8, bottom=y, color=color, 
               alpha=0.8, edgecolor='black', linewidth=0.3)


def main():
    # Load data
    print("Loading site data...")
    sites = load_site_locations(Path("data/processed/site_locations.csv"))
    supply = load_supply(Path("data/processed/site_day_supply.csv"))
    acs_alloc = load_allocations(Path("data/processed/site_day_allocation_comparison.csv"))
    cde_alloc = load_allocations(Path("data/processed/site_day_allocation_comparison_cde.csv"))
    
    print(f"Loaded {len(sites)} sites")
    
    # Create figure with map
    fig, ax = plt.subplots(figsize=(18, 16))
    
    # Set map bounds (SF bounding box in lat/lon)
    # SF roughly spans: 37.71°N to 37.81°N, -122.52°W to -122.37°W
    lat_min, lat_max = 37.70, 37.82
    lon_min, lon_max = -122.54, -122.36
    
    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_aspect('equal')
    
    # Try to add OpenStreetMap basemap
    if HAS_CONTEXTILY:
        try:
            # Add OSM basemap (zoom level 13 good for SF)
            ctx.add_basemap(ax, crs='EPSG:4326', source=ctx.providers.OpenStreetMap.Mapnik, 
                           zoom=13, alpha=0.6)
            print("✅ Added OpenStreetMap basemap")
        except Exception as e:
            print(f"⚠️  Could not add basemap: {e}")
            ax.set_facecolor('#f0f0f0')
            ax.grid(True, alpha=0.2, linestyle='--')
    else:
        print("⚠️  contextily not installed; using light background instead")
        ax.set_facecolor('#f0f0f0')
        ax.grid(True, alpha=0.2, linestyle='--')
    
    # Plot sites with embedded bar charts
    bar_colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue (SFUSD), Orange (ACS), Green (CDE)
    
    for site_id, site_info in sites.items():
        lat = site_info["lat"]
        lon = site_info["lon"]
        name = site_info["name"]
        
        # Get values for this site
        supply_meals = supply.get(site_id, 0)
        acs_meals = acs_alloc.get(site_id, 0)
        cde_meals = cde_alloc.get(site_id, 0)
        
        values = [supply_meals, acs_meals, cde_meals]
        
        # Skip if all zero
        if max(values) == 0:
            continue
        
        # Add small bar chart at site location (reduced size 80%)
        add_small_bar_chart(ax, lon, lat, values, bar_colors, 
                           bar_width=0.002, max_height=0.004)
        
        # Add site marker (small circle at center)
        ax.plot(lon, lat, 'ko', markersize=4, alpha=0.4, zorder=5)
    
    # Create legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#1f77b4', alpha=0.8, edgecolor='black', label='SFUSD Planned Supply'),
        Patch(facecolor='#ff7f0e', alpha=0.8, edgecolor='black', label='ACS Optimal Allocation'),
        Patch(facecolor='#2ca02c', alpha=0.8, edgecolor='black', label='CDE Optimal Allocation'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=11, framealpha=0.95)
    
    # Labels
    ax.set_xlabel('Longitude', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latitude', fontsize=12, fontweight='bold')
    ax.set_title('San Francisco Meal Distribution Sites:\nPlanned vs. Optimal Allocations (ACS vs. CDE)', 
                fontsize=14, fontweight='bold', pad=20)
    
    # Add note
    note_text = ('Each site shows three bars: SFUSD planned (blue), ACS optimal (orange), CDE optimal (green).\n' +
                'Bar heights scaled relative to maximum meals at any site for visibility.\nBasemap: OpenStreetMap')
    ax.text(0.02, 0.02, note_text, transform=ax.transAxes, fontsize=9, 
           verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='white', alpha=0.85))
    
    output_path = Path("outputs/figures/sf_distribution_sites_map.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ Saved map to {output_path}")
    plt.close()
    
    # Print site summary
    print("\n📍 Site Allocation Summary (sorted by ACS optimal):")
    print(f"{'Site ID':<40} {'SFUSD':>8} {'ACS':>8} {'CDE':>8}")
    print("-" * 70)
    
    sites_with_data = [
        (site_id, supply.get(site_id, 0), acs_alloc.get(site_id, 0), cde_alloc.get(site_id, 0))
        for site_id in sorted(sites.keys())
    ]
    
    # Sort by ACS allocation descending
    sites_with_data.sort(key=lambda x: x[2], reverse=True)
    
    for site_id, supply_val, acs_val, cde_val in sites_with_data[:15]:  # Top 15
        if acs_val > 0:
            print(f"{site_id:<40} {supply_val:>8.1f} {acs_val:>8.1f} {cde_val:>8.1f}")


if __name__ == "__main__":
    main()
