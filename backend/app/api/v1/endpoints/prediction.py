import uuid
from typing import Optional
from fastapi import APIRouter, status
from app.core.config import settings
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    ModelMetadataResponse,
)
from app.services.model_service import model_service

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    summary="Predict crop yield in tonnes per hectare (t/ha)",
)
def predict_crop_yield(request: PredictionRequest) -> PredictionResponse:
    """Predict Maharashtra Kharif soybean yield from verified weather and soil properties.

    Executes inference via the trained scikit-learn Random Forest pipeline serialized in Phase 3.
    """
    result = model_service.predict(request)
    request_id = f"pred-{uuid.uuid4().hex[:12]}"

    return PredictionResponse(
        crop=result["crop"],
        state=request.state,
        district=result["district"],
        season=result["season"],
        year=request.year,
        predicted_yield_t_ha=result["predicted_yield_t_ha"],
        predicted_yield_kg_ha=result["predicted_yield_kg_ha"],
        target_units="tonnes per hectare (t/ha)",
        model_name=result["model_name"],
        model_strategy=result["model_strategy"],
        model_version=settings.VERSION,
        prediction_policy=result.get("prediction_policy", "conservative"),
        coverage_status=result.get("coverage_status", "fully_covered"),
        is_out_of_distribution=result.get("is_out_of_distribution", False),
        out_of_distribution_features=result.get("out_of_distribution_features", []),
        qualitative_label=result.get("qualitative_label"),
        prediction_timing="end_of_season_estimate",
        timing_description=(
            f"End-of-season yield estimate using observed {result['season']} seasonal weather. "
            "This model reflects retrospective or harvest-time meteorological conditions; "
            "it is not an early-season or pre-sowing forecast."
        ),
        evaluation_summary=result.get("evaluation_summary"),
        prediction_interval=None,
        feature_contributions=None,
        global_feature_importance=model_service.feature_importance[:5] if model_service.feature_importance else None,
        explanation=result.get("explanation"),
        uncertainty_note=result.get("uncertainty_note"),
        limitations=result.get("limitations", []),
        request_id=request_id,
    )


@router.get(
    "/model/metadata",
    response_model=ModelMetadataResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    summary="Retrieve model architecture, training provenance, and governance metadata",
)
def get_model_metadata() -> ModelMetadataResponse:
    """Inspect model governance, training periods, performance metrics, and supported features."""
    return model_service.get_metadata()
