from typing import Optional, Dict, List
from pydantic import BaseModel, Field, field_validator


class SoilProperties(BaseModel):
    """Soil physical and chemical characteristics from topsoil (0-30cm)."""

    soil_ph: float = Field(
        ...,
        ge=3.5,
        le=10.0,
        description="Soil pH measured in H2O solution (unitless scale).",
        json_schema_extra={"example": 7.2},
    )
    organic_carbon_pct: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Soil organic carbon concentration in weight percentage (%).",
        json_schema_extra={"example": 0.65},
    )
    clay_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Clay fraction (<0.002 mm) in weight percentage (%).",
        json_schema_extra={"example": 42.0},
    )
    sand_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Sand fraction (0.05 - 2.0 mm) in weight percentage (%).",
        json_schema_extra={"example": 25.0},
    )
    bulk_density_g_cm3: float = Field(
        ...,
        ge=0.8,
        le=2.2,
        description="Bulk density of fine earth fraction in g/cm³.",
        json_schema_extra={"example": 1.35},
    )
    cation_exchange_capacity_cmol_kg: float = Field(
        ...,
        ge=0.0,
        le=120.0,
        description="Cation exchange capacity of soil in cmol(+)/kg.",
        json_schema_extra={"example": 38.5},
    )

    @field_validator("sand_pct")
    @classmethod
    def validate_texture_sum(cls, sand_val: float, info) -> float:
        clay_val = info.data.get("clay_pct")
        if clay_val is not None and (clay_val + sand_val) > 100.0:
            raise ValueError(f"Sum of clay ({clay_val}%) and sand ({sand_val}%) cannot exceed 100%.")
        return sand_val


class SeasonalWeather(BaseModel):
    """Aggregated agroclimatology indicators across the crop growing season."""

    cumulative_rainfall_mm: float = Field(
        ...,
        ge=0.0,
        le=5000.0,
        description="Total cumulative precipitation over the growing season in millimeters (mm).",
        json_schema_extra={"example": 850.5},
    )
    mean_temp_max_c: float = Field(
        ...,
        ge=15.0,
        le=50.0,
        description="Mean daily maximum temperature across the growing season in Celsius (°C).",
        json_schema_extra={"example": 31.8},
    )
    mean_temp_min_c: float = Field(
        ...,
        ge=5.0,
        le=35.0,
        description="Mean daily minimum temperature across the growing season in Celsius (°C).",
        json_schema_extra={"example": 22.4},
    )
    mean_solar_radiation_mj_m2: float = Field(
        ...,
        ge=5.0,
        le=35.0,
        description="Mean daily surface solar radiation in MJ/m²/day.",
        json_schema_extra={"example": 18.6},
    )
    mean_relative_humidity_pct: float = Field(
        ...,
        ge=10.0,
        le=100.0,
        description="Mean relative humidity at 2m in percentage (%).",
        json_schema_extra={"example": 76.2},
    )

    @field_validator("mean_temp_min_c")
    @classmethod
    def validate_temp_range(cls, min_val: float, info) -> float:
        max_val = info.data.get("mean_temp_max_c")
        if max_val is not None and min_val > max_val:
            raise ValueError(f"Minimum temperature ({min_val}°C) cannot exceed maximum temperature ({max_val}°C).")
        return min_val


class PredictionRequest(BaseModel):
    """Input payload for crop yield inference."""

    crop: str = Field(
        ...,
        description="Target agricultural crop (e.g. 'Soybean', 'Rice').",
        json_schema_extra={"example": "Soybean"},
    )
    state: str = Field(
        default="Maharashtra",
        description="Indian State.",
        json_schema_extra={"example": "Maharashtra"},
    )
    district: str = Field(
        ...,
        description="District within the state.",
        json_schema_extra={"example": "Latur"},
    )
    season: str = Field(
        default="Kharif",
        description="Agricultural growing season.",
        json_schema_extra={"example": "Kharif"},
    )
    year: int = Field(
        ...,
        ge=1990,
        le=2035,
        description="Harvest calendar year.",
        json_schema_extra={"example": 2024},
    )

    soil: SoilProperties
    weather: SeasonalWeather


class PredictionResponse(BaseModel):
    """Output prediction response with explainability and model governance metadata."""

    crop: str
    state: str
    district: str
    season: str
    year: int
    predicted_yield_t_ha: float = Field(
        ...,
        description="Estimated crop yield in tonnes per hectare (t/ha).",
    )
    model_name: str
    model_version: str
    prediction_interval: Optional[Dict[str, float]] = Field(
        default=None,
        description="Uncertainty bounds (e.g. 10th and 90th percentiles or prediction interval).",
    )
    feature_contributions: Optional[Dict[str, float]] = Field(
        default=None,
        description="Individual feature contribution values to the prediction.",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Model constraints, spatial resolution limitations, and advisory caveats.",
    )
