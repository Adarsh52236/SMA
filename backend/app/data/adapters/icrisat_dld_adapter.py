"""ICRISAT-TCI District Level Database (DLD) Modular Source Adapter.

Ingests multi-crop district-level agricultural statistics for Maharashtra (1966-2017),
maps crop aliases to the canonical CropRegistry, normalizes units (kg/ha -> t/ha),
resolves district aliases, and returns UnifiedCropObservation records.
"""

import os
import math
import pandas as pd
from typing import List, Tuple, Optional, Any, Set
from app.data.adapters.base import BaseSourceAdapter, AdapterIngestionReport
from app.data.crop_registry import resolve_crop, CropSpecification
from app.data.districts import get_district_by_name
from app.data.unified_schema import UnifiedCropObservation, convert_yield_to_t_ha


class IcrisatDldAdapter(BaseSourceAdapter):
    """Adapter for ICRISAT-TCI District Level Database (DLD) crop records."""

    def __init__(self):
        super().__init__(
            source_id="icrisat_des_dld",
            adapter_name="ICRISAT_TCI_DLD_Adapter",
        )

    def ingest(
        self,
        source_path: str,
        target_crops: Optional[List[str]] = None,
        min_year: int = 1966,
        max_year: int = 2017,
        target_state: str = "Maharashtra",
        **kwargs: Any,
    ) -> Tuple[List[UnifiedCropObservation], AdapterIngestionReport]:
        """Parse raw ICRISAT CSV into canonical UnifiedCropObservation records."""
        report = AdapterIngestionReport(
            adapter_name=self.adapter_name,
            source_id=self.source_id,
            source_path=source_path,
        )

        if not os.path.exists(source_path):
            report.errors.append(f"Source file not found at: {source_path}")
            return [], report

        try:
            df_raw = pd.read_csv(source_path)
        except Exception as e:
            report.errors.append(f"Failed to read CSV: {e}")
            return [], report

        report.total_records_read = len(df_raw)

        # Expected source columns
        expected_cols = {"Year", "Dist Name", "Crop", "Area(1000 ha)", "Production(1000 tons)", "Yield(Kg per ha)"}
        missing_cols = expected_cols - set(df_raw.columns)
        if missing_cols:
            report.errors.append(f"Missing mandatory source columns: {sorted(list(missing_cols))}")
            return [], report

        # Optional target crops resolution filter
        target_crop_ids: Optional[Set[str]] = None
        if target_crops:
            target_crop_ids = set()
            for c in target_crops:
                resolved = resolve_crop(c)
                if resolved:
                    target_crop_ids.add(resolved.crop_id)

        # 1. Deduplicate identical rows (known characteristic of concatenated DLD raw tables)
        pre_dedup = len(df_raw)
        df_clean = df_raw.drop_duplicates()
        report.deduplicated_records = pre_dedup - len(df_clean)

        accepted_observations: List[UnifiedCropObservation] = []

        # Iterate over records and construct UnifiedCropObservation
        for idx, row in df_clean.iterrows():
            raw_crop = str(row["Crop"]).strip() if pd.notna(row["Crop"]) else ""
            raw_dist = str(row["Dist Name"]).strip() if pd.notna(row["Dist Name"]) else ""
            year = int(row["Year"]) if pd.notna(row["Year"]) else None

            # Filter year window
            if year is None or year < min_year or year > max_year:
                report.rejected_records += 1
                report.rejection_reasons["out_of_year_range"] = report.rejection_reasons.get("out_of_year_range", 0) + 1
                continue

            # Resolve crop against registry
            crop_spec: Optional[CropSpecification] = resolve_crop(raw_crop)
            if not crop_spec:
                report.rejected_records += 1
                report.rejection_reasons["unregistered_crop"] = report.rejection_reasons.get("unregistered_crop", 0) + 1
                continue

            if target_crop_ids and crop_spec.crop_id not in target_crop_ids:
                report.rejected_records += 1
                report.rejection_reasons["filtered_crop"] = report.rejection_reasons.get("filtered_crop", 0) + 1
                continue

            # Resolve district
            district_meta = get_district_by_name(raw_dist)
            canonical_district = district_meta.canonical_name if district_meta else raw_dist.title()
            latitude = district_meta.latitude if district_meta else None
            longitude = district_meta.longitude if district_meta else None

            # Determine season
            raw_crop_upper = raw_crop.upper()
            if "KHARIF" in raw_crop_upper:
                season = "Kharif"
            elif "RABI" in raw_crop_upper:
                season = "Rabi"
            elif "SUMMER" in raw_crop_upper:
                season = "Summer"
            else:
                season = crop_spec.default_season

            # Extract agricultural measurements
            raw_yield = row["Yield(Kg per ha)"]
            raw_area = row["Area(1000 ha)"]
            raw_prod = row["Production(1000 tons)"]

            # Parse area (1000 ha -> ha)
            area_ha: Optional[float] = None
            if pd.notna(raw_area) and not math.isnan(raw_area):
                area_ha = round(float(raw_area) * 1000.0, 2)

            # Parse production (1000 tons -> tonnes)
            prod_tonnes: Optional[float] = None
            if pd.notna(raw_prod) and not math.isnan(raw_prod):
                prod_tonnes = round(float(raw_prod) * 1000.0, 2)

            # Convert and validate yield
            yield_t_ha: Optional[float] = None
            quality_flags: List[str] = []

            if pd.notna(raw_yield) and not math.isnan(raw_yield):
                raw_yield_float = float(raw_yield)
                if raw_yield_float < 0:
                    report.rejected_records += 1
                    report.rejection_reasons["negative_yield"] = report.rejection_reasons.get("negative_yield", 0) + 1
                    continue
                # If area is 0 or NaN but yield is reported 0, valid 0
                yield_t_ha = convert_yield_to_t_ha(raw_yield_float, "kg/ha")
            elif prod_tonnes is not None and area_ha is not None and area_ha > 0:
                # Derive yield if raw yield was missing but production and area are recorded
                yield_t_ha = round(prod_tonnes / area_ha, 4)
                quality_flags.append("yield_derived_from_production_area")
            else:
                report.missing_fields_summary["yield"] = report.missing_fields_summary.get("yield", 0) + 1

            # Build deterministic observation ID
            obs_id = f"icrisat_{canonical_district.lower().replace(' ', '_')}_{crop_spec.crop_id}_{season.lower()}_{year}"

            try:
                obs = UnifiedCropObservation(
                    observation_id=obs_id,
                    crop_name=crop_spec.display_name,
                    crop_id=crop_spec.crop_id,
                    crop_category=crop_spec.category,
                    country="India",
                    state=target_state,
                    district=canonical_district,
                    latitude=latitude,
                    longitude=longitude,
                    crop_year=year,
                    season=season,
                    yield_t_ha=yield_t_ha,
                    yield_unit="t/ha",
                    source_yield=float(raw_yield) if pd.notna(raw_yield) and not math.isnan(raw_yield) else None,
                    source_yield_unit="kg/ha",
                    reported_area_ha=area_ha,
                    reported_production_tonnes=prod_tonnes,
                    is_observed_yield=True,
                    source_dataset=self.source_id,
                    source_record_id=str(idx),
                    quality_flags=quality_flags,
                )
                accepted_observations.append(obs)
                report.accepted_records += 1

            except Exception as ex:
                report.rejected_records += 1
                report.rejection_reasons["schema_validation_error"] = report.rejection_reasons.get("schema_validation_error", 0) + 1
                report.warnings.append(f"Row {idx} rejected by UnifiedCropObservation validation: {ex}")

        report.warnings_count = len(report.warnings)
        return accepted_observations, report
