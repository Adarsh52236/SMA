"""Unit and Integration Tests for Machine Learning Pipeline (Phase 3).

Verifies:
1. Data audit failure on invalid targets, NaN values, duplicate keys, or unsupported feature values.
2. Leakage-column exclusion enforcement.
3. Chronological split boundary correctness and empty partition detection.
4. District-grouped split isolation (Leave-One-District-Out spatial holdout).
5. Preprocessing fit on training only (no lookahead / leakage into transform).
6. Baseline metric calculation (Mean Yield Baseline).
7. Benchmark model fitting and prediction with valid fixtures.
8. Metric calculation (MAE, RMSE, R²) on held-out observations.
9. Feature importance generation and ranking stability.
10. Artifact serialization, SHA-256 fingerprinting, and artifact reload.
11. Reproducibility of deterministic components.
"""

import os
import json
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from app.ml.config import MLConfig
from app.ml.audit import PreTrainingDataAudit
from app.ml.features import (
    ALL_PREDICTORS,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    PROHIBITED_LEAKAGE_COLUMNS,
    FEATURE_REGISTRY,
    validate_feature_columns,
)
from app.ml.splitting import DataSplitter
from app.ml.preprocessing import build_preprocessor
from app.ml.models import ModelFactory
from app.ml.evaluate import ModelEvaluator
from app.ml.explainability import ModelExplainer
from app.ml.artifacts import ArtifactManager


@pytest.fixture
def synthetic_toy_dataset():
    """Small synthetic dataset strictly for unit testing ML components.
    
    Contains 2 districts over 6 years (1995-2000), total 12 rows.
    """
    rows = []
    districts = ["Ahmednagar", "Akola"]
    years = [1995, 1996, 1997, 1998, 1999, 2000]
    
    np.random.seed(42)
    for i, d in enumerate(districts):
        for j, y in enumerate(years):
            idx = i * len(years) + j
            rows.append({
                "district": d,
                "year": y,
                "yield_t_ha": 0.8 + 0.05 * (y - 1995) + np.random.uniform(0.01, 0.05),
                "reported_area_ha": 50000.0 + idx * 100,
                "reported_production_tonnes": 45000.0 + idx * 90,
                "cumulative_rainfall_mm": 700.0 + (y - 1995) * 20.0 + i * 15.0,
                "mean_temp_max_c": 31.0 + (y - 1995) * 0.2 + i * 0.5,
                "mean_temp_min_c": 22.0 + (y - 1995) * 0.1 + i * 0.3,
                "mean_solar_radiation_mj_m2": 18.0 + (y - 1995) * 0.15,
                "mean_relative_humidity_pct": 75.0 - (y - 1995) * 0.5,
                "consecutive_dry_days_max": 8 + (idx % 3),
                "heat_stress_days": 4 + (idx % 2),
                "clay_pct": 45.0 + i * 2.0,
                "sand_pct": 20.0 - i * 1.0,
                "silt_pct": 35.0 - i * 1.0,
                "bulk_density_g_cm3": 1.25 + i * 0.02,
                "organic_carbon_pct": 0.65 + i * 0.05,
                "soil_ph": 7.4 + i * 0.1,
                "cation_exchange_capacity_cmol_kg": 38.0 + i * 1.5,
            })
    return pd.DataFrame(rows)


# --- 1. Pre-Training Data Audit Tests ---

def test_data_audit_passes_on_valid_data(synthetic_toy_dataset):
    config = MLConfig(TRAIN_START_YEAR=1995, TRAIN_END_YEAR=1998, VAL_START_YEAR=1999, VAL_END_YEAR=1999, TEST_START_YEAR=2000, TEST_END_YEAR=2000)
    auditor = PreTrainingDataAudit(config=config)
    audit = auditor.audit_dataset(synthetic_toy_dataset)
    assert audit["passed"] is True
    assert len(audit["errors"]) == 0
    assert audit["row_count"] == 12
    assert audit["districts"] == ["Ahmednagar", "Akola"]
    assert audit["target_statistics"]["min"] > 0


def test_data_audit_fails_on_negative_or_nan_target(synthetic_toy_dataset):
    auditor = PreTrainingDataAudit()
    
    bad_df = synthetic_toy_dataset.copy()
    bad_df.loc[0, "yield_t_ha"] = -0.5
    audit = auditor.audit_dataset(bad_df)
    assert audit["passed"] is False
    assert any("non-positive" in err for err in audit["errors"])

    bad_df2 = synthetic_toy_dataset.copy()
    bad_df2.loc[1, "yield_t_ha"] = np.nan
    audit2 = auditor.audit_dataset(bad_df2)
    assert audit2["passed"] is False
    assert any("NaN" in err for err in audit2["errors"])


