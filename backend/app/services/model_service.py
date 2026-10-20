"""Model Inference and Lifecycle Management Service (Phase 5).

Loads and manages both:
1. The validated legacy soybean Random Forest pipeline (for backward compatibility).
2. The universal multi-crop Random Forest pipeline (evaluated in Phase 4 across 7 crops).

Provides safe model routing, geographic coverage enforcement, crop/season validation,
thread-safe inference, and multi-crop governance metadata inspection.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.prediction import PredictionRequest, ModelMetadataResponse
from app.ml.features import FEATURE_REGISTRY
from app.data.crop_registry import CROP_REGISTRY, resolve_crop

logger = logging.getLogger("CropYieldAPI.ModelService")


class ModelService:
    """Singleton service managing trained model lifecycles and inference routing."""

    _instance: Optional["ModelService"] = None

    def __init__(self):
        self.is_loaded: bool = False
        self.is_multicrop_loaded: bool = False
        self.legacy_pipeline: Optional[Pipeline] = None
        self.legacy_metadata: Optional[Dict[str, Any]] = None
        self.multicrop_pipeline: Optional[Pipeline] = None
        self.multicrop_metadata: Optional[Dict[str, Any]] = None
        self.feature_importance: List[Dict[str, Any]] = []
        self.error_message: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ModelService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def pipeline(self) -> Optional[Pipeline]:
        """Backward-compatible property for existing tests/checks expecting .pipeline."""
        return self.legacy_pipeline

    @pipeline.setter
    def pipeline(self, val: Optional[Pipeline]):
        self.legacy_pipeline = val

    @property
    def metadata(self) -> Optional[Dict[str, Any]]:
        """Backward-compatible property for existing tests/checks expecting .metadata."""
        return self.legacy_metadata

    @metadata.setter
    def metadata(self, val: Optional[Dict[str, Any]]):
        self.legacy_metadata = val

    def load_model(self) -> bool:
        """Load both legacy and multi-crop model artifacts and metadata from disk.

        Returns:
            bool: True if at least the production model is loaded successfully.
        """
        # 1. Load Legacy Soybean Model
        legacy_model_path = os.path.join(settings.MODEL_DIR, settings.MODEL_FILENAME)
        legacy_meta_path = os.path.join(settings.MODEL_DIR, settings.METADATA_FILENAME)

        if not os.path.exists(legacy_model_path) or not os.path.exists(legacy_meta_path):
            self.error_message = "Failed to load model artifact: file not found."
            logger.warning(self.error_message)
            self.is_loaded = False
            return False

        try:
            legacy_pipeline = joblib.load(legacy_model_path)
            if not isinstance(legacy_pipeline, Pipeline):
                raise ValueError("Loaded production artifact is not a valid scikit-learn Pipeline.")

            with open(legacy_meta_path, "r", encoding="utf-8") as f:
                legacy_metadata = json.load(f)

            self.legacy_pipeline = legacy_pipeline
            self.legacy_metadata = legacy_metadata
            self.is_loaded = True
            self.error_message = None

            # Load permutation feature importance for legacy model
            pfi_candidates = [
                os.path.join(settings.REPORTS_DIR, "feature_importance.csv"),
                os.path.join(settings.MODEL_DIR, "feature_importance.csv"),
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

            logger.info("Legacy production soybean model loaded successfully.")

        except Exception as e:
            self.is_loaded = False
            self.legacy_pipeline = None
            self.legacy_metadata = None
            self.error_message = "Failed to load model artifact due to corruption or incompatible schema."
            logger.error(f"Error during legacy model loading: {e}", exc_info=True)
            return False

        # 2. Load Multi-Crop Universal Model Artifact (Phase 4)
        multicrop_model_path = os.path.join(settings.MULTICROP_MODEL_DIR, settings.MULTICROP_MODEL_FILENAME)
        multicrop_meta_path = os.path.join(settings.MULTICROP_MODEL_DIR, settings.MULTICROP_METADATA_FILENAME)

        if os.path.exists(multicrop_model_path) and os.path.exists(multicrop_meta_path):
            try:
                mc_pipeline = joblib.load(multicrop_model_path)
                with open(multicrop_meta_path, "r", encoding="utf-8") as f:
                    mc_metadata = json.load(f)

                self.multicrop_pipeline = mc_pipeline
                self.multicrop_metadata = mc_metadata
                self.is_multicrop_loaded = True
                logger.info(
                    f"Multi-crop universal model loaded successfully. "
                    f"Ready to serve inference for {len(settings.SUPPORTED_CROPS)} crops across {len(settings.SUPPORTED_DISTRICTS)} districts."
                )
            except Exception as e:
                logger.warning(f"Failed to load multi-crop model artifact: {e}")
                self.is_multicrop_loaded = False
                self.multicrop_pipeline = None
                self.multicrop_metadata = None
        else:
            logger.info("Multi-crop model artifact not found; only legacy soybean route will be active.")
            self.is_multicrop_loaded = False

        return self.is_loaded

    def predict(self, request: PredictionRequest) -> Dict[str, Any]:
        """Execute model inference with strict validation, coverage enforcement, and strategy routing.

        Returns:
            Dict containing predicted_yield_t_ha, predicted_yield_kg_ha, model_name,
            model_strategy, evaluation_summary, and limitations.
        """
        if not self.is_loaded or self.legacy_pipeline is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    self.error_message
                    or "Model artifact not found or currently unavailable. Predictions cannot be served."
                ),
            )

        # 1. Crop Identification & Registry Resolution
        raw_crop = request.crop.strip() if request.crop else "Soybean"
        crop_spec = resolve_crop(raw_crop)

        if not crop_spec or crop_spec.crop_id not in settings.SUPPORTED_CROPS:
            supported_crops_str = ", ".join([CROP_REGISTRY[c].display_name for c in settings.SUPPORTED_CROPS])
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unsupported crop '{request.crop}'. "
                    f"Supported crops in Maharashtra multi-crop catalog: {supported_crops_str}."
                ),
            )

        # 2. State & District Geographic Validation
        if request.state.strip().lower() != settings.TARGET_STATE.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported state '{request.state}'. This model is trained strictly for '{settings.TARGET_STATE}'.",
            )

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
                    f"Supported Maharashtra districts with verified SoilGrids profiles: {settings.SUPPORTED_DISTRICTS}. "
                    "Geographic coverage is strictly restricted to districts with empirical multimodal alignment."
                ),
            )

        # 3. Growing Season Validation
        input_season = request.season.strip().title() if request.season else crop_spec.default_season
        if input_season not in crop_spec.supported_seasons:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Unsupported season '{request.season}' for {crop_spec.display_name}. "
                    f"Valid growing season(s) for this crop: {crop_spec.supported_seasons}."
                ),
            )

        # 4. Weather Completeness Validation
        if request.weather.consecutive_dry_days_max is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Missing required seasonal weather feature: 'consecutive_dry_days_max'. "
                    "This model requires observed dry spell duration across the growing season. "
                    "Substituting arbitrary defaults is prohibited."
                ),
            )

        if request.weather.heat_stress_days is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Missing required seasonal weather feature: 'heat_stress_days'. "
                    "This model requires observed heat stress days (>35°C) across the growing season."
                ),
            )

        # Silt derivation
        silt_pct = request.soil.silt_pct
        if silt_pct is None:
            silt_pct = max(0.0, round(100.0 - request.soil.clay_pct - request.soil.sand_pct, 2))

        # 5. Model Strategy Routing
        requested_strategy = request.model_strategy.strip().lower() if request.model_strategy else None

        # Route logic:
        # - If non-soybean crop -> must use shared_multicrop
        # - If soybean and requested_strategy == 'shared_multicrop' -> use shared_multicrop
        # - If soybean and requested_strategy is None or 'legacy_soybean' -> use legacy_soybean (exact parity)
        if crop_spec.crop_id != "soybean":
            if requested_strategy == "legacy_soybean":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Strategy 'legacy_soybean' only supports crop 'Soybean', not '{crop_spec.display_name}'.",
                )
            active_strategy = "shared_multicrop"
        else:
            if requested_strategy == "shared_multicrop":
                active_strategy = "shared_multicrop"
            else:
                active_strategy = "legacy_soybean"

        # 6. Execute Active Strategy Inference
        if active_strategy == "shared_multicrop":
            if not self.is_multicrop_loaded or self.multicrop_pipeline is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="The multi-crop universal model is currently unavailable on the backend.",
                )

            # Build multi-crop feature row matching Phase 4 pipeline contract exactly
            feature_dict = {
                "crop_id": crop_spec.crop_id,
                "district": matched_district,
                "season": input_season,
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
            }
            input_df = pd.DataFrame([feature_dict])

            try:
                raw_pred = self.multicrop_pipeline.predict(input_df)[0]
                pred_val = float(raw_pred)
                if np.isnan(pred_val) or np.isinf(pred_val):
                    raise ValueError("Model produced a non-finite prediction value.")
                pred_t_ha = round(max(0.0, pred_val), 4)
            except Exception as e:
                logger.error(f"Multi-crop inference error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Inference failed due to an internal processing error.",
                )

            model_name = "Universal_Random_Forest_MultiCrop"
            eval_summary = None
            if self.multicrop_metadata and "temporal_evaluation" in self.multicrop_metadata:
                per_crop = self.multicrop_metadata["temporal_evaluation"].get("per_crop", {}).get(crop_spec.crop_id, {})
                eval_summary = per_crop.get("Shared_RandomForest")

            limitations = [
                f"Multi-crop empirical estimate for {crop_spec.display_name} under {input_season} seasonal conditions.",
                "Trained and evaluated on 1,294 genuine historical observations across 7 Maharashtra vertisol districts (1990-2017).",
                "Spatial leave-one-district-out evaluation demonstrated an overall R² of 0.5093 across unseen districts.",
                "Soil profiles represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages; farm-level variance is not modeled.",
            ]

        else:
            # Legacy Production Soybean Route (exact parity)
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

            try:
                raw_pred = self.legacy_pipeline.predict(input_df)[0]
                pred_val = float(raw_pred)
                if np.isnan(pred_val) or np.isinf(pred_val):
                    raise ValueError("Model produced a non-finite prediction value.")
                pred_t_ha = round(max(0.0, pred_val), 4)
            except Exception as e:
                logger.error(f"Legacy prediction error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Inference failed due to an internal processing error.",
                )

            model_name = self.legacy_metadata.get("model_name", "Random_Forest_Soybean_Maharashtra") if self.legacy_metadata else "Random_Forest"
            eval_summary = self.legacy_metadata.get("performance", {}).get("test") if self.legacy_metadata else None
            limitations = [
                "End-of-season yield estimate using observed weather (June-October); not an early-season or pre-sowing forecast.",
                "Trained strictly on 194 genuine district-year observations for Soybean in Maharashtra (1990-2017).",
                "Soil profiles represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages.",
            ]

        pred_kg_ha = round(pred_t_ha * 1000.0, 1)

        return {
            "predicted_yield_t_ha": pred_t_ha,
            "predicted_yield_kg_ha": pred_kg_ha,
            "crop": crop_spec.display_name,
            "district": matched_district,
            "season": input_season,
            "model_name": model_name,
            "model_strategy": active_strategy,
            "evaluation_summary": eval_summary,
            "limitations": limitations,
        }

    def get_metadata(self) -> ModelMetadataResponse:
        """Return public governance, multi-crop catalog, and explainability metadata."""
        if not self.is_loaded or self.legacy_metadata is None:
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

        # Multi-crop catalog information
        supported_crops_info = []
        for crop_id in settings.SUPPORTED_CROPS:
            spec = CROP_REGISTRY[crop_id]
            supported_crops_info.append({
                "crop_id": spec.crop_id,
                "display_name": spec.display_name,
                "scientific_name": spec.scientific_name,
                "category": spec.category.value,
                "default_season": spec.default_season,
                "supported_seasons": spec.supported_seasons,
                "typical_yield_range_t_ha": list(spec.typical_yield_range_t_ha),
                "is_model_ready": True,
            })

        available_strategies = [
            {
                "strategy_id": "legacy_soybean",
                "display_name": "Legacy Soybean Production Model",
                "description": "Baseline Random Forest trained strictly on 194 Maharashtra Kharif soybean observations.",
                "scope": ["soybean"],
            },
            {
                "strategy_id": "shared_multicrop",
                "display_name": "Universal Multi-Crop Random Forest",
                "description": "Universal Random Forest evaluated in Phase 4 across 7 crops (N=1,294) with spatial leave-one-district-out cross-validation.",
                "scope": settings.SUPPORTED_CROPS,
            },
        ]

        multicrop_eval = None
        if self.multicrop_metadata:
            multicrop_eval = {
                "temporal_holdout": self.multicrop_metadata.get("temporal_evaluation"),
                "spatial_holdout": self.multicrop_metadata.get("spatial_evaluation"),
            }

        limitations = [
            "End-of-season yield estimates using observed seasonal meteorological aggregates; not an early-season or pre-sowing forecast.",
            "Trained and evaluated on genuine district-year observations across 7 verified Maharashtra vertisol districts (1990-2017).",
            "Geographic coverage is restricted to 7 districts with verified ISRIC SoilGrids profiles (Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Buldhana).",
            "Far-eastern Maharashtra districts (e.g. Bhandara) with non-vertisol soils exhibit higher spatial holdout error; regional adaptation is recommended.",
            "Soil profiles represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages; farm-level soil variability is not captured.",
            "Correlations identified through feature importance do not imply direct agricultural causation.",
        ]

        return ModelMetadataResponse(
            model_name=self.legacy_metadata.get("model_name", "Random_Forest"),
            model_version=settings.VERSION,
            target=self.legacy_metadata.get("target", "yield_t_ha"),
            target_units=self.legacy_metadata.get("target_units", "tonnes per hectare (t/ha)"),
            crop=settings.TARGET_CROP,
            state=settings.TARGET_STATE,
            season=settings.TARGET_SEASON,
            prediction_timing="end_of_season_estimate",
            dataset_sha256=self.legacy_metadata.get("dataset_sha256", "N/A"),
            training_period=self.legacy_metadata.get("splits", {}).get("train", {}).get("years", [1990, 2010]),
            validation_period=self.legacy_metadata.get("splits", {}).get("validation", {}).get("years", [2011, 2014]),
            test_period=self.legacy_metadata.get("splits", {}).get("test", {}).get("years", [2015, 2017]),
            supported_districts=settings.SUPPORTED_DISTRICTS,
            supported_features=supported_features,
            validation_metrics=self.legacy_metadata.get("performance", {}).get("validation", {}),
            test_metrics=self.legacy_metadata.get("performance", {}).get("test", {}),
            global_feature_importance=self.feature_importance,
            limitations=limitations,
            supported_crops=supported_crops_info,
            available_strategies=available_strategies,
            multicrop_evaluation=multicrop_eval,
        )


model_service = ModelService.get_instance()
