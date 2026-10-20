"""Unit tests for Phase 2 Data Pipeline, Ingestion, Normalization, Alignment, and Validation.

All tests utilize isolated, mocked test fixtures to ensure fast, deterministic,
offline execution without reliance on external live services.
"""

import os
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from app.data.config import DataPipelineConfig
from app.data.districts import get_district_by_name, MAHARASHTRA_DISTRICTS
from app.data.schemas import NormalizedYieldRecord, SeasonalWeatherRecord, DistrictSoilProfile
from app.data.yield_ingestion import YieldIngestionService
from app.data.weather_ingestion import WeatherIngestionService
from app.data.soil_ingestion import SoilIngestionService
from app.data.alignment import DatasetAlignmentService
from app.data.validation import DataValidationService
from app.data.quality_report import QualityReportGenerator


@pytest.fixture
def test_config(tmp_path):
    """Temporary isolated configuration fixture."""
    return DataPipelineConfig(
        PROJECT_ROOT=str(tmp_path),
        RAW_DATA_DIR=str(tmp_path / "raw"),
        INTERIM_DATA_DIR=str(tmp_path / "interim"),
        PROCESSED_DATA_DIR=str(tmp_path / "processed"),
        REPORTS_DIR=str(tmp_path / "reports"),
    )


# --- 1. District Registry and Alias Tests ---

def test_district_lookup_and_aliases():
    """Verify that canonical names and historical aliases map properly."""
    # Canonical lookup
    latur = get_district_by_name("Latur")
    assert latur is not None
    assert latur.canonical_name == "Latur"

    # Alias lookup (historical ICRISAT spelling for Amravati)
    amravati = get_district_by_name("Amarawati")
    assert amravati is not None
    assert amravati.canonical_name == "Amravati"

    # Alias lookup for Nashik / Nasik
    nashik = get_district_by_name("Nasik")
    assert nashik is not None
    assert nashik.canonical_name == "Nashik"

    # Alias lookup for Yavatmal / Yeotmal
    yavatmal = get_district_by_name("Yeotmal")
    assert yavatmal is not None
    assert yavatmal.canonical_name == "Yavatmal"

    # Unknown district
    unknown = get_district_by_name("NonExistentDistrict")
    assert unknown is None


# --- 2. Yield Ingestion, Normalization, and Deduplication Tests ---

def test_yield_calculation_and_unit_conversion(test_config, tmp_path):
    """Verify that yield is correctly computed as production / area in t/ha."""
    svc = YieldIngestionService(test_config)

    # In ICRISAT DLD: Area is in 1000 ha, Production in 1000 tons.
    # 250.0 (1000 tons) / 200.0 (1000 ha) = 1.25 t/ha
    dummy_csv = tmp_path / "dummy_crop.csv"
    dummy_csv.write_text(
        "Year,Dist Name,Crop,Area(1000 ha),Production(1000 tons),Yield(Kg per ha)\n"
        "2015,Nagpur,SOYABEAN,200.0,250.0,1250.0\n"
    )

    df_cleaned, meta = svc.process_records(
        raw_file_path=str(dummy_csv),
        crop="Soybean",
        min_year=2015,
        max_year=2015,
    )

    assert len(df_cleaned) == 1
    row = df_cleaned.iloc[0]
    assert row["district"] == "Nagpur"
    assert row["reported_area_ha"] == 200000.0
    assert row["reported_production_tonnes"] == 250000.0
    assert row["yield_t_ha"] == 1.25
    assert meta["duplicate_rows_removed"] == 0


def test_duplicate_removal_in_yield_data(test_config, tmp_path):
    """Verify that identical duplicate rows are identified and deduplicated."""
    svc = YieldIngestionService(test_config)

    dummy_csv = tmp_path / "duplicate_crop.csv"
    dummy_csv.write_text(
        "Year,Dist Name,Crop,Area(1000 ha),Production(1000 tons),Yield(Kg per ha)\n"
        "2014,Akola,SOYABEAN,150.0,180.0,1200.0\n"
        "2014,Akola,SOYABEAN,150.0,180.0,1200.0\n"  # Exact duplicate
    )

    df_cleaned, meta = svc.process_records(
        raw_file_path=str(dummy_csv),
        crop="Soybean",
        min_year=2014,
        max_year=2014,
    )

    assert len(df_cleaned) == 1
    assert meta["duplicate_rows_removed"] == 1


