import os
from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Root directory of backend package (backend/)
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    """Application settings and environment configuration."""

    PROJECT_NAME: str = "Crop Yield Prediction API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS origins: support comma-separated or JSON list via CORS_ORIGINS or BACKEND_CORS_ORIGINS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://sma-production.up.railway.app",
        "https://sma-frontend.vercel.app",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Model artifact directory and target model name
    MODEL_DIR: str = str(BACKEND_ROOT / "models")
    MODEL_FILENAME: str = "crop_yield_model.joblib"
    METADATA_FILENAME: str = "model_metadata.json"
    REPORTS_DIR: str = str(PROJECT_ROOT / "reports" / "modeling")

    TARGET_CROP: str = "Soybean"
    TARGET_STATE: str = "Maharashtra"
    TARGET_SEASON: str = "Kharif"

    SUPPORTED_DISTRICTS: List[str] = [
        "Ahmednagar",
        "Akola",
        "Amravati",
        "Aurangabad",
        "Beed",
        "Bhandara",
        "Buldhana",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
