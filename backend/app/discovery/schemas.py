"""Pydantic schemas for Dynamic Dataset Discovery and Profiling Engine (Phase 6).

Defines machine-readable dataset profiles, column role definitions, data quality flags,
observed category relationships, and dynamically generated presets.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class ColumnRole(str, Enum):
    """Semantic role inferred for a dataset column."""

    TARGET = "target"
    CATEGORICAL = "categorical"
    NUMERICAL = "numerical"
    DATETIME = "datetime"
    GEOGRAPHIC = "geographic"
    IDENTIFIER = "identifier"
    LEAKAGE = "leakage"
    METADATA = "metadata"


class RepresentationSufficiency(str, Enum):
    """Data representation quality for observed category combinations."""

    WELL_REPRESENTED = "well_represented"  # >= 20 observations
    SPARSE = "sparse"                      # 5-19 observations
    INSUFFICIENT = "insufficient"          # 1-4 observations
    UNOBSERVED = "unobserved"              # 0 observations


class NumericStats(BaseModel):
    """Empirical distribution statistics for a numerical column."""

    min: float
    max: float
    mean: float
    std: float
    p25: float
    p50: float
    p75: float
    outlier_count_iqr: int = 0
    zero_count: int = 0


class CategoricalStats(BaseModel):
    """Empirical frequency statistics for a categorical column."""

    cardinality: int
    top_categories: Dict[str, int]
    rare_categories: List[str] = Field(default_factory=list, description="Categories with < 5 occurrences.")


class ColumnProfile(BaseModel):
    """Profile specification for an individual dataset column."""

    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: int
    unique_pct: float
    is_constant: bool
    inferred_role: ColumnRole
    confidence_role: float = Field(default=1.0, ge=0.0, le=1.0)
    inferred_units: Optional[str] = None
    description: Optional[str] = None
    numeric_stats: Optional[NumericStats] = None
    categorical_stats: Optional[CategoricalStats] = None
    is_leakage_risk: bool = False
    leakage_reason: Optional[str] = None


class CategoryCombination(BaseModel):
    """Observed cross-tabulated category pair (e.g., crop x season or crop x district)."""

    feature_a: str
    value_a: str
    feature_b: str
    value_b: str
    observation_count: int
    representation_status: RepresentationSufficiency
    is_supported_for_training: bool
    guidance: str


class DataQualityReport(BaseModel):
    """Comprehensive data quality and anomaly detection report."""

    total_rows: int
    total_columns: int
    duplicate_rows: int
    duplicate_rows_pct: float
    constant_columns: List[str] = Field(default_factory=list)
    high_null_columns: List[str] = Field(default_factory=list, description="Columns with > 30% nulls.")
    detected_leakage_columns: List[str] = Field(default_factory=list)
    quality_score_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    warnings: List[str] = Field(default_factory=list)


class DynamicPresetSample(BaseModel):
    """Illustrative sample preset dynamically derived from actual dataset observations."""

    preset_id: str
    name: str
    category_summary: Dict[str, str] = Field(default_factory=dict)
    description: str
    sample_values: Dict[str, Any]
    observed_target: Optional[float] = None
    source_row_index: Optional[int] = None


class DatasetProfile(BaseModel):
    """Complete machine-readable dataset profile produced by the Discovery Engine."""

    dataset_name: str
    file_format: str
    sha256_hash: str
    row_count: int
    col_count: int
    memory_bytes: int
    columns: Dict[str, ColumnProfile]
    target_candidates: List[str]
    selected_target: Optional[str] = None
    target_is_ambiguous: bool = False
    ambiguity_explanation: Optional[str] = None
    discovered_categories: Dict[str, List[str]] = Field(default_factory=dict)
    observed_combinations: List[CategoryCombination] = Field(default_factory=list)
    quality_report: DataQualityReport
    dynamic_presets: List[DynamicPresetSample] = Field(default_factory=list)
    human_readable_summary: str = ""
