"""Comprehensive Phase 6 Tests: Dynamic Discovery, Adaptive Training & Coverage-Aware Intelligence.

Validates that the system:
1. Discovers schemas from arbitrary tabular datasets without hardcoded assumptions.
2. Identifies new crops, districts, and categorical/numeric features dynamically.
3. Flags data leakage, ambiguous targets, duplicate observations, and constant columns.
4. Trains adaptive model candidates (baselines, regularized linear, non-linear ensembles)
   with chronological/spatial validation and zero leakage.
5. Serves predictions under conservative vs exploratory policies, detecting out-of-distribution
   features and generating dynamic qualitative labels.
6. Preserves full backward-compatibility for legacy soybean requests.
"""

import io
import json
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.discovery.engine import DatasetDiscoveryEngine
from app.discovery.schemas import ColumnRole, RepresentationSufficiency
from app.ml.adaptive.pipeline import AdaptiveMLPipeline
from app.ml.adaptive.models import GlobalMeanBaseline, GroupMeanBaseline
from app.ml.adaptive.evaluator import calculate_metrics, split_chronological

@pytest.fixture(scope="module")
def client():
    """Yield a TestClient initialized within the FastAPI lifespan context."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Dataset Discovery Engine Tests
# ---------------------------------------------------------------------------

def test_discovery_engine_detects_new_crop_and_new_district():
    """Verify discovery engine discovers previously unseen crops (e.g. Sorghum) and districts (e.g. Nagpur)."""
    df = pd.DataFrame({
        "crop_name": ["Sorghum", "Sorghum", "Sunflower", "Sunflower", "Sorghum"],
        "district_region": ["Nagpur", "Nagpur", "Kolhapur", "Kolhapur", "Nagpur"],
        "harvest_year": [2018, 2019, 2018, 2019, 2020],
        "rainfall_mm": [820.0, 910.0, 750.0, 780.0, 860.0],
        "temperature_c": [31.5, 32.0, 30.5, 31.0, 32.5],
        "grain_yield_t_ha": [1.45, 1.62, 1.10, 1.25, 1.55],
    })

    engine = DatasetDiscoveryEngine()
    profile = engine.profile_dataframe(df, dataset_name="novel_agriculture")

    assert profile.selected_target == "grain_yield_t_ha"
    assert profile.columns["grain_yield_t_ha"].inferred_role == ColumnRole.TARGET
    assert "Sorghum" in profile.discovered_categories["crop_name"]
    assert "Sunflower" in profile.discovered_categories["crop_name"]
    assert "Nagpur" in profile.discovered_categories["district_region"]
    assert "Kolhapur" in profile.discovered_categories["district_region"]
    assert profile.columns["rainfall_mm"].inferred_role == ColumnRole.NUMERICAL
    assert profile.columns["rainfall_mm"].inferred_units == "mm"


def test_discovery_engine_flags_ambiguous_targets():
    """Verify that multiple potential target columns trigger ambiguity flags rather than silent guessing."""
    df = pd.DataFrame({
        "crop": ["Rice", "Rice", "Rice"],
        "district": ["Bhandara", "Bhandara", "Bhandara"],
        "year": [2015, 2016, 2017],
        "harvest_yield": [1.8, 1.9, 1.7],
        "production_per_hectare": [1.8, 1.9, 1.7],
    })

    engine = DatasetDiscoveryEngine()
    profile = engine.profile_dataframe(df, dataset_name="ambiguous_targets")

    assert profile.target_is_ambiguous is True
    assert len(profile.target_candidates) >= 2
    assert profile.ambiguity_explanation is not None


def test_discovery_engine_detects_leakage_columns():
    """Verify post-outcome variables (e.g. reported_production_tonnes) are detected as leakage."""
    df = pd.DataFrame({
        "crop": ["Soybean", "Soybean"],
        "yield_t_ha": [1.2, 1.4],
        "reported_production_tonnes": [12000.0, 14000.0],
        "reported_area_ha": [10000.0, 10000.0],
        "rainfall_mm": [850.0, 920.0],
    })

    engine = DatasetDiscoveryEngine()
    profile = engine.profile_dataframe(df, dataset_name="leakage_test")

    assert profile.columns["reported_production_tonnes"].is_leakage_risk is True
    assert profile.columns["reported_production_tonnes"].inferred_role == ColumnRole.LEAKAGE
    assert "reported_production_tonnes" in profile.quality_report.detected_leakage_columns


def test_discovery_engine_handles_duplicates_and_constant_columns():
    """Verify quality report captures duplicate observations and zero-variance constant features."""
    df = pd.DataFrame({
        "crop": ["Soybean", "Soybean", "Soybean", "Soybean"],
        "constant_col": [42.0, 42.0, 42.0, 42.0],
        "yield_t_ha": [1.0, 1.1, 1.3, 1.4],
        "temp_c": [29.0, 30.0, 31.0, 32.0],
    })
    # Add a duplicate row
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)

    engine = DatasetDiscoveryEngine()
    profile = engine.profile_dataframe(df, dataset_name="quality_check")

    assert profile.quality_report.duplicate_rows == 1
    assert "constant_col" in profile.quality_report.constant_columns
    assert profile.quality_report.quality_score_pct < 100.0


def test_discovery_engine_evaluates_category_combinations():
    """Verify category cross-tabulation discovers well-represented vs sparse combinations."""
    crops = ["Soybean"] * 25 + ["Wheat"] * 7 + ["Barley"] * 2
    districts = ["Akola"] * 34
    df = pd.DataFrame({
        "crop": crops,
        "district": districts,
        "yield_t_ha": np.random.uniform(1.0, 2.0, size=34),
        "rainfall_mm": np.random.uniform(500, 1000, size=34),
    })

    engine = DatasetDiscoveryEngine()
    profile = engine.profile_dataframe(df, dataset_name="combinations_test")

    combos = {c.value_a: c for c in profile.observed_combinations if c.feature_a == "crop"}
    assert combos["Soybean"].representation_status == RepresentationSufficiency.WELL_REPRESENTED
    assert combos["Wheat"].representation_status == RepresentationSufficiency.SPARSE
    assert combos["Barley"].representation_status == RepresentationSufficiency.INSUFFICIENT


# ---------------------------------------------------------------------------
# 2. Adaptive Model Training & Selection Tests
# ---------------------------------------------------------------------------

def test_adaptive_pipeline_trains_and_compares_models(tmp_path):
    """Verify AdaptiveMLPipeline compares baselines, selects the top model, and serializes artifacts."""
    np.random.seed(42)
    n = 120
    df = pd.DataFrame({
        "crop": np.random.choice(["Soybean", "Cotton", "Maize"], size=n),
        "district": np.random.choice(["Akola", "Amravati", "Wardha"], size=n),
        "harvest_year": np.repeat(np.arange(2005, 2017), 10),
        "rainfall_mm": np.random.uniform(400, 1200, size=n),
        "soil_ph": np.random.uniform(6.0, 8.5, size=n),
        "target_yield": np.random.uniform(0.5, 3.0, size=n),
        "leakage_production": np.random.uniform(1000, 5000, size=n),  # should be excluded
    })

    engine = DatasetDiscoveryEngine()
    profile = engine.profile_dataframe(df, dataset_name="adaptive_test")

    pipeline = AdaptiveMLPipeline(
        random_state=42,
        output_dir=str(tmp_path),
    )

    result = pipeline.train_and_evaluate(
        df=df,
        profile=profile,
        target_col="target_yield",
        model_version="3.0.0-test",
    )

    assert result["status"] == "success"
    assert result["selected_algorithm"] in ("Random_Forest", "Hist_Gradient_Boosting", "Ridge_Regression")
    assert "Global_Mean_Baseline" in result["metadata"]["baseline_comparisons"]
    assert "leakage_production" not in result["metadata"]["all_features"]
    assert "target_yield" not in result["metadata"]["all_features"]
    assert "target_distribution" in result["metadata"]
    assert result["metadata"]["target_distribution"]["tertile_p33"] > 0.0


# ---------------------------------------------------------------------------
# 3. Dynamic Prediction Policy (Conservative vs Exploratory) Tests
# ---------------------------------------------------------------------------

def test_conservative_mode_rejects_unverified_district(client):
    """Verify conservative policy rejects districts without verified SoilGrids alignment."""
    payload = {
        "crop": "Soybean",
        "state": "Maharashtra",
        "district": "Thane",  # Unverified district
        "season": "Kharif",
        "year": 2024,
        "prediction_policy": "conservative",
        "soil": {
            "soil_ph": 7.4,
            "organic_carbon_pct": 0.65,
            "clay_pct": 45.0,
            "sand_pct": 20.0,
            "silt_pct": 35.0,
            "bulk_density_g_cm3": 1.25,
            "cation_exchange_capacity_cmol_kg": 38.0,
        },
        "weather": {
            "cumulative_rainfall_mm": 850.5,
            "mean_temp_max_c": 31.8,
            "mean_temp_min_c": 22.4,
            "mean_solar_radiation_mj_m2": 18.6,
            "mean_relative_humidity_pct": 76.2,
            "consecutive_dry_days_max": 8,
            "heat_stress_days": 4,
        },
    }

    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 422
    assert "District 'Thane' is not supported" in response.json()["detail"]


def test_exploratory_mode_allows_novel_crop_and_district(client):
    """Verify exploratory policy handles novel crops and districts with OOD status and clear warnings."""
    payload = {
        "crop": "Sorghum",      # Novel crop not in fixed 7-crop list
        "state": "Maharashtra",
        "district": "Nagpur",    # Novel district not in 7-district list
        "season": "Kharif",
        "year": 2024,
        "prediction_policy": "exploratory",
        "soil": {
            "soil_ph": 7.4,
            "organic_carbon_pct": 0.65,
            "clay_pct": 45.0,
            "sand_pct": 20.0,
            "silt_pct": 35.0,
            "bulk_density_g_cm3": 1.25,
            "cation_exchange_capacity_cmol_kg": 38.0,
        },
        "weather": {
            "cumulative_rainfall_mm": 850.5,
            "mean_temp_max_c": 31.8,
            "mean_temp_min_c": 22.4,
            "mean_solar_radiation_mj_m2": 18.6,
            "mean_relative_humidity_pct": 76.2,
            "consecutive_dry_days_max": 8,
            "heat_stress_days": 4,
        },
    }

    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "Sorghum"
    assert data["district"] == "Nagpur"
    assert data["prediction_policy"] == "exploratory"
    assert data["coverage_status"] == "out_of_distribution_category"
    assert data["is_out_of_distribution"] is True
    assert data["qualitative_label"] is not None
    assert "Exploratory mode active" in " ".join(data["limitations"])


def test_out_of_distribution_numeric_detection(client):
    """Verify extreme weather feature exceeding training distribution is flagged as OOD."""
    payload = {
        "crop": "Soybean",
        "state": "Maharashtra",
        "district": "Akola",
        "season": "Kharif",
        "year": 2024,
        "prediction_policy": "conservative",
        "soil": {
            "soil_ph": 7.4,
            "organic_carbon_pct": 0.65,
            "clay_pct": 45.0,
            "sand_pct": 20.0,
            "silt_pct": 35.0,
            "bulk_density_g_cm3": 1.25,
            "cation_exchange_capacity_cmol_kg": 38.0,
        },
        "weather": {
            "cumulative_rainfall_mm": 4800.0,  # Extreme precipitation outside typical training distribution
            "mean_temp_max_c": 31.8,
            "mean_temp_min_c": 22.4,
            "mean_solar_radiation_mj_m2": 18.6,
            "mean_relative_humidity_pct": 76.2,
            "consecutive_dry_days_max": 8,
            "heat_stress_days": 4,
        },
    }

    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_out_of_distribution"] is True
    assert "cumulative_rainfall_mm" in data["out_of_distribution_features"]
    assert data["coverage_status"] == "out_of_distribution_numeric"


# ---------------------------------------------------------------------------
# 4. New Discovery API Endpoints Tests
# ---------------------------------------------------------------------------

def test_discovery_profile_endpoint(client):
    """Verify GET /api/v1/discovery/profile returns the machine-readable profile."""
    response = client.get("/api/v1/discovery/profile")
    assert response.status_code == 200
    data = response.json()
    assert "dataset_name" in data
    assert "columns" in data
    assert "quality_report" in data
    assert len(data["dynamic_presets"]) > 0


def test_discovery_categories_endpoint(client):
    """Verify GET /api/v1/discovery/categories returns dynamic category catalog."""
    response = client.get("/api/v1/discovery/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "categories" in data
    assert "observed_combinations" in data


def test_discovery_samples_endpoint(client):
    """Verify GET /api/v1/discovery/samples returns empirical presets."""
    response = client.get("/api/v1/discovery/samples")
    assert response.status_code == 200
    data = response.json()
    assert len(data["presets"]) > 0
    first_preset = data["presets"][0]
    assert "name" in first_preset
    assert "sample_values" in first_preset


def test_discovery_inspect_upload_endpoint(client):
    """Verify POST /api/v1/discovery/inspect profiles an uploaded CSV on the fly."""
    csv_content = (
        "crop,district,season,rainfall_mm,temp_c,target_yield\n"
        "Mustard,Akola,Rabi,80.0,24.0,1.2\n"
        "Mustard,Akola,Rabi,90.0,23.5,1.3\n"
        "Barley,Amravati,Rabi,75.0,25.0,1.5\n"
    ).encode("utf-8")

    files = {"file": ("test_upload.csv", io.BytesIO(csv_content), "text/csv")}
    response = client.post("/api/v1/discovery/inspect", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["selected_target"] == "target_yield"
    assert "Mustard" in data["discovered_categories"]["crop"]
    assert "Barley" in data["discovered_categories"]["crop"]


def test_legacy_soybean_request_backward_compatibility(client):
    """Verify that original legacy soybean requests without crop parameter remain 100% operational."""
    payload = {
        "district": "Akola",
        "year": 2024,
        "soil": {
            "soil_ph": 7.4,
            "organic_carbon_pct": 0.65,
            "clay_pct": 45.0,
            "sand_pct": 20.0,
            "silt_pct": 35.0,
            "bulk_density_g_cm3": 1.25,
            "cation_exchange_capacity_cmol_kg": 38.0,
        },
        "weather": {
            "cumulative_rainfall_mm": 850.5,
            "mean_temp_max_c": 31.8,
            "mean_temp_min_c": 22.4,
            "mean_solar_radiation_mj_m2": 18.6,
            "mean_relative_humidity_pct": 76.2,
            "consecutive_dry_days_max": 8,
            "heat_stress_days": 4,
        },
    }

    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "Soybean"
    assert data["model_strategy"] == "legacy_soybean"
    assert data["predicted_yield_t_ha"] > 0.0
    assert data["qualitative_label"] is not None
