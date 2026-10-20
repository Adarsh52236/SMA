"""Model Evaluation, Benchmarking, and Diagnostic Metrics Engine.

Calculates Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and
Coefficient of Determination (R²) across validation and held-out test partitions.
Performs temporal slice analysis and residual diagnostics.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List, Tuple
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from app.ml.config import ml_config


class ModelEvaluator:
    """Computes evaluation metrics and generates diagnostic visualizations."""

    def __init__(self, config=ml_config):
        self.config = config
        os.makedirs(self.config.REPORTS_MODELING_DIR, exist_ok=True)
        os.makedirs(self.config.FIGURES_DIR, exist_ok=True)

    @staticmethod
    def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Compute standard regression performance metrics."""
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred))

        return {
            "mae_t_ha": round(mae, 4),
            "rmse_t_ha": round(rmse, 4),
            "r2_score": round(r2, 4),
            "sample_count": len(y_true),
        }

    def evaluate_validation_candidates(
        self,
        candidate_models: Dict[str, Any],
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
    ) -> Tuple[str, Dict[str, Any], Any]:
        """Fit all benchmark models on training data, evaluate on validation data, and select winner."""
        comparison_results = {}
        fitted_models = {}

        best_model_name = None
        best_val_rmse = float("inf")

        for name, pipeline in candidate_models.items():
            # Fit strictly on training partition
            pipeline.fit(X_train, y_train)
            fitted_models[name] = pipeline

            y_train_pred = pipeline.predict(X_train)
            y_val_pred = pipeline.predict(X_val)

            train_metrics = self.compute_metrics(y_train.values, y_train_pred)
            val_metrics = self.compute_metrics(y_val.values, y_val_pred)

            comparison_results[name] = {
                "train_metrics": train_metrics,
                "validation_metrics": val_metrics,
            }

            # Model selection criterion: lowest validation RMSE
            if val_metrics["rmse_t_ha"] < best_val_rmse:
                best_val_rmse = val_metrics["rmse_t_ha"]
                best_model_name = name

        # Export comparison to reports/modeling/model_comparison.json
        comp_path = os.path.join(self.config.REPORTS_MODELING_DIR, "model_comparison.json")
        with open(comp_path, "w", encoding="utf-8") as f:
            json.dump(comparison_results, f, indent=2)

        return best_model_name, comparison_results, fitted_models[best_model_name]

    def evaluate_test_set(
        self,
        selected_pipeline: Any,
        selected_model_name: str,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        df_test_full: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Evaluate the selected model ONCE on the untouched chronological test set."""
        y_test_pred = selected_pipeline.predict(X_test)
        overall_metrics = self.compute_metrics(y_test.values, y_test_pred)

        # Slice performance by test year
        year_metrics = {}
        for yr in sorted(df_test_full["year"].unique()):
            mask = df_test_full["year"] == yr
            y_t_yr = y_test[mask]
            y_p_yr = y_test_pred[mask]
            year_metrics[str(yr)] = self.compute_metrics(y_t_yr.values, y_p_yr)

        # Slice performance by district
        district_metrics = {}
        for dist in sorted(df_test_full["district"].unique()):
            mask = df_test_full["district"] == dist
            y_t_dist = y_test[mask]
            y_p_dist = y_test_pred[mask]
            district_metrics[dist] = self.compute_metrics(y_t_dist.values, y_p_dist)

        test_results = {
            "selected_model": selected_model_name,
            "overall_test_metrics": overall_metrics,
            "metrics_by_year": year_metrics,
            "metrics_by_district": district_metrics,
            "y_true": y_test.tolist(),
            "y_pred": [round(float(v), 4) for v in y_test_pred],
        }

        # Generate diagnostic figures
        self._plot_actual_vs_predicted(y_test.values, y_test_pred, selected_model_name)
        self._plot_residuals(y_test.values, y_test_pred, selected_model_name)

        return test_results

    def _plot_actual_vs_predicted(self, y_true: np.ndarray, y_pred: np.ndarray, model_name: str):
        plt.figure(figsize=(7, 7))
        plt.scatter(y_true, y_pred, color="#2e7d32", alpha=0.8, edgecolors="k", s=60)
        min_v = min(float(y_true.min()), float(y_pred.min())) * 0.9
        max_v = max(float(y_true.max()), float(y_pred.max())) * 1.1
        plt.plot([min_v, max_v], [min_v, max_v], "r--", linewidth=1.5, label="1:1 Perfect Agreement")
        plt.xlabel("Actual Soybean Yield (t/ha)", fontweight="bold")
        plt.ylabel("Predicted Soybean Yield (t/ha)", fontweight="bold")
        plt.title(f"Test Set: Actual vs. Predicted ({model_name})", fontweight="bold")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(self.config.FIGURES_DIR, "actual_vs_predicted.png"), dpi=150)
        plt.close()

    def _plot_residuals(self, y_true: np.ndarray, y_pred: np.ndarray, model_name: str):
        residuals = y_true - y_pred
        plt.figure(figsize=(8, 5))
        sns.histplot(residuals, kde=True, color="#d32f2f", bins=15)
        plt.axvline(0, color="k", linestyle="--", linewidth=1)
        plt.xlabel("Prediction Residual (Actual - Predicted in t/ha)", fontweight="bold")
        plt.ylabel("Frequency", fontweight="bold")
        plt.title(f"Test Set Residual Distribution ({model_name})", fontweight="bold")
        plt.tight_layout()
        plt.savefig(os.path.join(self.config.FIGURES_DIR, "residuals_distribution.png"), dpi=150)
        plt.close()
