"""Adaptive Candidate Models and Baselines (Phase 6).

Implements suitable candidate model families for tabular continuous targets:
1. GlobalMeanBaseline & GroupMeanBaseline (empirical benchmarks)
2. Ridge Regression (L2-regularized linear model)
3. RandomForestRegressor (ensemble non-linear bagging)
4. HistGradientBoostingRegressor (gradient boosting with native missing-value support)
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor


class GlobalMeanBaseline(BaseEstimator, RegressorMixin):
    """Simple baseline predicting the overall training target mean."""

    def __init__(self):
        self.mean_: float = 0.0

    def fit(self, X: Any, y: np.ndarray) -> "GlobalMeanBaseline":
        self.mean_ = float(np.mean(y))
        return self

    def predict(self, X: Any) -> np.ndarray:
        n_samples = len(X) if hasattr(X, "__len__") else 1
        return np.full(n_samples, self.mean_, dtype=float)


class GroupMeanBaseline(BaseEstimator, RegressorMixin):
    """Hierarchical baseline predicting group means (e.g. crop x district), falling back to global mean."""

    def __init__(self, group_cols: Optional[List[str]] = None):
        self.group_cols = group_cols or []
        self.global_mean_: float = 0.0
        self.group_means_: Dict[Tuple[str, ...], float] = {}

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "GroupMeanBaseline":
        self.global_mean_ = float(np.mean(y))
        if not self.group_cols or not isinstance(X, pd.DataFrame):
            return self

        valid_group_cols = [c for c in self.group_cols if c in X.columns]
        if not valid_group_cols:
            return self

        temp_df = X[valid_group_cols].copy()
        temp_df["__target__"] = y

        grouped = temp_df.groupby(valid_group_cols)["__target__"].mean()
        self.group_means_ = {
            tuple(str(k) for k in (idx if isinstance(idx, tuple) else (idx,))): float(val)
            for idx, val in grouped.items()
        }
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        n_samples = len(X)
        if not self.group_cols or not isinstance(X, pd.DataFrame):
            return np.full(n_samples, self.global_mean_, dtype=float)

        valid_group_cols = [c for c in self.group_cols if c in X.columns]
        if not valid_group_cols:
            return np.full(n_samples, self.global_mean_, dtype=float)

        preds = np.zeros(n_samples, dtype=float)
        for i, (_, row) in enumerate(X[valid_group_cols].iterrows()):
            key = tuple(str(row[c]) for c in valid_group_cols)
            preds[i] = self.group_means_.get(key, self.global_mean_)

        return preds


def get_candidate_models(
    random_state: int = 42,
    group_cols: Optional[List[str]] = None,
) -> Dict[str, BaseEstimator]:
    """Instantiate competitive candidate models and baselines for empirical evaluation."""
    return {
        "Global_Mean_Baseline": GlobalMeanBaseline(),
        "Group_Mean_Baseline": GroupMeanBaseline(group_cols=group_cols),
        "Ridge_Regression": Ridge(alpha=1.0, random_state=random_state),
        "Random_Forest": RandomForestRegressor(
            n_estimators=100,
            max_depth=16,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        ),
        "Hist_Gradient_Boosting": HistGradientBoostingRegressor(
            max_iter=100,
            max_depth=8,
            learning_rate=0.1,
            random_state=random_state,
        ),
    }
