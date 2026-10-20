"""Adaptive Evaluation and Validation Strategies (Phase 6).

Implements strict validation schemes without temporal lookahead or spatial group leakage:
- Chronological time-series splitting
- GroupKFold / Leave-One-Group-Out spatial cross-validation
- Robust metric computation (RMSE, MAE, R², MAPE)
- Held-out Permutation Feature Importance
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.inspection import permutation_importance
from sklearn.base import BaseEstimator


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Compute standard regression performance metrics."""
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    if not np.any(mask):
        return {"rmse": 0.0, "mae": 0.0, "r2": 0.0, "sample_count": 0}

    yt = y_true[mask]
    yp = y_pred[mask]

    rmse = float(np.sqrt(mean_squared_error(yt, yp)))
    mae = float(mean_absolute_error(yt, yp))
    r2 = float(r2_score(yt, yp)) if len(yt) > 1 and np.var(yt) > 0 else 0.0

    return {
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "r2": round(r2, 4),
        "sample_count": int(len(yt)),
    }


def split_chronological(
    df: pd.DataFrame,
    time_col: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Partition dataset chronologically based on a temporal column without lookahead leakage."""
    unique_times = sorted(df[time_col].dropna().unique())
    n_times = len(unique_times)

    if n_times < 3:
        # Fallback to standard index split if insufficient distinct time periods
        n = len(df)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        train_df = df.iloc[:train_end]
        val_df = df.iloc[train_end:val_end]
        test_df = df.iloc[val_end:]
        split_meta = {
            "type": "index_chronological",
            "train_size": len(train_df),
            "val_size": len(val_df),
            "test_size": len(test_df),
        }
        return train_df, val_df, test_df, split_meta

    n_train = max(1, int(n_times * train_ratio))
    n_val = max(1, int(n_times * val_ratio))

    train_times = unique_times[:n_train]
    val_times = unique_times[n_train : n_train + n_val]
    test_times = unique_times[n_train + n_val :]

    if not test_times:
        test_times = [val_times.pop()]

    train_df = df[df[time_col].isin(train_times)].copy()
    val_df = df[df[time_col].isin(val_times)].copy()
    test_df = df[df[time_col].isin(test_times)].copy()

    split_meta = {
        "type": "time_chronological",
        "time_column": time_col,
        "train_period": [int(train_times[0]), int(train_times[-1])],
        "val_period": [int(val_times[0]), int(val_times[-1])],
        "test_period": [int(test_times[0]), int(test_times[-1])],
        "train_samples": len(train_df),
        "val_samples": len(val_df),
        "test_samples": len(test_df),
    }

    return train_df, val_df, test_df, split_meta


def evaluate_spatial_cv(
    pipeline_builder_fn: Any,
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    group_col: str,
    n_splits: int = 5,
) -> Dict[str, Any]:
    """Execute GroupKFold spatial cross-validation to assess geographic transferability."""
    unique_groups = df[group_col].dropna().unique()
    actual_splits = min(n_splits, len(unique_groups))

    if actual_splits < 2:
        return {"status": "insufficient_groups", "mean_rmse": 0.0, "mean_r2": 0.0}

    gkf = GroupKFold(n_splits=actual_splits)
    X = df[feature_cols]
    y = df[target_col].values
    groups = df[group_col].values

    fold_metrics = []
    for fold, (train_idx, test_idx) in enumerate(gkf.split(X, y, groups=groups)):
        X_train, y_train = X.iloc[train_idx], y[train_idx]
        X_test, y_test = X.iloc[test_idx], y[test_idx]

        pipeline = pipeline_builder_fn()
        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        metrics = calculate_metrics(y_test, preds)
        fold_metrics.append(metrics)

    mean_rmse = round(float(np.mean([m["rmse"] for m in fold_metrics])), 4)
    mean_mae = round(float(np.mean([m["mae"] for m in fold_metrics])), 4)
    mean_r2 = round(float(np.mean([m["r2"] for m in fold_metrics])), 4)

    return {
        "group_column": group_col,
        "folds_evaluated": actual_splits,
        "mean_rmse": mean_rmse,
        "mean_mae": mean_mae,
        "mean_r2": mean_r2,
        "fold_details": fold_metrics,
    }


def compute_permutation_importance(
    pipeline: BaseEstimator,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    feature_names: List[str],
    n_repeats: int = 5,
    random_state: int = 42,
) -> List[Dict[str, Any]]:
    """Calculate held-out permutation feature importance on validation/test data."""
    if len(X_val) == 0:
        return []

    try:
        r = permutation_importance(
            pipeline,
            X_val,
            y_val,
            n_repeats=n_repeats,
            random_state=random_state,
            scoring="neg_root_mean_squared_error",
            n_jobs=-1,
        )

        importances = []
        for i, feat in enumerate(feature_names):
            importances.append({
                "feature": feat,
                "importance_mean_rmse": round(float(r.importances_mean[i]), 4),
                "importance_std_rmse": round(float(r.importances_std[i]), 4),
            })

        importances.sort(key=lambda x: x["importance_mean_rmse"], reverse=True)
        return importances

    except Exception:
        return []
