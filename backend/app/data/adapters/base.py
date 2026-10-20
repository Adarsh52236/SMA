"""Base Interface and Ingestion Report for Data Source Adapters.

Provides the abstract contract that all data source adapters must implement,
enforcing source traceability, explicit unit conversion, repeatable execution,
and structured quality audits.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field
from app.data.unified_schema import UnifiedCropObservation


class AdapterIngestionReport(BaseModel):
    """Structured audit report produced after an adapter completes an ingestion run."""

    adapter_name: str
    source_id: str
    source_path: str
    total_records_read: int = 0
    accepted_records: int = 0
    rejected_records: int = 0
    deduplicated_records: int = 0
    warnings_count: int = 0
    missing_fields_summary: Dict[str, int] = Field(default_factory=dict)
    rejection_reasons: Dict[str, int] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class BaseSourceAdapter(ABC):
    """Abstract Base Class for modular agricultural dataset adapters."""

    def __init__(self, source_id: str, adapter_name: str):
        self.source_id = source_id
        self.adapter_name = adapter_name

    @abstractmethod
    def ingest(
        self,
        source_path: str,
        **kwargs: Any,
    ) -> Tuple[List[UnifiedCropObservation], AdapterIngestionReport]:
        """Parse, validate, and normalize records from source file into canonical observations.

        Args:
            source_path: Local filesystem path to the raw source data file.
            **kwargs: Adapter-specific parameters (e.g. crop filters, year ranges).

        Returns:
            Tuple of (list_of_UnifiedCropObservation, AdapterIngestionReport)
        """
        pass
