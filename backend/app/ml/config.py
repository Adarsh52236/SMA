"""Machine learning configuration, split dates, random seeds, and file paths."""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class MLConfig(BaseSettings):
    """Configuration parameters for model training, evaluation, and serialization."""

    # Project paths
    PROJECT_ROOT: str = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    DATASET_PATH: str = os.path.join(
        PROJECT_ROOT, "data", "processed", "crop_yield_maharashtra.csv"
    )
    ARTIFACT_DIR: str = os.path.join(PROJECT_ROOT, "backend", "models")
    MODEL_FILENAME: str = "crop_yield_model.joblib"
    METADATA_FILENAME: str = "model_metadata.json"
    REPORTS_MODELING_DIR: str = os.path.join(PROJECT_ROOT, "reports", "modeling")
    FIGURES_DIR: str = os.path.join(PROJECT_ROOT, "reports", "modeling", "figures")

    # Target definition
    TARGET_COLUMN: str = "yield_t_ha"
    TARGET_UNITS: str = "tonnes per hectare (t/ha)"

    # Chronological Splits
    TRAIN_START_YEAR: int = 1990
    TRAIN_END_YEAR: int = 2010
    VAL_START_YEAR: int = 2011
    VAL_END_YEAR: int = 2014
    TEST_START_YEAR: int = 2015
    TEST_END_YEAR: int = 2017

    # Modeling Reproducibility
    RANDOM_SEED: int = 42

    # Permutation Feature Importance settings
    PFI_N_REPEATS: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ML_",
        extra="ignore",
    )


ml_config = MLConfig()
