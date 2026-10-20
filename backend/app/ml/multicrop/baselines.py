"""Statistical and Historical Baselines for Multi-Crop Yield Prediction (Phase 4).

Implements strictly causal, leakage-safe baselines:
1. GlobalMeanBaseline: Overall training set mean yield.
2. CropMeanBaseline: Crop-specific training set mean yield.
3. HistoricalCropDistrictMeanBaseline: Expanding-window historical mean for each (crop, district)
   using strictly prior years (year < T) without future information.
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class GlobalMeanBaseline:
    """Predicts the overall average crop yield across all crops and regions in the training partition."""

    def __init__(self):
        self.global_mean: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "GlobalMeanBaseline":
        self.global_mean = float(y.mean())
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.full(shape=(len(X),), fill_value=self.global_mean, dtype=float)


class CropMeanBaseline:
    """Predicts the crop-specific average yield learned on the training partition."""

    def __init__(self):
        self.crop_means: Dict[str, float] = {}
        self.global_mean: float = 0.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "CropMeanBaseline":
        self.global_mean = float(y.mean())
        df_temp = pd.DataFrame({"crop_id": X["crop_id"], "yield": y})
        self.crop_means = df_temp.groupby("crop_id")["yield"].mean().to_dict()
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in X.iterrows():
            crop = row.get("crop_id")
            preds.append(self.crop_means.get(crop, self.global_mean))
        return np.array(preds, dtype=float)


class HistoricalCropDistrictMeanBaseline:
    """Predicts historical mean for a crop and district using strictly years prior to prediction year (year < T).

    Ensures zero temporal leakage from same-year or future observations.
    Falls back gracefully to historical crop mean, then training global mean.
    """

    def __init__(self):
        self.history_df: Optional[pd.DataFrame] = None
        self.global_mean: float = 0.0

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        years: Optional[pd.Series] = None,
    ) -> "HistoricalCropDistrictMeanBaseline":
        year_series = years if years is not None else (X["year"] if "year" in X.columns else None)
        if year_series is None:
            raise ValueError("Historical baseline requires 'year' column in X or 'years' argument.")

        self.history_df = pd.DataFrame({
            "crop_id": X["crop_id"].values,
            "district": X["district"].values,
            "year": year_series.values,
            "yield": y.values,
        })
        self.global_mean = float(y.mean())
        return self

    def predict(
        self,
        X: pd.DataFrame,
        years: Optional[pd.Series] = None,
    ) -> np.ndarray:
        if self.history_df is None:
            raise ValueError("Historical baseline must be fitted before predict.")

        year_series = years if years is not None else (X["year"] if "year" in X.columns else None)
        if year_series is None:
            raise ValueError("Historical baseline requires 'year' column in X or 'years' argument.")

        crops = X["crop_id"].values
        districts = X["district"].values
        year_vals = year_series.values

        preds = []
        for crop, dist, year in zip(crops, districts, year_vals):
            # Filter historical records strictly before the observation year
            past_records = self.history_df[
                (self.history_df["crop_id"] == crop) &
                (self.history_df["district"] == dist) &
                (self.history_df["year"] < year)
            ]

            if len(past_records) > 0:
                pred = float(past_records["yield"].mean())
            else:
                # Fallback 1: Historical crop mean across all districts prior to year
                past_crop_records = self.history_df[
                    (self.history_df["crop_id"] == crop) &
                    (self.history_df["year"] < year)
                ]
                if len(past_crop_records) > 0:
                    pred = float(past_crop_records["yield"].mean())
                else:
                    # Fallback 2: Training global mean
                    pred = self.global_mean

            preds.append(pred)

        return np.array(preds, dtype=float)
