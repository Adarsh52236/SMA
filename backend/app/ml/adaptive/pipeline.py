"""Adaptive ML Pipeline and Auto-Model Selection Engine (Phase 6).

Dynamically inspects discovered dataset schema, constructs leakage-safe preprocessing,
evaluates candidate algorithms against empirical baselines, performs chronological/spatial
cross-validation, and serializes versioned self-describing model artifacts.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.discovery.schemas import DatasetProfile, ColumnRole
from app.ml.adaptive.models import get_candidate_models
from app.ml.adaptive.evaluator import (
    calculate_metrics,
    split_chronological,
    evaluate_spatial_cv,
    compute_permutation_importance,
)

logger = logging.getLogger("CropYieldAPI.AdaptivePipeline")


class AdaptiveMLPipeline:
    """End-to-end model training engine that adapts to any discovered dataset schema."""

    def __init__(
        self,
        random_state: int = 42,
        output_dir: Optional[str] = None,
    ):
        self.random_state = random_state
        self.output_dir = output_dir or "backend/models/adaptive"
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def train_and_evaluate(
        self,
        df: pd.DataFrame,
        profile: DatasetProfile,
        target_col: Optional[str] = None,
        feature_exclusions: Optional[List[str]] = None,
        model_version: str = "3.0.0",
    ) -> Dict[str, Any]:
        """Execute automated model selection, chronological validation, and artifact serialization.

        Args:
            df: Full training dataset.
            profile: Discovered dataset profile from DatasetDiscoveryEngine.
            target_col: Explicit target column name (defaults to profile.selected_target).
            feature_exclusions: Optional column names to exclude from model inputs.
            model_version: Semantic version string for the resulting artifact.

        Returns:
            Dictionary containing evaluation report, winning model metadata, and artifact paths.
        """
        target = target_col or profile.selected_target
        if not target or target not in df.columns:
            raise ValueError(f"Valid target column must be specified. Discovered candidates: {profile.target_candidates}")

        exclusions = set(feature_exclusions or [])
        # Automatically exclude identifiers, leakage, and the target itself
        for col_name, col_prof in profile.columns.items():
            if col_prof.inferred_role in (ColumnRole.TARGET, ColumnRole.LEAKAGE, ColumnRole.IDENTIFIER):
                exclusions.add(col_name)

        # Identify categorical and numerical input features
        categorical_features = []
        numerical_features = []
        time_col = None
        group_col = None

        for col_name, col_prof in profile.columns.items():
            if col_name in exclusions or col_name == target:
                continue

            if col_prof.inferred_role == ColumnRole.DATETIME:
                time_col = col_name
                # Time can also be a numerical feature if appropriate, or used strictly for splitting
                if pd.api.types.is_numeric_dtype(df[col_name]):
                    numerical_features.append(col_name)
            elif col_prof.inferred_role in (ColumnRole.CATEGORICAL, ColumnRole.GEOGRAPHIC):
                categorical_features.append(col_name)
                if "district" in col_name.lower() or "region" in col_name.lower():
                    group_col = col_name
            elif col_prof.inferred_role == ColumnRole.NUMERICAL:
                numerical_features.append(col_name)

        all_feature_cols = categorical_features + numerical_features
        if not all_feature_cols:
            raise ValueError("No valid input features remain after excluding leakage and target columns.")

        logger.info(
            f"Training on target '{target}' using {len(numerical_features)} numerical and "
            f"{len(categorical_features)} categorical features."
        )

        # Drop rows where target is NaN or non-positive (for yield quantities)
        clean_df = df.dropna(subset=[target]).copy()
        clean_df = clean_df[clean_df[target] >= 0.0]

        # 1. Validation Splitting Strategy
        if time_col and time_col in clean_df.columns and clean_df[time_col].nunique() >= 3:
            train_df, val_df, test_df, split_info = split_chronological(clean_df, time_col=time_col)
        else:
            # Fallback to deterministic index-based split
            n = len(clean_df)
            train_df = clean_df.iloc[: int(n * 0.70)].copy()
            val_df = clean_df.iloc[int(n * 0.70) : int(n * 0.85)].copy()
            test_df = clean_df.iloc[int(n * 0.85) :].copy()
            split_info = {
                "type": "sequential_index_split",
                "train_samples": len(train_df),
                "val_samples": len(val_df),
                "test_samples": len(test_df),
            }

        X_train = train_df[all_feature_cols]
        y_train = train_df[target].values.astype(float)
        X_val = val_df[all_feature_cols]
        y_val = val_df[target].values.astype(float)
        X_test = test_df[all_feature_cols]
        y_test = test_df[target].values.astype(float)

        # Compute empirical target distribution quantiles on training data for dynamic labeling
        p33 = float(np.percentile(y_train, 33.33))
        p66 = float(np.percentile(y_train, 66.67))
        target_distribution = {
            "mean": round(float(np.mean(y_train)), 4),
            "std": round(float(np.std(y_train)), 4),
            "min": round(float(np.min(y_train)), 4),
            "max": round(float(np.max(y_train)), 4),
            "tertile_p33": round(p33, 4),
            "tertile_p66": round(p66, 4),
            "label_low_threshold": round(p33, 4),
            "label_high_threshold": round(p66, 4),
        }

        # 2. Build Preprocessor Factory
        def create_preprocessor() -> ColumnTransformer:
            transformers = []
            if categorical_features:
                transformers.append(
                    (
                        "cat",
                        OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                        categorical_features,
                    )
                )
            if numerical_features:
                transformers.append(
                    (
                        "num",
                        Pipeline([
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                        ]),
                        numerical_features,
                    )
                )
            return ColumnTransformer(transformers=transformers, remainder="drop")

        # 3. Model Comparison & Selection on Validation Set
        group_candidate_cols = [c for c in ["crop", "crop_id", "district", "season"] if c in all_feature_cols]
        candidates = get_candidate_models(random_state=self.random_state, group_cols=group_candidate_cols)

        model_evaluations: Dict[str, Any] = {}
        best_model_name = None
        best_val_rmse = float("inf")
        best_candidate_pipeline = None

        for name, regressor in candidates.items():
            preprocessor = create_preprocessor()
            candidate_pipeline = Pipeline([
                ("preprocessor", preprocessor),
                ("regressor", regressor),
            ])

            try:
                candidate_pipeline.fit(X_train, y_train)
                val_preds = candidate_pipeline.predict(X_val)
                val_metrics = calculate_metrics(y_val, val_preds)
                train_preds = candidate_pipeline.predict(X_train)
                train_metrics = calculate_metrics(y_train, train_preds)

                model_evaluations[name] = {
                    "validation_metrics": val_metrics,
                    "training_metrics": train_metrics,
                }

                # Evaluate whether this is the best predictive model (exclude simple baselines from selection winner)
                if not name.endswith("_Baseline") and val_metrics["rmse"] < best_val_rmse:
                    best_val_rmse = val_metrics["rmse"]
                    best_model_name = name
                    best_candidate_pipeline = candidate_pipeline

            except Exception as e:
                logger.warning(f"Candidate model '{name}' fitting failed: {e}")
                model_evaluations[name] = {"error": str(e)}

        if best_candidate_pipeline is None:
            # Fallback to Ridge if tree models failed
            best_model_name = "Ridge_Regression"
            best_candidate_pipeline = Pipeline([
                ("preprocessor", create_preprocessor()),
                ("regressor", candidates["Ridge_Regression"]),
            ])
            best_candidate_pipeline.fit(X_train, y_train)

        # 4. Final Evaluation on Untouched Test Partition
        test_preds = best_candidate_pipeline.predict(X_test)
        test_metrics = calculate_metrics(y_test, test_preds)

        # 5. Compute Feature Permutation Importance
        feature_importance = compute_permutation_importance(
            pipeline=best_candidate_pipeline,
            X_val=X_test,
            y_val=y_test,
            feature_names=all_feature_cols,
            random_state=self.random_state,
        )

        # 6. Spatial Cross-Validation (if group column available)
        spatial_cv_results = None
        if group_col and group_col in clean_df.columns:
            def build_winning_pipeline():
                return Pipeline([
                    ("preprocessor", create_preprocessor()),
                    ("regressor", candidates[best_model_name]),
                ])

            spatial_cv_results = evaluate_spatial_cv(
                pipeline_builder_fn=build_winning_pipeline,
                df=clean_df,
                feature_cols=all_feature_cols,
                target_col=target,
                group_col=group_col,
                n_splits=5,
            )

        # 7. Record Discovered Training Coverage
        training_categories: Dict[str, List[str]] = {}
        for cat_col in categorical_features:
            training_categories[cat_col] = sorted([
                str(v) for v in train_df[cat_col].dropna().unique().tolist()
            ])

        numerical_boundaries: Dict[str, Dict[str, float]] = {}
        for num_col in numerical_features:
            s = train_df[num_col].dropna().astype(float)
            if len(s) > 0:
                numerical_boundaries[num_col] = {
                    "min": round(float(s.min()), 4),
                    "max": round(float(s.max()), 4),
                    "mean": round(float(s.mean()), 4),
                    "std": round(float(s.std()), 4),
                }

        # 8. Persist Versioned Artifacts
        artifact_filename = f"model_v{model_version}.joblib"
        artifact_path = os.path.join(self.output_dir, artifact_filename)
        joblib.dump(best_candidate_pipeline, artifact_path)

        metadata_dict = {
            "model_name": f"Adaptive_{best_model_name}",
            "model_version": model_version,
            "target": target,
            "target_units": profile.columns.get(target, {}).inferred_units or "units",
            "selected_algorithm": best_model_name,
            "dataset_sha256": profile.sha256_hash,
            "training_samples": len(train_df),
            "validation_samples": len(val_df),
            "test_samples": len(test_df),
            "split_info": split_info,
            "all_features": all_feature_cols,
            "categorical_features": categorical_features,
            "numerical_features": numerical_features,
            "training_categories": training_categories,
            "numerical_boundaries": numerical_boundaries,
            "target_distribution": target_distribution,
            "validation_metrics": model_evaluations[best_model_name]["validation_metrics"],
            "test_metrics": test_metrics,
            "baseline_comparisons": model_evaluations,
            "spatial_cv": spatial_cv_results,
            "feature_importance": feature_importance[:15],
            "random_seed": self.random_state,
        }

        meta_path = os.path.join(self.output_dir, f"metadata_v{model_version}.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, indent=2)

        schema_dict = {
            "target": target,
            "target_units": profile.columns.get(target, {}).inferred_units or "units",
            "features": [
                {
                    "name": col,
                    "dtype": profile.columns[col].dtype if col in profile.columns else "string",
                    "role": profile.columns[col].inferred_role.value if col in profile.columns else "numerical",
                    "units": profile.columns[col].inferred_units if col in profile.columns else None,
                    "is_categorical": col in categorical_features,
                    "categories": training_categories.get(col, []),
                    "range": numerical_boundaries.get(col),
                }
                for col in all_feature_cols
            ],
            "target_tertiles": {
                "low_threshold": p33,
                "high_threshold": p66,
            },
        }

        schema_path = os.path.join(self.output_dir, f"schema_v{model_version}.json")
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(schema_dict, f, indent=2)

        return {
            "status": "success",
            "model_version": model_version,
            "selected_algorithm": best_model_name,
            "artifact_path": artifact_path,
            "metadata_path": meta_path,
            "schema_path": schema_path,
            "metadata": metadata_dict,
        }