def test_invalid_zero_negative_area_handling(test_config, tmp_path):
    """Verify that observations with zero or negative area are filtered safely."""
    svc = YieldIngestionService(test_config)

    dummy_csv = tmp_path / "zero_area_crop.csv"
    dummy_csv.write_text(
        "Year,Dist Name,Crop,Area(1000 ha),Production(1000 tons),Yield(Kg per ha)\n"
        "2010,Wardha,SOYABEAN,0.0,0.0,0.0\n"
        "2011,Wardha,SOYABEAN,-5.0,0.0,0.0\n"
        "2012,Wardha,SOYABEAN,100.0,110.0,1100.0\n"
    )

    df_cleaned, meta = svc.process_records(
        raw_file_path=str(dummy_csv),
        crop="Soybean",
        min_year=2010,
        max_year=2012,
    )

    assert len(df_cleaned) == 1
    assert df_cleaned.iloc[0]["year"] == 2012
    assert meta["zero_or_negative_area_omitted"] == 2


# --- 3. Weather Aggregation & Missing Day Checks ---

def test_kharif_weather_aggregation(test_config):
    """Verify daily meteorological series aggregates properly over Kharif dates."""
    svc = WeatherIngestionService(test_config)

    # Synthetic daily weather dictionary matching NASA POWER schema
    dates = ["20160601", "20160602", "20160603"]
    mock_json = {
        "properties": {
            "parameter": {
                "PRECTOTCORR": {"20160601": 15.0, "20160602": 25.0, "20160603": 0.0},
                "T2M_MAX": {"20160601": 34.0, "20160602": 36.0, "20160603": 33.0},
                "T2M_MIN": {"20160601": 22.0, "20160602": 24.0, "20160603": 23.0},
                "ALLSKY_SFC_SW_DWN": {"20160601": 18.0, "20160602": 20.0, "20160603": 22.0},
                "RH2M": {"20160601": 75.0, "20160602": 80.0, "20160603": 70.0},
            }
        }
    }

    # Custom short window test
    test_config.KHARIF_START_MONTH_DAY = "06-01"
    test_config.KHARIF_END_MONTH_DAY = "06-03"

    recs = svc.aggregate_kharif_season("Latur", mock_json, start_year=2016, end_year=2016)
    assert len(recs) == 1
    r = recs[0]
    assert r.district == "Latur"
    assert r.year == 2016
    assert r.cumulative_rainfall_mm == 40.0  # 15 + 25 + 0
    assert r.mean_temp_max_c == round((34 + 36 + 33) / 3, 2)
    assert r.heat_stress_days == 1  # 36.0 >= 35.0
    assert r.missing_days == 0


def test_weather_missing_days_handling(test_config):
    """Verify that nodata flags (-999.0) in NASA POWER are tracked and excluded from means."""
    svc = WeatherIngestionService(test_config)

    mock_json = {
        "properties": {
            "parameter": {
                "PRECTOTCORR": {"20150601": 10.0, "20150602": -999.0},
                "T2M_MAX": {"20150601": 32.0, "20150602": -999.0},
                "T2M_MIN": {"20150601": 21.0, "20150602": -999.0},
                "ALLSKY_SFC_SW_DWN": {"20150601": 19.0, "20150602": -999.0},
                "RH2M": {"20150601": 70.0, "20150602": -999.0},
            }
        }
    }

    test_config.KHARIF_START_MONTH_DAY = "06-01"
    test_config.KHARIF_END_MONTH_DAY = "06-02"

    recs = svc.aggregate_kharif_season("Nanded", mock_json, start_year=2015, end_year=2015)
    assert len(recs) == 1
    r = recs[0]
    assert r.missing_days == 1
    assert r.cumulative_rainfall_mm == 10.0
    assert r.mean_temp_max_c == 32.0


# --- 4. SoilGrids Unit Conversions & Depth Weighting Tests ---

