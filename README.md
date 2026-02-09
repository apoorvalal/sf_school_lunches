# SF School Lunches (Strike Allocation LP)

## Key Visualization: Distribution Sites Map

Our analysis reveals significant geographic opportunities for meal reallocation across SF. The map below plots all 40 meal distribution sites with embedded bar charts comparing three allocation strategies:

![SF Distribution Sites Map](outputs/figures/sf_distribution_sites_map.png)

**Map Legend:**
- **Blue bars** = SFUSD planned meals
- **Orange bars** = Optimal allocation using Census child population (ACS)
- **Green bars** = Optimal allocation using school-level FRPM eligibility (CDE)

Each site shows how meal allocations would shift under optimal (LP-based) reallocation versus the current plan. The map reveals that 2-4 strategically located sites could serve far more of the eligible population efficiently.

---

## Project Overview

This project builds a reproducible pipeline to compare:

- `status_quo` meal allocations (listed site-day capacities)
- `optimal_reallocation` allocations from a linear program

for the SF strike days `2026-02-09` and `2026-02-10`, using tract-level child population (`age < 18`) from Census ACS and school-based free/reduced-price lunch (FRPM) eligibility from California Department of Education (CDE).

## What We Built

- Parsed meal-site capacities from an SF.gov PDF export
- Pulled SF tract child population from Census API (ACS 2024 in current run)
- Computed tract centroids from TIGER polygons (GeoPandas)
- Geocoded site addresses (Census geocoder)
- Built tract-site distance cost matrix
- Solved status-quo vs optimal LP comparison across participation scenarios
- Generated figures and a Quarto final report

## Prerequisites

- `uv`
- Quarto installed (e.g. `/usr/bin/quarto`)
- `pdftotext` / `pdfinfo` (Poppler tools)

## Reproduce

1. Sync environment:

```bash
uv sync
```

2.  Verify input data 

`data/Free meals for youth under age 18 during UESF strike _ SF.gov.pdf`

pdf export of [this sfgov page](https://www.sf.gov/departments--children-youth-and-their-families/free-youth-meals-sfusd-school-strike). 

3. Run the pipeline:

```bash
uv run python scripts/extract_meal_sites_from_pdf.py \
  "data/Free meals for youth under age 18 during UESF strike _ SF.gov.pdf" \
  --output-csv data/raw/meal_sites_manual.csv

uv run python scripts/build_site_day_supply.py
uv run python scripts/fetch_census_children.py
uv run python scripts/build_tract_day_demand.py
uv run python scripts/geocode_supply_sites.py
uv run python scripts/build_tract_centroids.py
uv run python scripts/build_tract_site_cost_matrix.py
uv run python scripts/solve_allocation_lp.py
uv run python scripts/plot_site_facets.py
```

4. Render report:

```bash
/usr/bin/quarto render index.qmd --to html
```

## Main Outputs

- `index.html`
- `data/processed/allocation_comparison_summary.csv`
- `data/processed/site_day_allocation_comparison.csv`
- `outputs/figures/status_quo_vs_optimal_allocations.png`
- `outputs/figures/site_allocation_facets_8x5.png`
