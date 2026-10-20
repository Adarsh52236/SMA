"""Data validation and integrity auditing engine."""

from typing import Dict, Any, List
import pandas as pd


class DataValidationService:
    """Performs rigorous integrity checks on aligned agricultural datasets."""

    def validate_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate physical boundaries, schema completeness, and consistency."""
        issues: List[str] = []
        warnings: List[str] = []

        if df.empty:
            return {
                "is_valid": False,
                "issues": ["Dataset is empty."],
                "warnings": [],
                "summary": {},
            }

        # 1. Null value audit
        null_counts = df.isnull().sum().to_dict()
        for col, count in null_counts.items():
            if count > 0:
                issues.append(f"Column '{col}' has {count} missing values.")

        # 2. Key uniqueness
        dup_keys = df.duplicated(subset=["state", "district", "crop", "season", "year"]).sum()
        if dup_keys > 0:
            issues.append(f"Found {dup_keys} duplicate observation keys.")

        # 3. Target yield validation
        if (df["yield_t_ha"] <= 0).any():
            issues.append("Found non-positive crop yield values (<= 0 t/ha).")

        # 4. Physical soil bounds
        if ((df["soil_ph"] < 3.5) | (df["soil_ph"] > 10.0)).any():
            issues.append("Soil pH out of physical bounds [3.5, 10.0].")

        if ((df["organic_carbon_pct"] < 0.0) | (df["organic_carbon_pct"] > 10.0)).any():
            issues.append("Soil organic carbon out of bounds [0.0%, 10.0%].")

        texture_sum = df["clay_pct"] + df["sand_pct"]
        if (texture_sum > 100.1).any():
            issues.append("Soil clay + sand sum exceeds 100%.")

        if ((df["bulk_density_g_cm3"] < 0.8) | (df["bulk_density_g_cm3"] > 2.2)).any():
            issues.append("Bulk density out of bounds [0.8, 2.2 g/cm³].")

        # 5. Meteorological bounds
        if (df["cumulative_rainfall_mm"] < 0.0).any():
            issues.append("Negative precipitation values detected.")

        if (df["mean_temp_min_c"] > df["mean_temp_max_c"]).any():
            issues.append("Mean minimum temperature exceeds maximum temperature.")

        if ((df["mean_relative_humidity_pct"] < 0.0) | (df["mean_relative_humidity_pct"] > 100.0)).any():
            issues.append("Relative humidity out of bounds [0%, 100%].")

        # Extreme yield checks (warnings for domain review, not fatal errors)
        low_yields = (df["yield_t_ha"] < 0.20).sum()
        if low_yields > 0:
            warnings.append(f"{low_yields} observations have yield < 0.20 t/ha (drought/pest impact).")

        high_yields = (df["yield_t_ha"] > 3.50).sum()
        if high_yields > 0:
            warnings.append(f"{high_yields} observations have yield > 3.50 t/ha (high production outlier).")

        summary = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "districts_count": df["district"].nunique(),
            "years_count": df["year"].nunique(),
            "mean_yield_t_ha": round(float(df["yield_t_ha"].mean()), 3),
            "min_yield_t_ha": round(float(df["yield_t_ha"].min()), 3),
            "max_yield_t_ha": round(float(df["yield_t_ha"].max()), 3),
            "mean_rainfall_mm": round(float(df["cumulative_rainfall_mm"].mean()), 2),
            "mean_temp_max_c": round(float(df["mean_temp_max_c"].mean()), 2),
            "null_counts": null_counts,
        }

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "summary": summary,
        }
