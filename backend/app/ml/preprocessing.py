"""Preprocessing Pipelines and Learned Transformers.

Provides scikit-learn ColumnTransformer pipelines configured to fit scalers
and encoders exclusively on training partitions to prevent data leakage.
"""

from typing import List
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from app.ml.features import NUMERIC_FEATURES, CATEGORICAL_FEATURES


def build_preprocessor(scale_numeric: bool = True) -> ColumnTransformer:
    """Build a ColumnTransformer for numerical scaling and categorical encoding.

    Args:
        scale_numeric: When True, applies StandardScaler to numeric features (needed for Ridge).
                       When False, passes numeric features through untouched (standard for tree ensembles).
    """
    transformers = []

    if scale_numeric:
        transformers.append(
            ("num", StandardScaler(), NUMERIC_FEATURES)
        )
    else:
        transformers.append(
            ("num", "passthrough", NUMERIC_FEATURES)
        )

    # OneHotEncoder for district with handle_unknown='ignore' for robust out-of-district evaluation
    transformers.append(
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            CATEGORICAL_FEATURES,
        )
    )

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )
