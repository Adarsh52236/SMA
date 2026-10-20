"""Model Explainability and Permutation Feature Importance Engine.

Computes held-out permutation feature importances, exports rankings to CSV,
and generates diagnostic visualizations.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List
from sklearn.inspection import permutation_importance

from app.ml.config import ml_config
from app.ml.features import ALL_PREDICTORS


class ModelExplainer:
    """Computes and visualizes model explainability metrics."""

    def __init__(self, config=ml_config):
        self.config = config
        os.makedirs(self.config.REPORTS_MODELING_DIR, exist_ok=True)
        os.makedirs(self.config.FIGURES_DIR, exist_ok=True)

    def compute_permutation_importance(
        self,
        pipeline: Any,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        n_repeats: int = ml_config.PFI_N_REPEATS,
        random_state: int = ml_config.RANDOM_SEED,
    ) -> pd.DataFrame:
        """Compute permutation feature importance on held-out validation data."""
        pfi = permutation_importance(
            estimator=pipeline,
            X=X_val,
            y=y_val,
            scoring="neg_root_mean_squared_error",
            n_repeats=n_repeats,
            random_state=random_state,
            n_jobs=-1,
        )

        importance_df = pd.DataFrame({
            "feature": X_val.columns.tolist(),
            "importance_mean": pfi.importances_mean,
            "importance_std": pfi.importances_std,
        }).sort_values(by="importance_mean", ascending=False).reset_index(drop=True)

        # Save to CSV
        csv_path = os.path.join(self.config.REPORTS_MODELING_DIR, "feature_importance.csv")
        importance_df.to_csv(csv_path, index=False)

        # Plot bar chart
        self._plot_feature_importance(importance_df)

        return importance_df

    def _plot_feature_importance(self, df_imp: pd.DataFrame):
        plt.figure(figsize=(10, 6))
        top_features = df_imp.head(10).sort_values(by="importance_mean", ascending=True)

        plt.barh(
            top_features["feature"],
            top_features["importance_mean"],
            xerr=top_features["importance_std"],
            color="#2e7d32",
            alpha=0.85,
            capsize=4,
        )
        plt.xlabel("Permutation Importance (Increase in RMSE in t/ha)", fontweight="bold")
        plt.ylabel("Predictor Feature", fontweight="bold")
        plt.title("Top Feature Importances (Permutation on Validation Data)", fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(self.config.FIGURES_DIR, "feature_importance.png"), dpi=150)
        plt.close()
