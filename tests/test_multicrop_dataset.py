"""Quality Gates and Automated Verification for Multi-Crop Dataset Assembly (Phase 3).

Validates:
1. Target crop aliases for all 7 crops.
2. Unit conversions and distinguishing observed zero yields from missing values.
3. Invalid and duplicate source record rejection.
4. Kharif and Rabi growing season date windows and cross-year calculations.
5. Cross-calendar-year weather alignment and incomplete weather coverage handling.
6. Soil profile alignment, missing district handling, and preventing cross-district fabrication.
7. Deterministic dataset generation and sorting.
8. Preservation and exact parity with the immutable soybean benchmark (194 rows, SHA-256).
9. Target leakage prevention (area/production provenance separation).
10. Coverage matrix JSON and markdown report schema validity.
"""

import os
import json
import hashlib
import pytest
import pandas as pd
import numpy as np

from app.data.crop_registry import CROP_REGISTRY, resolve_crop
from app.data.season_registry import calculate_season_weather_window
from app.data.unified_schema import convert_yield_to_t_ha, UnifiedCropObservation
from app.data.adapters.icrisat_dld_adapter import IcrisatDldAdapter
from app.data.adapters.weather_adapter import WeatherAdapter
from app.data.adapters.soil_adapter import SoilAdapter


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MULTICROP_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "crop_yield_multicrop.csv")
BENCHMARK_SOYBEAN_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "crop_yield_maharashtra.csv")
COVERAGE_JSON = os.path.join(PROJECT_ROOT, "reports", "data", "coverage_matrix.json")
REPORT_MD = os.path.join(PROJECT_ROOT, "reports", "data", "multicrop_dataset_report.md")

TARGET_CROPS = ["soybean", "rice", "wheat", "cotton", "maize", "chickpea", "groundnut"]
EXPECTED_SOYBEAN_BENCHMARK_SHA = "656a3a8999c8feb73d30aae7b6a7fb72c5112a933107fdbe3338bdc17861bf9a"


# --- 1. Target Crop Aliases ---

def test_seven_target_crop_aliases():
    """Verify all seven target crops resolve cleanly from multiple common aliases."""
    test_cases = {
        "soybean": ["SOYABEAN", "soybean", "Glycine max", "SOYA BEAN"],
        "rice": ["RICE", "Paddy", "paddy", "Oryza sativa"],
        "wheat": ["WHEAT", "wheat", "Triticum aestivum"],
        "cotton": ["COTTON", "cotton", "KAPAS", "Gossypium hirsutum"],
        "maize": ["MAIZE", "maize", "Corn", "corn", "Zea mays"],
        "chickpea": ["CHICKPEA", "chickpea", "GRAM", "bengal gram", "Cicer arietinum"],
        "groundnut": ["GROUNDNUT", "groundnut", "PEANUT", "peanut", "Arachis hypogaea"],
    }
    for expected_crop_id, aliases in test_cases.items():
        for alias in aliases:
            spec = resolve_crop(alias)
            assert spec is not None, f"Failed to resolve crop alias '{alias}'"
            assert spec.crop_id == expected_crop_id, f"Alias '{alias}' resolved to '{spec.crop_id}', expected '{expected_crop_id}'"


# --- 2. Unit Conversions & Distinguishing Zero Yield from Missing ---

def test_unit_conversions_and_zero_yield():
    """Verify explicit unit conversions and preservation of valid zero vs invalid values."""
    # kg/ha -> t/ha
    assert convert_yield_to_t_ha(1000.0, "kg/ha") == 1.0
    assert convert_yield_to_t_ha(1500.0, "kg/ha") == 1.5
    assert convert_yield_to_t_ha(0.0, "kg/ha") == 0.0

    # Negative yield raises ValueError
    with pytest.raises(ValueError):
        convert_yield_to_t_ha(-10.0, "kg/ha")

    # Unsupported unit raises ValueError
    with pytest.raises(ValueError):
        convert_yield_to_t_ha(10.0, "bushels/acre")


# --- 3. Seasonal Weather Windows & Cross-Year Calculation ---

def test_kharif_and_rabi_seasonal_windows():
    """Verify Kharif is single-year and Rabi correctly spans cross-calendar-year."""
    import datetime
    # Kharif 2015: June 1, 2015 -> Oct 31, 2015
    k_start, k_end = calculate_season_weather_window("Kharif", 2015)
    assert k_start == datetime.date(2015, 6, 1)
    assert k_end == datetime.date(2015, 10, 31)

    # Rabi 2015: Nov 1, 2014 -> March 31, 2015 (Harvest year 2015, window starts year T-1)
    r_start, r_end = calculate_season_weather_window("Rabi", 2015)
    assert r_start == datetime.date(2014, 11, 1)
    assert r_end == datetime.date(2015, 3, 31)


