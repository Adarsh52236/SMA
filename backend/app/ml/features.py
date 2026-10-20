"""Feature Registry and Target Leakage Prevention Engine.

Defines eligible agricultural predictor features, documents units, availability
timing, transformations, and enforces strict target-leakage isolation.
"""

from typing import Dict, List, Set
from pydantic import BaseModel


class FeatureMetadata(BaseModel):
    """Specification of an agricultural predictor feature."""

    name: str
    dtype: str
    units: str
    source: str
    availability_time: str
    description: str
    leakage_risk: str


# Explicit registry of eligible predictors
FEATURE_REGISTRY: Dict[str, FeatureMetadata] = {
    # Weather predictors (aggregated across Kharif growing season)
    "cumulative_rainfall_mm": FeatureMetadata(
        name="cumulative_rainfall_mm",
        dtype="float64",
        units="millimeters (mm)",
        source="NASA POWER Agroclimatology Daily",
        availability_time="Harvest or late-season (end of October)",
        description="Total precipitation accumulated across the Kharif growing season (June 1 - October 31).",
        leakage_risk="None (strictly exogenous historical meteorology)",
    ),
    "mean_temp_max_c": FeatureMetadata(
        name="mean_temp_max_c",
        dtype="float64",
        units="Celsius (°C)",
        source="NASA POWER Agroclimatology Daily",
        availability_time="Harvest or late-season",
        description="Mean daily maximum temperature at 2m across the Kharif season.",
        leakage_risk="None",
    ),
    "mean_temp_min_c": FeatureMetadata(
        name="mean_temp_min_c",
        dtype="float64",
        units="Celsius (°C)",
        source="NASA POWER Agroclimatology Daily",
        availability_time="Harvest or late-season",
        description="Mean daily minimum temperature at 2m across the Kharif season.",
        leakage_risk="None",
    ),
    "mean_solar_radiation_mj_m2": FeatureMetadata(
        name="mean_solar_radiation_mj_m2",
        dtype="float64",
        units="MJ/m²/day",
        source="NASA POWER Agroclimatology Daily",
        availability_time="Harvest or late-season",
        description="Mean surface shortwave downward insolation.",
        leakage_risk="None",
    ),
    "mean_relative_humidity_pct": FeatureMetadata(
        name="mean_relative_humidity_pct",
        dtype="float64",
        units="percentage (%)",
        source="NASA POWER Agroclimatology Daily",
        availability_time="Harvest or late-season",
        description="Mean relative humidity at 2m.",
        leakage_risk="None",
    ),
    "consecutive_dry_days_max": FeatureMetadata(
        name="consecutive_dry_days_max",
        dtype="int64",
        units="count of days",
        source="NASA POWER Agroclimatology Daily",
        availability_time="Harvest or late-season",
        description="Longest streak of consecutive days with precipitation < 2.5mm during Kharif.",
        leakage_risk="None",
    ),
    "heat_stress_days": FeatureMetadata(
        name="heat_stress_days",
        dtype="int64",
        units="count of days",
        source="NASA POWER Agroclimatology Daily",
        availability_time="Harvest or late-season",
        description="Count of days where maximum daily temperature exceeded 35°C during Kharif.",
        leakage_risk="None",
    ),
    # Topsoil pedological properties (0-30cm depth)
    "soil_ph": FeatureMetadata(
        name="soil_ph",
        dtype="float64",
        units="pH in H2O (unitless)",
        source="ISRIC SoilGrids 2.0 (0-30cm weighted mean)",
        availability_time="Pre-sowing (static edaphic baseline)",
        description="Topsoil pH measured in water solution.",
        leakage_risk="None (static physical baseline)",
    ),
    "organic_carbon_pct": FeatureMetadata(
        name="organic_carbon_pct",
        dtype="float64",
        units="percentage (%)",
        source="ISRIC SoilGrids 2.0 (0-30cm weighted mean)",
        availability_time="Pre-sowing",
        description="Topsoil organic carbon concentration in weight percentage.",
        leakage_risk="None",
    ),
    "clay_pct": FeatureMetadata(
        name="clay_pct",
        dtype="float64",
        units="percentage (%)",
        source="ISRIC SoilGrids 2.0 (0-30cm weighted mean)",
        availability_time="Pre-sowing",
        description="Clay fraction (<2µm) in weight percentage.",
        leakage_risk="None",
    ),
    "sand_pct": FeatureMetadata(
        name="sand_pct",
        dtype="float64",
        units="percentage (%)",
        source="ISRIC SoilGrids 2.0 (0-30cm weighted mean)",
        availability_time="Pre-sowing",
        description="Sand fraction (50-2000µm) in weight percentage.",
        leakage_risk="None",
    ),
    "silt_pct": FeatureMetadata(
        name="silt_pct",
        dtype="float64",
        units="percentage (%)",
        source="ISRIC SoilGrids 2.0 (0-30cm weighted mean)",
        availability_time="Pre-sowing",
        description="Silt fraction (2-50µm) in weight percentage.",
        leakage_risk="None",
    ),
    "bulk_density_g_cm3": FeatureMetadata(
        name="bulk_density_g_cm3",
        dtype="float64",
        units="g/cm³",
        source="ISRIC SoilGrids 2.0 (0-30cm weighted mean)",
        availability_time="Pre-sowing",
        description="Bulk density of fine earth fraction.",
        leakage_risk="None",
    ),
    "cation_exchange_capacity_cmol_kg": FeatureMetadata(
        name="cation_exchange_capacity_cmol_kg",
        dtype="float64",
        units="cmol(+)/kg",
        source="ISRIC SoilGrids 2.0 (0-30cm weighted mean)",
        availability_time="Pre-sowing",
        description="Cation exchange capacity at pH 7.",
        leakage_risk="None",
    ),
    # Categorical location feature
    "district": FeatureMetadata(
        name="district",
        dtype="object",
        units="categorical name",
        source="Administrative boundary",
        availability_time="Pre-sowing",
        description="District in Maharashtra.",
        leakage_risk="None",
    ),
}

# Strict exclusion list: columns that MUST NEVER enter the predictor feature set
PROHIBITED_LEAKAGE_COLUMNS: Set[str] = {
    "yield_t_ha",                  # Target variable
    "reported_production_tonnes",  # Post-harvest production (yield = prod / area)
    "reported_area_ha",            # Post-harvest area
    "yield_source",                # Metadata
    "quality_flags",               # Post-processing audit flags
    "crop",                        # Constant in single-crop dataset
    "state",                       # Constant
    "season",                      # Constant (Kharif)
}

NUMERIC_FEATURES: List[str] = [
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
]

CATEGORICAL_FEATURES: List[str] = [
    "district",
]

ALL_PREDICTORS: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def validate_feature_columns(columns: List[str]) -> None:
    """Enforce strict target leakage checks before training."""
    leaked = set(columns).intersection(PROHIBITED_LEAKAGE_COLUMNS)
    if leaked:
        raise ValueError(
            f"TARGET LEAKAGE VIOLATION: Prohibited columns detected in training feature set: {sorted(list(leaked))}. "
            "These variables must be strictly excluded."
        )
