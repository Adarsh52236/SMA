"""Multi-crop Machine Learning Module (Phase 4).

Provides dataset auditing, leakage-free feature pipelines, historical baselines,
temporal and spatial cross-validation, and multi-model benchmarking across crops.
"""

from .dataset import load_and_audit_multicrop_data, get_feature_contract
from .baselines import GlobalMeanBaseline, CropMeanBaseline, HistoricalCropDistrictMeanBaseline
from .pipeline import build_multicrop_pipeline, get_candidate_models
from .evaluation import evaluate_temporal_holdout, evaluate_spatial_holdout
from .runner import run_phase4_benchmarking

__all__ = [
    "load_and_audit_multicrop_data",
    "get_feature_contract",
    "GlobalMeanBaseline",
    "CropMeanBaseline",
    "HistoricalCropDistrictMeanBaseline",
    "build_multicrop_pipeline",
    "get_candidate_models",
    "evaluate_temporal_holdout",
    "evaluate_spatial_holdout",
    "run_phase4_benchmarking",
]
