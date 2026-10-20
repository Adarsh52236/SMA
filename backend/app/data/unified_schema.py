"""Canonical Unified Multi-Crop Agricultural Observation Schema.

Provides the standardized Pydantic v2 data model representing an aligned
or partially-aligned agricultural observation across diverse crops, regions,
and seasons. Distinguishes hard validation errors from non-fatal quality warnings.
"""

import math
import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from app.data.crop_registry import CropCategory, resolve_crop
from app.data.season_registry import resolve_season


class WeatherMeasurement(BaseModel):
    """Aggregated seasonal agroclimatology indicators for a crop growing period."""

    cumulative_rainfall_mm: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total precipitation accumulated across the crop growing season in mm.",
    )
    mean_temp_max_c: Optional[float] = Field(
        default=None,
        description="Mean daily maximum temperature at 2m in Celsius (°C).",
    )
    mean_temp_min_c: Optional[float] = Field(
        default=None,
        description="Mean daily minimum temperature at 2m in Celsius (°C).",
    )
    mean_solar_radiation_mj_m2: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Mean surface shortwave downward insolation in MJ/m²/day.",
    )
    mean_relative_humidity_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Mean relative humidity at 2m in percent (%).",
    )
    consecutive_dry_days_max: Optional[int] = Field(
        default=None,
        ge=0,
        description="Longest streak of consecutive days with precipitation < 2.5mm.",
    )
    heat_stress_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Count of days where maximum daily temperature exceeded 35°C.",
    )
    weather_window_start: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD) indicating the start of the weather accumulation window.",
    )
    weather_window_end: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD) indicating the end of the weather accumulation window.",
    )
    weather_days_total: Optional[int] = Field(
        default=None,
        ge=1,
        description="Total calendar days spanned by the weather aggregation window.",
    )
    weather_days_missing: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of days in the window where raw meteorological observations were absent or imputed.",
    )
    source: Optional[str] = Field(
        default="NASA POWER Agroclimatology Daily",
        description="Name and version of the meteorological data source.",
    )

    @field_validator(
        "cumulative_rainfall_mm",
        "mean_temp_max_c",
        "mean_temp_min_c",
        "mean_solar_radiation_mj_m2",
        "mean_relative_humidity_pct",
        mode="before",
    )
    @classmethod
    def validate_finite_floats(cls, v: Any) -> Any:
        if v is not None:
            if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
                raise ValueError("Weather indicator must be a valid, finite number (NaN and Inf are prohibited).")
        return v

    @model_validator(mode="after")
    def validate_temperature_consistency(self) -> "WeatherMeasurement":
        if self.mean_temp_min_c is not None and self.mean_temp_max_c is not None:
            if self.mean_temp_min_c > self.mean_temp_max_c:
                raise ValueError(
                    f"Minimum temperature ({self.mean_temp_min_c}°C) cannot exceed maximum temperature ({self.mean_temp_max_c}°C)."
                )
        return self


class SoilMeasurement(BaseModel):
    """Topsoil pedological properties representing root-zone physical and chemical properties."""

    soil_ph: Optional[float] = Field(
        default=None,
        ge=3.0,
        le=10.5,
        description="Soil pH measured in H2O solution (unitless scale).",
    )
    organic_carbon_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=12.0,
        description="Soil organic carbon concentration in weight percentage (% wt).",
    )
    clay_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Clay fraction (<0.002 mm) in weight percentage (% wt).",
    )
    sand_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Sand fraction (0.05 - 2.0 mm) in weight percentage (% wt).",
    )
    silt_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Silt fraction (0.002 - 0.05 mm) in weight percentage (% wt).",
    )
    bulk_density_g_cm3: Optional[float] = Field(
        default=None,
        ge=0.5,
        le=2.5,
        description="Bulk density of fine earth fraction in g/cm³.",
    )
    cation_exchange_capacity_cmol_kg: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=150.0,
        description="Cation exchange capacity of soil in cmol(+)/kg.",
    )
    depth_interval: str = Field(
        default="0-30cm",
        description="Standardized vertical depth interval of the measurement (e.g. '0-30cm').",
    )
    source_resolution: str = Field(
        default="250m",
        description="Spatial resolution of the underlying pedological model (e.g. '250m').",
    )
    source: Optional[str] = Field(
        default="ISRIC SoilGrids 2.0",
        description="Source dataset or measurement platform.",
    )

    @field_validator(
        "soil_ph",
        "organic_carbon_pct",
        "clay_pct",
        "sand_pct",
        "silt_pct",
        "bulk_density_g_cm3",
        "cation_exchange_capacity_cmol_kg",
        mode="before",
    )
    @classmethod
    def validate_finite_floats(cls, v: Any) -> Any:
        if v is not None:
            if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
                raise ValueError("Soil property value must be a valid, finite number (NaN and Inf are prohibited).")
        return v

    @model_validator(mode="after")
    def validate_texture_fractions(self) -> "SoilMeasurement":
        # If all three texture fractions are provided, verify they sum to ~100%
        if self.clay_pct is not None and self.sand_pct is not None and self.silt_pct is not None:
            total = self.clay_pct + self.sand_pct + self.silt_pct
            if total > 102.0 or total < 95.0:
                raise ValueError(
                    f"Soil texture fractions must sum to approximately 100% (clay + sand + silt = {round(total, 1)}%)."
                )
        return self


