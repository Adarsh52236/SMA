"""Historical Crop Production & Yield Ingestion and Normalization.

Retrieves and processes historical agricultural records from the ICRISAT-TCI
District Level Database (DLD) for Maharashtra. Performs deduplication,
canonical district naming, area and production normalization, and yield
computation in tonnes per hectare (t/ha).
"""

import os
import io
import time
import requests
import pandas as pd
from typing import Dict, Any, Tuple
from app.data.config import data_config
from app.data.districts import get_district_by_name
from app.data.schemas import NormalizedYieldRecord


class YieldIngestionService:
    """Ingestion and normalization service for historical crop yield statistics."""

    def __init__(self, config=data_config):
        self.config = config
        os.makedirs(self.config.RAW_DATA_DIR, exist_ok=True)
        os.makedirs(self.config.INTERIM_DATA_DIR, exist_ok=True)

    def fetch_raw_data(self, force_download: bool = False) -> str:
        """Download raw crop CSV from mirror or return cached file path."""
        cache_path = os.path.join(self.config.RAW_DATA_DIR, "crop_data_icrisat_dld.csv")

        if os.path.exists(cache_path) and not force_download:
            return cache_path

        # Download from configured URL
        response = requests.get(
            self.config.CROP_DATA_URL,
            timeout=self.config.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        with open(cache_path, "wb") as f:
            f.write(response.content)

        return cache_path

    def process_records(
        self,
        raw_file_path: str,
        crop: str = "Soybean",
        season: str = "Kharif",
        min_year: int = 1990,
        max_year: int = 2017,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Normalize raw records into validated crop yield observations.

        Returns:
            Tuple of (cleaned_dataframe, audit_metadata_dict)
        """
        df_raw = pd.read_csv(raw_file_path)
        initial_row_count = len(df_raw)

        # 1. Filter target crop (ICRISAT records soybean as 'SOYABEAN')
        crop_name_upper = "SOYABEAN" if crop.lower() == "soybean" else crop.upper()
        df_crop = df_raw[df_raw["Crop"].str.strip().str.upper() == crop_name_upper].copy()

        # 2. Drop identical duplicate rows (known feature of raw concatenated DLD files)
        pre_dedup = len(df_crop)
        df_crop = df_crop.drop_duplicates()
        dedup_count = pre_dedup - len(df_crop)

        # 3. Filter year window
        df_crop = df_crop[(df_crop["Year"] >= min_year) & (df_crop["Year"] <= max_year)].copy()

        normalized_records = []
        unmapped_districts = set()
        zero_area_count = 0
        extreme_yield_count = 0

        for _, row in df_crop.iterrows():
            raw_dist = str(row["Dist Name"]).strip()
            district_meta = get_district_by_name(raw_dist)

            if not district_meta:
                unmapped_districts.add(raw_dist)
                continue

            canonical_district = district_meta.canonical_name
            year = int(row["Year"])

            # In ICRISAT DLD: Area is in 1000 ha, Production is in 1000 metric tons
            area_1000ha = float(row.get("Area(1000 ha)", 0.0))
            prod_1000tons = float(row.get("Production(1000 tons)", 0.0))

            area_ha = area_1000ha * 1000.0
            prod_tonnes = prod_1000tons * 1000.0

            flags = []

            # Filter zero/negligible area
            if area_ha <= 0.0:
                zero_area_count += 1
                continue

            # Calculate derived yield (tonnes/ha)
            yield_t_ha = prod_tonnes / area_ha

            if area_ha < self.config.MIN_AREA_HA:
                flags.append("AREA_BELOW_MIN_THRESHOLD")

            if yield_t_ha < self.config.EXTREME_YIELD_LOW_T_HA:
                flags.append("EXTREME_YIELD_LOW")
                extreme_yield_count += 1
            elif yield_t_ha > self.config.EXTREME_YIELD_HIGH_T_HA:
                flags.append("EXTREME_YIELD_HIGH")
                extreme_yield_count += 1

            record = NormalizedYieldRecord(
                district=canonical_district,
                crop=crop,
                season=season,
                year=year,
                reported_area_ha=round(area_ha, 2),
                reported_production_tonnes=round(prod_tonnes, 2),
                yield_t_ha=round(yield_t_ha, 4),
                source="ICRISAT_TCI_DLD_MAHARASHTRA",
                quality_flags=flags,
            )
            normalized_records.append(record.model_dump())

        df_cleaned = pd.DataFrame(normalized_records)

        # Sort chronologically by district and year
        if not df_cleaned.empty:
            df_cleaned = df_cleaned.sort_values(by=["district", "year"]).reset_index(drop=True)

        # Save to interim directory
        interim_path = os.path.join(
            self.config.INTERIM_DATA_DIR, f"yield_{crop.lower()}_maharashtra.csv"
        )
        df_cleaned.to_csv(interim_path, index=False)

        metadata = {
            "source_file": raw_file_path,
            "raw_total_rows": initial_row_count,
            "crop_rows_pre_dedup": pre_dedup,
            "duplicate_rows_removed": dedup_count,
            "zero_or_negative_area_omitted": zero_area_count,
            "unmapped_districts": list(unmapped_districts),
            "extreme_yield_records_flagged": extreme_yield_count,
            "final_yield_records": len(df_cleaned),
            "years_covered": sorted(df_cleaned["year"].unique().tolist()) if not df_cleaned.empty else [],
            "districts_covered": sorted(df_cleaned["district"].unique().tolist()) if not df_cleaned.empty else [],
            "interim_output_path": interim_path,
        }

        return df_cleaned, metadata
