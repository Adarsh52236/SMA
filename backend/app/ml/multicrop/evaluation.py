"""Temporal and Spatial Holdout Evaluation Engine for Multi-Crop Modeling (Phase 4).

Executes:
1. Chronological Holdout (Train 1990–2012, Test 2013–2017).
2. Spatial Holdout (Leave-One-District-Out across 7 districts).
3. Metric calculations: RMSE, MAE, R², Bias, per-crop breakdown, and residual records.
"""

from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import root_mean_squared_error, mean_absolute_error, r2_score

from .dataset import MODEL_FEATURE_COLUMNS, TARGET_COLUMN
from .baselines import (
    GlobalMeanBaseline,
    CropMeanBaseline,
    HistoricalCropDistrictMeanBaseline,
)
from .pipeline import build_multicrop_pipeline, get_candidate_models


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute standard regression metrics, handling negative R2 cleanly."""
    if len(y_true) == 0:
        return {"rmse": 0.0, "mae": 0.0, "r2": 0.0, "bias": 0.0, "count": 0}

    # Ensure 1D float arrays
    yt = np.asarray(y_true, dtype=float).ravel()
    yp = np.asarray(y_pred, dtype=float).ravel()

    rmse = float(root_mean_squared_error(yt, yp))
    mae = float(mean_absolute_error(yt, yp))

    # Variance check for R2
    ss_tot = float(np.sum((yt - np.mean(yt)) ** 2))
    if ss_tot == 0.0:
        r2 = 0.0
    else:
        ss_res = float(np.sum((yt - yp) ** 2))
        r2 = float(1.0 - (ss_res / ss_tot))

    bias = float(np.mean(yp - yt))

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "r2": round(r2, 4),
        "bias": round(bias, 4),
        "count": int(len(yt)),
    }


def evaluate_temporal_holdout(
    df: pd.DataFrame,
    split_year: int = 2012,
    random_state: int = 42,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Evaluate baselines, shared models, and crop-specific models on a chronological split.

    Args:
        df: Cleaned modeling dataset.
        split_year: Last year of training partition (default 2012 -> Test is 2013–2017).
        random_state: Random seed for model training.

    Returns:
        Tuple of (metrics_dictionary, test_predictions_dataframe).
    """
    train_mask = df["year"] <= split_year
    test_mask = df["year"] > split_year

    train_df = df[train_mask].copy().reset_index(drop=True)
    test_df = df[test_mask].copy().reset_index(drop=True)

    X_train = train_df[MODEL_FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]

    X_test = test_df[MODEL_FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    # Initialize prediction tracking DataFrame
    pred_df = test_df[[
        "observation_id", "crop_id", "district", "season", "year", TARGET_COLUMN
    ]].copy()

    results: Dict[str, Any] = {
        "split": {
            "type": "chronological",
            "train_years": [int(train_df["year"].min()), int(train_df["year"].max())],
            "test_years": [int(test_df["year"].min()), int(test_df["year"].max())],
            "train_count": len(train_df),
            "test_count": len(test_df),
            "train_districts": sorted(train_df["district"].unique().tolist()),
            "test_districts": sorted(test_df["district"].unique().tolist()),
        },
        "models": {},
        "per_crop": {},
    }

    # 1. Evaluate Statistical Baselines
    base_global = GlobalMeanBaseline().fit(X_train, y_train)
    preds_global = base_global.predict(X_test)
    pred_df["Baseline_GlobalMean"] = preds_global
    results["models"]["Baseline_GlobalMean"] = calculate_metrics(y_test.values, preds_global)

    base_crop = CropMeanBaseline().fit(X_train, y_train)
    preds_crop = base_crop.predict(X_test)
    pred_df["Baseline_CropMean"] = preds_crop
    results["models"]["Baseline_CropMean"] = calculate_metrics(y_test.values, preds_crop)

    base_hist = HistoricalCropDistrictMeanBaseline().fit(X_train, y_train, years=train_df["year"])
    preds_hist = base_hist.predict(X_test, years=test_df["year"])
    pred_df["Baseline_HistoricalMean"] = preds_hist
    results["models"]["Baseline_HistoricalMean"] = calculate_metrics(y_test.values, preds_hist)

    # 2. Evaluate Shared Multi-Crop ML Candidates
    candidates = get_candidate_models(random_state=random_state)
    shared_pipelines = {}

    for model_name, regressor in candidates.items():
        pipe = build_multicrop_pipeline(regressor, include_crop_categorical=True)
        pipe.fit(X_train, y_train)
        shared_pipelines[model_name] = pipe

        preds = pipe.predict(X_test)
        col_name = f"Shared_{model_name}"
        pred_df[col_name] = preds
        results["models"][col_name] = calculate_metrics(y_test.values, preds)

    # 3. Evaluate Crop-Specific Models (Dedicated models per crop)
    crop_list = sorted(df["crop_id"].unique().tolist())
    crop_specific_preds = np.zeros(len(test_df), dtype=float)

    # We evaluate Random Forest as the primary crop-specific model architecture
    crop_models = {}
    for crop in crop_list:
        c_train = train_df[train_df["crop_id"] == crop]
        c_test = test_df[test_df["crop_id"] == crop]

        if len(c_train) < 30 or len(c_test) == 0:
            continue

        c_regressor = get_candidate_models(random_state=random_state)["RandomForest"]
        c_pipe = build_multicrop_pipeline(c_regressor, include_crop_categorical=False)
        c_pipe.fit(c_train[MODEL_FEATURE_COLUMNS], c_train[TARGET_COLUMN])
        crop_models[crop] = c_pipe

        c_test_preds = c_pipe.predict(c_test[MODEL_FEATURE_COLUMNS])
        test_indices = test_df[test_df["crop_id"] == crop].index
        crop_specific_preds[test_indices] = c_test_preds

    pred_df["CropSpecific_RandomForest"] = crop_specific_preds
    results["models"]["CropSpecific_RandomForest"] = calculate_metrics(y_test.values, crop_specific_preds)

    # 4. Compute Per-Crop Breakdown on Chronological Test Set
    for crop in crop_list:
        c_mask = test_df["crop_id"] == crop
        if not c_mask.any():
            continue

        c_y = y_test[c_mask].values
        crop_res = {}
        for model_col in results["models"].keys():
            if model_col in pred_df.columns:
                c_preds = pred_df.loc[c_mask, model_col].values
                crop_res[model_col] = calculate_metrics(c_y, c_preds)

        results["per_crop"][crop] = crop_res

    return results, pred_df


def evaluate_spatial_holdout(
    df: pd.DataFrame,
    random_state: int = 42,
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Evaluate generalization across unseen districts via Leave-One-District-Out CV.

    Ensures that for each held-out district D, all observations for D (across all crops
    and years) are completely excluded from training.

    Args:
        df: Cleaned modeling dataset.
        random_state: Random seed for model training.

    Returns:
        Tuple of (spatial_metrics_dictionary, out_of_fold_predictions_dataframe).
    """
    districts = sorted(df["district"].unique().tolist())
    pred_df = df[[
        "observation_id", "crop_id", "district", "season", "year", TARGET_COLUMN
    ]].copy()

    # Pre-allocate columns for out-of-fold spatial predictions
    candidate_names = ["Baseline_CropMean", "Shared_RandomForest", "Shared_GradientBoosting", "CropSpecific_RandomForest"]
    for cname in candidate_names:
        pred_df[cname] = np.nan

    spatial_results: Dict[str, Any] = {
        "split": {
            "type": "leave_one_district_out",
            "districts_count": len(districts),
            "districts": districts,
            "total_observations": len(df),
        },
        "per_district": {},
        "overall": {},
        "per_crop": {},
    }

    # Iterate over each held-out district
    for held_out_district in districts:
        train_mask = df["district"] != held_out_district
        test_mask = df["district"] == held_out_district

        train_df = df[train_mask].copy().reset_index(drop=True)
        test_df = df[test_mask].copy().reset_index(drop=True)
        test_orig_idx = df[test_mask].index

        X_train = train_df[MODEL_FEATURE_COLUMNS]
        y_train = train_df[TARGET_COLUMN]

        X_test = test_df[MODEL_FEATURE_COLUMNS]
        y_test = test_df[TARGET_COLUMN]

        # 1. Baseline Crop Mean
        base_crop = CropMeanBaseline().fit(X_train, y_train)
        preds_base = base_crop.predict(X_test)
        pred_df.loc[test_orig_idx, "Baseline_CropMean"] = preds_base

        # 2. Shared Random Forest
        rf_reg = get_candidate_models(random_state=random_state)["RandomForest"]
        rf_pipe = build_multicrop_pipeline(rf_reg, include_crop_categorical=True)
        rf_pipe.fit(X_train, y_train)
        preds_rf = rf_pipe.predict(X_test)
        pred_df.loc[test_orig_idx, "Shared_RandomForest"] = preds_rf

        # 3. Shared Gradient Boosting
        gb_reg = get_candidate_models(random_state=random_state)["GradientBoosting"]
        gb_pipe = build_multicrop_pipeline(gb_reg, include_crop_categorical=True)
        gb_pipe.fit(X_train, y_train)
        preds_gb = gb_pipe.predict(X_test)
        pred_df.loc[test_orig_idx, "Shared_GradientBoosting"] = preds_gb

        # 4. Crop-Specific Models (Dedicated per crop)
        crop_preds_fold = np.zeros(len(test_df), dtype=float)
        for crop in df["crop_id"].unique():
            c_train = train_df[train_df["crop_id"] == crop]
            c_test = test_df[test_df["crop_id"] == crop]
            if len(c_train) == 0 or len(c_test) == 0:
                continue

            c_pipe = build_multicrop_pipeline(
                get_candidate_models(random_state=random_state)["RandomForest"],
                include_crop_categorical=False,
            )
            c_pipe.fit(c_train[MODEL_FEATURE_COLUMNS], c_train[TARGET_COLUMN])
            sub_preds = c_pipe.predict(c_test[MODEL_FEATURE_COLUMNS])

            local_mask = (test_df["crop_id"] == crop).values
            crop_preds_fold[local_mask] = sub_preds

        pred_df.loc[test_orig_idx, "CropSpecific_RandomForest"] = crop_preds_fold

        # Per-district evaluation metrics
        spatial_results["per_district"][held_out_district] = {
            "count": len(test_df),
            "Baseline_CropMean": calculate_metrics(y_test.values, preds_base),
            "Shared_RandomForest": calculate_metrics(y_test.values, preds_rf),
            "Shared_GradientBoosting": calculate_metrics(y_test.values, preds_gb),
            "CropSpecific_RandomForest": calculate_metrics(y_test.values, crop_preds_fold),
        }

    # Overall Spatial Generalization Metrics across all out-of-fold predictions
    y_all = pred_df[TARGET_COLUMN].values
    for cname in candidate_names:
        spatial_results["overall"][cname] = calculate_metrics(y_all, pred_df[cname].values)

    # Per-Crop Spatial Generalization Metrics
    for crop in sorted(df["crop_id"].unique().tolist()):
        c_mask = pred_df["crop_id"] == crop
        c_y = pred_df.loc[c_mask, TARGET_COLUMN].values
        c_metrics = {}
        for cname in candidate_names:
            c_metrics[cname] = calculate_metrics(c_y, pred_df.loc[c_mask, cname].values)
        spatial_results["per_crop"][crop] = c_metrics

    return spatial_results, pred_df
