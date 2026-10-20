"""Agricultural Growing Season Registry and Meteorological Window Engine.

Defines calendar windows, planting periods, harvest periods, and weather aggregation
intervals for Indian agricultural seasons (Kharif, Rabi, Summer/Zaid, Whole Year),
accounting for cross-calendar-year crops (e.g., Rabi wheat spanning Nov-March).
"""

import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class SeasonName(str, Enum):
    """Canonical agro-climatic season identifiers in Indian agriculture."""

    KHARIF = "Kharif"
    RABI = "Rabi"
    SUMMER = "Summer"
    WHOLE_YEAR = "Whole Year"


class SeasonDefinition(BaseModel):
    """Metadata specification for an agricultural growing season."""

    season_id: str = Field(..., description="Canonical season slug (e.g. 'kharif', 'rabi').")
    display_name: str = Field(..., description="Human-readable title (e.g., 'Kharif (Monsoon)').")
    canonical_name: SeasonName = Field(..., description="Standardized enum value.")
    planting_months_label: str = Field(..., description="Typical sowing window (e.g., 'June - July').")
    harvest_months_label: str = Field(..., description="Typical harvest window (e.g., 'October - November').")
    weather_start_month: int = Field(..., description="Start month (1-12) for seasonal weather accumulation.")
    weather_start_day: int = Field(..., description="Start day (1-31) for seasonal weather accumulation.")
    weather_end_month: int = Field(..., description="End month (1-12) for seasonal weather accumulation.")
    weather_end_day: int = Field(..., description="End day (1-31) for seasonal weather accumulation.")
    spans_calendar_year: bool = Field(
        default=False,
        description="True if sowing occurs in year T-1 and harvest occurs in year T (e.g. Rabi crops).",
    )
    description: str = Field(..., description="Agronomic description of the season.")


SEASON_REGISTRY: Dict[str, SeasonDefinition] = {
    "kharif": SeasonDefinition(
        season_id="kharif",
        display_name="Kharif (Monsoon)",
        canonical_name=SeasonName.KHARIF,
        planting_months_label="June - July",
        harvest_months_label="October - November",
        weather_start_month=6,
        weather_start_day=1,
        weather_end_month=10,
        weather_end_day=31,
        spans_calendar_year=False,
        description=(
            "Southwest monsoon cropping season. Crops (soybean, rice, cotton, maize, groundnut) "
            "are sown with the onset of monsoon rains in June and harvested in autumn (Oct-Nov). "
            "Meteorological window is strictly June 1 to October 31 (153 days)."
        ),
    ),
    "rabi": SeasonDefinition(
        season_id="rabi",
        display_name="Rabi (Winter)",
        canonical_name=SeasonName.RABI,
        planting_months_label="October - November",
        harvest_months_label="March - April",
        weather_start_month=11,
        weather_start_day=1,
        weather_end_month=3,
        weather_end_day=31,
        spans_calendar_year=True,
        description=(
            "Post-monsoon winter cropping season. Crops (wheat, chickpea/gram, rabi sorghum) "
            "are sown in October-November and harvested in spring (March-April). "
            "For a harvest year T, planting and early vegetative growth occur in November of year T-1, "
            "and grain filling/harvest occurs in March of year T."
        ),
    ),
    "summer": SeasonDefinition(
        season_id="summer",
        display_name="Summer (Zaid / Pre-Kharif)",
        canonical_name=SeasonName.SUMMER,
        planting_months_label="February - March",
        harvest_months_label="May - June",
        weather_start_month=2,
        weather_start_day=1,
        weather_end_month=5,
        weather_end_day=31,
        spans_calendar_year=False,
        description=(
            "Hot pre-monsoon season reliant on irrigation. Sown in Feb-March and harvested in May-June "
            "before monsoon onset. Crops include summer groundnut and summer pulses."
        ),
    ),
    "whole_year": SeasonDefinition(
        season_id="whole_year",
        display_name="Whole Year (Perennial / Annual)",
        canonical_name=SeasonName.WHOLE_YEAR,
        planting_months_label="Year-round (Varies by cane crop: Adsali, Pre-seasonal, Suru)",
        harvest_months_label="10 - 18 months post-planting",
        weather_start_month=6,
        weather_start_day=1,
        weather_end_month=5,
        weather_end_day=31,
        spans_calendar_year=True,
        description=(
            "Annual or long-duration crops such as sugarcane spanning a 12-month or multi-season cycle. "
            "Weather window aggregates a full 365-day annual cycle preceding harvest."
        ),
    ),
}

_SEASON_ALIASES: Dict[str, str] = {
    "kharif": "kharif",
    "monsoon": "kharif",
    "rainy": "kharif",
    "autumn": "kharif",
    "rabi": "rabi",
    "winter": "rabi",
    "spring": "rabi",
    "summer": "summer",
    "zaid": "summer",
    "pre-kharif": "summer",
    "whole year": "whole_year",
    "annual": "whole_year",
    "perennial": "whole_year",
}


def resolve_season(query: str) -> Optional[SeasonDefinition]:
    """Resolve a season name or alias to canonical SeasonDefinition."""
    if not query or not isinstance(query, str):
        return None
    cleaned = query.strip().lower()
    canonical_id = _SEASON_ALIASES.get(cleaned)
    if canonical_id and canonical_id in SEASON_REGISTRY:
        return SEASON_REGISTRY[canonical_id]
    return None


def calculate_season_weather_window(
    season: str,
    harvest_year: int,
    custom_crop_offset_days: int = 0,
) -> Tuple[datetime.date, datetime.date]:
    """Calculate the precise start and end calendar dates for seasonal weather aggregation.

    Args:
        season: Season name (e.g. 'Kharif', 'Rabi', 'Summer').
        harvest_year: Calendar year in which the crop was or will be harvested.
        custom_crop_offset_days: Optional adjustment in days for early/late varieties.

    Returns:
        Tuple of (window_start_date, window_end_date)
    """
    season_def = resolve_season(season)
    if not season_def:
        raise ValueError(f"Unknown or unsupported agricultural season '{season}'.")

    if season_def.spans_calendar_year:
        # Cross-year season: sowing starts in (harvest_year - 1), harvests in harvest_year
        start_year = harvest_year - 1
        end_year = harvest_year
    else:
        # Same-year season: both sowing and harvest occur in harvest_year
        start_year = harvest_year
        end_year = harvest_year

    start_date = datetime.date(start_year, season_def.weather_start_month, season_def.weather_start_day)
    end_date = datetime.date(end_year, season_def.weather_end_month, season_def.weather_end_day)

    if custom_crop_offset_days != 0:
        end_date += datetime.timedelta(days=custom_crop_offset_days)

    return start_date, end_date
