#!/usr/bin/env python3
"""
Create an interactive map of SF meal distribution sites using Folium.
Shows planned vs optimal allocations with popup charts.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict


def read_csv(path: Path):
    """Read CSV and yield rows as dicts."""
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def load_site_locations(path: Path):
    """Load site locations."""
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
    """Load supply."""
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
    """Load allocations."""
    allocations = defaultdict(float)
    for row in read_csv(path):
        site_id = row["site_id"].strip()
        try:
            meals = float(row["optimal_meals"])
            allocations[site_id] += meals
        except (ValueError, KeyError):
            pass
    return allocations


def create_bar_chart_html(supply_val, acs_val, cde_val):
    """Create a simple bar chart HTML for popup."""
    # Find max for scaling
    max_val = max(supply_val, acs_val, cde_val, 1)
    
    # Scale to 0-100 for display
    supply_pct = (supply_val / max_val) * 100
    acs_pct = (acs_val / max_val) * 100
    cde_pct = (cde_val / max_val) * 100
    
    html = f"""
    <div style="width: 220px; font-family: Arial, sans-serif; font-size: 11px;">
        <div style="margin-bottom: 8px;">
            <strong style="color: #1f77b4;">SFUSD Planned</strong>: {supply_val:.0f} meals
            <div style="background-color: #e6f2ff; height: 8px; margin-top: 2px;">
                <div style="background-color: #1f77b4; height: 100%; width: {supply_pct}%;"></div>
            </div>
        </div>
        <div style="margin-bottom: 8px;">
            <strong style="color: #ff7f0e;">ACS Optimal</strong>: {acs_val:.0f} meals
            <div style="background-color: #ffe6cc; height: 8px; margin-top: 2px;">
                <div style="background-color: #ff7f0e; height: 100%; width: {acs_pct}%;"></div>
            </div>
        </div>
        <div>
            <strong style="color: #2ca02c;">CDE Optimal</strong>: {cde_val:.0f} meals
            <div style="background-color: #e6ffe6; height: 8px; margin-top: 2px;">
                <div style="background-color: #2ca02c; height: 100%; width: {cde_pct}%;"></div>
            </div>
        </div>
    </div>
    """
    return html


def main():
    try:
        import folium
        from folium import plugins
    except ImportError:
        print("⚠️  folium not installed. Creating static matplotlib map instead.")
        return
    
    # Load data
    print("Loading site data...")
    sites = load_site_locations(Path("data/processed/site_locations.csv"))
    supply = load_supply(Path("data/processed/site_day_supply.csv"))
    acs_alloc = load_allocations(Path("data/processed/site_day_allocation_comparison.csv"))
    cde_alloc = load_allocations(Path("data/processed/site_day_allocation_comparison_cde.csv"))
    
    print(f"Loaded {len(sites)} sites")
    
    # Create map centered on SF
    sf_center = [37.765, -122.450]
    m = folium.Map(location=sf_center, zoom_start=12, tiles='OpenStreetMap')
    
    # Add sites with popups
    for site_id, site_info in sites.items():
        lat = site_info["lat"]
        lon = site_info["lon"]
        name = site_info["name"]
        
        supply_meals = supply.get(site_id, 0)
        acs_meals = acs_alloc.get(site_id, 0)
        cde_meals = cde_alloc.get(site_id, 0)
        
        # Skip if all zero
        if max(supply_meals, acs_meals, cde_meals) == 0:
            continue
        
        # Determine marker color based on ACS allocation
        if acs_meals > 1000:
            color = 'red'
        elif acs_meals > 500:
            color = 'orange'
        elif acs_meals > 200:
            color = 'yellow'
        else:
            color = 'green'
        
        # Create popup with HTML
        popup_html = f"""
        <div style="font-family: Arial; font-size: 12px; width: 250px;">
            <h4 style="margin: 0 0 10px 0; color: #1f77b4;">{name}</h4>
            {create_bar_chart_html(supply_meals, acs_meals, cde_meals)}
        </div>
        """
        
        popup = folium.Popup(popup_html, max_width=300)
        
        # Add marker
        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            popup=popup,
            color='white',
            fill=True,
            fillColor=color,
            fillOpacity=0.7,
            weight=2,
            tooltip=f"{name}<br>ACS: {acs_meals:.0f} meals"
        ).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
        bottom: 50px; left: 50px; width: 220px; height: 200px; 
        background-color: white; border:2px solid grey; z-index:9999; 
        font-size:12px; font-family: Arial; padding: 10px;">
        
        <h4 style="margin-top: 0;">Meal Distribution Sites</h4>
        
        <p style="margin: 5px 0;"><strong>Marker color</strong> = ACS optimal meals:</p>
        <div style="margin-left: 10px;">
            <span style="color: red; font-weight: bold;">●</span> &gt; 1000 meals<br>
            <span style="color: orange; font-weight: bold;">●</span> 500-1000 meals<br>
            <span style="color: yellow; font-weight: bold;">●</span> 200-500 meals<br>
            <span style="color: green; font-weight: bold;">●</span> &lt; 200 meals
        </div>
        
        <hr style="margin: 8px 0;">
        
        <p style="margin: 5px 0;"><strong>Popup shows:</strong></p>
        <div style="margin-left: 10px; font-size: 11px;">
            <span style="color: #1f77b4;">■</span> SFUSD planned<br>
            <span style="color: #ff7f0e;">■</span> ACS optimal<br>
            <span style="color: #2ca02c;">■</span> CDE optimal
        </div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save map
    output_path = Path("outputs/figures/sf_distribution_sites_interactive_map.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    print(f"✅ Saved interactive map to {output_path}")


if __name__ == "__main__":
    main()