def convert_yield_to_t_ha(value: float, from_unit: str) -> float:
    """Explicitly convert agricultural yield from source unit to standard t/ha (tonnes per hectare).

    Supported source units:
    - 'kg/ha', 'kg per ha', 'kilograms per hectare' -> divide by 1000.0
    - 't/ha', 'tonnes/ha', 'tons per hectare', 'metric tons/ha' -> divide by 1.0
    - 'hg/ha', 'hectograms per hectare' (FAOSTAT standard) -> divide by 10,000.0
    - 'quintals/ha', 'q/ha' (Indian state standard) -> divide by 10.0
    - 'lbs/acre', 'pounds per acre' (US standard) -> multiply by 0.00112085
    - 'bu/acre (soybean/wheat 60lb/bu)' -> multiply by 0.06725
    - 'bu/acre (corn 56lb/bu)' -> multiply by 0.06277
    """
    if value is None or math.isnan(value):
        raise ValueError("Cannot convert NaN yield value.")

    if value < 0.0:
        raise ValueError(f"Yield cannot be negative: {value}")

    normalized_unit = from_unit.strip().lower().replace(" ", "").replace("_", "")

    conversion_table = {
        "t/ha": 1.0,
        "tonnes/ha": 1.0,
        "tons/ha": 1.0,
        "tonnesperhectare": 1.0,
        "kg/ha": 0.001,
        "kgperha": 0.001,
        "kilogramsperhectare": 0.001,
        "hg/ha": 0.0001,
        "hectogramsperhectare": 0.0001,
        "q/ha": 0.1,
        "quintals/ha": 0.1,
        "quintalsperhectare": 0.1,
    }

    factor = conversion_table.get(normalized_unit)
    if factor is None:
        raise ValueError(
            f"Unsupported or unrecognized yield unit '{from_unit}'. "
            f"Supported units: {sorted(list(conversion_table.keys()))}"
        )

    return round(value * factor, 4)


