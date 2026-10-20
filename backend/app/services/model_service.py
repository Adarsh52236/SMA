"""Model Inference and Lifecycle Management Service.

Loads the trained Random Forest pipeline and metadata once at application startup.
Provides thread-safe, validated inference and governance metadata inspection.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.prediction import PredictionRequest, ModelMetadataResponse
from app.ml.features import FEATURE_REGISTRY

logger = logging.getLogger("CropYieldAPI.ModelService")


class ModelService:
    """Singleton service managing trained model lifecycle and inference requests."""

    _instance: Optional["ModelService"] = None

    def __init__(self):
        self.is_loaded: bool = False
        self.pipeline: Optional[Pipeline] = None
        self.metadata: Optional[Dict[str, Any]] = None
        self.feature_importance: List[Dict[str, Any]] = []
        self.error_message: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ModelService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_model(self) -> bool:
        """Load the model artifact and metadata from disk.
        
        Returns:
            bool: True if loaded successfully, False otherwise.
        """
        model_path = os.path.join(settings.MODEL_DIR, settings.MODEL_FILENAME)
        meta_path = os.path.join(settings.MODEL_DIR, settings.METADATA_FILENAME)

        if not os.path.exists(model_path):
            self.error_message = (
                f"Model artifact not found at configured path. "
                "Per project policy, predictions are only served from genuine trained models."
            )
            logger.warning(self.error_message)
            self.is_loaded = False
            return False

        if not os.path.exists(meta_path):
            self.error_message = f"Model metadata manifest not found. Cannot verify artifact provenance."
            logger.warning(self.error_message)
            self.is_loaded = False
            return False

        try:
            # 1. Load pipeline
            pipeline = joblib.load(model_path)
            if not isinstance(pipeline, Pipeline):
                raise ValueError("Loaded artifact is not a valid scikit-learn Pipeline instance.")

            # 2. Load and validate metadata
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            if "feature_schema" not in metadata or "all_predictors" not in metadata["feature_schema"]:
                raise ValueError("Model metadata manifest is missing expected feature schema.")

            self.pipeline = pipeline
            self.metadata = metadata
            self.is_loaded = True
            self.error_message = None

            # 3. Load permutation feature importance table if available
            pfi_candidates = [
                os.path.join(settings.REPORTS_DIR, "feature_importance.csv"),
                os.path.join(settings.MODEL_DIR, "feature_importance.csv"),
                os.path.join(os.path.dirname(settings.MODEL_DIR), "models", "feature_importance.csv"),
            ]
            pfi_csv = next((p for p in pfi_candidates if os.path.exists(p)), None)
            if pfi_csv:
                try:
                    df_imp = pd.read_csv(pfi_csv)
                    self.feature_importance = [
                        {
                            "feature": str(row["feature"]),
                            "importance_mean_rmse": round(float(row["importance_mean"]), 4),
                            "importance_std_rmse": round(float(row["importance_std"]), 4),
                        }
                        for _, row in df_imp.iterrows()
                    ]
                except Exception as ex:
                    logger.warning(f"Could not parse feature importance CSV: {ex}")
                    self.feature_importance = []

            logger.info(
                f"Model '{metadata.get('model_name')}' successfully loaded into memory. "
                f"Ready to serve inference for {len(settings.SUPPORTED_DISTRICTS)} districts."
            )
            return True

        except Exception as e:
            self.is_loaded = False
            self.pipeline = None
            self.metadata = None
            self.error_message = "Failed to load model artifact due to corruption or incompatible schema."
            logger.error(f"Error during model loading: {e}", exc_info=True)
            return False

    def predict(self, request: PredictionRequest) -> float:
        """Execute model inference with strict validation and error handling."""
        if not self.is_loaded or self.pipeline is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    self.error_message
                    or "Model artifact not found or currently unavailable. Predictions cannot be served."
                ),
            )

        # 1. Geographic and Scope validation
        if request.crop.strip().lower() != settings.TARGET_CROP.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported crop '{request.crop}'. This model is trained strictly for '{settings.TARGET_CROP}'.",
            )

        if request.state.strip().lower() != settings.TARGET_STATE.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported state '{request.state}'. This model is trained strictly for '{settings.TARGET_STATE}'.",
            )

        if request.season.strip().lower() != settings.TARGET_SEASON.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported season '{request.season}'. This model is trained strictly for the '{settings.TARGET_SEASON}' season.",
            )

        # Match district against supported districts case-insensitively
        matched_district = None
        for d in settings.SUPPORTED_DISTRICTS:
            if d.lower() == request.district.strip().lower():
                matched_district = d
                break

        if not matched_district:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"District '{request.district}' is not supported. "
                    f"Supported Maharashtra districts with verified SoilGrids profiles: {settings.SUPPORTED_DISTRICTS}"
                ),
            )

        # 2. Check required seasonal weather features
        if request.weather.consecutive_dry_days_max is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Missing required seasonal weather feature: 'consecutive_dry_days_max'. "
                    "This end-of-season model requires observed dry spell duration across the Kharif season. "
                    "Substituting arbitrary defaults is prohibited."
                ),
            )

        if request.weather.heat_stress_days is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Missing required seasonal weather feature: 'heat_stress_days'. "
                    "This end-of-season model requires observed heat stress days (>35°C) across the Kharif season."
                ),
            )

        # 3. Derive or use silt percentage
        silt_pct = request.soil.silt_pct
        if silt_pct is None:
            silt_pct = max(0.0, round(100.0 - request.soil.clay_pct - request.soil.sand_pct, 2))

        # 4. Construct input row with identical feature schema as trained pipeline
        feature_dict = {
            "cumulative_rainfall_mm": float(request.weather.cumulative_rainfall_mm),
            "mean_temp_max_c": float(request.weather.mean_temp_max_c),
            "mean_temp_min_c": float(request.weather.mean_temp_min_c),
            "mean_solar_radiation_mj_m2": float(request.weather.mean_solar_radiation_mj_m2),
            "mean_relative_humidity_pct": float(request.weather.mean_relative_humidity_pct),
            "consecutive_dry_days_max": int(request.weather.consecutive_dry_days_max),
            "heat_stress_days": int(request.weather.heat_stress_days),
            "soil_ph": float(request.soil.soil_ph),
            "organic_carbon_pct": float(request.soil.organic_carbon_pct),
            "clay_pct": float(request.soil.clay_pct),
            "sand_pct": float(request.soil.sand_pct),
            "silt_pct": float(silt_pct),
            "bulk_density_g_cm3": float(request.soil.bulk_density_g_cm3),
            "cation_exchange_capacity_cmol_kg": float(request.soil.cation_exchange_capacity_cmol_kg),
            "district": str(matched_district),
        }

        input_df = pd.DataFrame([feature_dict])

        # 5. Run inference
        try:
            prediction = self.pipeline.predict(input_df)[0]
            return round(float(prediction), 4)
        except Exception as e:
            logger.error(f"Prediction inference error: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Inference failed due to an internal processing error.",
            )

    def get_metadata(self) -> ModelMetadataResponse:
        """Return public governance and explainability metadata."""
        if not self.is_loaded or self.metadata is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model metadata is unavailable because the model artifact is not loaded.",
            )

        supported_features = []
        for name, meta in FEATURE_REGISTRY.items():
            supported_features.append({
                "name": meta.name,
                "dtype": meta.dtype,
                "units": meta.units,
                "source": meta.source,
                "availability_time": meta.availability_time,
                "description": meta.description,
            })

        limitations = [
            "End-of-season yield estimate using observed weather (June-October); not an early-season or pre-sowing forecast.",
            "Trained and validated on 194 genuine district-year observations across 7 Maharashtra districts (1990-2017).",
            "Generalization to extreme regional climate anomalies (e.g. statewide 2015 drought) may show higher error.",
            "Soil profiles represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages; farm-level soil variability is not captured.",
            "Correlations identified through feature importance do not imply direct agricultural causation.",
        ]

        return ModelMetadataResponse(
            model_name=self.metadata.get("model_name", "Random_Forest"),
            model_version=settings.VERSION,
            target=self.metadata.get("target", "yield_t_ha"),
            target_units=self.metadata.get("target_units", "tonnes per hectare (t/ha)"),
            crop=settings.TARGET_CROP,
            state=settings.TARGET_STATE,
            season=settings.TARGET_SEASON,
            prediction_timing="end_of_season_estimate",
            dataset_sha256=self.metadata.get("dataset_sha256", "N/A"),
            training_period=self.metadata.get("splits", {}).get("train", {}).get("years", [1990, 2010]),
            validation_period=self.metadata.get("splits", {}).get("validation", {}).get("years", [2011, 2014]),
            test_period=self.metadata.get("splits", {}).get("test", {}).get("years", [2015, 2017]),
            supported_districts=settings.SUPPORTED_DISTRICTS,
            supported_features=supported_features,
            validation_metrics=self.metadata.get("performance", {}).get("validation", {}),
            test_metrics=self.metadata.get("performance", {}).get("test", {}),
            global_feature_importance=self.feature_importance,
            limitations=limitations,
        )


model_service = ModelService.get_instance()
