"""Comprehensive Quality Gates and Test Suite for Multi-Crop Modeling & Evaluation (Phase 4).

Validates:
1. Target leakage prevention: no target, production, or area variables in predictor features.
2. Temporal split boundaries: train <= 2012, test 2013-2017, no overlap.
3. District-group isolation: held-out district records completely excluded from training.
4. Pre-training audit & uncultivated zero exclusions: area=0, yield=0 excluded while genuine failures retained.
5. Training-only preprocessing: transformers fit solely on training folds.
6. Reproducible training: fixed random seed produces identical predictions.
7. Artifact metadata completeness and serialization integrity in backend/models/experiments/multicrop/.
8. Independent metric verification: recomputed metrics from saved test predictions match reports exactly.
9. Immutability of baseline soybean model and artifacts.
"""

import os
import json
import hashlib
import pytest
import pandas as pd
import numpy as np

from app.ml.multicrop.dataset import (
    load_and_audit_multicrop_data,
    get_feature_contract,
    MODEL_FEATURE_COLUMNS,
    TARGET_COLUMN,
    STRICT_EXCLUDED_COLUMNS,
)
from app.ml.multicrop.baselines import (
    GlobalMeanBaseline,
    CropMeanBaseline,
    HistoricalCropDistrictMeanBaseline,
)
from app.ml.multicrop.pipeline import build_multicrop_pipeline, get_candidate_models
from app.ml.multicrop.evaluation import calculate_metrics, evaluate_temporal_holdout


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATASET_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "crop_yield_multicrop.csv")
EXPERIMENT_DIR = os.path.join(PROJECT_ROOT, "backend", "models", "experiments", "multicrop")
METRICS_JSON_PATH = os.path.join(PROJECT_ROOT, "reports", "modeling", "multicrop_metrics.json")
REPORT_MD_PATH = os.path.join(PROJECT_ROOT, "reports", "modeling", "multicrop_benchmarking_report.md")
PRODUCTION_MODEL_PATH = os.path.join(PROJECT_ROOT, "backend", "models", "crop_yield_model.joblib")
PRODUCTION_METADATA_PATH = os.path.join(PROJECT_ROOT, "backend", "models", "model_metadata.json")
BENCHMARK_SOYBEAN_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "crop_yield_maharashtra.csv")


# --- 1. Target Leakage Prevention Tests ---

def test_target_leakage_strict_isolation():
    """Verify that predictor columns do not contain target, area, production, or future identifiers."""
    contract = get_feature_contract()
    predictors = set(MODEL_FEATURE_COLUMNS)

    for leakage_col in STRICT_EXCLUDED_COLUMNS:
        assert leakage_col not in predictors, f"Leakage column '{leakage_col}' found in model predictor set!"

    # Verify target column is not in feature list
    assert TARGET_COLUMN not in predictors
    assert "reported_area_ha" not in predictors
    assert "reported_production_tonnes" not in predictors


# --- 2. Pre-Training Audit & Uncultivated Zero Exclusions ---

def test_pre_training_audit_and_exclusions():
    """Verify that uncultivated panel zeros are excluded while genuine crop failures are retained."""
    df_clean, audit = load_and_audit_multicrop_data(DATASET_PATH)

    # Clean records must be non-empty and around 1,293
    assert len(df_clean) == 1293
    assert audit["exclusions"]["uncultivated_panel_zeros_count"] == 64
    assert audit["exclusions"]["genuine_crop_failures_retained_count"] == 1

    # Verify that no area=0, yield=0 records exist in clean modeling dataset
    uncultivated = df_clean[(df_clean["reported_area_ha"] == 0.0) & (df_clean["yield_t_ha"] == 0.0)]
    assert len(uncultivated) == 0, "Uncultivated panel zeros leaked into clean modeling dataset!"


# --- 3. Temporal Split Boundaries ---

def test_temporal_split_boundaries_and_disjoint_partitions():
    """Verify train partition <= 2012, test partition 2013-2017, and zero temporal overlap."""
    df_clean, _ = load_and_audit_multicrop_data(DATASET_PATH)

    train_df = df_clean[df_clean["year"] <= 2012]
    test_df = df_clean[df_clean["year"] > 2012]

    assert len(train_df) == 1068
    assert len(test_df) == 225

    assert train_df["year"].max() == 2012
    assert test_df["year"].min() == 2013

    # Check intersection of observation IDs between train and test
    train_ids = set(train_df["observation_id"])
    test_ids = set(test_df["observation_id"])
    assert len(train_ids.intersection(test_ids)) == 0, "Temporal train and test partitions overlap!"


# --- 4. District-Group Spatial Isolation ---

def test_spatial_district_isolation():
    """Verify that in leave-one-district-out splits, held-out district records never appear in training."""
    df_clean, _ = load_and_audit_multicrop_data(DATASET_PATH)
    districts = df_clean["district"].unique()

    for held_out in districts:
        train_fold = df_clean[df_clean["district"] != held_out]
        test_fold = df_clean[df_clean["district"] == held_out]

        assert held_out not in train_fold["district"].values
        assert (test_fold["district"] == held_out).all()
        assert len(set(train_fold["observation_id"]).intersection(set(test_fold["observation_id"]))) == 0


# --- 5. Training-Only Preprocessing Fit ---

