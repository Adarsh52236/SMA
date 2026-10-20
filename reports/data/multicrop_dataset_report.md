# Multi-Crop Agricultural Dataset & Alignment Audit Report

**Generated**: 2026-10-20T11:37:21.242546+00:00  
**Dataset Artifact**: `C:\Users\adars\OneDrive\Documents\PROJECTS\SMA\data\processed\crop_yield_multicrop.csv`  
**Dataset SHA-256**: `50092b4060979d215d217317691b033c7edc6d0e25c46b309f774ab15f6115fa`  
**Geographic Domain**: Maharashtra, India  
**Historical Horizon**: 1990 – 2017 (28 harvest years)  

---

## 1. Executive Summary

Phase 3 assembled a defensible, multi-crop multimodal dataset integrating historical crop statistics (ICRISAT-TCI DLD), seasonal agroclimatology (NASA POWER), and topsoil pedological profiles (ISRIC SoilGrids 2.0).

- **Total Processed Yield Records**: **5,068** across 7 target crops and 26 districts.
- **Fully Aligned Observations** (Yield + Season Weather + Topsoil): **1,358**
- **Partially Aligned Observations** (Yield + Season Weather): **2,910**
- **Yield-Only Observations** (Coastal/Metropolitan areas without gridded weather): **800**
- **Raw Rows Read**: 62,054
- **Exact Duplicate Rows Dropped**: 31,050 (characteristic of raw DLD exports)

---

## 2. Crop-by-Crop Alignment & Coverage Matrix

| Crop | Category | Default Season | Total Yield Obs | Weather Aligned | Fully Aligned ($N$) | Mean Yield ($t/ha$) | Phase 4 Model-Ready |
|---|---|---|---|---|---|---|---|
| **Soybean** | Oilseed | Kharif | 724 | 616 | **196** | 1.038 ± 0.657 | ✓ Yes (N >= 100) |
| **Rice (Paddy)** | Cereal | Kharif | 724 | 616 | **196** | 1.111 ± 0.817 | ✓ Yes (N >= 100) |
| **Wheat** | Cereal | Rabi | 724 | 594 | **189** | 1.208 ± 0.616 | ✓ Yes (N >= 100) |
| **Cotton** | Cash_Crop | Kharif | 724 | 616 | **196** | 0.183 ± 0.143 | ✓ Yes (N >= 100) |
| **Maize (Corn)** | Cereal | Kharif | 724 | 616 | **196** | 1.555 ± 0.911 | ✓ Yes (N >= 100) |
| **Chickpea (Gram)** | Pulse | Rabi | 724 | 594 | **189** | 0.621 ± 0.281 | ✓ Yes (N >= 100) |
| **Groundnut (Peanut)** | Oilseed | Kharif | 724 | 616 | **196** | 1.051 ± 0.463 | ✓ Yes (N >= 100) |

---

## 3. Geographic Alignment Breakdown

- **Districts with Historical Yield Records (26)**:
  `Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Bombay, Buldhana, Chandrapur, Dhule, Jalgaon, Kolhapur, Nagpur, Nanded, Nashik, Osmanabad, Parbhani, Pune, Raigad, Ratnagiri, Sangli, Satara, Solapur, Thane, Wardha, Yavatmal`
- **Districts with NASA POWER Daily Weather Caches (22)**:
  `Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Buldhana, Chandrapur, Dhule, Jalgaon, Kolhapur, Nagpur, Nanded, Nashik, Osmanabad, Parbhani, Pune, Sangli, Satara, Solapur, Wardha, Yavatmal`
- **Districts with Full Multimodal Alignment (7)**:
  `Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Buldhana`
  *(Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Buldhana)*

> **Scientific Disclosure**: For the 15 districts where daily NASA POWER weather is present but localized ISRIC SoilGrids caches are currently absent, records are preserved with `is_weather_aligned = True` and `is_soil_aligned = False`. We do **NOT** cross-assign neighboring soil profiles or substitute fabricated soil defaults.

---

## 4. Seasonal Weather Alignment & Cross-Year Rules

1. **Kharif Crops** (Soybean, Rice, Cotton, Maize, Groundnut):
   - **Meteorological Window**: June 1 to October 31 of the harvest year (153 days).
   - **Completeness**: 100% complete across all 22 weather-cached districts from 1990 to 2017.
2. **Rabi Crops** (Wheat, Chickpea):
   - **Meteorological Window**: November 1 of year T-1 to March 31 of harvest year T (151 days).
   - **Cross-Year Boundary**: The 1990 harvest year has incomplete Nov-Dec 1989 weather (prior to NASA POWER start date 1990-01-01), and is safely marked unaligned. Harvest years 1991-2017 are 100% complete.

---

## 5. Preservation of the Soybean Benchmark

The baseline soybean dataset (`data/processed/crop_yield_maharashtra.csv`) was preserved with 100% immutability:
- **Baseline Rows**: 194
- **Baseline SHA-256**: `656a3a8999c8feb73d30aae7b6a7fb72c5112a933107fdbe3338bdc17861bf9a`
- **Soybean Coverage in Multi-Crop Dataset**: Exactly 196 fully aligned observations across the 7 verified districts (1990–2017).
- **Difference Analysis**: The 2 additional rows in the multi-crop dataset correspond to `(Ahmednagar, 1990)` and `(Aurangabad, 1990)` where raw ICRISAT records indicated 0.0 area and 0.0 yield. The Phase 1 script had dropped zero-area rows, whereas the Phase 2/3 adapter preserves observed zero yields with appropriate area provenance.
- **Numerical Parity**: Across all 194 overlapping benchmark records, feature and target parity is 100% (max rainfall discrepancy = 0.0 mm, max soil pH discrepancy = 0.0, max yield rounding difference < 0.0001 t/ha).

---

## 6. Recommendations for Phase 4 Modeling

1. **All 7 Target Crops qualify for Phase 4 modeling** (N = 189 to 196 fully aligned observations per crop across the 7 verified districts).
2. **Strategy A (Shared Multi-Crop Pipeline)**: Can be trained on the combined N = 1,356 observations using crop categorical encoding.
3. **Strategy B (Crop-Specific Pipelines)**: Dedicated Random Forest and Gradient Boosting models can be trained independently for each of the 7 crops (N = 189 to 196 per crop).
4. **Strategy C (Regional Mean Baselines)**: Evaluated per-crop and per-district as the reference baseline.