def test_data_audit_fails_on_duplicate_district_year(synthetic_toy_dataset):
    auditor = PreTrainingDataAudit()
    dup_df = pd.concat([synthetic_toy_dataset, synthetic_toy_dataset.iloc[[0]]], ignore_index=True)
    audit = auditor.audit_dataset(dup_df)
    assert audit["passed"] is False
    assert any("duplicate" in err for err in audit["errors"])


def test_data_audit_fails_on_unphysical_soil_values(synthetic_toy_dataset):
    auditor = PreTrainingDataAudit()
    bad_soil_df = synthetic_toy_dataset.copy()
    bad_soil_df.loc[0, "soil_ph"] = 12.5  # Impossible pH
    audit = auditor.audit_dataset(bad_soil_df)
    assert audit["passed"] is False
    assert any("Soil pH" in err for err in audit["errors"])


# --- 2. Leakage Column Exclusion Tests ---

def test_leakage_columns_are_strictly_excluded():
    assert "yield_t_ha" in PROHIBITED_LEAKAGE_COLUMNS
    assert "reported_area_ha" in PROHIBITED_LEAKAGE_COLUMNS
    assert "reported_production_tonnes" in PROHIBITED_LEAKAGE_COLUMNS
    
    for col in PROHIBITED_LEAKAGE_COLUMNS:
        assert col not in ALL_PREDICTORS


def test_validate_feature_columns_catches_leakage():
    with pytest.raises(ValueError, match="TARGET LEAKAGE VIOLATION"):
        validate_feature_columns(["cumulative_rainfall_mm", "yield_t_ha"])
    
    with pytest.raises(ValueError, match="TARGET LEAKAGE VIOLATION"):
        validate_feature_columns(["mean_temp_max_c", "reported_production_tonnes"])

    # Valid feature list should pass without error
    validate_feature_columns(ALL_PREDICTORS)


# --- 3. Chronological Split Tests ---

def test_chronological_split_boundaries(synthetic_toy_dataset):
    config = MLConfig(
        TRAIN_START_YEAR=1995, TRAIN_END_YEAR=1997,
        VAL_START_YEAR=1998, VAL_END_YEAR=1999,
        TEST_START_YEAR=2000, TEST_END_YEAR=2000,
    )
    splitter = DataSplitter(config=config)
    train_df, val_df, test_df, summary = splitter.chronological_split(synthetic_toy_dataset)
    
    assert train_df["year"].max() == 1997
    assert val_df["year"].min() == 1998
    assert val_df["year"].max() == 1999
    assert test_df["year"].min() == 2000
    assert len(train_df) == 6  # 2 districts * 3 years
    assert len(val_df) == 4    # 2 districts * 2 years
    assert len(test_df) == 2   # 2 districts * 1 year


def test_empty_chronological_partition_raises_error(synthetic_toy_dataset):
    config = MLConfig(
        TRAIN_START_YEAR=1995, TRAIN_END_YEAR=1997,
        VAL_START_YEAR=2010, VAL_END_YEAR=2012,  # Years not in dataset
        TEST_START_YEAR=1998, TEST_END_YEAR=2000,
    )
    splitter = DataSplitter(config=config)
    with pytest.raises(ValueError, match="Validation split .* has 0 observations"):
        splitter.chronological_split(synthetic_toy_dataset)


# --- 4. Spatial Holdout Isolation Tests ---

def test_spatial_holdout_district_isolation(synthetic_toy_dataset):
    splitter = DataSplitter()
    splits = list(splitter.spatial_holdout_splits(synthetic_toy_dataset))
    assert len(splits) == 2  # Ahmednagar, Akola
    
    for train_part, test_part, held_out in splits:
        assert held_out not in train_part["district"].values
        assert (test_part["district"] == held_out).all()
        assert len(train_part) + len(test_part) == len(synthetic_toy_dataset)


# --- 5. Preprocessing Leakage Prevention Tests ---

def test_preprocessing_fitted_on_training_only(synthetic_toy_dataset):
    train_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] <= 1997]
    val_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] > 1997]
    
    preprocessor = build_preprocessor(scale_numeric=True)
    
    # Fit strictly on train
    preprocessor.fit(train_df[ALL_PREDICTORS])
    
    # Check that transform works on val_df without raising or refitting
    val_transformed = preprocessor.transform(val_df[ALL_PREDICTORS])
    assert val_transformed.shape[0] == len(val_df)
    assert not np.isnan(val_transformed).any()


# --- 6. Metric Calculations & Baseline ---

def test_metric_calculations():
    y_true = np.array([1.0, 2.0, 3.0])
    y_pred = np.array([1.0, 2.0, 3.0])
    metrics = ModelEvaluator.compute_metrics(y_true, y_pred)
    assert metrics["mae_t_ha"] == 0.0
    assert metrics["rmse_t_ha"] == 0.0
    assert metrics["r2_score"] == 1.0

    y_bad = np.array([2.0, 3.0, 4.0])
    metrics_bad = ModelEvaluator.compute_metrics(y_true, y_bad)
    assert metrics_bad["mae_t_ha"] == 1.0
    assert metrics_bad["rmse_t_ha"] == 1.0


