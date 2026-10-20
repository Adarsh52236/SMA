import math
from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class SoilProperties(BaseModel):
    """Soil physical and chemical characteristics from topsoil (0-30cm)."""

    soil_ph: float = Field(
        ...,
        ge=3.5,
        le=10.0,
        description="Soil pH measured in H2O solution (unitless scale [3.5, 10.0]).",
        json_schema_extra={"example": 7.4},
    )
    organic_carbon_pct: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Soil organic carbon concentration in weight percentage (% wt).",
        json_schema_extra={"example": 0.65},
    )
    clay_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Clay fraction (<0.002 mm) in weight percentage (% wt).",
        json_schema_extra={"example": 45.0},
    )
    sand_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Sand fraction (0.05 - 2.0 mm) in weight percentage (% wt).",
        json_schema_extra={"example": 20.0},
    )
    silt_pct: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Silt fraction (0.002 - 0.05 mm) in weight percentage (% wt). If omitted, derived as (100 - clay - sand).",
        json_schema_extra={"example": 35.0},
    )
    bulk_density_g_cm3: float = Field(
        ...,
        ge=0.8,
        le=2.2,
        description="Bulk density of fine earth fraction in g/cm³ [0.8, 2.2].",
        json_schema_extra={"example": 1.25},
    )
    cation_exchange_capacity_cmol_kg: float = Field(
        ...,
        ge=0.0,
        le=120.0,
        description="Cation exchange capacity of soil in cmol(+)/kg [0.0, 120.0].",
        json_schema_extra={"example": 38.0},
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
    def validate_finite_number(cls, v: Any) -> Any:
        if v is not None:
            if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
                raise ValueError("Numeric value must be a valid, finite number (NaN and Inf are prohibited).")
        return v

    @field_validator("sand_pct")
    @classmethod
    def validate_texture_sum(cls, sand_val: float, info) -> float:
        clay_val = info.data.get("clay_pct")
        if clay_val is not None and (clay_val + sand_val) > 100.0:
            raise ValueError(f"Sum of clay ({clay_val}%) and sand ({sand_val}%) cannot exceed 100%.")
        return sand_val

    @model_validator(mode="after")
    def validate_complete_texture(self) -> "SoilProperties":
        if self.silt_pct is not None:
            total_texture = self.clay_pct + self.sand_pct + self.silt_pct
            if total_texture > 100.5 or total_texture < 95.0:
                raise ValueError(
                    f"Soil texture fractions must sum to approximately 100% (clay + sand + silt = {round(total_texture, 1)}%)."
                )
        return self


class SeasonalWeather(BaseModel):
    """Aggregated agroclimatology indicators across the Kharif growing season (June 1 - October 31)."""

    cumulative_rainfall_mm: float = Field(
        ...,
        ge=0.0,
        le=5000.0,
        description="Total cumulative precipitation over the Kharif season in millimeters (mm).",
        json_schema_extra={"example": 850.5},
    )
    mean_temp_max_c: float = Field(
        ...,
        ge=15.0,
        le=50.0,
        description="Mean daily maximum temperature across the season in Celsius (°C).",
        json_schema_extra={"example": 31.8},
    )
    mean_temp_min_c: float = Field(
        ...,
        ge=5.0,
        le=35.0,
        description="Mean daily minimum temperature across the season in Celsius (°C).",
        json_schema_extra={"example": 22.4},
    )
    mean_solar_radiation_mj_m2: float = Field(
        ...,
        ge=5.0,
        le=35.0,
        description="Mean daily surface shortwave downward insolation in MJ/m²/day.",
        json_schema_extra={"example": 18.6},
    )
    mean_relative_humidity_pct: float = Field(
        ...,
        ge=10.0,
        le=100.0,
        description="Mean relative humidity at 2m in percentage (%).",
        json_schema_extra={"example": 76.2},
    )
    consecutive_dry_days_max: Optional[int] = Field(
        default=None,
        ge=0,
        le=153,
        description="Longest streak of consecutive days with rainfall < 2.5mm during Kharif (June-Oct: 153 days max).",
        json_schema_extra={"example": 8},
    )
    heat_stress_days: Optional[int] = Field(
        default=None,
        ge=0,
        le=153,
        description="Count of days where maximum daily temperature exceeded 35°C during Kharif.",
        json_schema_extra={"example": 4},
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
    def validate_finite_number(cls, v: Any) -> Any:
        if v is not None:
            if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
                raise ValueError("Weather indicator must be a valid, finite number (NaN and Inf are prohibited).")
        return v

    @field_validator("mean_temp_min_c")
    @classmethod
    def validate_temp_range(cls, min_val: float, info) -> float:
        max_val = info.data.get("mean_temp_max_c")
        if max_val is not None and min_val > max_val:
            raise ValueError(f"Minimum temperature ({min_val}°C) cannot exceed maximum temperature ({max_val}°C).")
        return min_val


class PredictionPolicy(str, Enum):
    """Validation policy governing prediction requests."""

    CONSERVATIVE = "conservative"  # Restricts to verified/training combinations
    EXPLORATORY = "exploratory"    # Permits unseen categories and warns on OOD features


class PredictionRequest(BaseModel):
    """Input payload for crop yield prediction across supported crops in Maharashtra."""

    crop: str = Field(
        default="Soybean",
        description="Target agricultural crop. Supported: Soybean, Rice, Wheat, Cotton, Maize, Chickpea, Groundnut.",
        json_schema_extra={"example": "Soybean"},
    )
    state: str = Field(
        default="Maharashtra",
        description="Indian State.",
        json_schema_extra={"example": "Maharashtra"},
    )
    district: str = Field(
        ...,
        description="District or administrative region.",
        json_schema_extra={"example": "Akola"},
    )
    season: str = Field(
        default="Kharif",
        description="Agricultural growing season (e.g. 'Kharif', 'Rabi', 'Summer').",
        json_schema_extra={"example": "Kharif"},
    )
    year: int = Field(
        ...,
        ge=1990,
        le=2035,
        description="Harvest calendar year.",
        json_schema_extra={"example": 2024},
    )
    model_strategy: Optional[str] = Field(
        default=None,
        description="Optional model routing strategy: 'legacy_soybean', 'shared_multicrop', or 'adaptive'.",
        json_schema_extra={"example": "shared_multicrop"},
    )
    prediction_policy: str = Field(
        default="conservative",
        description="Prediction policy: 'conservative' (strict training coverage) or 'exploratory' (permits novel categories with warnings).",
        json_schema_extra={"example": "conservative"},
    )

    soil: SoilProperties
    weather: SeasonalWeather
    custom_features: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional dynamic feature key-values for novel or newly discovered attributes.",
    )


class PredictionResponse(BaseModel):
    """Prediction output schema with model governance, timing disclosure, and limitations."""

    crop: str
    state: str
    district: str
    season: str
    year: int
    predicted_yield_t_ha: float = Field(
        ...,
        description="Estimated crop yield in tonnes per hectare (t/ha).",
    )
    predicted_yield_kg_ha: float = Field(
        default=0.0,
        description="Estimated crop yield in kilograms per hectare (kg/ha).",
    )
    target_units: str = Field(
        default="tonnes per hectare (t/ha)",
        description="Physical unit of the target prediction.",
    )
    model_name: str
    model_strategy: str = Field(
        default="legacy_soybean",
        description="Active model architecture strategy used for this inference.",
    )
    model_version: str
    prediction_policy: str = Field(
        default="conservative",
        description="Active prediction policy used for request evaluation ('conservative' or 'exploratory').",
    )
    coverage_status: str = Field(
        default="fully_covered",
        description="Coverage classification: 'fully_covered', 'sparse_coverage', 'out_of_distribution_category', or 'out_of_distribution_numeric'.",
    )
    is_out_of_distribution: bool = Field(
        default=False,
        description="True if one or more features exceed the empirical training distribution.",
    )
    out_of_distribution_features: List[str] = Field(
        default_factory=list,
        description="List of feature names that exceeded the training distribution boundaries.",
    )
    qualitative_label: Optional[str] = Field(
        default=None,
        description="Estimated qualitative category (e.g. Low, Moderate, High) derived dynamically from target distribution quantiles.",
    )
    prediction_timing: str = Field(
        default="end_of_season_estimate",
        description="Temporal availability disclosure.",
    )
    timing_description: str = Field(
        default=(
            "End-of-season yield estimate using observed seasonal weather. "
            "This model reflects retrospective or harvest-time meteorological conditions; "
            "it is not an early-season or pre-sowing forecast."
        )
    )
    evaluation_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Summary of benchmark metrics (RMSE, MAE, R²) applicable to this crop and strategy.",
    )
    prediction_interval: Optional[Dict[str, float]] = Field(
        default=None,
        description="Formal prediction interval. Reserved for future conformal/quantile models; not fabricated.",
    )
    feature_contributions: Optional[Dict[str, float]] = Field(
        default=None,
        description="Instance-level local SHAP feature contributions where supported.",
    )
    global_feature_importance: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Global permutation feature importance from validation evaluation.",
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable transparent explanation of how the prediction was computed.",
    )
    uncertainty_note: Optional[str] = Field(
        default="Calibrated statistical prediction intervals are not available for this point estimate; estimate is a statistical expected value.",
        description="Statement regarding uncertainty calibration.",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Model constraints, spatial boundaries, and agricultural caveats.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Traceability identifier for request tracking.",
    )


