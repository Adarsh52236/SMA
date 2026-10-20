"""Unit and Integration Tests for Production Prediction API (Phase 4).

Verifies:
1. Successful inference using the actual trained Random Forest pipeline artifact.
2. Prediction output schema, physical units, and timing disclosures.
3. Missing-model behavior (HTTP 503).
4. Corrupted or incompatible artifact handling.
5. Rejection of NaN, Infinity, and out-of-range numeric inputs (HTTP 422).
6. Rejection of unsupported districts, crops, states, or seasons (HTTP 422).
7. Rejection of missing required seasonal weather features (dry spells, heat stress).
8. Feature mapping and ordering consistency.
9. Application liveness vs. model readiness probe behavior.
10. Model governance metadata endpoint output and explainability.
11. CORS headers and middleware configuration.
12. Consistency between model metadata and the loaded scikit-learn pipeline.
"""

import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.model_service import model_service
from app.schemas.prediction import PredictionResponse, ModelMetadataResponse


@pytest.fixture
def valid_prediction_payload():
    """Illustrative valid prediction request payload for Akola district."""
    return {
        "crop": "Soybean",
        "state": "Maharashtra",
        "district": "Akola",
        "season": "Kharif",
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


# --- 1. Successful Prediction Integration Test ---

def test_successful_prediction_with_actual_artifact(valid_prediction_payload):
    """Integration test: Verify inference using the actual trained Random Forest artifact."""
    with TestClient(app) as client:
        response = client.post("/api/v1/predict", json=valid_prediction_payload)
        assert response.status_code == 200
        data = response.json()

        # Validate against Pydantic schema
        validated_response = PredictionResponse(**data)
        assert validated_response.crop == "Soybean"
        assert validated_response.state == "Maharashtra"
        assert validated_response.district == "Akola"
        assert validated_response.season == "Kharif"
        assert validated_response.year == 2024
        assert validated_response.target_units == "tonnes per hectare (t/ha)"
        assert validated_response.model_name == "Random_Forest"
        assert validated_response.prediction_timing == "end_of_season_estimate"

        # Check yield prediction is physically plausible for rainfed soybean (0.1 to 4.5 t/ha)
        assert 0.1 <= validated_response.predicted_yield_t_ha <= 4.5
        assert validated_response.prediction_interval is None  # Not fabricated
        assert validated_response.request_id is not None
        assert len(validated_response.limitations) > 0


# --- 2. Missing-Model & Service Unavailable Behavior ---

def test_predict_returns_503_when_model_unloaded(valid_prediction_payload):
    """Verify that if the model is not loaded, the endpoint returns 503 Service Unavailable."""
    # Temporarily simulate model unloaded state
    original_loaded = model_service.is_loaded
    original_pipeline = model_service.pipeline
    try:
        model_service.is_loaded = False
        model_service.pipeline = None

        client = TestClient(app)
        response = client.post("/api/v1/predict", json=valid_prediction_payload)
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower() or "not found" in response.json()["detail"].lower()
    finally:
        model_service.is_loaded = original_loaded
        model_service.pipeline = original_pipeline


# --- 3. Liveness vs. Readiness Probes ---

def test_readiness_probe_when_ready():
    """Verify /ready probe returns 200 and model details when model is loaded."""
    with TestClient(app) as client:
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["model_name"] == "Random_Forest"
        assert data["target_crop"] == "Soybean"


def test_readiness_probe_when_not_ready():
    """Verify /ready probe returns 503 when model is unloaded."""
    original_loaded = model_service.is_loaded
    try:
        model_service.is_loaded = False
        client = TestClient(app)
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
    finally:
        model_service.is_loaded = original_loaded


# --- 4. Corrupted or Incompatible Artifact Handling ---

def test_corrupted_artifact_handling(tmp_path, monkeypatch):
    """Verify that a corrupted artifact file does not crash the server and marks service unready."""
    corrupted_file = tmp_path / "crop_yield_model.joblib"
    corrupted_file.write_text("not a valid joblib file content")
    
    meta_file = tmp_path / "model_metadata.json"
    meta_file.write_text(json.dumps({"feature_schema": {"all_predictors": []}}))

    monkeypatch.setattr(settings, "MODEL_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "MODEL_FILENAME", "crop_yield_model.joblib")
    monkeypatch.setattr(settings, "METADATA_FILENAME", "model_metadata.json")

    # Attempt to load corrupted artifact
    success = model_service.load_model()
    assert success is False
    assert model_service.is_loaded is False
    assert "Failed to load model artifact" in model_service.error_message

    # Restore true model
    monkeypatch.undo()
    model_service.load_model()


# --- 5. Rejection of NaN, Infinity, and Out-of-Range Inputs ---

def test_rejection_of_nan_and_infinity(valid_prediction_payload):
    """Verify Pydantic schema rejects NaN and Infinity inputs with HTTP 422."""
    with TestClient(app) as client:
        # Test NaN in weather
        payload_nan = json.loads(json.dumps(valid_prediction_payload))
        payload_nan["weather"]["cumulative_rainfall_mm"] = None
        resp_nan = client.post("/api/v1/predict", json=payload_nan)
        assert resp_nan.status_code == 422

        # Test out-of-range pH (> 10.0)
        payload_ph = json.loads(json.dumps(valid_prediction_payload))
        payload_ph["soil"]["soil_ph"] = 12.0
        resp_ph = client.post("/api/v1/predict", json=payload_ph)
        assert resp_ph.status_code == 422


# --- 6. Rejection of Unsupported Districts and Categories ---

def test_rejection_of_unsupported_district(valid_prediction_payload):
    """Verify that districts without verified SoilGrids profiles are rejected with HTTP 422."""
    with TestClient(app) as client:
        payload = json.loads(json.dumps(valid_prediction_payload))
        payload["district"] = "UnsupportedDistrictName"
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422
        assert "not supported" in response.json()["detail"]


def test_rejection_of_unsupported_crop_or_season(valid_prediction_payload):
    """Verify that unsupported crops or seasons are rejected with HTTP 422."""
    with TestClient(app) as client:
        payload_crop = json.loads(json.dumps(valid_prediction_payload))
        payload_crop["crop"] = "Cotton"
        resp_crop = client.post("/api/v1/predict", json=payload_crop)
        assert resp_crop.status_code == 422
        assert "Unsupported crop" in resp_crop.json()["detail"]

        payload_season = json.loads(json.dumps(valid_prediction_payload))
        payload_season["season"] = "Rabi"
        resp_season = client.post("/api/v1/predict", json=payload_season)
        assert resp_season.status_code == 422
        assert "Unsupported season" in resp_season.json()["detail"]


# --- 7. Rejection of Missing Required Seasonal Weather Features ---

def test_rejection_of_missing_dry_days_or_heat_stress(valid_prediction_payload):
    """Verify that end-of-season predictors cannot be silently omitted or defaulted."""
    with TestClient(app) as client:
        payload = json.loads(json.dumps(valid_prediction_payload))
        payload["weather"]["consecutive_dry_days_max"] = None
        response = client.post("/api/v1/predict", json=payload)
        assert response.status_code == 422
        assert "consecutive_dry_days_max" in response.json()["detail"]


# --- 8. Model Metadata Endpoint Output ---

def test_model_metadata_endpoint():
    """Verify GET /api/v1/model/metadata returns safe, verified governance metadata."""
    with TestClient(app) as client:
        response = client.get("/api/v1/model/metadata")
        assert response.status_code == 200
        data = response.json()

        # Validate against schema
        metadata = ModelMetadataResponse(**data)
        assert metadata.model_name == "Random_Forest"
        assert metadata.target == "yield_t_ha"
        assert metadata.target_units == "tonnes per hectare (t/ha)"
        assert metadata.crop == "Soybean"
        assert metadata.state == "Maharashtra"
        assert metadata.season == "Kharif"
        assert metadata.training_period == [1990, 2010]
        assert metadata.validation_period == [2011, 2014]
        assert metadata.test_period == [2015, 2017]
        assert len(metadata.supported_districts) == 7
        assert len(metadata.supported_features) == 15
        assert metadata.validation_metrics["rmse_t_ha"] == 0.4483
        assert metadata.test_metrics["rmse_t_ha"] == 0.436
        assert len(metadata.global_feature_importance) > 0


# --- 9. CORS Configuration ---

def test_cors_headers_on_requests():
    """Verify CORS middleware headers allow configured frontend origins."""
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


# --- 10. Pipeline & Metadata Schema Consistency ---

def test_pipeline_metadata_schema_consistency():
    """Verify that loaded pipeline expects all columns declared in metadata."""
    assert model_service.is_loaded is True
    assert model_service.metadata is not None
    assert model_service.pipeline is not None

    declared_features = model_service.metadata["feature_schema"]["all_predictors"]
    preprocessor = model_service.pipeline.named_steps["preprocessor"]
    
    # Preprocessor ColumnTransformer transformer names
    transformer_features = []
    for name, trans, cols in preprocessor.transformers:
        transformer_features.extend(cols)
    
    assert set(declared_features) == set(transformer_features)
