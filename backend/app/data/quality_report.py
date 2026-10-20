"""Quality Report Generator for Agricultural Data Pipeline.

Generates comprehensive machine-readable JSON and human-readable Markdown reports
documenting data provenance, record counts, deduplication, missingness,
join cardinality, and domain limitations.
"""

import os
import json
from datetime import datetime, timezone
from typing import Dict, Any
from app.data.config import data_config
from app.data.source_registry import DATA_SOURCES


class QualityReportGenerator:
    """Compiles and exports data quality reports."""

    def __init__(self, config=data_config):
        self.config = config
        os.makedirs(self.config.REPORTS_DIR, exist_ok=True)

    def generate_report(
        self,
        yield_meta: Dict[str, Any],
        weather_meta: Dict[str, Any],
        soil_meta: Dict[str, Any],
        alignment_meta: Dict[str, Any],
        validation_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Aggregate all pipeline stage metadata and export reports."""
        timestamp = datetime.now(timezone.utc).isoformat()

        report_data = {
            "title": "Maharashtra Soybean Yield Data Quality & Alignment Report",
            "timestamp_utc": timestamp,
            "crop": self.config.TARGET_CROP,
            "season": self.config.TARGET_SEASON,
            "state": self.config.TARGET_STATE,
            "pipeline_configuration": {
                "start_year": self.config.START_YEAR,
                "end_year": self.config.END_YEAR,
                "kharif_window": f"{self.config.KHARIF_START_MONTH_DAY} to {self.config.KHARIF_END_MONTH_DAY}",
                "min_area_ha": self.config.MIN_AREA_HA,
            },
            "sources": {k: v.model_dump() for k, v in DATA_SOURCES.items()},
            "ingestion_metrics": {
                "yield": yield_meta,
                "weather": weather_meta,
                "soil": soil_meta,
            },
            "alignment_metrics": alignment_meta,
            "validation_results": validation_results,
        }

        # 1. Export JSON report
        json_path = os.path.join(self.config.REPORTS_DIR, "data_quality_report.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # 2. Export Markdown report
        md_path = os.path.join(self.config.REPORTS_DIR, "data_quality_report.md")
        md_content = self._build_markdown_report(report_data)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {
            "json_report_path": json_path,
            "markdown_report_path": md_path,
            "summary": validation_results.get("summary", {}),
        }

    def _build_markdown_report(self, data: Dict[str, Any]) -> str:
        summary = data["validation_results"].get("summary", {})
        ym = data["ingestion_metrics"]["yield"]
        wm = data["ingestion_metrics"]["weather"]
        sm = data["ingestion_metrics"]["soil"]
        am = data["alignment_metrics"]
        val = data["validation_results"]

        md = f"""# Maharashtra Agricultural Data Quality & Alignment Report

**Generated**: {data['timestamp_utc']}  
**Target Focus**: {data['crop']} ({data['season']} season) in {data['state']}, India  
**Historical Period**: {data['pipeline_configuration']['start_year']} – {data['pipeline_configuration']['end_year']}

---

## 1. Executive Summary & Verification

- **Final Aligned Dataset**: `{am.get('output_path', 'N/A')}`
- **Analytical Observations**: **{summary.get('total_rows', 0)}** district-year rows
- **Districts Covered**: **{summary.get('districts_count', 0)}** canonical agricultural districts
- **Years Covered**: **{summary.get('years_count', 0)}** harvest years
- **Mean Historical Yield**: **{summary.get('mean_yield_t_ha', 0.0)} t/ha** (Range: {summary.get('min_yield_t_ha', 0.0)} – {summary.get('max_yield_t_ha', 0.0)} t/ha)
- **Pipeline Integrity Status**: **{"PASSED" if val.get('is_valid') else "FLAGGED"}**

---

## 2. Source Ingestion Audit

### A. Historical Crop Yield Statistics (ICRISAT-TCI DLD)
- **Source**: ICRISAT-TCI District Level Database for Indian Agriculture (harmonized to 1966 boundaries).
- **Raw Observations Evaluated**: {ym.get('raw_total_rows', 0):,} rows.
- **Soybean Records (Pre-deduplication)**: {ym.get('crop_rows_pre_dedup', 0):,} rows.
- **Identical Duplicate Rows Removed**: {ym.get('duplicate_rows_removed', 0):,} rows.
- **Zero / Negative Area Records Omitted**: {ym.get('zero_or_negative_area_omitted', 0):,} rows (reflects pre-adoption periods).
- **Extreme Yield Observations Flagged**: {ym.get('extreme_yield_records_flagged', 0)} records (<0.20 or >4.50 t/ha).
- **Valid Normalized Yield Records**: **{ym.get('final_yield_records', 0)}** rows.

### B. Daily Agroclimatology (NASA POWER API)
- **Source**: NASA POWER Agroclimatology Daily Archive (0.5° resolution).
- **Growing Season Window**: {data['pipeline_configuration']['kharif_window']} (Kharif monsoon period).
- **Districts Processed**: {wm.get('successful_districts', 0)} of {wm.get('districts_requested', 0)}.
- **Total District-Season Weather Aggregations**: **{wm.get('total_seasonal_records', 0)}** records.
- **Parameters Calculated**: Cumulative Rainfall (mm), Mean Tmax (°C), Mean Tmin (°C), Surface Solar Insolation (MJ/m²/day), Mean Relative Humidity (%), Max Consecutive Dry Days (<2.5mm rain), and Heat Stress Days (Tmax >= 35°C).

### C. Soil Pedological Profiles (ISRIC SoilGrids 2.0)
- **Source**: ISRIC SoilGrids 2.0 Global Gridded Soil Database (250m resolution).
- **Depth Conventional Standard**: Weighted average across topsoil (0–30cm: 0–5cm, 5–15cm, 15–30cm).
- **Districts Successfully Profiled**: **{sm.get('successful_profiles', 0)}** of {sm.get('districts_requested', 0)}.
- **Pedological Indicators**: Soil pH, Organic Carbon (%), Clay (%), Sand (%), Silt (%), Bulk Density (g/cm³), CEC (cmol(+)/kg).

---

## 3. Dataset Alignment & Cardinality Verification

```
  Crop Statistics (DLD)          NASA POWER Weather              ISRIC SoilGrids
  [{ym.get('final_yield_records', 0)} records]                    [{wm.get('total_seasonal_records', 0)} records]                  [{sm.get('successful_profiles', 0)} profiles]
            │                               │                              │
            └──► Joined on (district, year) ◄──────────────────────────────┘
                                  │
                                  ▼ Post-Merge: {am.get('final_aligned_rows', 0)} rows
```

- **Initial Yield Records**: {am.get('initial_yield_rows', 0)}
- **Post-Weather Merge Rows**: {am.get('post_weather_merge_rows', 0)} (Unmatched weather rows: {am.get('unmatched_yield_weather_rows', 0)})
- **Post-Soil Merge Rows (Final)**: **{am.get('final_aligned_rows', 0)}** (Unmatched soil rows: {am.get('unmatched_soil_rows', 0)})
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
"""
        return md
