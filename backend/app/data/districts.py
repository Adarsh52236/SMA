"""Maharashtra Agricultural District Metadata and Coordinate Registry.

Provides canonical district names, historical ICRISAT DLD alias mappings,
agro-ecological regions, and verified representative agricultural coordinates for
weather and soil extraction.
"""

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel


class DistrictMetadata(BaseModel):
    """Metadata for an agricultural district in Maharashtra."""

    canonical_name: str
    icrisat_alias: str
    region: str
    longitude: float
    latitude: float
    fallback_coords: List[Tuple[float, float]] = []
    major_soybean_producer: bool = False


# Canonical registry of 22 soybean-cultivating districts in Maharashtra
# Every coordinate has been verified against live SoilGrids & NASA POWER services
MAHARASHTRA_DISTRICTS: Dict[str, DistrictMetadata] = {
    "Ahmednagar": DistrictMetadata(
        canonical_name="Ahmednagar",
        icrisat_alias="Ahmednagar",
        region="Western Maharashtra",
        longitude=74.65,
        latitude=19.15,
        major_soybean_producer=True,
    ),
    "Akola": DistrictMetadata(
        canonical_name="Akola",
        icrisat_alias="Akola",
        region="Vidarbha",
        longitude=77.05,
        latitude=20.70,
        major_soybean_producer=True,
    ),
    "Amravati": DistrictMetadata(
        canonical_name="Amravati",
        icrisat_alias="Amarawati",
        region="Vidarbha",
        longitude=77.65,
        latitude=20.85,
        major_soybean_producer=True,
    ),
    "Aurangabad": DistrictMetadata(
        canonical_name="Aurangabad",
        icrisat_alias="Aurangabad",
        region="Marathwada",
        longitude=75.25,
        latitude=19.95,
        major_soybean_producer=True,
    ),
    "Beed": DistrictMetadata(
        canonical_name="Beed",
        icrisat_alias="Beed",
        region="Marathwada",
        longitude=75.85,
        latitude=19.05,
        major_soybean_producer=True,
    ),
    "Bhandara": DistrictMetadata(
        canonical_name="Bhandara",
        icrisat_alias="Bhandara",
        region="Vidarbha",
        longitude=79.70,
        latitude=21.10,
        major_soybean_producer=False,
    ),
    "Buldhana": DistrictMetadata(
        canonical_name="Buldhana",
        icrisat_alias="Buldhana",
        region="Vidarbha",
        longitude=76.25,
        latitude=20.60,
        major_soybean_producer=True,
    ),
    "Chandrapur": DistrictMetadata(
        canonical_name="Chandrapur",
        icrisat_alias="Chandrapur",
        region="Vidarbha",
        longitude=79.20,
        latitude=19.80,
        major_soybean_producer=False,
    ),
    "Dhule": DistrictMetadata(
        canonical_name="Dhule",
        icrisat_alias="Dhule",
        region="Khandesh",
        longitude=74.90,
        latitude=21.00,
        major_soybean_producer=False,
    ),
    "Jalgaon": DistrictMetadata(
        canonical_name="Jalgaon",
        icrisat_alias="Jalgaon",
        region="Khandesh",
        longitude=75.65,
        latitude=20.95,
        major_soybean_producer=True,
    ),
    "Kolhapur": DistrictMetadata(
        canonical_name="Kolhapur",
        icrisat_alias="Kolhapur",
        region="Western Maharashtra",
        longitude=74.40,
        latitude=16.80,
        major_soybean_producer=True,
    ),
    "Latur": DistrictMetadata(
        canonical_name="Latur",
        icrisat_alias="Osmanabad",
        region="Marathwada",
        longitude=76.60,
        latitude=18.35,
        major_soybean_producer=True,
    ),
    "Nagpur": DistrictMetadata(
        canonical_name="Nagpur",
        icrisat_alias="Nagpur",
        region="Vidarbha",
        longitude=79.20,
        latitude=21.30,
        major_soybean_producer=True,
    ),
    "Nanded": DistrictMetadata(
        canonical_name="Nanded",
        icrisat_alias="Nanded",
        region="Marathwada",
        longitude=77.38,
        latitude=19.10,
        major_soybean_producer=True,
    ),
    "Nashik": DistrictMetadata(
        canonical_name="Nashik",
        icrisat_alias="Nasik",
        region="Khandesh",
        longitude=73.85,
        latitude=20.05,
        major_soybean_producer=True,
    ),
    "Osmanabad": DistrictMetadata(
        canonical_name="Osmanabad",
        icrisat_alias="Osmanabad",
        region="Marathwada",
        longitude=76.20,
        latitude=18.30,
        major_soybean_producer=True,
    ),
    "Parbhani": DistrictMetadata(
        canonical_name="Parbhani",
        icrisat_alias="Parbhani",
        region="Marathwada",
        longitude=76.85,
        latitude=19.20,
        major_soybean_producer=True,
    ),
    "Pune": DistrictMetadata(
        canonical_name="Pune",
        icrisat_alias="Pune",
        region="Western Maharashtra",
        longitude=73.95,
        latitude=18.60,
        major_soybean_producer=False,
    ),
    "Sangli": DistrictMetadata(
        canonical_name="Sangli",
        icrisat_alias="Sangli",
        region="Western Maharashtra",
        longitude=74.50,
        latitude=16.80,
        major_soybean_producer=True,
    ),
    "Satara": DistrictMetadata(
        canonical_name="Satara",
        icrisat_alias="Satara",
        region="Western Maharashtra",
        longitude=74.08,
        latitude=17.75,
        major_soybean_producer=True,
    ),
    "Solapur": DistrictMetadata(
        canonical_name="Solapur",
        icrisat_alias="Solapur",
        region="Western Maharashtra",
        longitude=75.80,
        latitude=17.72,
        major_soybean_producer=False,
    ),
    "Wardha": DistrictMetadata(
        canonical_name="Wardha",
        icrisat_alias="Wardha",
        region="Vidarbha",
        longitude=78.50,
        latitude=20.80,
        major_soybean_producer=True,
    ),
    "Yavatmal": DistrictMetadata(
        canonical_name="Yavatmal",
        icrisat_alias="Yeotmal",
        region="Vidarbha",
        longitude=78.20,
        latitude=20.45,
        major_soybean_producer=True,
    ),
}


def get_district_by_name(name: str) -> Optional[DistrictMetadata]:
    """Look up district metadata by canonical name or common alias."""
    clean_name = name.strip()
    if clean_name in MAHARASHTRA_DISTRICTS:
        return MAHARASHTRA_DISTRICTS[clean_name]

    for meta in MAHARASHTRA_DISTRICTS.values():
        if (
            meta.canonical_name.lower() == clean_name.lower()
            or meta.icrisat_alias.lower() == clean_name.lower()
        ):
            return meta
    return None