# --- 7. Model Fitting & Prediction on Fixtures ---

def test_candidate_models_fitting_and_evaluation(synthetic_toy_dataset):
    train_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] <= 1997]
    val_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] > 1997]
    
    candidate_models = ModelFactory.get_candidate_models(seed=42)
    evaluator = ModelEvaluator()
    
    best_name, comparison, fitted = evaluator.evaluate_validation_candidates(
        candidate_models=candidate_models,
        X_train=train_df[ALL_PREDICTORS],
        y_train=train_df["yield_t_ha"],
        X_val=val_df[ALL_PREDICTORS],
        y_val=val_df["yield_t_ha"],
    )
    
    assert best_name in candidate_models
    assert "Mean_Yield_Baseline" in comparison
    assert "Ridge_Regression" in comparison
    assert "Random_Forest" in comparison
    assert "Gradient_Boosting" in comparison
    assert comparison[best_name]["validation_metrics"]["rmse_t_ha"] > 0


# --- 8. Feature Importance Generation ---

def test_permutation_importance_generation(synthetic_toy_dataset):
    train_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] <= 1997]
    val_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] > 1997]
    
    candidate_models = ModelFactory.get_candidate_models(seed=42)
    rf_pipe = candidate_models["Random_Forest"]
    rf_pipe.fit(train_df[ALL_PREDICTORS], train_df["yield_t_ha"])
    
    explainer = ModelExplainer()
    importance_df = explainer.compute_permutation_importance(
        pipeline=rf_pipe,
        X_val=val_df[ALL_PREDICTORS],
        y_val=val_df["yield_t_ha"],
        n_repeats=3,
        random_state=42,
    )
    assert not importance_df.empty
    assert "feature" in importance_df.columns
    assert "importance_mean" in importance_df.columns
    assert len(importance_df) == len(ALL_PREDICTORS)


# --- 9. Artifact Serialization and Reloading ---

def test_artifact_serialization_and_reload(synthetic_toy_dataset, tmp_path):
    train_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] <= 1997]
    
    candidate_models = ModelFactory.get_candidate_models(seed=42)
    pipe = candidate_models["Ridge_Regression"]
    pipe.fit(train_df[ALL_PREDICTORS], train_df["yield_t_ha"])
    
    # Custom config pointing to tmp_path
    tmp_config = MLConfig(
        ARTIFACT_DIR=str(tmp_path),
        REPORTS_MODELING_DIR=str(tmp_path / "reports"),
    )
    manager = ArtifactManager(config=tmp_config)
    
    val_metrics = {"rmse_t_ha": 0.45, "mae_t_ha": 0.38, "r2_score": 0.30}
    test_metrics = {"rmse_t_ha": 0.43, "mae_t_ha": 0.35, "r2_score": 0.14}
    split_summary = {"train": {"rows": len(train_df)}}
    
    model_path, meta_path = manager.save_artifact(
        pipeline=pipe,
        model_name="Ridge_Regression",
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        split_summary=split_summary,
        dataset_path="dummy_path.csv",
    )
    
    assert os.path.exists(model_path)
    assert os.path.exists(meta_path)
    
    # Reload artifact
    loaded_pipe, metadata = manager.load_artifact()
    assert isinstance(loaded_pipe, Pipeline)
    assert metadata["model_name"] == "Ridge_Regression"
    assert metadata["feature_schema"]["all_predictors"] == ALL_PREDICTORS
    
    # Validate prediction equality
    test_sample = synthetic_toy_dataset.iloc[[0]][ALL_PREDICTORS]
    orig_pred = pipe.predict(test_sample)
    loaded_pred = loaded_pipe.predict(test_sample)
    np.testing.assert_allclose(orig_pred, loaded_pred)


# --- 10. Reproducibility Test ---

def test_model_reproducibility(synthetic_toy_dataset):
    train_df = synthetic_toy_dataset[synthetic_toy_dataset["year"] <= 1997]
    
    models_1 = ModelFactory.get_candidate_models(seed=42)
    models_2 = ModelFactory.get_candidate_models(seed=42)
    
    rf1 = models_1["Random_Forest"]
    rf2 = models_2["Random_Forest"]
    
    rf1.fit(train_df[ALL_PREDICTORS], train_df["yield_t_ha"])
    rf2.fit(train_df[ALL_PREDICTORS], train_df["yield_t_ha"])
    
    test_sample = synthetic_toy_dataset.iloc[[0]][ALL_PREDICTORS]
    pred1 = rf1.predict(test_sample)
    pred2 = rf2.predict(test_sample)
    
    np.testing.assert_allclose(pred1, pred2)
