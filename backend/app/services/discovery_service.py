"""Discovery and Adaptive Intelligence Service (Phase 6).

Maintains dataset profiling caches, manages dynamic category discovery, generates authentic
empirical presets from data, and coordinates adaptive model retraining workflows.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import pandas as pd

from app.discovery.engine import DatasetDiscoveryEngine
from app.discovery.schemas import DatasetProfile, DynamicPresetSample
from app.ml.adaptive.pipeline import AdaptiveMLPipeline

logger = logging.getLogger("CropYieldAPI.DiscoveryService")


class DiscoveryService:
    """Singleton service for dataset discovery, dynamic categories, and adaptive retraining."""

    _instance: Optional["DiscoveryService"] = None

    def __init__(self, data_dir: str = "data/processed", models_dir: str = "backend/models/adaptive"):
        self.data_dir = data_dir
        self.models_dir = models_dir
        self.engine = DatasetDiscoveryEngine()
        self.cached_profiles: Dict[str, DatasetProfile] = {}
        self.active_dataset_name: Optional[str] = None
        self._initialize_default_profile()

    @classmethod
    def get_instance(cls) -> "DiscoveryService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _initialize_default_profile(self) -> None:
        """Profile default datasets available on disk at startup."""
        primary_dataset = os.path.join(self.data_dir, "crop_yield_multicrop.csv")
        fallback_dataset = os.path.join(self.data_dir, "crop_yield_maharashtra.csv")

        target_file = None
        if os.path.exists(primary_dataset):
            target_file = primary_dataset
        elif os.path.exists(fallback_dataset):
            target_file = fallback_dataset

        if target_file:
            try:
                profile = self.engine.profile_file(target_file)
                self.cached_profiles[profile.dataset_name] = profile
                self.active_dataset_name = profile.dataset_name
                logger.info(
                    f"DatasetDiscoveryService initialized with profile '{profile.dataset_name}' "
                    f"({profile.row_count:,} rows, target='{profile.selected_target}')."
                )
            except Exception as e:
                logger.warning(f"Could not automatically profile dataset '{target_file}': {e}")

    def get_active_profile(self) -> Optional[DatasetProfile]:
        """Return the current active dataset profile."""
        if self.active_dataset_name and self.active_dataset_name in self.cached_profiles:
            return self.cached_profiles[self.active_dataset_name]
        if self.cached_profiles:
            first_key = next(iter(self.cached_profiles))
            return self.cached_profiles[first_key]
        return None

    def get_categories(self) -> Dict[str, Any]:
        """Return dynamically discovered categories and observed combinations with sufficiency."""
        profile = self.get_active_profile()
        if not profile:
            return {
                "status": "unprofiled",
                "categories": {},
                "observed_combinations": [],
            }

        return {
            "status": "ready",
            "dataset_name": profile.dataset_name,
            "categories": profile.discovered_categories,
            "observed_combinations": [c.model_dump() for c in profile.observed_combinations],
        }

    def get_dynamic_presets(self, max_samples: int = 6) -> List[Dict[str, Any]]:
        """Return illustrative sample presets derived dynamically from genuine dataset rows."""
        profile = self.get_active_profile()
        if not profile or not profile.dynamic_presets:
            return []

        return [p.model_dump() for p in profile.dynamic_presets[:max_samples]]

    def inspect_dataset(
        self,
        content_bytes: bytes,
        filename: str,
        target_override: Optional[str] = None,
    ) -> DatasetProfile:
        """Inspect and profile an arbitrary uploaded dataset dynamically."""
        engine = DatasetDiscoveryEngine(target_override=target_override)
        dataset_name = Path(filename).stem
        ext = Path(filename).suffix.lower().lstrip(".")

        if ext == "parquet":
            df = pd.read_parquet(pd.io.common.BytesIO(content_bytes))
        else:
            df = pd.read_csv(pd.io.common.BytesIO(content_bytes))

        profile = engine.profile_dataframe(
            df=df,
            dataset_name=dataset_name,
            file_format=ext or "csv",
            content_bytes=content_bytes,
        )

        self.cached_profiles[dataset_name] = profile
        self.active_dataset_name = dataset_name
        return profile

    def retrain_adaptive_model(
        self,
        dataset_name: Optional[str] = None,
        target_col: Optional[str] = None,
        feature_exclusions: Optional[List[str]] = None,
        model_version: str = "3.0.0",
    ) -> Dict[str, Any]:
        """Execute automated model selection, validation, and serialization on a discovered dataset."""
        profile = self.cached_profiles.get(dataset_name) if dataset_name else self.get_active_profile()
        if not profile:
            raise ValueError(f"No profiled dataset found for name '{dataset_name}'.")

        # Load dataframe from disk
        csv_path = os.path.join(self.data_dir, f"{profile.dataset_name}.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Source file for dataset '{profile.dataset_name}' not found at {csv_path}.")

        df = pd.read_csv(csv_path)

        pipeline = AdaptiveMLPipeline(
            random_state=42,
            output_dir=self.models_dir,
        )

        result = pipeline.train_and_evaluate(
            df=df,
            profile=profile,
            target_col=target_col,
            feature_exclusions=feature_exclusions,
            model_version=model_version,
        )

        return result


discovery_service = DiscoveryService.get_instance()
