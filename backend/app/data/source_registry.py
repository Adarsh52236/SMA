"""Data Source Registry and Provenance Metadata.

Catalogues all external data sources, exact API endpoints, spatial/temporal
resolutions, licensing requirements, and operational constraints.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class DataSourceInfo(BaseModel):
    """Metadata specification for an official external data source."""

    source_id: str
    name: str
    organization: str
    url: str
    endpoint_or_download: str
    license: str
    attribution: str
    spatial_coverage: str
    temporal_coverage: str
    reported_variables: List[str]
    access_method: str
    rate_limits_or_constraints: str
    known_limitations: List[str]


DATA_SOURCES: Dict[str, DataSourceInfo] = {
    "crop_statistics": DataSourceInfo(
        source_id="icrisat_des_dld",
        name="ICRISAT-TCI District Level Database (DLD) for Indian Agriculture",
        organization="ICRISAT & Directorate of Economics and Statistics (DES), Ministry of Agriculture & Farmers Welfare, India",
        url="http://data.icrisat.org/dld/",
        endpoint_or_download="https://raw.githubusercontent.com/Runax15/crop-yield-prediction-maharashtra/main/crop_data.csv",
        license="Open Access for Research & Development (ICRISAT / Government of India)",
        attribution="ICRISAT-TCI District Level Database (DLD) for Indian Agriculture (1966-2017), harmonized to 1966 district boundaries.",
        spatial_coverage="26 historical districts of Maharashtra, India",
        temporal_coverage="1966 - 2017 (Soybean commercial adoption: ~1990 - 2017)",
        reported_variables=[
            "Year",
            "Dist Name",
            "Crop",
            "Area(1000 ha)",
            "Production(1000 tons)",
            "Yield(Kg per ha)",
        ],
        access_method="Direct CSV download / local caching",
        rate_limits_or_constraints="Static public repository mirror with verifiable provenance",
        known_limitations=[
            "Data is harmonized to 1966 district boundary definitions; newer bifurcations (e.g. Washim from Akola) are reported within parent districts.",
            "Raw file contains duplicated records from concatenated tables that must be explicitly deduplicated during normalization.",
            "Reports gross cultivated area and production; farm-level input variations (seeds, irrigation, fertilizer) are aggregated out.",
        ],
    ),
    "weather": DataSourceInfo(
        source_id="nasa_power_daily",
        name="NASA POWER Agroclimatology Daily Point API",
        organization="NASA Langley Research Center (LaRC)",
        url="https://power.larc.nasa.gov/",
        endpoint_or_download="https://power.larc.nasa.gov/api/temporal/daily/point",
        license="NASA Open Science Data Policy (Public Domain)",
        attribution="NASA Prediction Of Worldwide Energy Resources (POWER) Project, Agroclimatology Daily Archive.",
        spatial_coverage="Global gridded (0.5° latitude x 0.5° longitude / ~50km grid cells)",
        temporal_coverage="1981 - present (Daily temporal grain)",
        reported_variables=[
            "PRECTOTCORR: Corrected Precipitation (mm/day)",
            "T2M_MAX: Maximum Temperature at 2m (°C)",
            "T2M_MIN: Minimum Temperature at 2m (°C)",
            "ALLSKY_SFC_SW_DWN: All Sky Surface Shortwave Downward Insolation (MJ/m²/day)",
            "RH2M: Relative Humidity at 2m (%)",
        ],
        access_method="HTTP REST API (JSON format) with district representative coordinates",
        rate_limits_or_constraints="Up to 30 requests/min; supports multi-year date ranges in single queries",
        known_limitations=[
            "Meteorological estimates derived from assimilation models (MERRA-2 / GEOS) and satellite observations, not point weather stations.",
            "0.5° spatial grid smooths localized convective cloudbursts and hilly terrain rainfall gradients.",
            "District representative coordinates approximate county-wide weather but cannot capture intra-district microclimates.",
        ],
    ),
    "soil": DataSourceInfo(
        source_id="isric_soilgrids_v2",
        name="ISRIC SoilGrids 2.0 Global Soil Information",
        organization="ISRIC - World Soil Information",
        url="https://www.isric.org/explore/soilgrids",
        endpoint_or_download="https://rest.isric.org/soilgrids/v2.0/properties/query",
        license="Open Database License (ODbL) v1.0",
        attribution="Poggio, L., de Sousa, L. M., Batjes, N. H., et al. (2021). SoilGrids 2.0: producing soil property maps with machine learning. SOIL, 7, 217-240.",
        spatial_coverage="Global gridded at 250-meter spatial resolution",
        temporal_coverage="Static baseline representation (depth intervals: 0-5cm, 5-15cm, 15-30cm)",
        reported_variables=[
            "phh2o: Soil pH in H2O solution (pH*10)",
            "soc: Soil organic carbon content (dg/kg -> g/kg / %)",
            "clay: Clay content fraction (<2um) (g/kg -> %)",
            "sand: Sand content fraction (50-2000um) (g/kg -> %)",
            "silt: Silt content fraction (2-50um) (g/kg -> %)",
            "bdod: Bulk density of the fine earth fraction (cg/cm³ -> g/cm³)",
            "cec: Cation exchange capacity at pH 7 (mmol(c)/kg -> cmol(+)/kg)",
        ],
        access_method="HTTP REST API (GeoJSON Point Query) & Web Coverage Service (WCS)",
        rate_limits_or_constraints="Approx 5-10 requests/sec; rate-limited; urban/water pixels map to nodata (None)",
        known_limitations=[
            "Represents machine learning predictions derived from global soil profile data and environmental covariates, not direct soil tests on individual farms.",
            "Static profiles do not reflect seasonal changes in soil moisture or farmer tillage/fertilizer additions.",
            "Urban coordinates return nodata, requiring rural agricultural fallback sampling.",
        ],
    ),
}
