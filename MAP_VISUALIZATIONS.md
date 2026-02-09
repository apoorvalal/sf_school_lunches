# SF Meal Distribution Sites - Map Visualizations

## Overview
Two complementary map visualizations showing the 40 SF meal distribution sites and meal allocations under three scenarios:
1. **SFUSD Planned**: Current planned distribution
2. **ACS Optimal**: Optimal allocation based on ACS child population data
3. **CDE Optimal**: Optimal allocation based on CDE FRPM (Free/Reduced-Price Lunch) eligibility data

---

## Visualization 1: Static Matplotlib Map with Embedded Bar Charts
**File**: `outputs/figures/sf_distribution_sites_map.png` (355 KB)

### Features
- 40 meal distribution sites plotted on San Francisco map
- Each site has 3-bar chart showing:
  - **Blue bars**: SFUSD planned meals
  - **Orange bars**: ACS optimal allocation
  - **Green bars**: CDE optimal allocation
- Bars scaled to maximum allocation across all sites for visual comparison
- Legend and title included
- Suitable for reports and presentations

### Example Site Rankings (by ACS optimal allocation)
| Site ID | Name | SFUSD Planned | ACS Optimal | CDE Optimal |
|---------|------|--------------|-------------|------------|
| 010 | Community Youth Center - Richmond | 250 | 1,218 | 381 |
| 012 | FACES SF | 200 | 1,174 | 522 |
| 021 | Mission Language & Vocational - Main | 400 | 1,075 | 1,351 |
| 035 | Up On Top | 200 | 900 | 293 |
| 032 | Tel-Hi Neighborhood Center - Site 3 | 150 | 815 | 131 |

---

## Visualization 2: Interactive Folium Web Map
**File**: `outputs/figures/sf_distribution_sites_interactive_map.html` (104 KB)

### Features
- Fully interactive OpenStreetMap-based visualization
- **Click any site** to see a popup with:
  - Site name and meal allocation bars
  - Detailed numbers for each scenario
  - Visual bar chart for quick comparison
- **Marker colors** indicate allocation intensity (red=high, green=low)
- **Hover tooltips** show site name and ACS optimal meals
- **Zoom and pan** to explore different areas of SF
- **Legend** explains marker colors and popup content
- Suitable for exploration and decision-making

### How to Use
1. Open `sf_distribution_sites_interactive_map.html` in any web browser
2. Zoom in/out using scroll wheel or +/- buttons
3. Click any site marker to see allocation details
4. Hover over markers to see quick info

---

## Key Insights from Map Visualizations

### Allocation Divergence
The three allocation schemes show **distinct geographic patterns**:

1. **SFUSD Planned** (Blue):
   - More uniform distribution across sites
   - Range: 40-400 meals per site
   - Total planned: ~8,000 meals/day

2. **ACS Optimal** (Orange):
   - Highly concentrated at 3-4 sites
   - Top site (Richmond Youth Center): 1,218 meals
   - Follows child population density from Census
   - Total optimal: ~19,500 meals/day across scenarios

3. **CDE Optimal** (Green):
   - Different concentration pattern than ACS
   - Top site (Mission Language & Vocational): 1,351 meals
   - Follows school-based FRPM eligibility counts
   - Total optimal: ~19,200 meals/day across scenarios

### Correlation Analysis
- **ACS vs CDE** allocations: r = 0.382 (moderate positive correlation)
- Both demand models suggest 2.4-2.5x more meals could be optimally allocated
- Significant geographic redistribution from current SFUSD plan

### Policy Implications
- **Static map** best for stakeholder presentations and reports
- **Interactive map** best for exploratory analysis and sensitivity testing
- Both visualizations suggest consolidating supply at fewer, strategically located sites based on demand

---

## Files Generated
```
outputs/figures/
├── sf_distribution_sites_map.png (355 KB)          # Static matplotlib map
├── sf_distribution_sites_interactive_map.html (104 KB)  # Interactive Folium map
├── acs_vs_cde_allocations_scatter.png (297 KB)     # Comparison scatterplot
├── status_quo_vs_optimal_allocations.png (116 KB)  # ACS scenario comparison
└── status_quo_vs_optimal_allocations_cde.png (118 KB)  # CDE scenario comparison
```

## Scripts Used
- `scripts/plot_distribution_sites_map.py` - Static matplotlib map
- `scripts/plot_distribution_sites_interactive_map.py` - Interactive Folium map
- `scripts/solve_allocation_lp.py` - LP optimization for both ACS and CDE
