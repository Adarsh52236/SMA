# Maharashtra Agricultural Data Quality & Alignment Report

**Generated**: 2026-10-20T07:09:06.748072+00:00  
**Target Focus**: Soybean (Kharif season) in Maharashtra, India  
**Historical Period**: 1990 – 2017

---

## 1. Executive Summary & Verification

- **Final Aligned Dataset**: `C:\Users\adars\OneDrive\Documents\PROJECTS\SMA\data\processed\crop_yield_maharashtra.csv`
- **Analytical Observations**: **194** district-year rows
- **Districts Covered**: **7** canonical agricultural districts
- **Years Covered**: **28** harvest years
- **Mean Historical Yield**: **1.05 t/ha** (Range: 0.136 – 2.163 t/ha)
- **Pipeline Integrity Status**: **PASSED**

---

## 2. Source Ingestion Audit

### A. Historical Crop Yield Statistics (ICRISAT-TCI DLD)
- **Source**: ICRISAT-TCI District Level Database for Indian Agriculture (harmonized to 1966 boundaries).
- **Raw Observations Evaluated**: 62,054 rows.
- **Soybean Records (Pre-deduplication)**: 2,698 rows.
- **Identical Duplicate Rows Removed**: 1,350 rows.
- **Zero / Negative Area Records Omitted**: 6 rows (reflects pre-adoption periods).
- **Extreme Yield Observations Flagged**: 3 records (<0.20 or >4.50 t/ha).
- **Valid Normalized Yield Records**: **610** rows.

### B. Daily Agroclimatology (NASA POWER API)
- **Source**: NASA POWER Agroclimatology Daily Archive (0.5° resolution).
- **Growing Season Window**: 06-01 to 10-31 (Kharif monsoon period).
- **Districts Processed**: 22 of 22.
- **Total District-Season Weather Aggregations**: **616** records.
- **Parameters Calculated**: Cumulative Rainfall (mm), Mean Tmax (°C), Mean Tmin (°C), Surface Solar Insolation (MJ/m²/day), Mean Relative Humidity (%), Max Consecutive Dry Days (<2.5mm rain), and Heat Stress Days (Tmax >= 35°C).

### C. Soil Pedological Profiles (ISRIC SoilGrids 2.0)
- **Source**: ISRIC SoilGrids 2.0 Global Gridded Soil Database (250m resolution).
- **Depth Conventional Standard**: Weighted average across topsoil (0–30cm: 0–5cm, 5–15cm, 15–30cm).
- **Districts Successfully Profiled**: **7** of 22.
- **Pedological Indicators**: Soil pH, Organic Carbon (%), Clay (%), Sand (%), Silt (%), Bulk Density (g/cm³), CEC (cmol(+)/kg).

---

## 3. Dataset Alignment & Cardinality Verification

```
  Crop Statistics (DLD)          NASA POWER Weather              ISRIC SoilGrids
  [610 records]                    [616 records]                  [7 profiles]
            │                               │                              │
            └──► Joined on (district, year) ◄──────────────────────────────┘
                                  │
                                  ▼ Post-Merge: 194 rows
```

- **Initial Yield Records**: 610
- **Post-Weather Merge Rows**: 610 (Unmatched weather rows: 0)
- **Post-Soil Merge Rows (Final)**: **194** (Unmatched soil rows: 416)
- **Join Cardinality**: Exactly 1-to-1 per `(district, crop, season, year)` grain. No many-to-many observation multiplication occurred.

---

## 4. Target Leakage Prevention Controls

The following measures strictly prevent future yield information or target-derived statistics from contaminating the predictor features:
1. **Target Isolation**: `yield_t_ha` is designated strictly as the learning target variable.
2. **Feature Exclusions**: `reported_area_ha` and `reported_production_tonnes` are stored for historical record volume and post-evaluation capacity audits, but are strictly excluded from the ML training feature set.
3. **No Target Leakage in Weather**: Weather features represent aggregations strictly within the historical growing season of the specified calendar year.

---

## 5. Domain Caveats & Data Governance Limitations

1. **Spatial Aggregation Smearing**: District-level yield statistics represent county-wide averages. Farm-level microclimates, undulating topography, and local soil differences are smoothed out.
2. **Gridded Model Estimates vs Soil Tests**: SoilGrids parameters are machine learning spatial estimates, not direct soil laboratory measurements from individual farmer fields.
3. **Management Factor Absence**: Fertilizer dosage (NPK), seed varieties (e.g. JS-335 vs newer hybrids), pesticide treatments, and irrigation events are unrecorded in official district statistics.