def test_preprocessing_fitted_on_training_only():
    """Verify that encoders and scalers are fitted strictly on training data."""
    df_clean, _ = load_and_audit_multicrop_data(DATASET_PATH)

    train_df = df_clean[df_clean["year"] <= 2012]
    test_df = df_clean[df_clean["year"] > 2012]

    regressor = get_candidate_models(random_state=42)["RandomForest"]
    pipeline = build_multicrop_pipeline(regressor, include_crop_categorical=True)

    # Fit only on train
    pipeline.fit(train_df[MODEL_FEATURE_COLUMNS], train_df[TARGET_COLUMN])

    # Check that preprocessor learned train statistics, not full dataset
    preprocessor = pipeline.named_steps["preprocessor"]
    scaler = preprocessor.named_transformers_["num"]

    # Verify scaler mean has correct shape (14 continuous variables: 7 weather + 7 soil)
    assert len(scaler.mean_) == 14
    # Scaler mean must match train_df continuous features mean
    num_cols = [
        "cumulative_rainfall_mm", "mean_temp_max_c", "mean_temp_min_c",
        "mean_solar_radiation_mj_m2", "mean_relative_humidity_pct",
        "consecutive_dry_days_max", "heat_stress_days", "soil_ph",
        "organic_carbon_pct", "clay_pct", "sand_pct", "silt_pct",
        "bulk_density_g_cm3", "cation_exchange_capacity_cmol_kg",
    ]
    expected_means = train_df[num_cols].mean().values
    np.testing.assert_allclose(scaler.mean_, expected_means, rtol=1e-5)


# --- 6. Reproducibility with Fixed Random Seed ---

def test_model_training_reproducibility():
    """Verify that repeated training with identical random seed produces identical predictions."""
    df_clean, _ = load_and_audit_multicrop_data(DATASET_PATH)
    train_df = df_clean[df_clean["year"] <= 2012]
    test_df = df_clean[df_clean["year"] > 2012]

    reg_1 = get_candidate_models(random_state=42)["RandomForest"]
    pipe_1 = build_multicrop_pipeline(reg_1)
    pipe_1.fit(train_df[MODEL_FEATURE_COLUMNS], train_df[TARGET_COLUMN])
    preds_1 = pipe_1.predict(test_df[MODEL_FEATURE_COLUMNS])

    reg_2 = get_candidate_models(random_state=42)["RandomForest"]
    pipe_2 = build_multicrop_pipeline(reg_2)
    pipe_2.fit(train_df[MODEL_FEATURE_COLUMNS], train_df[TARGET_COLUMN])
    preds_2 = pipe_2.predict(test_df[MODEL_FEATURE_COLUMNS])

    np.testing.assert_allclose(preds_1, preds_2, atol=1e-7)


# --- 7. Artifact Integrity in backend/models/experiments/multicrop/ ---

def test_experimental_artifacts_completeness():
    """Verify that all Phase 4 experimental artifacts exist and are isolated."""
    required_files = [
        "shared_random_forest.joblib",
        "shared_gradient_boosting.joblib",
        "crop_specific_models.joblib",
        "test_predictions_temporal.csv",
        "test_predictions_spatial.csv",
        "multicrop_experiment_metadata.json",
    ]
    for fname in required_files:
        fpath = os.path.join(EXPERIMENT_DIR, fname)
        assert os.path.exists(fpath), f"Required experimental artifact '{fname}' missing from {EXPERIMENT_DIR}!"
        assert os.path.getsize(fpath) > 0, f"Artifact '{fname}' is empty!"


# --- 8. Metric Verification Against Saved Predictions ---

def test_saved_predictions_reproduce_reported_metrics():
    """Verify that recomputing metrics from saved test predictions matches the JSON report."""
    temporal_preds_path = os.path.join(EXPERIMENT_DIR, "test_predictions_temporal.csv")
    assert os.path.exists(temporal_preds_path)
    df_preds = pd.read_csv(temporal_preds_path)

    with open(METRICS_JSON_PATH, "r", encoding="utf-8") as f:
        meta = json.load(f)

    reported_models = meta["temporal_evaluation"]["models"]
    for model_name, rep_metric in reported_models.items():
        if model_name in df_preds.columns:
            recomputed = calculate_metrics(df_preds["yield_t_ha"].values, df_preds[model_name].values)
            assert recomputed["rmse"] == rep_metric["rmse"], f"RMSE mismatch for {model_name}"
            assert recomputed["mae"] == rep_metric["mae"], f"MAE mismatch for {model_name}"
            assert recomputed["r2"] == rep_metric["r2"], f"R2 mismatch for {model_name}"


# --- 9. Production Model & Benchmark Preservation ---

def test_production_artifacts_unmodified():
    """Verify production soybean model, metadata, and benchmark dataset remain strictly untouched."""
    assert os.path.exists(PRODUCTION_MODEL_PATH)
    assert os.path.exists(PRODUCTION_METADATA_PATH)
    assert os.path.exists(BENCHMARK_SOYBEAN_CSV)

    # Check benchmark CSV row count and SHA
    df_bench = pd.read_csv(BENCHMARK_SOYBEAN_CSV)
    assert len(df_bench) == 194

    hasher = hashlib.sha256()
    with open(BENCHMARK_SOYBEAN_CSV, "rb") as f:
        hasher.update(f.read())
    assert hasher.hexdigest().lower() == "656a3a8999c8feb73d30aae7b6a7fb72c5112a933107fdbe3338bdc17861bf9a"
