"""Preprocessing Pipelines and Machine Learning Candidates for Multi-Crop Modeling (Phase 4).

Constructs leakage-free scikit-learn Pipelines combining OneHotEncoder for
categoricals and StandardScaler for continuous agroclimatic and pedological features.
"""

from typing import Dict, Any, List, Tuple
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import (
    RandomForestRegressor,
    ExtraTreesRegressor,
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
)

from .dataset import (
    CATEGORICAL_FEATURES,
    WEATHER_FEATURES,
    SOIL_FEATURES,
    MODEL_FEATURE_COLUMNS,
)


def build_feature_preprocessor(include_crop_categorical: bool = True) -> ColumnTransformer:
    """Build a ColumnTransformer fitting encoders and scalers strictly on training folds.

    Args:
        include_crop_categorical: Whether to include 'crop_id' in categorical features
                                  (True for shared models, False for crop-specific models).

    Returns:
        Configured ColumnTransformer.
    """
    cat_cols = [c for c in CATEGORICAL_FEATURES if include_crop_categorical or c != "crop_id"]
    num_cols = WEATHER_FEATURES + SOIL_FEATURES

    transformers = [
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            cat_cols,
        ),
        (
            "num",
            StandardScaler(),
            num_cols,
        ),
    ]

    return ColumnTransformer(transformers=transformers, remainder="drop")


def build_multicrop_pipeline(
    regressor: Any,
    include_crop_categorical: bool = True,
) -> Pipeline:
    """Construct a full ML Pipeline binding the preprocessor and regressor."""
    preprocessor = build_feature_preprocessor(include_crop_categorical=include_crop_categorical)
    return Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", regressor),
    ])


def get_candidate_models(random_state: int = 42) -> Dict[str, Any]:
    """Return dictionary of candidate model estimators with reproducible seeds."""
    return {
        "RandomForest": RandomForestRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        ),
        "ExtraTrees": ExtraTreesRegressor(
            n_estimators=100,
            max_depth=12,
            min_samples_split=4,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            min_samples_leaf=3,
            subsample=0.85,
            random_state=random_state,
        ),
        "HistGradientBoosting": HistGradientBoostingRegressor(
            max_iter=100,
            learning_rate=0.05,
            max_depth=6,
            min_samples_leaf=5,
            random_state=random_state,
        ),
    }
