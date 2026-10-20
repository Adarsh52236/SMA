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

        # 1. Prediction Policy & Category Resolution
        policy = (request.prediction_policy or "conservative").strip().lower()
        is_exploratory = policy == "exploratory"

        raw_crop = request.crop.strip() if request.crop else "Soybean"
        crop_spec = resolve_crop(raw_crop)

        is_novel_crop = False
        if not crop_spec or crop_spec.crop_id not in settings.SUPPORTED_CROPS:
            if not is_exploratory:
                supported_crops_str = ", ".join([CROP_REGISTRY[c].display_name for c in settings.SUPPORTED_CROPS])
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Unsupported crop '{request.crop}'. "
                        f"Supported crops in Maharashtra multi-crop catalog: {supported_crops_str}. "
                        "To evaluate novel or unverified crops with higher variance, use prediction_policy='exploratory'."
                    ),
                )
            is_novel_crop = True
            crop_id = raw_crop.lower().replace(" ", "_")
            crop_display_name = raw_crop
            crop_default_season = "Kharif"
        else:
            crop_id = crop_spec.crop_id
            crop_display_name = crop_spec.display_name
            crop_default_season = crop_spec.default_season

        # 2. State & District Geographic Validation
        if not is_exploratory and request.state.strip().lower() != settings.TARGET_STATE.lower():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported state '{request.state}'. This model is trained strictly for '{settings.TARGET_STATE}'.",
            )

        matched_district = None
        for d in settings.SUPPORTED_DISTRICTS:
            if d.lower() == request.district.strip().lower():
                matched_district = d
                break

        is_novel_district = False
        if not matched_district:
            if not is_exploratory:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"District '{request.district}' is not supported. "
                        f"Supported Maharashtra districts with verified SoilGrids profiles: {settings.SUPPORTED_DISTRICTS}. "
                        "To evaluate unverified districts, use prediction_policy='exploratory'."
                    ),
                )
            is_novel_district = True
            matched_district = request.district.strip()

        # 3. Growing Season Validation
        input_season = request.season.strip().title() if request.season else crop_default_season
        is_novel_season = False
        if crop_spec and input_season not in crop_spec.supported_seasons:
            if not is_exploratory:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Unsupported season '{request.season}' for {crop_spec.display_name}. "
                        f"Valid growing season(s) for this crop: {crop_spec.supported_seasons}. "
                        "To evaluate non-standard seasons, use prediction_policy='exploratory'."
                    ),
                )
            is_novel_season = True

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

        # 5. Out-of-Distribution (OOD) Analysis for Numerics
        training_bounds = {
            "cumulative_rainfall_mm": (20.0, 2500.0, 750.0, 350.0),
            "mean_temp_max_c": (18.0, 45.0, 31.0, 3.5),
            "mean_temp_min_c": (8.0, 28.0, 21.0, 3.0),
            "mean_solar_radiation_mj_m2": (8.0, 28.0, 18.5, 3.0),
            "mean_relative_humidity_pct": (25.0, 95.0, 72.0, 12.0),
            "consecutive_dry_days_max": (0, 90, 14.0, 10.0),
            "heat_stress_days": (0, 60, 5.0, 6.0),
            "soil_ph": (5.5, 8.8, 7.5, 0.6),
            "organic_carbon_pct": (0.2, 2.5, 0.62, 0.25),
            "clay_pct": (15.0, 65.0, 44.0, 8.0),
            "sand_pct": (5.0, 55.0, 21.0, 7.0),
            "silt_pct": (10.0, 50.0, 35.0, 6.0),
            "bulk_density_g_cm3": (1.0, 1.6, 1.28, 0.08),
            "cation_exchange_capacity_cmol_kg": (15.0, 65.0, 38.0, 8.0),
        }

        feature_values = {
            "cumulative_rainfall_mm": float(request.weather.cumulative_rainfall_mm),
            "mean_temp_max_c": float(request.weather.mean_temp_max_c),
            "mean_temp_min_c": float(request.weather.mean_temp_min_c),
            "mean_solar_radiation_mj_m2": float(request.weather.mean_solar_radiation_mj_m2),
            "mean_relative_humidity_pct": float(request.weather.mean_relative_humidity_pct),
            "consecutive_dry_days_max": float(request.weather.consecutive_dry_days_max),
            "heat_stress_days": float(request.weather.heat_stress_days),
            "soil_ph": float(request.soil.soil_ph),
            "organic_carbon_pct": float(request.soil.organic_carbon_pct),
            "clay_pct": float(request.soil.clay_pct),
            "sand_pct": float(request.soil.sand_pct),
            "silt_pct": float(silt_pct),
            "bulk_density_g_cm3": float(request.soil.bulk_density_g_cm3),
            "cation_exchange_capacity_cmol_kg": float(request.soil.cation_exchange_capacity_cmol_kg),
        }

        ood_features = []
        for feat_name, (b_min, b_max, b_mean, b_std) in training_bounds.items():
            val = feature_values.get(feat_name)
            if val is not None:
                if val < b_min or val > b_max or abs(val - b_mean) > 3.5 * b_std:
                    ood_features.append(feat_name)

        is_ood = len(ood_features) > 0 or is_novel_crop or is_novel_district or is_novel_season

        # Coverage status determination
        if is_novel_crop or is_novel_district or is_novel_season:
            coverage_status = "out_of_distribution_category"
        elif len(ood_features) > 0:
            coverage_status = "out_of_distribution_numeric"
        else:
            coverage_status = "fully_covered"

        # 6. Model Strategy Routing
        requested_strategy = request.model_strategy.strip().lower() if request.model_strategy else None

        if crop_id != "soybean" or is_novel_crop or is_novel_district:
            if requested_strategy == "legacy_soybean":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Strategy 'legacy_soybean' only supports crop 'Soybean', not '{crop_display_name}'.",
                )
            active_strategy = "shared_multicrop"
        else:
            if requested_strategy == "shared_multicrop":
                active_strategy = "shared_multicrop"
            else:
                active_strategy = "legacy_soybean"

        # 7. Execute Active Strategy Inference
        if active_strategy == "shared_multicrop":
            if not self.is_multicrop_loaded or self.multicrop_pipeline is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="The multi-crop universal model is currently unavailable on the backend.",
                )

            # Build multi-crop feature row matching Phase 4 pipeline contract exactly
            feature_dict = {
                "crop_id": crop_id,
                "district": matched_district,
                "season": input_season,
                "cumulative_rainfall_mm": feature_values["cumulative_rainfall_mm"],
                "mean_temp_max_c": feature_values["mean_temp_max_c"],
                "mean_temp_min_c": feature_values["mean_temp_min_c"],
                "mean_solar_radiation_mj_m2": feature_values["mean_solar_radiation_mj_m2"],
                "mean_relative_humidity_pct": feature_values["mean_relative_humidity_pct"],
                "consecutive_dry_days_max": int(feature_values["consecutive_dry_days_max"]),
                "heat_stress_days": int(feature_values["heat_stress_days"]),
                "soil_ph": feature_values["soil_ph"],
                "organic_carbon_pct": feature_values["organic_carbon_pct"],
                "clay_pct": feature_values["clay_pct"],
                "sand_pct": feature_values["sand_pct"],
                "silt_pct": feature_values["silt_pct"],
                "bulk_density_g_cm3": feature_values["bulk_density_g_cm3"],
                "cation_exchange_capacity_cmol_kg": feature_values["cation_exchange_capacity_cmol_kg"],
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
                per_crop = self.multicrop_metadata["temporal_evaluation"].get("per_crop", {}).get(crop_id, {})
                eval_summary = per_crop.get("Shared_RandomForest")

            limitations = [
                f"Multi-crop empirical estimate for {crop_display_name} under {input_season} seasonal conditions.",
                "Trained and evaluated on genuine historical observations across Maharashtra vertisol districts (1990-2017).",
                "Spatial leave-one-district-out evaluation demonstrated an overall R² of 0.5093 across unseen districts.",
                "Soil profiles represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages; farm-level variance is not modeled.",
            ]

        else:
            # Legacy Production Soybean Route (exact parity)
            feature_dict = {
                "cumulative_rainfall_mm": feature_values["cumulative_rainfall_mm"],
                "mean_temp_max_c": feature_values["mean_temp_max_c"],
                "mean_temp_min_c": feature_values["mean_temp_min_c"],
                "mean_solar_radiation_mj_m2": feature_values["mean_solar_radiation_mj_m2"],
                "mean_relative_humidity_pct": feature_values["mean_relative_humidity_pct"],
                "consecutive_dry_days_max": int(feature_values["consecutive_dry_days_max"]),
                "heat_stress_days": int(feature_values["heat_stress_days"]),
                "soil_ph": feature_values["soil_ph"],
                "organic_carbon_pct": feature_values["organic_carbon_pct"],
                "clay_pct": feature_values["clay_pct"],
                "sand_pct": feature_values["sand_pct"],
                "silt_pct": feature_values["silt_pct"],
                "bulk_density_g_cm3": feature_values["bulk_density_g_cm3"],
                "cation_exchange_capacity_cmol_kg": feature_values["cation_exchange_capacity_cmol_kg"],
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

        # 8. Dynamic Qualitative Categorization from Empirical Distribution Tertiles
        # Thresholds: Tertiles computed from empirical training set (p33 ≈ 0.85 t/ha, p66 ≈ 1.45 t/ha)
        tertile_low = 0.85
        tertile_high = 1.45
        if pred_t_ha < tertile_low:
            qualitative_label = f"Low Yield (< {tertile_low} t/ha, Bottom 33% Empirical Tertile)"
        elif pred_t_ha <= tertile_high:
            qualitative_label = f"Moderate Yield ({tertile_low} – {tertile_high} t/ha, Middle 33% Empirical Tertile)"
        else:
            qualitative_label = f"High Yield (> {tertile_high} t/ha, Top 33% Empirical Tertile)"

        # 9. Dynamic Transparent Explanation
        explanation_parts = [
            f"Estimated harvest yield of {pred_t_ha:.2f} t/ha ({round(pred_t_ha * 1000):,} kg/ha) for {crop_display_name} in {matched_district} ({input_season}).",
            f"Dispatched via {active_strategy.replace('_', ' ')} pipeline under {policy} policy.",
            f"Coverage status: {coverage_status}.",
            f"Empirical classification: {qualitative_label}.",
        ]
        if is_ood:
            explanation_parts.append(
                f"Notice: Inputs for {', '.join(ood_features) if ood_features else 'category'} exceed the historical training distribution; uncertainty is elevated."
            )

        if is_exploratory and (is_novel_crop or is_novel_district or is_novel_season):
            limitations.append(
                f"Exploratory mode active: Category was not observed in training data. Inference executed via unencoded feature routing; proceed with caution."
            )

        pred_kg_ha = round(pred_t_ha * 1000.0, 1)

        return {
            "predicted_yield_t_ha": pred_t_ha,
            "predicted_yield_kg_ha": pred_kg_ha,
            "crop": crop_display_name,
            "district": matched_district,
            "season": input_season,
            "model_name": model_name,
            "model_strategy": active_strategy,
            "prediction_policy": policy,
            "coverage_status": coverage_status,
            "is_out_of_distribution": is_ood,
            "out_of_distribution_features": ood_features,
            "qualitative_label": qualitative_label,
            "explanation": " ".join(explanation_parts),
            "uncertainty_note": "Calibrated prediction intervals are unavailable for this point estimate; estimate is a statistical expected value.",
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
