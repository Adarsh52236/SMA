"""Pydantic schemas for data ingestion, normalization, and dataset alignment."""

from typing import List, Optional
from pydantic import BaseModel, Field


class NormalizedYieldRecord(BaseModel):
    """Cleaned, deduplicated crop yield observation."""

    district: str
    crop: str
    season: str
    year: int
    reported_area_ha: float = Field(..., ge=0.0, description="Cultivated area in hectares")
    reported_production_tonnes: float = Field(..., ge=0.0, description="Production in metric tonnes")
    yield_t_ha: float = Field(..., ge=0.0, description="Yield in tonnes per hectare (t/ha)")
    source: str
    quality_flags: List[str] = Field(default_factory=list)


class SeasonalWeatherRecord(BaseModel):
    """Aggregated seasonal weather metrics for a district-year growing season."""

    district: str
    year: int
    season: str
    start_date: str
    end_date: str
    total_days: int
    missing_days: int
    cumulative_rainfall_mm: float = Field(..., ge=0.0)
    mean_temp_max_c: float
    mean_temp_min_c: float
    mean_solar_radiation_mj_m2: float = Field(..., ge=0.0)
    mean_relative_humidity_pct: float = Field(..., ge=0.0, le=100.0)
    consecutive_dry_days_max: int = Field(default=0, description="Max consecutive days with rainfall < 2.5mm")
    heat_stress_days: int = Field(default=0, description="Days with daily max temp >= 35°C")


class DistrictSoilProfile(BaseModel):
    """Topsoil (0-30cm) pedological characteristics for a district."""

    district: str
    latitude: float
    longitude: float
    sampling_point_type: str = "rural_agricultural_centroid"
    depth_interval: str = "0-30cm_weighted_mean"
    soil_ph: float = Field(..., ge=3.5, le=10.0)
    organic_carbon_pct: float = Field(..., ge=0.0, le=10.0)
    clay_pct: float = Field(..., ge=0.0, le=100.0)
    sand_pct: float = Field(..., ge=0.0, le=100.0)
    silt_pct: float = Field(..., ge=0.0, le=100.0)
    bulk_density_g_cm3: float = Field(..., ge=0.8, le=2.2)
    cation_exchange_capacity_cmol_kg: float = Field(..., ge=0.0, le=120.0)


class AlignedCropObservation(BaseModel):
    """Final aligned observation at district x crop x season x year grain."""

    state: str = "Maharashtra"
    district: str
    crop: str
    season: str
    year: int

    # Target variable (strictly excluded from input features)
    yield_t_ha: float = Field(..., ge=0.0, description="Yield in t/ha (Target)")

    # Metadata & historical volume
    reported_area_ha: float = Field(..., ge=0.0)
    reported_production_tonnes: float = Field(..., ge=0.0)

    # Weather predictor features (growing season aggregations)
    cumulative_rainfall_mm: float
    mean_temp_max_c: float
    mean_temp_min_c: float
    mean_solar_radiation_mj_m2: float
    mean_relative_humidity_pct: float
    consecutive_dry_days_max: int
    heat_stress_days: int

    # Soil predictor features
    soil_ph: float
    organic_carbon_pct: float
    clay_pct: float
    sand_pct: float
    silt_pct: float
    bulk_density_g_cm3: float
    cation_exchange_capacity_cmol_kg: float

    # Data governance & provenance
    yield_source: str
    quality_flags: List[str] = Field(default_factory=list)