def test_soil_unit_conversions_and_depth_weighting(test_config):
    """Verify topsoil depth weighted mean calculation and unit conversions."""
    svc = SoilIngestionService(test_config)

    mock_soil_json = {
        "properties": {
            "layers": [
                {
                    "name": "phh2o",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 70.0}},
                        {"label": "5-15cm", "values": {"mean": 73.0}},
                        {"label": "15-30cm", "values": {"mean": 76.0}},
                    ],
                },
                {
                    "name": "clay",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 400.0}},
                        {"label": "5-15cm", "values": {"mean": 420.0}},
                        {"label": "15-30cm", "values": {"mean": 440.0}},
                    ],
                },
                {
                    "name": "sand",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 250.0}},
                        {"label": "5-15cm", "values": {"mean": 240.0}},
                        {"label": "15-30cm", "values": {"mean": 230.0}},
                    ],
                },
                {
                    "name": "silt",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 350.0}},
                        {"label": "5-15cm", "values": {"mean": 340.0}},
                        {"label": "15-30cm", "values": {"mean": 330.0}},
                    ],
                },
                {
                    "name": "soc",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 100.0}},
                        {"label": "5-15cm", "values": {"mean": 80.0}},
                        {"label": "15-30cm", "values": {"mean": 60.0}},
                    ],
                },
                {
                    "name": "bdod",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 130.0}},
                        {"label": "5-15cm", "values": {"mean": 135.0}},
                        {"label": "15-30cm", "values": {"mean": 140.0}},
                    ],
                },
                {
                    "name": "cec",
                    "depths": [
                        {"label": "0-5cm", "values": {"mean": 360.0}},
                        {"label": "5-15cm", "values": {"mean": 370.0}},
                        {"label": "15-30cm", "values": {"mean": 380.0}},
                    ],
                },
            ]
        }
    }

    profile = svc.calculate_topsoil_weighted_mean(
        district_name="Latur",
        soil_json=mock_soil_json,
        lon=76.60,
        lat=18.35,
    )

    # pH: (70*5 + 73*10 + 76*15) / 30 = 74.0 -> /10 = 7.4
    assert profile.soil_ph == 7.4
    # Texture fractions sum to 100%
    assert round(profile.clay_pct + profile.sand_pct + profile.silt_pct, 1) == 100.0
    assert profile.bulk_density_g_cm3 > 1.0


# --- 5. Dataset Alignment & Cardinality Tests ---

def test_dataset_alignment_cardinality(test_config):
    """Verify alignment preserves 1-to-1 cardinality and handles missing keys."""
    alignment_svc = DatasetAlignmentService(test_config)

    df_yield = pd.DataFrame([
        {"district": "Latur", "crop": "Soybean", "season": "Kharif", "year": 2015, "yield_t_ha": 1.2, "reported_area_ha": 1000.0, "reported_production_tonnes": 1200.0, "source": "TEST", "quality_flags": []},
        {"district": "Akola", "crop": "Soybean", "season": "Kharif", "year": 2015, "yield_t_ha": 1.4, "reported_area_ha": 2000.0, "reported_production_tonnes": 2800.0, "source": "TEST", "quality_flags": []},
    ])

    df_weather = pd.DataFrame([
        {"district": "Latur", "year": 2015, "season": "Kharif", "cumulative_rainfall_mm": 800.0, "mean_temp_max_c": 31.5, "mean_temp_min_c": 22.0, "mean_solar_radiation_mj_m2": 18.0, "mean_relative_humidity_pct": 75.0, "consecutive_dry_days_max": 7, "heat_stress_days": 2},
        {"district": "Akola", "year": 2015, "season": "Kharif", "cumulative_rainfall_mm": 750.0, "mean_temp_max_c": 32.0, "mean_temp_min_c": 22.5, "mean_solar_radiation_mj_m2": 18.5, "mean_relative_humidity_pct": 74.0, "consecutive_dry_days_max": 8, "heat_stress_days": 3},
    ])

    df_soil = pd.DataFrame([
        {"district": "Latur", "soil_ph": 7.2, "organic_carbon_pct": 0.65, "clay_pct": 42.0, "sand_pct": 25.0, "silt_pct": 33.0, "bulk_density_g_cm3": 1.35, "cation_exchange_capacity_cmol_kg": 38.5},
        {"district": "Akola", "soil_ph": 7.3, "organic_carbon_pct": 0.70, "clay_pct": 45.0, "sand_pct": 22.0, "silt_pct": 33.0, "bulk_density_g_cm3": 1.32, "cation_exchange_capacity_cmol_kg": 40.0},
    ])

    df_final, meta = alignment_svc.align_datasets(df_yield, df_weather, df_soil)
    assert len(df_final) == 2
    assert meta["final_aligned_rows"] == 2
    assert "yield_t_ha" in df_final.columns
    assert "cumulative_rainfall_mm" in df_final.columns
    assert "soil_ph" in df_final.columns


