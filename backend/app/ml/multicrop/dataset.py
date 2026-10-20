"""Dataset Ingestion, Pre-Training Audit, and Feature Contract for Multi-Crop Modeling (Phase 4).

Audits Phase 3 processed observations, isolates genuine observed crop yields from
uncultivated district panel zeros, and defines leakage-safe feature boundaries.
"""

import os
import hashlib
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np


TARGET_COLUMN = "yield_t_ha"

CATEGORICAL_FEATURES = ["crop_id", "district", "season"]

WEATHER_FEATURES = [
    "cumulative_rainfall_mm",
    "mean_temp_max_c",
    "mean_temp_min_c",
    "mean_solar_radiation_mj_m2",
    "mean_relative_humidity_pct",
    "consecutive_dry_days_max",
    "heat_stress_days",
]

SOIL_FEATURES = [
    "soil_ph",
    "organic_carbon_pct",
    "clay_pct",
    "sand_pct",
    "silt_pct",
    "bulk_density_g_cm3",
    "cation_exchange_capacity_cmol_kg",
]

MODEL_FEATURE_COLUMNS = CATEGORICAL_FEATURES + WEATHER_FEATURES + SOIL_FEATURES

STRICT_EXCLUDED_COLUMNS = [
    TARGET_COLUMN,
    "yield_unit",
    "is_observed_yield",
    "reported_area_ha",
    "reported_production_tonnes",
    "observation_id",
    "source_record_id",
    "crop",
    "crop_category",
    "state",
    "weather_window_start",
    "weather_window_end",
    "weather_days_total",
    "weather_days_missing",
    "weather_source",
    "soil_depth_interval",
    "soil_source",
    "is_weather_aligned",
    "is_soil_aligned",
    "is_fully_aligned",
    "alignment_status",
    "missingness_flags",
    "quality_flags",
    "quality_score",
    "source_dataset",
]


def compute_file_sha256(filepath: str) -> str:
    """Compute the SHA-256 cryptographic digest of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def get_feature_contract() -> Dict[str, Any]:
    """Return explicit documentation of permitted predictor features and exclusions."""
    return {
        "target": TARGET_COLUMN,
        "categorical_features": CATEGORICAL_FEATURES,
        "weather_features": WEATHER_FEATURES,
        "soil_features": SOIL_FEATURES,
        "total_predictor_count": len(MODEL_FEATURE_COLUMNS),
        "excluded_leakage_features": STRICT_EXCLUDED_COLUMNS,
    }


def load_and_audit_multicrop_data(
    csv_path: str,
    target_crops: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load, audit, and clean the multi-crop dataset for machine learning modeling.

    Audit Rules:
    1. Verify file exists and compute hash.
    2. Confirm only fully aligned observations (yield + seasonal weather + soil profile) are considered.
    3. Distinguish genuine crop failures (area > 0, yield = 0) from uncultivated panel records
       (area == 0, yield == 0). Exclude uncultivated panel records from yield modeling.
    4. Exclude inconsistent records where reported area is 0 but yield is non-zero.
    5. Verify zero target leakage into the predictor columns.

    Args:
        csv_path: Absolute path to data/processed/crop_yield_multicrop.csv.
        target_crops: Optional subset of crops to filter.

    Returns:
        Tuple of (clean_modeling_dataframe, audit_report_dict)
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Multi-crop dataset not found at {csv_path}")

    file_hash = compute_file_sha256(csv_path)
    df_raw = pd.read_csv(csv_path)

    total_records = len(df_raw)
    fully_aligned_records = len(df_raw[df_raw["is_fully_aligned"] == True])

    # Subset to fully aligned observations
    df_fa = df_raw[df_raw["is_fully_aligned"] == True].copy()

    if target_crops:
        df_fa = df_fa[df_fa["crop_id"].isin(target_crops)].copy()

    # Pre-training audit of zero-area and zero-yield patterns
    zero_area_mask = (df_fa["reported_area_ha"] == 0.0) | df_fa["reported_area_ha"].isna()
    zero_yield_mask = df_fa["yield_t_ha"] == 0.0

    uncultivated_panel_zeros = df_fa[zero_area_mask & zero_yield_mask]
    crop_failures_genuine = df_fa[(~zero_area_mask) & zero_yield_mask]
    inconsistent_zero_area_pos_yield = df_fa[zero_area_mask & (~zero_yield_mask)]

    # Exclude uncultivated panel records and inconsistent records
    exclusion_mask = zero_area_mask & (zero_yield_mask | (~zero_yield_mask))
    df_clean = df_fa[~exclusion_mask].copy().reset_index(drop=True)

    # Validate target column integrity
    if df_clean[TARGET_COLUMN].isna().any():
        raise ValueError("Target column contains unexpected NaN values in clean dataset.")
    if (df_clean[TARGET_COLUMN] < 0.0).any():
        raise ValueError("Target column contains negative yield values in clean dataset.")

    # Validate predictor column integrity
    for col in MODEL_FEATURE_COLUMNS:
        if col not in df_clean.columns:
            raise ValueError(f"Required model feature '{col}' missing from dataset.")
        if df_clean[col].isna().any():
            nan_count = df_clean[col].isna().sum()
            raise ValueError(f"Feature '{col}' contains {nan_count} unexpected NaN values in fully aligned subset.")

    # Audit statistics per crop
    per_crop_audit = {}
    for crop_id, group in df_clean.groupby("crop_id"):
        per_crop_audit[crop_id] = {
            "total_clean_observations": len(group),
            "distinct_districts": int(group["district"].nunique()),
            "districts": sorted(group["district"].unique().tolist()),
            "years_range": [int(group["year"].min()), int(group["year"].max())],
            "yield_mean": float(round(group[TARGET_COLUMN].mean(), 4)),
            "yield_std": float(round(group[TARGET_COLUMN].std(), 4)),
            "yield_min": float(round(group[TARGET_COLUMN].min(), 4)),
            "yield_max": float(round(group[TARGET_COLUMN].max(), 4)),
            "yield_median": float(round(group[TARGET_COLUMN].median(), 4)),
        }

    audit_report = {
        "dataset_file": csv_path,
        "dataset_sha256": file_hash,
        "total_source_records": total_records,
        "fully_aligned_records": fully_aligned_records,
        "exclusions": {
            "uncultivated_panel_zeros_count": len(uncultivated_panel_zeros),
            "uncultivated_panel_zeros_districts_crops": {
                f"{c}:{d}": int(cnt)
                for (c, d), cnt in uncultivated_panel_zeros.groupby(["crop_id", "district"]).size().to_dict().items()
            },
            "inconsistent_zero_area_positive_yield_count": len(inconsistent_zero_area_pos_yield),
            "genuine_crop_failures_retained_count": len(crop_failures_genuine),
        },
        "clean_modeling_observations": len(df_clean),
        "per_crop_summary": per_crop_audit,
    }

    return df_clean, audit_report
