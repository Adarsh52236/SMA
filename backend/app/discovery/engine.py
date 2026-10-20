"""Dynamic Dataset Discovery and Profiling Engine (Phase 6).

Inspects incoming agricultural/environmental datasets without assuming a fixed crop-yield
schema. Discovers column semantics, target candidates, data quality anomalies, category
distributions, and observed category combinations. Generates dynamic presets and
comprehensive machine-readable and human-readable profiles.
"""

import hashlib
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import pandas as pd

from app.discovery.schemas import (
    ColumnProfile,
    ColumnRole,
    NumericStats,
    CategoricalStats,
    RepresentationSufficiency,
    CategoryCombination,
    DataQualityReport,
    DynamicPresetSample,
    DatasetProfile,
)

logger = logging.getLogger("CropYieldAPI.DiscoveryEngine")

# Semantic keyword heuristic dictionaries
TARGET_KEYWORDS = [
    "yield", "target", "tonnes_per_hectare", "t_ha", "kg_ha", "output", "production_per_hectare",
    "harvest_yield", "grain_yield"
]

LEAKAGE_KEYWORDS = [
    "leakage", "leak", "reported_production", "production_tonnes", "reported_area", "area_ha", "area_harvested",
    "total_production", "harvest_status", "harvested_production"
]

GEOGRAPHIC_KEYWORDS = [
    "district", "state", "region", "taluka", "zone", "province", "country", "latitude", "longitude",
    "lat", "lon"
]

DATETIME_KEYWORDS = [
    "year", "harvest_year", "date", "month", "timestamp", "calendar_year", "season_year"
]

IDENTIFIER_KEYWORDS = [
    "id", "uuid", "identifier", "row_num", "index", "code"
]


