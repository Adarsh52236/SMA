from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.services.model_service import model_service
from app.services.keep_alive import keep_alive_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
def get_health() -> HealthResponse:
    """Liveness check returning service operational status, model readiness, and keep-alive metrics."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc),
        environment=settings.ENVIRONMENT,
        model_loaded=model_service.is_loaded,
        message="Crop Yield Prediction API operational",
        keep_alive=keep_alive_service.get_status(),
    )


@router.get("/ready", tags=["Health"])
def get_readiness(response: Response):
    """Readiness probe distinguishing application liveness from model readiness."""
    if model_service.is_loaded:
        return {
            "status": "ready",
            "model_name": model_service.legacy_metadata.get("model_name") if model_service.legacy_metadata else "Unknown",
            "model_version": settings.VERSION,
            "target_crop": settings.TARGET_CROP,
            "target_state": settings.TARGET_STATE,
            "multicrop_ready": model_service.is_multicrop_loaded,
            "supported_crops": settings.SUPPORTED_CROPS,
            "supported_districts": settings.SUPPORTED_DISTRICTS,
        }
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "detail": model_service.error_message or "Model artifact is not loaded or unavailable.",
        }
