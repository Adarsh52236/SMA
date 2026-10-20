"""Dataset Splitting Engine: Chronological, Rolling-Origin, and Spatial Holdout.

Implements leakage-free chronological train/val/test splits, rolling-origin
time-series folds for training diagnostics, and spatial GroupKFold partitions.
"""

from typing import Dict, List, Tuple, Generator, Any
import pandas as pd
from app.ml.config import ml_config


class DataSplitter:
    """Orchestrates temporal and geographic partitioning."""

    def __init__(self, config=ml_config):
        self.config = config

    def chronological_split(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """Partition dataset into strict chronological Train, Validation, and Test subsets."""
        train_mask = (df["year"] >= self.config.TRAIN_START_YEAR) & (
            df["year"] <= self.config.TRAIN_END_YEAR
        )
        val_mask = (df["year"] >= self.config.VAL_START_YEAR) & (
            df["year"] <= self.config.VAL_END_YEAR
        )
        test_mask = (df["year"] >= self.config.TEST_START_YEAR) & (
            df["year"] <= self.config.TEST_END_YEAR
        )

        df_train = df[train_mask].copy().reset_index(drop=True)
        df_val = df[val_mask].copy().reset_index(drop=True)
        df_test = df[test_mask].copy().reset_index(drop=True)

        # Sanity validation
        if df_train.empty:
            raise ValueError(f"Training split ({self.config.TRAIN_START_YEAR}-{self.config.TRAIN_END_YEAR}) has 0 observations.")
        if df_val.empty:
            raise ValueError(f"Validation split ({self.config.VAL_START_YEAR}-{self.config.VAL_END_YEAR}) has 0 observations.")
        if df_test.empty:
            raise ValueError(f"Test split ({self.config.TEST_START_YEAR}-{self.config.TEST_END_YEAR}) has 0 observations.")

        split_summary = {
            "train": {
                "rows": len(df_train),
                "years": [int(df_train["year"].min()), int(df_train["year"].max())],
                "districts": sorted(df_train["district"].unique().tolist()),
            },
            "validation": {
                "rows": len(df_val),
                "years": [int(df_val["year"].min()), int(df_val["year"].max())],
                "districts": sorted(df_val["district"].unique().tolist()),
            },
            "test": {
                "rows": len(df_test),
                "years": [int(df_test["year"].min()), int(df_test["year"].max())],
                "districts": sorted(df_test["district"].unique().tolist()),
            },
        }

        return df_train, df_val, df_test, split_summary

    def rolling_origin_folds(
        self, df_train: pd.DataFrame
    ) -> Generator[Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]], None, None]:
        """Generate rolling-origin forward-chaining folds strictly within the training set.

        Folds:
            Fold 1: Train 1990-2004, Val 2005-2006
            Fold 2: Train 1990-2006, Val 2007-2008
            Fold 3: Train 1990-2008, Val 2009-2010
        """
        fold_definitions = [
            {"train_years": (1990, 2004), "val_years": (2005, 2006)},
            {"train_years": (1990, 2006), "val_years": (2007, 2008)},
            {"train_years": (1990, 2008), "val_years": (2009, 2010)},
        ]

        for idx, fold in enumerate(fold_definitions, 1):
            t_min, t_max = fold["train_years"]
            v_min, v_max = fold["val_years"]

            fold_train = df_train[
                (df_train["year"] >= t_min) & (df_train["year"] <= t_max)
            ].copy()
            fold_val = df_train[
                (df_train["year"] >= v_min) & (df_train["year"] <= v_max)
            ].copy()

            fold_meta = {
                "fold": idx,
                "train_years": [t_min, t_max],
                "val_years": [v_min, v_max],
                "train_rows": len(fold_train),
                "val_rows": len(fold_val),
            }

            yield fold_train, fold_val, fold_meta

    def spatial_holdout_splits(
        self, df: pd.DataFrame
    ) -> Generator[Tuple[pd.DataFrame, pd.DataFrame, str], None, None]:
        """Generate Leave-One-District-Out spatial partitions.

        Guarantees that 100% of observations from a held-out district are
        completely excluded from the training partition.
        """
        all_districts = sorted(df["district"].unique().tolist())
        for held_out_district in all_districts:
            train_part = df[df["district"] != held_out_district].copy()
            spatial_test_part = df[df["district"] == held_out_district].copy()

            yield train_part, spatial_test_part, held_out_district
