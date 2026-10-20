from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.services.model_service import model_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def get_health() -> HealthResponse:
    """Liveness check returning service operational status and model readiness."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc),
        environment=settings.ENVIRONMENT,
        model_loaded=model_service.is_loaded,
        message="Crop Yield Prediction API operational",
    )


@router.get("/ready", tags=["Health"])
def get_readiness(response: Response):
    """Readiness probe distinguishing application liveness from model readiness."""
    if model_service.is_loaded:
        return {
            "status": "ready",
            "model_name": model_service.metadata.get("model_name") if model_service.metadata else "Unknown",
            "model_version": settings.VERSION,
            "target_crop": settings.TARGET_CROP,
            "target_state": settings.TARGET_STATE,
        }
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "detail": model_service.error_message or "Model artifact is not loaded or unavailable.",
        }
