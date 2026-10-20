"""Adaptive Machine Learning module for Phase 6."""

from app.ml.adaptive.models import GlobalMeanBaseline, GroupMeanBaseline, get_candidate_models
from app.ml.adaptive.evaluator import (
    calculate_metrics,
    split_chronological,
    evaluate_spatial_cv,
    compute_permutation_importance,
)
from app.ml.adaptive.pipeline import AdaptiveMLPipeline

__all__ = [
    "GlobalMeanBaseline",
    "GroupMeanBaseline",
    "get_candidate_models",
    "calculate_metrics",
    "split_chronological",
    "evaluate_spatial_cv",
    "compute_permutation_importance",
    "AdaptiveMLPipeline",
]
