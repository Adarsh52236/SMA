import os
from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
from app.schemas.prediction import PredictionRequest, PredictionResponse

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    tags=["Prediction"],
    summary="Predict crop yield in tonnes per hectare (t/ha)",
)
def predict_crop_yield(request: PredictionRequest) -> PredictionResponse:
    """Predict crop yield from verified weather and soil inputs.

    Note: In Phase 1 (skeleton setup), this endpoint validates incoming schemas.
    If no trained model artifact exists on disk, it returns HTTP 503 rather than
    fabricating or guessing predictions. Real inference will be activated in Phase 4
    using artifacts trained in Phase 3.
    """
    model_path = os.path.join(settings.MODEL_DIR, settings.MODEL_FILENAME)

    if not os.path.exists(model_path):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Model artifact not found at '{model_path}'. "
                "Per project specification, predictions are only served from genuine trained models "
                "produced during Phase 3. Please train the model pipeline before requesting inference."
            ),
        )

    # In Phase 4, loaded model pipeline will execute inference here.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Model loading pipeline scheduled for Phase 4.",
    )
