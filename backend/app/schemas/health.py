from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., json_schema_extra={"example": "healthy"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    timestamp: datetime
    environment: str = Field(..., json_schema_extra={"example": "development"})
    model_loaded: bool = Field(..., json_schema_extra={"example": False})
    message: str = Field(..., json_schema_extra={"example": "Crop Yield Prediction API operational"})
    keep_alive: Optional[Dict[str, Any]] = Field(None, description="Current status of autonomous keep-alive self-triggering worker")
