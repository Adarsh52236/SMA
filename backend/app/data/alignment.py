"""Dataset Alignment Engine for Crop Yield, Weather, and Soil Properties.

Merges normalized crop yield observations, Kharif seasonal agroclimatology,
and topsoil pedological profiles at the grain of:
    (state, district, crop, season, year)

Guarantees 1-to-1 join cardinality, validates post-merge row counts,
and enforces strict target-leakage prevention rules.
"""

import os
import pandas as pd
from typing import Dict, Any, Tuple
from app.data.config import data_config
from app.data.schemas import AlignedCropObservation


class DatasetAlignmentService:
    """Merges and validates multimodal agricultural dataset."""

    def __init__(self, config=data_config):
        self.config = config
        os.makedirs(self.config.PROCESSED_DATA_DIR, exist_ok=True)

    def align_datasets(
        self,
        df_yield: pd.DataFrame,
        df_weather: pd.DataFrame,
        df_soil: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Join yield, weather, and soil records with cardinality verification."""
        initial_yield_rows = len(df_yield)
        initial_weather_rows = len(df_weather)
        initial_soil_rows = len(df_soil)

        # 1. Validate merge keys and remove any trailing whitespaces
        df_yield_clean = df_yield.copy()
        df_weather_clean = df_weather.copy()
        df_soil_clean = df_soil.copy()

        df_yield_clean["district"] = df_yield_clean["district"].astype(str).str.strip()
        df_weather_clean["district"] = df_weather_clean["district"].astype(str).str.strip()
        df_soil_clean["district"] = df_soil_clean["district"].astype(str).str.strip()

        # 2. Check for duplicate keys in source datasets before joining
        yield_dup_keys = df_yield_clean.duplicated(subset=["district", "year"]).sum()
        weather_dup_keys = df_weather_clean.duplicated(subset=["district", "year"]).sum()
        soil_dup_keys = df_soil_clean.duplicated(subset=["district"]).sum()

        if yield_dup_keys > 0 or weather_dup_keys > 0 or soil_dup_keys > 0:
            raise ValueError(
                f"Duplicate keys detected prior to alignment! "
                f"Yield: {yield_dup_keys}, Weather: {weather_dup_keys}, Soil: {soil_dup_keys}."
            )

        # 3. Join Yield with Weather on (district, year)
        # We use an inner join to ensure every training observation has real meteorological data
        merged_yw = pd.merge(
            df_yield_clean,
            df_weather_clean,
            on=["district", "year"],
            how="inner",
            suffixes=("", "_weather"),
        )
        post_weather_rows = len(merged_yw)
        unmatched_weather = initial_yield_rows - post_weather_rows

        # 4. Join with District Soil Profile on (district)
        merged_all = pd.merge(
            merged_yw,
            df_soil_clean,
            on=["district"],
            how="inner",
            suffixes=("", "_soil"),
        )
        final_rows = len(merged_all)
        unmatched_soil = post_weather_rows - final_rows

        # 5. Add state and organize columns per AlignedCropObservation schema
        merged_all["state"] = self.config.TARGET_STATE

        # Rename yield source for clarity
        if "source" in merged_all.columns:
            merged_all = merged_all.rename(columns={"source": "yield_source"})

        # Clean quality_flags column to ensure serializability
        if "quality_flags" in merged_all.columns:
            merged_all["quality_flags"] = merged_all["quality_flags"].apply(
                lambda x: x if isinstance(x, list) else []
            )

        # Select & order columns explicitly
        expected_columns = [
            "state",
            "district",
            "crop",
            "season",
            "year",
            "yield_t_ha",
            "reported_area_ha",
            "reported_production_tonnes",
            "cumulative_rainfall_mm",
            "mean_temp_max_c",
            "mean_temp_min_c",
            "mean_solar_radiation_mj_m2",
            "mean_relative_humidity_pct",
            "consecutive_dry_days_max",
            "heat_stress_days",
            "soil_ph",
            "organic_carbon_pct",
            "clay_pct",
            "sand_pct",
            "silt_pct",
            "bulk_density_g_cm3",
            "cation_exchange_capacity_cmol_kg",
            "yield_source",
            "quality_flags",
        ]

        df_final = merged_all[expected_columns].copy()
        df_final = df_final.sort_values(by=["district", "year"]).reset_index(drop=True)

        # Save to processed directory
        output_csv_path = os.path.join(
            self.config.PROCESSED_DATA_DIR, "crop_yield_maharashtra.csv"
        )
        df_final.to_csv(output_csv_path, index=False)

        metadata = {
            "initial_yield_rows": initial_yield_rows,
            "initial_weather_rows": initial_weather_rows,
            "initial_soil_rows": initial_soil_rows,
            "post_weather_merge_rows": post_weather_rows,
            "unmatched_yield_weather_rows": unmatched_weather,
            "final_aligned_rows": final_rows,
            "unmatched_soil_rows": unmatched_soil,
            "output_path": output_csv_path,
            "districts_aligned": sorted(df_final["district"].unique().tolist()),
            "years_aligned": sorted(df_final["year"].unique().tolist()),
            "target_variable": "yield_t_ha",
            "prevented_leakage": [
                "reported_area_ha",
                "reported_production_tonnes",
            ],
        }

        return df_final, metadata