def test_prevention_of_target_leakage(test_config):
    """Verify that predictor columns do not include target-derived features."""
    alignment_svc = DatasetAlignmentService(test_config)

    df_yield = pd.DataFrame([
        {"district": "Latur", "crop": "Soybean", "season": "Kharif", "year": 2015, "yield_t_ha": 1.2, "reported_area_ha": 1000.0, "reported_production_tonnes": 1200.0, "source": "TEST", "quality_flags": []},
    ])
    df_weather = pd.DataFrame([
        {"district": "Latur", "year": 2015, "season": "Kharif", "cumulative_rainfall_mm": 800.0, "mean_temp_max_c": 31.5, "mean_temp_min_c": 22.0, "mean_solar_radiation_mj_m2": 18.0, "mean_relative_humidity_pct": 75.0, "consecutive_dry_days_max": 7, "heat_stress_days": 2},
    ])
    df_soil = pd.DataFrame([
        {"district": "Latur", "soil_ph": 7.2, "organic_carbon_pct": 0.65, "clay_pct": 42.0, "sand_pct": 25.0, "silt_pct": 33.0, "bulk_density_g_cm3": 1.35, "cation_exchange_capacity_cmol_kg": 38.5},
    ])

    df_final, meta = alignment_svc.align_datasets(df_yield, df_weather, df_soil)
    assert "reported_area_ha" in meta["prevented_leakage"]
    assert "reported_production_tonnes" in meta["prevented_leakage"]


# --- 6. Data Validation Service Tests ---

def test_data_validation_service():
    """Verify data validation catches range and consistency violations."""
    validator = DataValidationService()

    valid_df = pd.DataFrame([{
        "state": "Maharashtra",
        "district": "Latur",
        "crop": "Soybean",
        "season": "Kharif",
        "year": 2015,
        "yield_t_ha": 1.25,
        "reported_area_ha": 1000.0,
        "reported_production_tonnes": 1250.0,
        "cumulative_rainfall_mm": 850.0,
        "mean_temp_max_c": 31.0,
        "mean_temp_min_c": 22.0,
        "mean_solar_radiation_mj_m2": 18.0,
        "mean_relative_humidity_pct": 75.0,
        "consecutive_dry_days_max": 6,
        "heat_stress_days": 1,
        "soil_ph": 7.2,
        "organic_carbon_pct": 0.65,
        "clay_pct": 42.0,
        "sand_pct": 25.0,
        "silt_pct": 33.0,
        "bulk_density_g_cm3": 1.35,
        "cation_exchange_capacity_cmol_kg": 38.5,
        "yield_source": "TEST",
        "quality_flags": [],
    }])

    res = validator.validate_dataset(valid_df)
    assert res["is_valid"] is True
    assert len(res["issues"]) == 0

    # Corrupt with invalid pH and inverted temperatures
    invalid_df = valid_df.copy()
    invalid_df["soil_ph"] = 14.0
    invalid_df["mean_temp_min_c"] = 40.0
    invalid_df["mean_temp_max_c"] = 30.0

    bad_res = validator.validate_dataset(invalid_df)
    assert bad_res["is_valid"] is False
    assert any("Soil pH out of physical bounds" in s for s in bad_res["issues"])
    assert any("minimum temperature exceeds maximum" in s for s in bad_res["issues"])
