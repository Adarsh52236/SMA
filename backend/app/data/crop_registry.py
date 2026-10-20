"""Crop Registry and Agro-Botanical Metadata Catalog.

Maintains normalized crop identifiers, taxonomic classification, crop categories,
source aliases (e.g., ICRISAT DLD, FAOSTAT, DES), typical yield boundaries,
and supported growing seasons.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class CropCategory(str, Enum):
    """Broad agro-economic crop classification."""

    CEREAL = "cereal"
    PULSE = "pulse"
    OILSEED = "oilseed"
    CASH_CROP = "cash_crop"
    FODDER = "fodder"
    HORTICULTURE = "horticulture"
    OTHER = "other"


class CropSpecification(BaseModel):
    """Definitive metadata specification for an agricultural crop."""

    crop_id: str = Field(..., description="Canonical URL-friendly slug identifier (e.g., 'soybean', 'rice').")
    display_name: str = Field(..., description="Human-readable title (e.g., 'Soybean', 'Rice (Paddy)').")
    category: CropCategory = Field(..., description="Broad category: cereal, pulse, oilseed, cash_crop, etc.")
    scientific_name: str = Field(..., description="Botanical binomial nomenclature.")
    default_season: str = Field(..., description="Predominant cultivation season in Central/Western India.")
    supported_seasons: List[str] = Field(..., description="Seasons in which this crop is legitimately grown.")
    source_aliases: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapping from source system (e.g. 'icrisat_dld') to source column names/aliases.",
    )
    typical_yield_range_t_ha: Tuple[float, float] = Field(
        ...,
        description="Plausible yield range (min, max) in tonnes per hectare (t/ha) under Indian rainfed/irrigated conditions.",
    )
    nitrogen_fixing: bool = Field(default=False, description="Whether the crop fixes atmospheric nitrogen (legumes).")
    water_intensity: str = Field(default="medium", description="Qualitative water requirement: low, medium, high, very_high.")


# Canonical registry of evaluated and supported crops in Indian Agricultural Statistics
CROP_REGISTRY: Dict[str, CropSpecification] = {
    "soybean": CropSpecification(
        crop_id="soybean",
        display_name="Soybean",
        category=CropCategory.OILSEED,
        scientific_name="Glycine max",
        default_season="Kharif",
        supported_seasons=["Kharif"],
        source_aliases={
            "icrisat_dld": ["SOYABEAN", "SOYBEAN"],
            "des_dacnet": ["Soyabean", "Soybean"],
            "faostat": ["Soya beans", "Soybeans"],
        },
        typical_yield_range_t_ha=(0.1, 4.5),
        nitrogen_fixing=True,
        water_intensity="medium",
    ),
    "rice": CropSpecification(
        crop_id="rice",
        display_name="Rice (Paddy)",
        category=CropCategory.CEREAL,
        scientific_name="Oryza sativa",
        default_season="Kharif",
        supported_seasons=["Kharif", "Summer"],
        source_aliases={
            "icrisat_dld": ["RICE", "PADDY"],
            "des_dacnet": ["Rice", "Paddy"],
            "faostat": ["Rice, paddy"],
        },
        typical_yield_range_t_ha=(0.2, 8.0),
        nitrogen_fixing=False,
        water_intensity="very_high",
    ),
    "wheat": CropSpecification(
        crop_id="wheat",
        display_name="Wheat",
        category=CropCategory.CEREAL,
        scientific_name="Triticum aestivum",
        default_season="Rabi",
        supported_seasons=["Rabi"],
        source_aliases={
            "icrisat_dld": ["WHEAT"],
            "des_dacnet": ["Wheat"],
            "faostat": ["Wheat"],
        },
        typical_yield_range_t_ha=(0.2, 6.5),
        nitrogen_fixing=False,
        water_intensity="medium",
    ),
    "cotton": CropSpecification(
        crop_id="cotton",
        display_name="Cotton",
        category=CropCategory.CASH_CROP,
        scientific_name="Gossypium hirsutum",
        default_season="Kharif",
        supported_seasons=["Kharif"],
        source_aliases={
            "icrisat_dld": ["COTTON"],
            "des_dacnet": ["Cotton(lint)", "Cotton"],
            "faostat": ["Seed cotton", "Cotton lint"],
        },
        typical_yield_range_t_ha=(0.05, 3.5),
        nitrogen_fixing=False,
        water_intensity="medium",
    ),
    "maize": CropSpecification(
        crop_id="maize",
        display_name="Maize (Corn)",
        category=CropCategory.CEREAL,
        scientific_name="Zea mays",
        default_season="Kharif",
        supported_seasons=["Kharif", "Rabi"],
        source_aliases={
            "icrisat_dld": ["MAIZE", "CORN"],
            "des_dacnet": ["Maize"],
            "faostat": ["Maize"],
        },
        typical_yield_range_t_ha=(0.2, 8.0),
        nitrogen_fixing=False,
        water_intensity="medium",
    ),
    "chickpea": CropSpecification(
        crop_id="chickpea",
        display_name="Chickpea (Gram)",
        category=CropCategory.PULSE,
        scientific_name="Cicer arietinum",
        default_season="Rabi",
        supported_seasons=["Rabi"],
        source_aliases={
            "icrisat_dld": ["CHICKPEA", "GRAM", "BENGAL GRAM"],
            "des_dacnet": ["Gram", "Chickpea"],
            "faostat": ["Chick peas"],
        },
        typical_yield_range_t_ha=(0.1, 3.5),
        nitrogen_fixing=True,
        water_intensity="low",
    ),
    "groundnut": CropSpecification(
        crop_id="groundnut",
        display_name="Groundnut (Peanut)",
        category=CropCategory.OILSEED,
        scientific_name="Arachis hypogaea",
        default_season="Kharif",
        supported_seasons=["Kharif", "Summer"],
        source_aliases={
            "icrisat_dld": ["GROUNDNUT", "PEANUT"],
            "des_dacnet": ["Groundnut"],
            "faostat": ["Groundnuts, with shell"],
        },
        typical_yield_range_t_ha=(0.1, 4.0),
        nitrogen_fixing=True,
        water_intensity="medium",
    ),
    "pigeon_pea": CropSpecification(
        crop_id="pigeon_pea",
        display_name="Pigeon Pea (Tur / Arhar)",
        category=CropCategory.PULSE,
        scientific_name="Cajanus cajan",
        default_season="Kharif",
        supported_seasons=["Kharif"],
        source_aliases={
            "icrisat_dld": ["PIGEONPEA", "TUR", "ARHAR"],
            "des_dacnet": ["Arhar/Tur", "Tur", "Pigeon Pea"],
            "faostat": ["Pigeon peas"],
        },
        typical_yield_range_t_ha=(0.1, 3.0),
        nitrogen_fixing=True,
        water_intensity="low",
    ),
    "sugarcane": CropSpecification(
        crop_id="sugarcane",
        display_name="Sugarcane",
        category=CropCategory.CASH_CROP,
        scientific_name="Saccharum officinarum",
        default_season="Whole Year",
        supported_seasons=["Whole Year", "Kharif"],
        source_aliases={
            "icrisat_dld": ["SUGARCANE"],
            "des_dacnet": ["Sugarcane"],
            "faostat": ["Sugar cane"],
        },
        typical_yield_range_t_ha=(10.0, 160.0),
        nitrogen_fixing=False,
        water_intensity="very_high",
    ),
    "sorghum": CropSpecification(
        crop_id="sorghum",
        display_name="Sorghum (Jowar)",
        category=CropCategory.CEREAL,
        scientific_name="Sorghum bicolor",
        default_season="Kharif",
        supported_seasons=["Kharif", "Rabi"],
        source_aliases={
            "icrisat_dld": ["SORGHUM", "KHARIF SORGHUM", "RABI SORGHUM", "JOWAR"],
            "des_dacnet": ["Jowar", "Sorghum"],
            "faostat": ["Sorghum"],
        },
        typical_yield_range_t_ha=(0.1, 4.5),
        nitrogen_fixing=False,
        water_intensity="low",
    ),
}


# Precomputed inverted alias lookup index: alias_lower -> crop_id
_ALIAS_LOOKUP_CACHE: Dict[str, str] = {}

for cid, spec in CROP_REGISTRY.items():
    _ALIAS_LOOKUP_CACHE[cid.lower()] = cid
    _ALIAS_LOOKUP_CACHE[spec.display_name.lower()] = cid
    _ALIAS_LOOKUP_CACHE[spec.scientific_name.lower()] = cid
    for source_key, aliases in spec.source_aliases.items():
        for alias in aliases:
            _ALIAS_LOOKUP_CACHE[alias.lower().strip()] = cid


def resolve_crop(query: str, source_hint: Optional[str] = None) -> Optional[CropSpecification]:
    """Resolve a raw crop string or source alias to a canonical CropSpecification.

    Args:
        query: Crop name, alias, or ID (e.g. 'SOYABEAN', 'rice', 'Gram', 'Jowar').
        source_hint: Optional source identifier (e.g. 'icrisat_dld') to disambiguate.

    Returns:
        CropSpecification if recognized, None otherwise.
    """
    if not query or not isinstance(query, str):
        return None

    cleaned = query.strip().lower()

    # Exact key match
    if cleaned in CROP_REGISTRY:
        return CROP_REGISTRY[cleaned]

    # Inverted alias lookup
    if cleaned in _ALIAS_LOOKUP_CACHE:
        return CROP_REGISTRY[_ALIAS_LOOKUP_CACHE[cleaned]]

    # Normalized whitespace/hyphen fallback
    normalized_query = cleaned.replace("-", " ").replace("_", " ")
    for alias, cid in _ALIAS_LOOKUP_CACHE.items():
        if alias.replace("-", " ").replace("_", " ") == normalized_query:
            return CROP_REGISTRY[cid]

    return None


def list_registered_crops() -> List[CropSpecification]:
    """Return all registered crops ordered by display name."""
    return sorted(list(CROP_REGISTRY.values()), key=lambda c: c.display_name)