class ModelMetadataResponse(BaseModel):
    """Governance metadata manifest describing model architecture, training provenance, and performance."""

    model_name: str
    model_version: str
    target: str
    target_units: str
    crop: str
    state: str
    season: str
    prediction_timing: str
    dataset_sha256: str
    training_period: List[int]
    validation_period: List[int]
    test_period: List[int]
    supported_districts: List[str]
    supported_features: List[Dict[str, Any]]
    validation_metrics: Dict[str, Any]
    test_metrics: Dict[str, Any]
    global_feature_importance: List[Dict[str, Any]]
    limitations: List[str]

    # Phase 5 Multi-crop additions (optional for full backward-compatibility)
    supported_crops: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Registry of supported crops with display names, scientific names, categories, and seasons.",
    )
    available_strategies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Available model serving strategies ('legacy_soybean', 'shared_multicrop').",
    )
    multicrop_evaluation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Phase 4 multi-crop temporal and spatial benchmark evaluation results.",
    )


class DynamicCategoriesResponse(BaseModel):
    """Dynamically discovered categorical dimensions and observed combinations."""

    status: str
    dataset_name: Optional[str] = None
    categories: Dict[str, List[str]] = Field(default_factory=dict)
    observed_combinations: List[Dict[str, Any]] = Field(default_factory=list)


class DynamicPresetsResponse(BaseModel):
    """Collection of authentic sample presets generated from data."""

    presets: List[Dict[str, Any]] = Field(default_factory=list)


class RetrainRequest(BaseModel):
    """Configuration payload for initiating adaptive model retraining."""

    dataset_name: Optional[str] = Field(default=None, description="Dataset name to train on.")
    target_col: Optional[str] = Field(default=None, description="Explicit target column override.")
    feature_exclusions: Optional[List[str]] = Field(default=None, description="Columns to omit from feature inputs.")
    model_version: str = Field(default="3.0.0", description="Version string for the new model artifact.")


class RetrainResponse(BaseModel):
    """Output summary of adaptive model selection, validation, and serialization."""

    status: str
    model_version: str
    selected_algorithm: str
    artifact_path: str
    metadata_path: str
    schema_path: str
    metadata: Dict[str, Any]
