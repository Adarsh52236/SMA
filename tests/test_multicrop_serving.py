"""Quality Gates for Coverage-Aware Multi-Crop Model Serving (Phase 5).

Validates:
1. Legacy soybean prediction requests without a crop field default safely to soybean.
2. Inference for all 7 supported crops using realistic test inputs in verified districts.
3. Rejection of unknown or unsupported crops (e.g. Barley, Rubber, Canola).
4. Rejection of unsupported districts (e.g. Thane, Kalyan, Pune) without verified soil profiles.
5. Rejection of crop/season mismatches (e.g. Wheat in Kharif, Rice in Rabi).
6. Routing policies: legacy_soybean vs shared_multicrop.
7. Prevention of silent fallback from non-soybean crops to the soybean model.
8. Output schema completeness: predicted_yield_t_ha, predicted_yield_kg_ha, strategy, limitations.
9. Dynamic model metadata and readiness endpoint consistency.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.model_service import model_service
from app.core.config import settings


@pytest.fixture
def realistic_sample_payload():
    """Realistic test input fixture for agricultural inference.

    NOTE: Explicitly documented as illustrative test inputs, not measured field data.
    """
    return {
        "crop": "Soybean",
        "state": "Maharashtra",
        "district": "Akola",
        "season": "Kharif",
        "year": 2024,
        "soil": {
            "soil_ph": 7.5,
            "organic_carbon_pct": 0.65,
            "clay_pct": 46.0,
            "sand_pct": 20.0,
            "silt_pct": 34.0,
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


def test_legacy_soybean_request_without_crop_field(realistic_sample_payload):
    """Verify legacy payload omitting 'crop' defaults to Soybean and uses legacy pipeline."""
    payload = dict(realistic_sample_payload)
    del payload["crop"]

    with TestClient(app) as client:
        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["crop"] == "Soybean"
        assert data["model_strategy"] == "legacy_soybean"
        assert data["predicted_yield_t_ha"] > 0.0
        assert data["predicted_yield_kg_ha"] == round(data["predicted_yield_t_ha"] * 1000.0, 1)


def test_all_seven_supported_crops_inference(realistic_sample_payload):
    """Verify that all 7 supported crops execute successfully on supported districts and seasons."""
    crop_test_cases = [
        ("Soybean", "Kharif", "Akola"),
        ("Rice", "Kharif", "Bhandara"),
        ("Wheat", "Rabi", "Ahmednagar"),
        ("Cotton", "Kharif", "Amravati"),
        ("Maize", "Kharif", "Aurangabad"),
        ("Chickpea", "Rabi", "Beed"),
        ("Groundnut", "Kharif", "Buldhana"),
    ]

    with TestClient(app) as client:
        for crop, season, district in crop_test_cases:
            payload = json.loads(json.dumps(realistic_sample_payload))
            payload["crop"] = crop
            payload["season"] = season
            payload["district"] = district

            resp = client.post("/api/v1/predict", json=payload)
            assert resp.status_code == 200, f"Inference failed for {crop}: {resp.text}"
            data = resp.json()

            assert data["district"] == district
            assert data["season"] == season
            assert data["predicted_yield_t_ha"] >= 0.0
            assert data["predicted_yield_kg_ha"] >= 0.0
            assert data["target_units"] == "tonnes per hectare (t/ha)"

            if crop.lower() == "soybean":
                assert data["model_strategy"] in ("legacy_soybean", "shared_multicrop")
            else:
                # All non-soybean crops must use the shared multi-crop pipeline
                assert data["model_strategy"] == "shared_multicrop"
                assert "Universal_Random_Forest_MultiCrop" in data["model_name"]


def test_explicit_strategy_routing_for_soybean(realistic_sample_payload):
    """Verify that soybean can explicitly opt into the shared_multicrop model."""
    with TestClient(app) as client:
        # 1. Default (legacy)
        resp_leg = client.post("/api/v1/predict", json=realistic_sample_payload)
        assert resp_leg.status_code == 200
        assert resp_leg.json()["model_strategy"] == "legacy_soybean"

        # 2. Explicit shared_multicrop
        payload_shared = json.loads(json.dumps(realistic_sample_payload))
        payload_shared["model_strategy"] = "shared_multicrop"
        resp_shared = client.post("/api/v1/predict", json=payload_shared)
        assert resp_shared.status_code == 200
        assert resp_shared.json()["model_strategy"] == "shared_multicrop"


def test_rejection_of_unknown_crop(realistic_sample_payload):
    """Verify unknown crops are strictly rejected with HTTP 422 and no silent fallback."""
    unsupported_crops = ["Barley", "Canola", "Rubber", "Oilpalm", "UnknownCrop"]

    with TestClient(app) as client:
        for bad_crop in unsupported_crops:
            payload = json.loads(json.dumps(realistic_sample_payload))
            payload["crop"] = bad_crop

            resp = client.post("/api/v1/predict", json=payload)
            assert resp.status_code == 422
            detail = resp.json()["detail"]
            assert "Unsupported crop" in detail
            assert "Soybean" in detail
            assert "Wheat" in detail


def test_rejection_of_unsupported_district(realistic_sample_payload):
    """Verify unverified districts (e.g. Thane, Kalyan, Pune) are rejected with clear coverage explanation."""
    unsupported_districts = ["Thane", "Kalyan", "Pune", "Mumbai", "Ratnagiri"]

    with TestClient(app) as client:
        for bad_dist in unsupported_districts:
            payload = json.loads(json.dumps(realistic_sample_payload))
            payload["district"] = bad_dist

            resp = client.post("/api/v1/predict", json=payload)
            assert resp.status_code == 422
            detail = resp.json()["detail"]
            assert "is not supported" in detail
            assert "Akola" in detail
            assert "SoilGrids" in detail


def test_rejection_of_season_mismatch(realistic_sample_payload):
    """Verify season mismatches are rejected (e.g. Wheat in Kharif, Rice in Rabi)."""
    with TestClient(app) as client:
        # Wheat is strictly Rabi
        payload_wheat = json.loads(json.dumps(realistic_sample_payload))
        payload_wheat["crop"] = "Wheat"
        payload_wheat["season"] = "Kharif"
        resp_wheat = client.post("/api/v1/predict", json=payload_wheat)
        assert resp_wheat.status_code == 422
        assert "Unsupported season" in resp_wheat.json()["detail"]

        # Rice is Kharif in central Maharashtra
        payload_rice = json.loads(json.dumps(realistic_sample_payload))
        payload_rice["crop"] = "Rice"
        payload_rice["season"] = "Rabi"
        resp_rice = client.post("/api/v1/predict", json=payload_rice)
        assert resp_rice.status_code == 422
        assert "Unsupported season" in resp_rice.json()["detail"]


def test_rejection_of_legacy_strategy_on_non_soybean_crop(realistic_sample_payload):
    """Verify that callers cannot force non-soybean crops into the legacy soybean pipeline."""
    with TestClient(app) as client:
        payload = json.loads(json.dumps(realistic_sample_payload))
        payload["crop"] = "Cotton"
        payload["model_strategy"] = "legacy_soybean"

        resp = client.post("/api/v1/predict", json=payload)
        assert resp.status_code == 422
        assert "only supports crop 'Soybean'" in resp.json()["detail"]


def test_metadata_endpoint_coverage_and_governance():
    """Verify GET /api/v1/model/metadata exposes supported crops, strategies, and evaluations."""
    with TestClient(app) as client:
        resp = client.get("/api/v1/model/metadata")
        assert resp.status_code == 200
        meta = resp.json()

        # Legacy backward-compatibility
        assert meta["crop"] == "Soybean"
        assert len(meta["supported_districts"]) == 7

        # Multi-crop catalog
        assert "supported_crops" in meta
        crops_in_meta = [c["crop_id"] for c in meta["supported_crops"]]
        for expected_crop in ["soybean", "rice", "wheat", "cotton", "maize", "chickpea", "groundnut"]:
            assert expected_crop in crops_in_meta

        # Strategies
        assert "available_strategies" in meta
        strategy_ids = [s["strategy_id"] for s in meta["available_strategies"]]
        assert "legacy_soybean" in strategy_ids
        assert "shared_multicrop" in strategy_ids

        # Multi-crop evaluation
        assert meta["multicrop_evaluation"] is not None
        assert "temporal_holdout" in meta["multicrop_evaluation"]
        assert "spatial_holdout" in meta["multicrop_evaluation"]


def test_readiness_probe_reports_multicrop():
    """Verify GET /api/v1/ready reports multicrop readiness and supported crops."""
    with TestClient(app) as client:
        resp = client.get("/api/v1/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["multicrop_ready"] is True
        assert "wheat" in data["supported_crops"]
        assert "Akola" in data["supported_districts"]