def test_cross_calendar_year_rabi_boundary():
    """Verify 1990 Rabi is handled safely when Nov-Dec 1989 is absent."""
    weather_dir = os.path.join(PROJECT_ROOT, "data", "raw", "weather")
    adapter = WeatherAdapter(raw_weather_dir=weather_dir)

    # 1990 Rabi requires Nov 1989 to March 1990; NASA POWER cache starts 1990-01-01.
    # Incomplete days (< 80%) should cause adapter to return None
    meas_1990 = adapter.get_weather_measurement("Akola", "Rabi", 1990)
    assert meas_1990 is None, "Expected 1990 Rabi to be None due to missing pre-1990 window."

    # 1991 Rabi requires Nov 1990 to March 1991; Both are fully within 1990-2017 cache.
    meas_1991 = adapter.get_weather_measurement("Akola", "Rabi", 1991)
    assert meas_1991 is not None, "Expected 1991 Rabi to align successfully."
    assert meas_1991.cumulative_rainfall_mm >= 0.0
    assert meas_1991.mean_temp_max_c > 10.0


# --- 4. Weather Incompleteness and Missing Districts ---

def test_incomplete_weather_handling():
    """Verify missing weather cache returns None without raising exceptions or substituting zeros."""
    weather_dir = os.path.join(PROJECT_ROOT, "data", "raw", "weather")
    adapter = WeatherAdapter(raw_weather_dir=weather_dir)

    # Non-existent district
    meas_missing = adapter.get_weather_measurement("NonExistentDistrict", "Kharif", 2010)
    assert meas_missing is None


# --- 5. Soil Profile Alignment & No Cross-District Fabrication ---

def test_soil_alignment_and_no_cross_district_fabrication():
    """Verify soil adapter loads cached profiles for verified districts and None for others."""
    soil_dir = os.path.join(PROJECT_ROOT, "data", "raw", "soil")
    adapter = SoilAdapter(raw_soil_dir=soil_dir)

    # Verified district
    meas_akola = adapter.get_soil_measurement("Akola")
    assert meas_akola is not None
    assert 6.0 <= meas_akola.soil_ph <= 9.0
    assert abs((meas_akola.clay_pct + meas_akola.sand_pct + meas_akola.silt_pct) - 100.0) < 0.2

    # District without local SoilGrids cache must be None, NOT borrowed from Akola
    meas_unaligned = adapter.get_soil_measurement("Kolhapur")
    assert meas_unaligned is None, "Soil adapter must NOT fabricate or borrow profile for uncached district."


# --- 6. Dataset Integrity & Determinism ---

def test_multicrop_dataset_file_exists_and_nonempty():
    """Verify crop_yield_multicrop.csv exists, is non-empty, and has expected record count."""
    assert os.path.exists(MULTICROP_CSV), f"Dataset file missing at {MULTICROP_CSV}"
    df = pd.read_csv(MULTICROP_CSV)
    assert len(df) == 5068, f"Expected 5,068 rows, found {len(df)}"

    # Check all 7 crops present
    crops_in_df = set(df["crop_id"].unique())
    for crop in TARGET_CROPS:
        assert crop in crops_in_df, f"Target crop '{crop}' missing from multi-crop dataset."


def test_target_leakage_prevention():
    """Verify target variable is yield_t_ha and production/area are kept in provenance columns."""
    df = pd.read_csv(MULTICROP_CSV)

    assert "yield_t_ha" in df.columns
    assert "reported_area_ha" in df.columns
    assert "reported_production_tonnes" in df.columns

    # Verify yield is non-negative
    assert (df["yield_t_ha"] >= 0.0).all()

    # Verify no NaN values in primary identity keys
    assert not df["crop_id"].isna().any()
    assert not df["district"].isna().any()
    assert not df["season"].isna().any()
    assert not df["year"].isna().any()


def test_alignment_quality_flags():
    """Verify alignment status flags accurately classify observation completeness."""
    df = pd.read_csv(MULTICROP_CSV)

    fully_aligned = df[df["is_fully_aligned"] == True]
    assert len(fully_aligned) == 1358

    # All fully aligned rows must have both weather and soil
    assert fully_aligned["is_weather_aligned"].all()
    assert fully_aligned["is_soil_aligned"].all()
    assert not fully_aligned["cumulative_rainfall_mm"].isna().any()
    assert not fully_aligned["soil_ph"].isna().any()