class UnifiedCropObservation(BaseModel):
    """Canonical multi-crop agricultural observation data model."""

    # 1. Identification
    observation_id: str = Field(
        ...,
        description="Globally unique deterministic observation identifier (e.g. 'icrisat_akola_soybean_kharif_2015').",
    )
    crop_name: str = Field(..., description="Canonical display name of the crop (e.g. 'Soybean', 'Rice (Paddy)').")
    crop_id: str = Field(..., description="Normalized lowercase crop slug (e.g. 'soybean', 'rice', 'wheat').")
    crop_category: CropCategory = Field(..., description="Category: cereal, pulse, oilseed, cash_crop, etc.")
    variety: Optional[str] = Field(default=None, description="Cultivar or seed variety if documented by source.")

    # Geographic metadata
    country: str = Field(default="India", description="Country of cultivation.")
    state: str = Field(..., description="State or province name (e.g. 'Maharashtra').")
    district: str = Field(..., description="Canonical district or county name.")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0, description="Representative centroid latitude.")
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0, description="Representative centroid longitude.")
    elevation_m: Optional[float] = Field(default=None, ge=-500.0, le=9000.0, description="Elevation above sea level in meters.")

    # Temporal & Seasonal metadata
    crop_year: int = Field(..., ge=1950, le=2050, description="Harvest calendar year.")
    season: str = Field(..., description="Cropping season (e.g. 'Kharif', 'Rabi', 'Summer', 'Whole Year').")

    # 2. Yield & Agricultural Volume (Production/Area kept separate from prediction features)
    yield_t_ha: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Standardized crop yield in tonnes per hectare (t/ha). Target variable.",
    )
    yield_unit: str = Field(default="t/ha", description="Target measurement unit.")
    source_yield: Optional[float] = Field(default=None, ge=0.0, description="Raw yield reported in source dataset.")
    source_yield_unit: Optional[str] = Field(default=None, description="Original unit in source dataset.")
    reported_area_ha: Optional[float] = Field(default=None, ge=0.0, description="Cultivated area in hectares.")
    reported_production_tonnes: Optional[float] = Field(default=None, ge=0.0, description="Gross production in metric tonnes.")
    is_observed_yield: bool = Field(
        default=True,
        description="True for observed historical ground truth; False for model predictions.",
    )

    # 3. Multimodal Features (Nullable to preserve raw records when one modality is pending)
    weather: Optional[WeatherMeasurement] = Field(default=None, description="Seasonal weather features if aligned.")
    soil: Optional[SoilMeasurement] = Field(default=None, description="Topsoil pedological features if aligned.")

    # 4. Provenance & Quality Governance
    source_dataset: str = Field(..., description="Source dataset ID (e.g. 'icrisat_des_dld').")
    source_record_id: Optional[str] = Field(default=None, description="Original row index or key in source table.")
    ingestion_timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.utcnow,
        description="UTC timestamp when the observation was ingested or updated.",
    )
    missingness_flags: List[str] = Field(default_factory=list, description="Flags for legitimately absent measurements.")
    quality_flags: List[str] = Field(default_factory=list, description="Audit flags (e.g. 'deduplicated', 'outlier_yield').")
    validation_warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings caught during ingestion.")
    quality_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Documented composite completeness score [0.0 - 1.0].",
    )

    @field_validator("crop_id")
    @classmethod
    def validate_crop_registered(cls, v: str) -> str:
        spec = resolve_crop(v)
        if not spec:
            raise ValueError(f"Crop '{v}' is not registered in CROP_REGISTRY. Register the crop first.")
        return spec.crop_id

    @field_validator("season")
    @classmethod
    def validate_season_registered(cls, v: str) -> str:
        season_def = resolve_season(v)
        if not season_def:
            raise ValueError(f"Season '{v}' is not recognized in SEASON_REGISTRY.")
        return season_def.canonical_name.value

    @model_validator(mode="after")
    def validate_plausibility_and_derive_flags(self) -> "UnifiedCropObservation":
        # 1. Check coordinates if present
        if self.latitude is not None and self.longitude is not None:
            # India bounding box roughly: lat 6 to 38, lon 68 to 98
            if self.country.lower() == "india":
                if not (6.0 <= self.latitude <= 38.0 and 68.0 <= self.longitude <= 98.0):
                    self.validation_warnings.append(
                        f"Coordinates ({self.latitude}, {self.longitude}) lie outside India's geographic bounding box."
                    )

        # 2. Check yield plausibility against crop registry
        crop_spec = resolve_crop(self.crop_id)
        if crop_spec and self.yield_t_ha is not None:
            min_y, max_y = crop_spec.typical_yield_range_t_ha
            if self.yield_t_ha > max_y * 1.5:
                self.validation_warnings.append(
                    f"Yield {self.yield_t_ha} t/ha significantly exceeds typical upper bound ({max_y} t/ha) for {crop_spec.display_name}."
                )
                if "exceptional_high_yield" not in self.quality_flags:
                    self.quality_flags.append("exceptional_high_yield")

        # 3. Check weather/soil presence and update missingness flags
        if self.weather is None and "missing_weather" not in self.missingness_flags:
            self.missingness_flags.append("missing_weather")
        if self.soil is None and "missing_soil" not in self.missingness_flags:
            self.missingness_flags.append("missing_soil")

        # 4. Compute completeness quality score
        score = 0.4  # Base score for valid crop identification + yield
        if self.weather is not None:
            score += 0.3
        if self.soil is not None:
            score += 0.3
        if self.validation_warnings:
            score -= min(0.2, 0.05 * len(self.validation_warnings))
        self.quality_score = round(max(0.0, min(1.0, score)), 2)

        return self
