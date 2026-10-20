import pytest
from pydantic import ValidationError
from app.schemas.prediction import SoilProperties, SeasonalWeather, PredictionRequest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_valid_soil_properties():
    """Verify valid soil characteristics pass validation."""
    soil = SoilProperties(
        soil_ph=6.8,
        organic_carbon_pct=0.75,
        clay_pct=45.0,
        sand_pct=25.0,
        bulk_density_g_cm3=1.32,
        cation_exchange_capacity_cmol_kg=35.0,
    )
    assert soil.soil_ph == 6.8
    assert soil.clay_pct == 45.0


def test_soil_texture_sum_validation():
    """Verify soil texture validation prevents clay + sand exceeding 100%."""
    with pytest.raises(ValidationError) as exc_info:
        SoilProperties(
            soil_ph=7.0,
            organic_carbon_pct=1.0,
            clay_pct=65.0,
            sand_pct=45.0,  # 65 + 45 = 110 > 100
            bulk_density_g_cm3=1.3,
            cation_exchange_capacity_cmol_kg=30.0,
        )
    assert "Sum of clay" in str(exc_info.value)


def test_weather_temp_range_validation():
    """Verify min temperature cannot exceed max temperature."""
    with pytest.raises(ValidationError) as exc_info:
        SeasonalWeather(
            cumulative_rainfall_mm=800.0,
            mean_temp_max_c=25.0,
            mean_temp_min_c=30.0,  # min > max
            mean_solar_radiation_mj_m2=18.0,
            mean_relative_humidity_pct=70.0,
        )
    assert "Minimum temperature" in str(exc_info.value)


def test_predict_endpoint_returns_503_when_model_absent():
    """Verify predict endpoint handles missing model artifact gracefully without fake numbers."""
    payload = {
        "crop": "Soybean",
        "state": "Maharashtra",
        "district": "Latur",
        "season": "Kharif",
        "year": 2024,
        "soil": {
            "soil_ph": 7.2,
            "organic_carbon_pct": 0.65,
            "clay_pct": 42.0,
            "sand_pct": 25.0,
            "bulk_density_g_cm3": 1.35,
            "cation_exchange_capacity_cmol_kg": 38.5,
        },
        "weather": {
            "cumulative_rainfall_mm": 850.5,
            "mean_temp_max_c": 31.8,
            "mean_temp_min_c": 22.4,
            "mean_solar_radiation_mj_m2": 18.6,
            "mean_relative_humidity_pct": 76.2,
        },
    }
    response = client.post("/api/v1/predict", json=payload)
    # Must be 503 Service Unavailable, stating model artifact needs to be trained
    assert response.status_code == 503
    assert "Model artifact not found" in response.json()["detail"]


def test_predict_endpoint_rejects_invalid_inputs():
    """Verify predict endpoint rejects out-of-bounds inputs with 422 Unprocessable Entity."""
    payload = {
        "crop": "Soybean",
        "state": "Maharashtra",
        "district": "Latur",
        "season": "Kharif",
        "year": 2024,
        "soil": {
            "soil_ph": 15.0,  # Invalid pH (> 10.0)
            "organic_carbon_pct": 0.65,
            "clay_pct": 42.0,
            "sand_pct": 25.0,
            "bulk_density_g_cm3": 1.35,
            "cation_exchange_capacity_cmol_kg": 38.5,
        },
        "weather": {
            "cumulative_rainfall_mm": 850.5,
            "mean_temp_max_c": 31.8,
            "mean_temp_min_c": 22.4,
            "mean_solar_radiation_mj_m2": 18.6,
            "mean_relative_humidity_pct": 76.2,
        },
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 422
