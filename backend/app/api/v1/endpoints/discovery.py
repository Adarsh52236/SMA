"""Dynamic Dataset Discovery, Quality Profiling, and Retraining Endpoints (Phase 6).

Provides public API routes for:
- GET  /api/v1/discovery/profile     -> active dataset profile & quality audit
- GET  /api/v1/discovery/categories  -> discovered categorical dimensions & observed combinations
- GET  /api/v1/discovery/samples     -> authentic data-driven presets
- POST /api/v1/discovery/inspect     -> upload/inspect arbitrary datasets on the fly
- POST /api/v1/discovery/retrain     -> autonomous retraining with candidate baseline comparison
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from app.services.discovery_service import discovery_service
from app.discovery.schemas import DatasetProfile, DynamicPresetSample
from app.schemas.prediction import (
    DynamicCategoriesResponse,
    DynamicPresetsResponse,
    RetrainRequest,
    RetrainResponse,
)

logger = logging.getLogger("CropYieldAPI.DiscoveryEndpoints")
router = APIRouter()


@router.get(
    "/discovery/profile",
    response_model=DatasetProfile,
    status_code=status.HTTP_200_OK,
    tags=["Discovery"],
    summary="Retrieve active dataset discovery profile, quality metrics, and schema",
)
def get_dataset_profile() -> DatasetProfile:
    """Retrieve machine-readable dataset profile, column semantics, and data quality report."""
    profile = discovery_service.get_active_profile()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No dataset has been profiled yet on the backend.",
        )
    return profile


@router.get(
    "/discovery/categories",
    response_model=DynamicCategoriesResponse,
    status_code=status.HTTP_200_OK,
    tags=["Discovery"],
    summary="Retrieve dynamically discovered categories and observed combinations with sufficiency",
)
def get_discovered_categories() -> DynamicCategoriesResponse:
    """Return discovered categorical dimensions (crops, districts, seasons) and cross-tabulation sufficiency."""
    data = discovery_service.get_categories()
    return DynamicCategoriesResponse(
        status=data["status"],
        dataset_name=data.get("dataset_name"),
        categories=data.get("categories", {}),
        observed_combinations=data.get("observed_combinations", []),
    )


@router.get(
    "/discovery/samples",
    response_model=DynamicPresetsResponse,
    status_code=status.HTTP_200_OK,
    tags=["Discovery"],
    summary="Retrieve illustrative sample presets derived dynamically from genuine dataset observations",
)
def get_dynamic_presets() -> DynamicPresetsResponse:
    """Return authentic observation presets extracted directly from data records."""
    presets = discovery_service.get_dynamic_presets(max_samples=8)
    return DynamicPresetsResponse(presets=presets)


@router.post(
    "/discovery/inspect",
    response_model=DatasetProfile,
    status_code=status.HTTP_200_OK,
    tags=["Discovery"],
    summary="Upload and inspect an arbitrary tabular dataset to infer schema and data quality on the fly",
)
async def inspect_uploaded_dataset(
    file: UploadFile = File(..., description="CSV or Parquet dataset file"),
    target_override: Optional[str] = Form(None, description="Optional target column override"),
) -> DatasetProfile:
    """Upload an arbitrary dataset to discover schema, quality anomalies, and candidate targets."""
    if not file.filename.endswith((".csv", ".parquet", ".pq")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV (.csv) and Parquet (.parquet) dataset files are supported for profiling.",
        )

    # Resource limit check: Max 25MB
    content = await file.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Dataset file exceeds maximum allowed size of 25MB.",
        )

    try:
        profile = discovery_service.inspect_dataset(
            content_bytes=content,
            filename=file.filename,
            target_override=target_override,
        )
        return profile
    except Exception as e:
        logger.error(f"Failed to profile uploaded dataset: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse and profile dataset: {str(e)}",
        )


@router.post(
    "/discovery/retrain",
    response_model=RetrainResponse,
    status_code=status.HTTP_200_OK,
    tags=["Discovery"],
    summary="Trigger autonomous model training, candidate algorithm selection, and versioned serialization",
)
def retrain_adaptive_model(config: RetrainRequest) -> RetrainResponse:
    """Train candidate models, compare against baselines, and save versioned model artifacts."""
    try:
        result = discovery_service.retrain_adaptive_model(
            dataset_name=config.dataset_name,
            target_col=config.target_col,
            feature_exclusions=config.feature_exclusions,
            model_version=config.model_version,
        )
        return RetrainResponse(
            status=result["status"],
            model_version=result["model_version"],
            selected_algorithm=result["selected_algorithm"],
            artifact_path=result["artifact_path"],
            metadata_path=result["metadata_path"],
            schema_path=result["schema_path"],
            metadata=result["metadata"],
        )
    except Exception as e:
        logger.error(f"Adaptive model retraining failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Adaptive retraining error: {str(e)}",
        )
