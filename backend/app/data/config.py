"""Data pipeline configuration and directory paths."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataPipelineConfig(BaseSettings):
    """Configuration parameters for the data acquisition and alignment pipeline."""

    # Base workspace directories
    PROJECT_ROOT: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    RAW_DATA_DIR: str = os.path.join(PROJECT_ROOT, "data", "raw")
    INTERIM_DATA_DIR: str = os.path.join(PROJECT_ROOT, "data", "interim")
    PROCESSED_DATA_DIR: str = os.path.join(PROJECT_ROOT, "data", "processed")
    REPORTS_DIR: str = os.path.join(PROJECT_ROOT, "reports")

    # Ingestion URLs
    CROP_DATA_URL: str = "https://raw.githubusercontent.com/Runax15/crop-yield-prediction-maharashtra/main/crop_data.csv"
    NASA_POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/temporal/daily/point"
    SOILGRIDS_BASE_URL: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    # Crop & Season Defaults
    TARGET_STATE: str = "Maharashtra"
    TARGET_CROP: str = "Soybean"
    TARGET_SEASON: str = "Kharif"
    KHARIF_START_MONTH_DAY: str = "06-01"  # June 1
    KHARIF_END_MONTH_DAY: str = "10-31"    # October 31

    # Date range for historical baseline
    START_YEAR: int = 1990
    END_YEAR: int = 2017

    # Quality control thresholds
    MIN_AREA_HA: float = 100.0
    EXTREME_YIELD_LOW_T_HA: float = 0.20
    EXTREME_YIELD_HIGH_T_HA: float = 4.50

    # HTTP Network parameters
    REQUEST_TIMEOUT_SECONDS: int = 40
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATA_",
        extra="ignore",
    )


data_config = DataPipelineConfig()
