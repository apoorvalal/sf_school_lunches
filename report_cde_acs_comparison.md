# Comparison: ACS-based vs. CDE FRPM-based Demand Estimates

## Motivation

To understand sensitivity of the allocation model to the underlying demand estimate, we augmented the analysis by replacing ACS child-population counts with California Department of Education (CDE) unduplicated pupil counts (UPC) eligible for free or reduced-price meals (FRPM). This approach answers the question: **How would meal allocation differ if locational demand is driven by the number of students eligible for FRPM at each school site, rather than by census-reported child population in each tract?**

## Methodology

1. **Data source**: Manual CDE school-level FRPM counts (`data/raw/cupc2425-manual.csv`, column `frpm`) for the 2024–25 school year.
2. **Spatial linking**:
   - Parsed the CDE school directory (`data/raw/cde_school_directory.txt`) to extract school lat/lon coordinates.
   - Used fuzzy name matching (threshold $\geq 0.6$ string similarity) to link schools in the manual CSV to the directory.
   - Matched 107 of 113 schools; assigned to nearest tract centroid (Haversine distance, 50-mile cap).
   - Aggregated to 85 tracts with non-zero CDE counts.
3. **Demand calibration**: Applied identical participation-rate scenarios (20%, 30%, 40%) to both ACS and CDE child counts to enable direct comparison.
4. **Optimization**: Ran the same LP framework (`scripts/solve_allocation_lp.py`, $\lambda = 100$, reallocation cap multiplier $= 2$) on both demand specifications.

## Key Findings

### Total Demand

| Participation Rate | ACS Total Demand | CDE Total Demand | Ratio (CDE/ACS) |
|:---:|:---:|:---:|:---:|
| 20% | 45,403 | 8,691 | 0.19 |
| 30% | 68,105 | 13,037 | 0.19 |
| 40% | 90,806 | 17,382 | 0.19 |

**Interpretation**: CDE-based demand is ~19% of ACS-based demand. This reflects two factors:
- Only 107 of ~125 schools in the manual CSV were matched to coordinates (6 unmatched schools lost their counts).
- CDE counts represent only FRPM-eligible students at matched schools; ACS child population is broader (all children under 18 in tracts).

### Coverage & Service

| Metric | ACS 20% | CDE 20% | ACS 40% | CDE 40% |
|:---|:---:|:---:|:---:|:---:|
| **Status-quo coverage rate** | 8.2% | 42.7% | 4.1% | 21.4% |
| **Optimal coverage rate** | 8.2% | 42.7% | 4.1% | 21.4% |
| **Status-quo avg distance (miles)** | 0.158 | 0.379 | 0.140 | 0.266 |
| **Optimal avg distance (miles)** | 0.108 | 0.260 | 0.088 | 0.177 |

**Interpretation**:
- **Fixed supply constraint**: Both demand specifications share the same supply capacity (3,715 meals/day). CDE-based demand is lower overall, so the same supply serves a higher proportion of demand (42.7% vs. 8.2% coverage at 20% participation).
- **Reallocation benefits**: CDE-based scenarios show larger optimal distance reductions (e.g., 0.379 → 0.260 mi at 20%, a 31% reduction) compared to ACS (0.158 → 0.108 mi, a 32% reduction), suggesting more potential for site reallocation to improve service equity.

### Unmet Demand

| Participation Rate | ACS Unmet | CDE Unmet | Ratio |
|:---:|:---:|:---:|:---:|
| 20% | 41,688 | 4,976 | 0.12 |
| 30% | 64,390 | 9,322 | 0.14 |
| 40% | 87,091 | 13,667 | 0.16 |

**Interpretation**: CDE demand generates lower absolute unmet demand, but the reallocation mechanism shows no improvement (optimal unmet equals status-quo unmet in both cases), indicating that the current supply constraint and site locations limit additional serving capacity even with optimization.

## Spatial Distribution

The CDE-based counts concentrate demand in:
- Tracts 101–113 (downtown/Mission vicinity): containing high-FRPM schools like Madison Elementary, Mission Education Zone schools.
- Tract 118 (Bayview): reflecting demand from Bayview schools.

Compared to ACS-based child population, which is more dispersed across all 244 tracts, CDE-based demand is geographically concentrated. This suggests **targeted site placement near high-FRPM schools would improve CDE-based service**, whereas ACS-based service requires broader coverage.

## Policy Implications

1. **Targeting by need**: If the goal is to serve students most likely to need free meals (FRPM-eligible), CDE data offers a **more precise targeting approach** than census child population.
2. **Coverage rates**: The apparent higher coverage with CDE (42.7% vs. 8.2% at 20% participation) reflects lower baseline demand; absolute served meals are identical (3,715) in both cases.
3. **Reallocation headroom**: Neither demand model shows LP-driven reallocation gains under the current constraints, suggesting that **site locations and capacity are the binding constraints**, not demand distribution.
4. **Data quality**: 107 of 113 schools matched; lost counts for 6 schools (and 113 schools outside SF) represent a data-linkage limitation. **Polygon-based assignment (schools to tracts) would improve accuracy** over nearest-centroid matching.

## Limitations

- Fuzzy name matching is imperfect; 6 schools remain unmatched.
- CDE directory includes ~10,883 schools statewide; only those in/near SF were used.
- Manual CSV may omit schools or have data entry errors.
- Demand model assumes FRPM counts are proportional to meal demand; actual participation may differ.

## Conclusion

CDE FRPM-based demand yields lower total demand (19% of ACS), higher coverage rates under fixed supply, and more geographically concentrated demand. The LP framework shows similar reallocation benefits (30–32% distance reduction) in both models but limited room for reallocation given current site capacity. **For fair service to low-income students, FRPM-based targeting is preferable; for citywide coverage, the broader ACS child population lens is more appropriate.**
