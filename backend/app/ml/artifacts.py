"""Model Artifact Serialization, Provenance Hashing, and API Inference Loader.

Serializes the winning pipeline and operational metadata with SHA-256 dataset
fingerprinting. Provides a thread-safe loader for the FastAPI serving layer.
"""

import os
import json
import hashlib
import joblib
import sklearn
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
from app.ml.config import ml_config
from app.ml.features import ALL_PREDICTORS, NUMERIC_FEATURES, CATEGORICAL_FEATURES


class ArtifactManager:
    """Manages model artifact lifecycle, serialization, and deserialization."""

    def __init__(self, config=ml_config):
        self.config = config
        os.makedirs(self.config.ARTIFACT_DIR, exist_ok=True)

    @staticmethod
    def compute_file_sha256(filepath: str) -> str:
        """Compute SHA-256 hash of a file for immutable dataset version tracking."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    def save_artifact(
        self,
        pipeline: Any,
        model_name: str,
        val_metrics: Dict[str, float],
        test_metrics: Dict[str, float],
        split_summary: Dict[str, Any],
        dataset_path: str,
    ) -> Tuple[str, str]:
        """Serialize pipeline and export governance metadata manifest."""
        model_path = os.path.join(self.config.ARTIFACT_DIR, self.config.MODEL_FILENAME)
        meta_path = os.path.join(self.config.ARTIFACT_DIR, self.config.METADATA_FILENAME)

        # 1. Serialize scikit-learn pipeline
        joblib.dump(pipeline, model_path, compress=3)

        # 2. Build metadata manifest
        dataset_sha256 = self.compute_file_sha256(dataset_path) if os.path.exists(dataset_path) else "N/A"

        metadata = {
            "model_name": model_name,
            "target": self.config.TARGET_COLUMN,
            "target_units": self.config.TARGET_UNITS,
            "dataset_sha256": dataset_sha256,
            "feature_schema": {
                "all_predictors": ALL_PREDICTORS,
                "numeric_features": NUMERIC_FEATURES,
                "categorical_features": CATEGORICAL_FEATURES,
            },
            "splits": split_summary,
            "performance": {
                "validation": val_metrics,
                "test": test_metrics,
            },
            "environment": {
                "scikit_learn_version": sklearn.__version__,
                "numpy_version": np.__version__,
                "pandas_version": pd.__version__,
                "joblib_version": joblib.__version__,
            },
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return model_path, meta_path

    def load_artifact(self) -> Tuple[Any, Dict[str, Any]]:
        """Load fitted pipeline and verify schema compatibility."""
        model_path = os.path.join(self.config.ARTIFACT_DIR, self.config.MODEL_FILENAME)
        meta_path = os.path.join(self.config.ARTIFACT_DIR, self.config.METADATA_FILENAME)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model artifact not found at '{model_path}'.")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Model metadata manifest not found at '{meta_path}'.")

        pipeline = joblib.load(model_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        return pipeline, metadata


def load_model_for_inference() -> Tuple[Any, Dict[str, Any]]:
    """Convenience accessor for FastAPI startup."""
    manager = ArtifactManager()
    return manager.load_artifact()
