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
    predicted_yield = model_service.predict(request)
    request_id = f"pred-{uuid.uuid4().hex[:12]}"

    limitations = [
        "End-of-season yield estimate using observed weather (June-October); not an early-season or pre-sowing forecast.",
        "Soil properties represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages.",
        "Validated within Maharashtra agroclimatic conditions; spatial extrapolation outside supported districts is prohibited.",
    ]

    return PredictionResponse(
        crop=settings.TARGET_CROP,
        state=settings.TARGET_STATE,
        district=request.district.strip().title(),
        season=settings.TARGET_SEASON,
        year=request.year,
        predicted_yield_t_ha=predicted_yield,
        target_units="tonnes per hectare (t/ha)",
        model_name=model_service.metadata.get("model_name", "Random_Forest") if model_service.metadata else "Random_Forest",
        model_version=settings.VERSION,
        prediction_timing="end_of_season_estimate",
        timing_description=(
            "End-of-season yield estimate using observed Kharif seasonal weather (June 1 - October 31). "
            "This model reflects retrospective or harvest-time meteorological conditions; "
            "it is not an early-season or pre-sowing forecast."
        ),
        prediction_interval=None,
        feature_contributions=None,
        global_feature_importance=model_service.feature_importance[:5] if model_service.feature_importance else None,
        limitations=limitations,
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