class DatasetDiscoveryEngine:
    """Engine that profiles arbitrary tabular datasets and infers semantic roles dynamically."""

    def __init__(self, target_override: Optional[str] = None):
        self.target_override = target_override

    @staticmethod
    def compute_sha256(content_bytes: bytes) -> str:
        """Compute SHA-256 fingerprint of file content bytes."""
        return hashlib.sha256(content_bytes).hexdigest()

    def profile_dataframe(
        self,
        df: pd.DataFrame,
        dataset_name: str = "dataset",
        file_format: str = "dataframe",
        content_bytes: Optional[bytes] = None,
    ) -> DatasetProfile:
        """Analyze a pandas DataFrame and construct a comprehensive DatasetProfile."""
        if content_bytes is None:
            # Generate deterministic hash from serialized values
            csv_str = df.to_csv(index=False)
            content_bytes = csv_str.encode("utf-8")
        sha256_hash = self.compute_sha256(content_bytes)

        row_count, col_count = df.shape
        memory_bytes = int(df.memory_usage(deep=True).sum())

        # 1. Duplicate rows inspection
        duplicate_rows = int(df.duplicated().sum())
        duplicate_rows_pct = round((duplicate_rows / row_count * 100.0), 2) if row_count > 0 else 0.0

        # 2. Per-column profiling and semantic role inference
        columns_profile: Dict[str, ColumnProfile] = {}
        target_candidates: List[Tuple[str, float, str]] = []  # (col_name, score, rationale)
        constant_columns: List[str] = []
        high_null_columns: List[str] = []
        detected_leakage: List[str] = []

        for col in df.columns:
            series = df[col]
            col_profile, is_target_candidate, candidate_score, rationale = self._profile_column(
                series, col, row_count
            )
            columns_profile[col] = col_profile

            if col_profile.is_constant:
                constant_columns.append(col)
            if col_profile.null_pct > 30.0:
                high_null_columns.append(col)
            if col_profile.is_leakage_risk:
                detected_leakage.append(col)
            if is_target_candidate:
                target_candidates.append((col, candidate_score, rationale))

        # Sort candidate targets by score descending
        target_candidates.sort(key=lambda x: x[1], reverse=True)
        target_candidate_names = [c[0] for c in target_candidates]

        # 3. Resolve Target Variable
        selected_target: Optional[str] = None
        target_is_ambiguous = False
        ambiguity_explanation: Optional[str] = None

        if self.target_override and self.target_override in df.columns:
            selected_target = self.target_override
            if selected_target in columns_profile:
                columns_profile[selected_target].inferred_role = ColumnRole.TARGET
                columns_profile[selected_target].confidence_role = 1.0
        elif len(target_candidate_names) == 1:
            selected_target = target_candidate_names[0]
            columns_profile[selected_target].inferred_role = ColumnRole.TARGET
            columns_profile[selected_target].confidence_role = 0.95
        elif len(target_candidate_names) > 1:
            target_is_ambiguous = True
            selected_target = target_candidate_names[0]  # Default highest score
            columns_profile[selected_target].inferred_role = ColumnRole.TARGET
            ambiguity_explanation = (
                f"Multiple candidate target columns discovered: {target_candidate_names}. "
                f"Top candidate '{selected_target}' was provisionally assigned, but explicit confirmation is recommended."
            )
            logger.info(ambiguity_explanation)

        # 4. Discovered Categories for Categorical Features
        discovered_categories: Dict[str, List[str]] = {}
        for col_name, prof in columns_profile.items():
            if prof.inferred_role in (ColumnRole.CATEGORICAL, ColumnRole.GEOGRAPHIC):
                unique_vals = [
                    str(v) for v in df[col_name].dropna().unique().tolist()
                ]
                unique_vals.sort()
                discovered_categories[col_name] = unique_vals

        # 5. Observed Category Relationships (e.g. crop x season, crop x district)
        observed_combinations = self._discover_category_combinations(df, columns_profile)

        # 6. Data Quality Report & Quality Scoring
        quality_score = 100.0
        warnings: List[str] = []

        if duplicate_rows > 0:
            quality_score -= min(25.0, duplicate_rows_pct * 2.0)
            warnings.append(f"Found {duplicate_rows} duplicate rows ({duplicate_rows_pct}% of dataset).")

        if constant_columns:
            quality_score -= len(constant_columns) * 5.0
            warnings.append(f"Columns with constant values offer zero predictive variance: {constant_columns}.")

        if high_null_columns:
            quality_score -= len(high_null_columns) * 10.0
            warnings.append(f"Columns with high missingness (>30% null): {high_null_columns}.")

        if detected_leakage:
            warnings.append(
                f"Potential data leakage variables detected (should be excluded from features): {detected_leakage}."
            )

        quality_report = DataQualityReport(
            total_rows=row_count,
            total_columns=col_count,
            duplicate_rows=duplicate_rows,
            duplicate_rows_pct=duplicate_rows_pct,
            constant_columns=constant_columns,
            high_null_columns=high_null_columns,
            detected_leakage_columns=detected_leakage,
            quality_score_pct=max(0.0, round(quality_score, 1)),
            warnings=warnings,
        )

        # 7. Extract Dynamic Presets from Genuine Observations
        dynamic_presets = self._extract_dynamic_presets(
            df, columns_profile, selected_target
        )

        # 8. Human-Readable Summary Generation
        summary = self._generate_markdown_summary(
            dataset_name=dataset_name,
            row_count=row_count,
            col_count=col_count,
            columns_profile=columns_profile,
            selected_target=selected_target,
            target_candidates=target_candidate_names,
            target_is_ambiguous=target_is_ambiguous,
            quality_report=quality_report,
            discovered_categories=discovered_categories,
        )

        return DatasetProfile(
            dataset_name=dataset_name,
            file_format=file_format,
            sha256_hash=sha256_hash,
            row_count=row_count,
            col_count=col_count,
            memory_bytes=memory_bytes,
            columns=columns_profile,
            target_candidates=target_candidate_names,
            selected_target=selected_target,
            target_is_ambiguous=target_is_ambiguous,
            ambiguity_explanation=ambiguity_explanation,
            discovered_categories=discovered_categories,
            observed_combinations=observed_combinations,
            quality_report=quality_report,
            dynamic_presets=dynamic_presets,
            human_readable_summary=summary,
        )

    def profile_file(self, file_path: Union[str, Path]) -> DatasetProfile:
        """Inspect and profile a file path (CSV, Parquet, JSON)."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file '{file_path}' does not exist.")

        with open(path, "rb") as f:
            content_bytes = f.read()

        file_format = path.suffix.lower().lstrip(".")
        if file_format == "csv":
            df = pd.read_csv(io.BytesIO(content_bytes))
        elif file_format in ("parquet", "pq"):
            df = pd.read_parquet(io.BytesIO(content_bytes))
        elif file_format == "json":
            df = pd.read_json(io.BytesIO(content_bytes))
        else:
            # Fallback attempt as CSV
            try:
                df = pd.read_csv(io.BytesIO(content_bytes))
                file_format = "csv"
            except Exception as e:
                raise ValueError(f"Unsupported file format '{file_format}': {e}")

        return self.profile_dataframe(
            df=df,
            dataset_name=path.stem,
            file_format=file_format,
            content_bytes=content_bytes,
        )

    def _profile_column(
        self, series: pd.Series, col_name: str, total_rows: int
    ) -> Tuple[ColumnProfile, bool, float, str]:
        """Profile an individual column, determine statistics, and infer its semantic role."""
        name_lower = col_name.strip().lower()
        null_count = int(series.isnull().sum())
        null_pct = round((null_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))
        unique_pct = round((unique_count / total_rows * 100.0), 2) if total_rows > 0 else 0.0
        is_constant = unique_count <= 1

        dtype_str = str(series.dtype)
        is_numeric = pd.api.types.is_numeric_dtype(series)

        # 1. Check for Leakage risk
        is_leakage = False
        leakage_reason = None
        for lkw in LEAKAGE_KEYWORDS:
            if lkw in name_lower:
                is_leakage = True
                leakage_reason = f"Column name contains post-harvest/target leakage keyword '{lkw}'."
                break

        # 2. Check for Target candidacy
        is_target_candidate = False
        candidate_score = 0.0
        target_rationale = ""

        if is_numeric and not is_constant and not is_leakage:
            for tkw in TARGET_KEYWORDS:
                if tkw in name_lower:
                    is_target_candidate = True
                    candidate_score = 0.9 if tkw in ("yield", "tonnes_per_hectare", "t_ha") else 0.7
                    target_rationale = f"Numeric column matches target keyword '{tkw}'."
                    break

        # 3. Infer Role
        inferred_role = ColumnRole.NUMERICAL
        confidence = 0.8
        inferred_units: Optional[str] = None

        if is_leakage:
            inferred_role = ColumnRole.LEAKAGE
            confidence = 0.95
        elif any(gkw in name_lower for gkw in GEOGRAPHIC_KEYWORDS) and (
            not is_numeric or "district" in name_lower or "state" in name_lower or "region" in name_lower
        ):
            inferred_role = ColumnRole.GEOGRAPHIC
            confidence = 0.95
        elif any(dkw in name_lower for dkw in DATETIME_KEYWORDS):
            inferred_role = ColumnRole.DATETIME
            confidence = 0.9
        elif any(ikw in name_lower for ikw in IDENTIFIER_KEYWORDS) and unique_pct > 80.0:
            inferred_role = ColumnRole.IDENTIFIER
            confidence = 0.9
        elif not is_numeric or (unique_count <= 25 and unique_pct < 10.0):
            inferred_role = ColumnRole.CATEGORICAL
            confidence = 0.9
        else:
            inferred_role = ColumnRole.NUMERICAL
            confidence = 0.85

        # Infer units from column name
        if "t_ha" in name_lower or "tonnes_per_hectare" in name_lower:
            inferred_units = "t/ha"
        elif "kg_ha" in name_lower:
            inferred_units = "kg/ha"
        elif "rainfall" in name_lower or "precip" in name_lower or "_mm" in name_lower:
            inferred_units = "mm"
        elif "temp" in name_lower or "_c" in name_lower:
            inferred_units = "°C"
        elif "humidity" in name_lower or "_pct" in name_lower or "percent" in name_lower:
            inferred_units = "%"
        elif "radiation" in name_lower or "solar" in name_lower:
            inferred_units = "MJ/m²/day"
        elif "ph" in name_lower:
            inferred_units = "pH"
        elif "density" in name_lower:
            inferred_units = "g/cm³"
        elif "cec" in name_lower or "cation" in name_lower:
            inferred_units = "cmol(+)/kg"
        elif "days" in name_lower or "streak" in name_lower:
            inferred_units = "days"

        # Compute Numeric Stats if applicable
        num_stats = None
        if is_numeric and unique_count > 0:
            valid_s = series.dropna().astype(float)
            if len(valid_s) > 0:
                q25 = float(valid_s.quantile(0.25))
                q75 = float(valid_s.quantile(0.75))
                iqr = q75 - q25
                lower_bound = q25 - 1.5 * iqr
                upper_bound = q75 + 1.5 * iqr
                outliers = int(((valid_s < lower_bound) | (valid_s > upper_bound)).sum())

                num_stats = NumericStats(
                    min=round(float(valid_s.min()), 4),
                    max=round(float(valid_s.max()), 4),
                    mean=round(float(valid_s.mean()), 4),
                    std=round(float(valid_s.std()), 4) if len(valid_s) > 1 else 0.0,
                    p25=round(q25, 4),
                    p50=round(float(valid_s.median()), 4),
                    p75=round(q75, 4),
                    outlier_count_iqr=outliers,
                    zero_count=int((valid_s == 0).sum()),
                )

        # Compute Categorical Stats if applicable
        cat_stats = None
        if inferred_role in (ColumnRole.CATEGORICAL, ColumnRole.GEOGRAPHIC) or not is_numeric:
            val_counts = series.dropna().astype(str).value_counts()
            top_counts = {str(k): int(v) for k, v in val_counts.head(15).items()}
            rare_cats = [str(k) for k, v in val_counts.items() if v < 5]

            cat_stats = CategoricalStats(
                cardinality=unique_count,
                top_categories=top_counts,
                rare_categories=rare_cats,
            )

        col_profile = ColumnProfile(
            name=col_name,
            dtype=dtype_str,
            null_count=null_count,
            null_pct=null_pct,
            unique_count=unique_count,
            unique_pct=unique_pct,
            is_constant=is_constant,
            inferred_role=inferred_role,
            confidence_role=confidence,
            inferred_units=inferred_units,
            numeric_stats=num_stats,
            categorical_stats=cat_stats,
            is_leakage_risk=is_leakage,
            leakage_reason=leakage_reason,
        )

        return col_profile, is_target_candidate, candidate_score, target_rationale

    def _discover_category_combinations(
        self, df: pd.DataFrame, columns_profile: Dict[str, ColumnProfile]
    ) -> List[CategoryCombination]:
        """Discover and assess representation of paired categorical combinations."""
        combinations: List[CategoryCombination] = []

        # Find key categorical dimensions like crop, season, district
        cat_cols = [
            c for c, p in columns_profile.items()
            if p.inferred_role in (ColumnRole.CATEGORICAL, ColumnRole.GEOGRAPHIC)
            and p.unique_count <= 50
        ]

        # Prioritize pairs involving crop or district
        target_pairs: List[Tuple[str, str]] = []
        crop_col = next((c for c in cat_cols if "crop" in c.lower()), None)
        season_col = next((c for c in cat_cols if "season" in c.lower()), None)
        district_col = next((c for c in cat_cols if "district" in c.lower() or "region" in c.lower()), None)

        if crop_col and season_col:
            target_pairs.append((crop_col, season_col))
        if crop_col and district_col:
            target_pairs.append((crop_col, district_col))

        # If none of the specific names match, take first two categoricals
        if not target_pairs and len(cat_cols) >= 2:
            target_pairs.append((cat_cols[0], cat_cols[1]))

        for col_a, col_b in target_pairs:
            ct = pd.crosstab(df[col_a].astype(str), df[col_b].astype(str))
            for val_a in ct.index:
                for val_b in ct.columns:
                    count = int(ct.loc[val_a, val_b])
                    if count >= 20:
                        status = RepresentationSufficiency.WELL_REPRESENTED
                        supported = True
                        guidance = f"Well-represented with {count} observations; suitable for training."
                    elif count >= 5:
                        status = RepresentationSufficiency.SPARSE
                        supported = True
                        guidance = f"Sparse coverage ({count} observations); generalization may be limited."
                    elif count >= 1:
                        status = RepresentationSufficiency.INSUFFICIENT
                        supported = False
                        guidance = f"Insufficient data ({count} observations); high variance risk."
                    else:
                        status = RepresentationSufficiency.UNOBSERVED
                        supported = False
                        guidance = "Unobserved combination in dataset; requires exploratory handling."

                    combinations.append(
                        CategoryCombination(
                            feature_a=col_a,
                            value_a=val_a,
                            feature_b=col_b,
                            value_b=val_b,
                            observation_count=count,
                            representation_status=status,
                            is_supported_for_training=supported,
                            guidance=guidance,
                        )
                    )

        return combinations

    def _extract_dynamic_presets(
        self,
        df: pd.DataFrame,
        columns_profile: Dict[str, ColumnProfile],
        target_col: Optional[str],
        max_presets: int = 6,
    ) -> List[DynamicPresetSample]:
        """Extract representative illustrative presets directly from genuine dataset rows."""
        presets: List[DynamicPresetSample] = []
        if len(df) == 0:
            return presets

        crop_col = next((c for c in df.columns if "crop" in c.lower()), None)
        district_col = next((c for c in df.columns if "district" in c.lower()), None)

        # Select diverse representative indices
        selected_indices: List[int] = []

        if crop_col and district_col:
            grouped = df.groupby([crop_col, district_col], as_index=False)
            for _, group in grouped:
                if len(selected_indices) >= max_presets:
                    break
                # Pick median row of group if numeric columns exist
                mid_idx = group.index[len(group) // 2]
                selected_indices.append(int(mid_idx))
        else:
            step = max(1, len(df) // max_presets)
            selected_indices = [i for i in range(0, len(df), step)][:max_presets]

        for i, idx in enumerate(selected_indices):
            row = df.loc[idx]
            cat_summary = {}
            for col_name, prof in columns_profile.items():
                if prof.inferred_role in (ColumnRole.CATEGORICAL, ColumnRole.GEOGRAPHIC):
                    cat_summary[col_name] = str(row[col_name])

            sample_dict = {}
            for col_name, prof in columns_profile.items():
                if prof.inferred_role not in (ColumnRole.LEAKAGE, ColumnRole.IDENTIFIER, ColumnRole.TARGET):
                    val = row[col_name]
                    sample_dict[col_name] = None if pd.isna(val) else (int(val) if isinstance(val, (int, np.integer)) else float(val) if isinstance(val, (float, np.floating)) else str(val))

            target_val = None
            if target_col and target_col in row and not pd.isna(row[target_col]):
                target_val = round(float(row[target_col]), 4)

            crop_str = cat_summary.get(crop_col, "Observation") if crop_col else "Observation"
            dist_str = cat_summary.get(district_col, f"Row {idx}") if district_col else f"Row {idx}"

            preset = DynamicPresetSample(
                preset_id=f"preset_{i+1}_{crop_str.lower().replace(' ', '_')}_{dist_str.lower().replace(' ', '_')}",
                name=f"{dist_str} — {crop_str}",
                category_summary=cat_summary,
                description=f"Authentic observation from row index {idx} in {df.shape[0]}-record dataset.",
                sample_values=sample_dict,
                observed_target=target_val,
                source_row_index=idx,
            )
            presets.append(preset)

        return presets

    def _generate_markdown_summary(
        self,
        dataset_name: str,
        row_count: int,
        col_count: int,
        columns_profile: Dict[str, ColumnProfile],
        selected_target: Optional[str],
        target_candidates: List[str],
        target_is_ambiguous: bool,
        quality_report: DataQualityReport,
        discovered_categories: Dict[str, List[str]],
    ) -> str:
        """Generate human-readable Markdown documentation for the discovered dataset."""
        lines = [
            f"# Dataset Discovery Report: {dataset_name}",
            "",
            "## 1. General Overview",
            f"- **Dimensions:** {row_count:,} observations × {col_count} attributes",
            f"- **Data Quality Score:** {quality_report.quality_score_pct}%",
            f"- **Duplicate Observations:** {quality_report.duplicate_rows:,} rows ({quality_report.duplicate_rows_pct}%)",
            "",
            "## 2. Target Variable Identification",
        ]

        if selected_target:
            target_prof = columns_profile.get(selected_target)
            units_str = f" ({target_prof.inferred_units})" if target_prof and target_prof.inferred_units else ""
            lines.append(f"- **Selected Target:** `{selected_target}`{units_str}")
            if target_is_ambiguous:
                lines.append(f"> ⚠️ **Ambiguity Notice:** Multiple potential targets were found ({target_candidates}). Please confirm or override.")
        else:
            lines.append("- **Selected Target:** None identified. Manual specification required.")

        lines.extend([
            "",
            "## 3. Discovered Column Roles & Feature Types",
            "| Column Name | Inferred Role | Data Type | Null % | Unique | Units | Quality Notes |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for col_name, prof in columns_profile.items():
            units = prof.inferred_units or "—"
            notes = []
            if prof.is_constant:
                notes.append("Constant")
            if prof.null_pct > 30.0:
                notes.append("High Null")
            if prof.is_leakage_risk:
                notes.append(f"Leakage Risk ({prof.leakage_reason})")
            note_str = ", ".join(notes) if notes else "Valid"

            lines.append(
                f"| `{col_name}` | {prof.inferred_role.value} | `{prof.dtype}` | {prof.null_pct}% | {prof.unique_count:,} | {units} | {note_str} |"
            )

        if discovered_categories:
            lines.extend([
                "",
                "## 4. Discovered Categories",
            ])
            for cat_col, vals in discovered_categories.items():
                val_preview = ", ".join(vals[:10]) + ("..." if len(vals) > 10 else "")
                lines.append(f"- **`{cat_col}`** ({len(vals)} distinct): {val_preview}")

        if quality_report.warnings:
            lines.extend([
                "",
                "## 5. Data Governance & Hygiene Warnings",
            ])
            for w in quality_report.warnings:
                lines.append(f"- ⚠️ {w}")

        return "\n".join(lines)
