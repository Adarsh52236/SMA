"""Model Architecture Definitions and Candidate Pipeline Factories.

Implements the 4 mandatory benchmark model architectures:
1. Historical Mean Baseline (DummyRegressor)
2. Ridge Regression
3. Random Forest Regressor
4. Gradient Boosting Regressor
"""

from typing import Dict, Any
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor

from app.ml.config import ml_config
from app.ml.preprocessing import build_preprocessor


class ModelFactory:
    """Instantiates scikit-learn candidate pipelines."""

    @staticmethod
    def get_candidate_models(seed: int = ml_config.RANDOM_SEED) -> Dict[str, Pipeline]:
        """Instantiate preconfigured pipelines for all 4 benchmark models."""
        return {
            "Mean_Yield_Baseline": Pipeline([
                ("preprocessor", build_preprocessor(scale_numeric=False)),
                ("regressor", DummyRegressor(strategy="mean")),
            ]),
            "Ridge_Regression": Pipeline([
                ("preprocessor", build_preprocessor(scale_numeric=True)),
                ("regressor", Ridge(alpha=10.0, random_state=seed)),
            ]),
            "Random_Forest": Pipeline([
                ("preprocessor", build_preprocessor(scale_numeric=False)),
                (
                    "regressor",
                    RandomForestRegressor(
                        n_estimators=100,
                        max_depth=5,
                        min_samples_split=4,
                        min_samples_leaf=2,
                        random_state=seed,
                        n_jobs=-1,
                    ),
                ),
            ]),
            "Gradient_Boosting": Pipeline([
                ("preprocessor", build_preprocessor(scale_numeric=False)),
                (
                    "regressor",
                    GradientBoostingRegressor(
                        n_estimators=100,
                        learning_rate=0.05,
                        max_depth=3,
                        min_samples_split=4,
                        min_samples_leaf=2,
                        subsample=0.85,
                        random_state=seed,
                    ),
                ),
            ]),
        }