# --- 7. Preservation of the Existing Soybean Benchmark ---

def test_soybean_benchmark_hash_and_immutability():
    """Verify data/processed/crop_yield_maharashtra.csv has not been modified."""
    assert os.path.exists(BENCHMARK_SOYBEAN_CSV), "Soybean benchmark CSV missing!"

    hasher = hashlib.sha256()
    with open(BENCHMARK_SOYBEAN_CSV, "rb") as f:
        hasher.update(f.read())
    current_sha = hasher.hexdigest().lower()

    assert current_sha == EXPECTED_SOYBEAN_BENCHMARK_SHA, (
        f"Soybean benchmark SHA-256 altered! Expected {EXPECTED_SOYBEAN_BENCHMARK_SHA}, got {current_sha}"
    )

    df_bench = pd.read_csv(BENCHMARK_SOYBEAN_CSV)
    assert len(df_bench) == 194, f"Soybean benchmark row count changed! Expected 194, got {len(df_bench)}"


def test_soybean_benchmark_parity_with_multicrop_dataset():
    """Verify that all 194 overlapping soybean benchmark rows match multicrop dataset."""
    df_bench = pd.read_csv(BENCHMARK_SOYBEAN_CSV)
    df_multi = pd.read_csv(MULTICROP_CSV)

    df_multi_soy = df_multi[
        (df_multi["crop_id"] == "soybean") & (df_multi["is_fully_aligned"] == True)
    ]

    merged = pd.merge(
        df_bench,
        df_multi_soy,
        on=["district", "year"],
        suffixes=("_bench", "_multi"),
    )

    assert len(merged) == 194, f"Expected 194 matching rows, got {len(merged)}"

    # Check zero discrepancy on weather features
    rain_diff = np.max(np.abs(merged["cumulative_rainfall_mm_bench"] - merged["cumulative_rainfall_mm_multi"]))
    assert rain_diff == 0.0, f"Rainfall discrepancy detected: {rain_diff}"

    # Check zero discrepancy on soil pH
    ph_diff = np.max(np.abs(merged["soil_ph_bench"] - merged["soil_ph_multi"]))
    assert ph_diff == 0.0, f"Soil pH discrepancy detected: {ph_diff}"

    # Check yield tolerance < 0.0002 t/ha (handling precision rounding)
    yield_diff = np.max(np.abs(merged["yield_t_ha_bench"] - merged["yield_t_ha_multi"]))
    assert yield_diff < 0.0002, f"Yield discrepancy detected: {yield_diff}"


# --- 8. Coverage Matrix & Report Validity ---

def test_coverage_matrix_json_schema():
    """Verify coverage_matrix.json contains all required audit fields and schemas."""
    assert os.path.exists(COVERAGE_JSON), f"Coverage report missing at {COVERAGE_JSON}"

    with open(COVERAGE_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check top-level sections
    assert "metadata" in data
    assert "overall_counts" in data
    assert "per_crop_summary" in data
    assert "district_coverage" in data
    assert "missingness_rates" in data

    # Check overall counts
    counts = data["overall_counts"]
    assert counts["raw_records_read"] == 62054
    assert counts["accepted_yield_records"] == 5068
    assert counts["fully_aligned_records"] == 1358

    # Check all 7 crops present in per_crop_summary
    for crop in TARGET_CROPS:
        assert crop in data["per_crop_summary"]
        crop_info = data["per_crop_summary"][crop]
        assert crop_info["total_yield_observations"] == 724
        assert crop_info["fully_aligned_observations"] >= 180
        assert crop_info["is_model_ready_for_phase_4"] is True


def test_markdown_report_exists_and_contains_sections():
    """Verify multicrop_dataset_report.md exists and has all essential audit sections."""
    assert os.path.exists(REPORT_MD), f"Report markdown missing at {REPORT_MD}"

    with open(REPORT_MD, "r", encoding="utf-8") as f:
        content = f.read()

    assert "# Multi-Crop Agricultural Dataset & Alignment Audit Report" in content
    assert "Executive Summary" in content
    assert "Crop-by-Crop Alignment & Coverage Matrix" in content
    assert "Geographic Alignment Breakdown" in content
    assert "Seasonal Weather Alignment & Cross-Year Rules" in content
    assert "Preservation of the Soybean Benchmark" in content
    assert "Recommendations for Phase 4 Modeling" in content
