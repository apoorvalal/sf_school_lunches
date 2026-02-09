# Branch Comparison: master → cde-inclusion

## Overview
The `cde-inclusion` branch adds a parallel demand estimation approach using California Department of Education (CDE) FRPM (free/reduced-price meal) unduplicated pupil counts, enabling direct comparison with the existing ACS-based child population demand model.

**Commits:** 2
- `214543b` - adding unduplicated pupil count data
- `7d2a6fc` - adding report

**Files changed:** 26 (+22,746 insertions, -6,136 deletions)

---

## New Features

### 1. CDE Data Integration
**Raw data sources:**
- `data/raw/cupc2425-k12.xlsx` (1.9 MB) - CDE Excel workbook
- `data/raw/cde_school_directory.txt` (18,412 lines) - School directory with coordinates
- `data/raw/cupc2425-manual.csv` (127 schools) - User-provided CDE FRPM counts

**Processed outputs:**
- `data/processed/tract_child_population_cde.csv` - CDE counts aggregated to tracts
- `data/processed/tract_day_demand_cde.csv` - CDE demand scenarios (1,465 rows)
- `data/processed/allocation_comparison_summary_cde.csv` - CDE allocation results
- `data/processed/site_day_allocation_comparison_cde.csv` - Site-level allocations

### 2. New Analysis Scripts (6)
| Script | Purpose |
|--------|---------|
| `augment_with_cde_from_directory.py` | Parse CDE directory, fuzzy-match schools, map to tracts |
| `plot_acs_vs_cde_allocations.py` | Create scatterplot comparing allocations (r=0.382) |
| `generate_site_summary_tables.py` | Generate site-level allocation tables |
| `convert_qmd_to_html.py` | Convert Quarto markdown to standalone HTML |
| `fetch_cde_and_run.py` | Download and process CDE Excel |
| `extract_cde_sf.py` | Parse CDE data from Excel sheets |

### 3. Visualizations
- `outputs/figures/acs_vs_cde_allocations_scatter.png` (304 KB) - Scatterplot of allocations
- `outputs/figures/status_quo_vs_optimal_allocations_cde.png` (121 KB) - CDE allocation comparison

### 4. Rendered HTML Reports
- `index.html` - Rendered from index.qmd
- `problem_formulation.html` - Rendered from problem_formulation.qmd
- `report_sections/empirics_nested.html` - Full empirical analysis report

---

## Key Findings

### Demand Magnitude
| Metric | ACS | CDE | Comparison |
|--------|-----|-----|------------|
| Total (20% part.) | 45,403 meals | 8,691 meals | CDE is 19% of ACS |
| Coverage rate | 8.2% | 42.7% | CDE achieves 5.2× coverage |
| Unmet demand | 41,688 meals | 4,976 meals | CDE has 88% less unmet |
| Geographic scope | 244 tracts | 85 tracts | CDE is concentrated |

### Optimization Results
Both models show:
- **30–34% distance reduction** via optimal reallocation (primary benefit)
- **Largely unchanged unmet demand** (supply is binding constraint)
- **Robust reallocation value** across both demand specs

### Site Allocation Differences
**ACS top 3:**
1. Community Youth Center - Richmond (1,218 meals)
2. FACES SF (1,174 meals)
3. Mission Language & Vocational (1,075 meals)

**CDE top 3:**
1. Richmond Neighborhood Center (1,699 meals)
2. Mission Language & Vocational Main (1,351 meals)
3. Community Youth Center - Chinatown (1,084 meals)

**Scatterplot insight:** Moderate correlation (r = 0.382) shows distinct allocation patterns—ACS disperses across more sites, CDE concentrates near high-FRPM schools.

---

## Report Enhancements

### Section 8: "Demand Sensitivity: Two Cases (ACS vs. CDE FRPM)"
- 8.1 ACS-Based Demand (universal child population)
- 8.2 CDE FRPM-Based Demand (low-income targeted)
- 8.3 Side-by-side comparison with policy guidance table
- 8.4 Methodological notes on CDE augmentation

### Section 9: "Model Outputs: Site-Level Allocations & Comparison"
- 9.1 ACS site allocation table
- 9.2 CDE site allocation table
- 9.3 Scatterplot visualization with interpretation

### Updated Section 10: Execution Log
Added 6 new completed tasks tracking CDE data pipeline.

---

## Data Quality Metrics

**CDE School Matching:**
- Schools matched: 107 of 113 (94.7%)
- Unmatched: 6 schools (data lost)
- Tracts with non-zero CDE demand: 85 of 244 (34.8%)

**Method:** Fuzzy name matching (threshold ≥0.6) + nearest-centroid Haversine distance

**Known Limitations:**
1. Fuzzy matching may miss schools with alternate names
2. Schools outside SF not captured
3. Nearest-centroid assignment is approximate (polygon join would improve accuracy)
4. Manual CSV may be incomplete or contain errors

---

## Policy Guidance (New)

| Objective | Recommended | Rationale |
|-----------|-------------|-----------|
| Citywide strike coverage | **ACS** | Universal; captures all children |
| Target low-income students | **CDE** | FRPM eligibility; direct proxy |
| Resource efficiency | **CDE** | Lower demand enables higher coverage rates |
| Equity by geography | **ACS** | Broader distribution for fairness constraints |

---

## New Analysis Pipeline

```
CDE Excel/Manual CSV 
  ↓ 
augment_with_cde_from_directory.py
  ↓ 
tract_child_population_cde.csv
  ↓ 
build_tract_day_demand.py
  ↓ 
tract_day_demand_cde.csv
  ↓ 
solve_allocation_lp.py
  ↓ 
allocation_comparison_summary_cde.csv
  ↓ 
generate_site_summary_tables.py + plot_acs_vs_cde_allocations.py
  ↓ 
Report tables & scatterplot visualization
```

---

## Files Comparison Summary

### Modified
- `report_sections/empirics_nested.qmd` (+207 lines) - Added Sections 8 & 9

### New Code (627 lines total)
- 6 analysis scripts totaling 627 lines
- 1 HTML conversion utility

### New Data (22,119 insertions)
- Raw: 3 files (1.9 MB Excel + 18.5 MB text directory + CSV)
- Processed: 5 CSV files for CDE pipeline
- Outputs: 3 visualizations + tables

---

## Recommendations for Review

✅ **Start here:**
- [report_sections/empirics_nested.html](report_sections/empirics_nested.html) - Full analysis in browser

✅ **Review visualizations:**
- [outputs/figures/acs_vs_cde_allocations_scatter.png](outputs/figures/acs_vs_cde_allocations_scatter.png)
- [outputs/figures/status_quo_vs_optimal_allocations_cde.png](outputs/figures/status_quo_vs_optimal_allocations_cde.png)

✅ **Check data artifacts:**
- All processed CSVs in `data/processed/`
- Source files in `data/raw/`

✅ **Scripts available for:**
- Reproducibility (all scripts executable)
- Extension (parameterizable for future scenarios)
- Validation (can re-run pipeline end-to-end)
