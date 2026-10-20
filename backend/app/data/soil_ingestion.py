"""ISRIC SoilGrids 2.0 Ingestion and Pedological Profile Builder.

Queries the ISRIC SoilGrids 2.0 REST API for Maharashtra district agricultural
locations. Calculates depth-weighted averages across the topsoil layer (0-30cm),
applies documented unit conversions, and normalizes soil texture fractions.
"""

import os
import json
import time
import requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Tuple, Optional
from app.data.config import data_config
from app.data.districts import MAHARASHTRA_DISTRICTS, DistrictMetadata
from app.data.schemas import DistrictSoilProfile


class SoilIngestionService:
    """Ingestion and feature engineering service for ISRIC SoilGrids 2.0."""

    def __init__(self, config=data_config):
        self.config = config
        self.raw_soil_dir = os.path.join(self.config.RAW_DATA_DIR, "soil")
        os.makedirs(self.raw_soil_dir, exist_ok=True)
        os.makedirs(self.config.INTERIM_DATA_DIR, exist_ok=True)

    def fetch_soilgrids_point(
        self,
        district_name: str,
        lon: float,
        lat: float,
        force_download: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Query SoilGrids REST API for topsoil properties at a coordinate point."""
        safe_name = district_name.lower().replace(" ", "_")
        cache_file = os.path.join(
            self.raw_soil_dir, f"soilgrids_{safe_name}_{lon:.2f}_{lat:.2f}.json"
        )

        if os.path.exists(cache_file) and not force_download:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        properties = ["phh2o", "soc", "clay", "sand", "silt", "bdod", "cec"]
        depths = ["0-5cm", "5-15cm", "15-30cm"]

        params_query = "&".join([f"property={p}" for p in properties])
        depths_query = "&".join([f"depth={d}" for d in depths])
        url = f"{self.config.SOILGRIDS_BASE_URL}?lon={lon}&lat={lat}&{params_query}&{depths_query}"

        request_timeout = 15

        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = requests.get(
                    url,
                    headers={"accept": "application/json"},
                    timeout=request_timeout,
                )
                if response.status_code == 200:
                    data = response.json()
                    layers = data.get("properties", {}).get("layers", [])
                    has_data = any(
                        l.get("depths", [{}])[0].get("values", {}).get("mean") is not None
                        for l in layers
                    )
                    if has_data:
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                        return data
                elif response.status_code == 429:
                    time.sleep(1.0 * (attempt + 1))
            except Exception:
                time.sleep(0.5 * (attempt + 1))

        return None

    def calculate_topsoil_weighted_mean(
        self,
        district_name: str,
        soil_json: Dict[str, Any],
        lon: float,
        lat: float,
    ) -> DistrictSoilProfile:
        """Compute depth-weighted mean (0-30cm) and convert raw SoilGrids units."""
        layers_dict = {
            layer["name"]: layer for layer in soil_json.get("properties", {}).get("layers", [])
        }

        # Depths and their thickness weights (total = 30cm)
        depth_weights = {
            "0-5cm": 5.0 / 30.0,
            "5-15cm": 10.0 / 30.0,
            "15-30cm": 15.0 / 30.0,
        }

        def get_weighted_value(layer_name: str, default_val: float) -> float:
            layer = layers_dict.get(layer_name)
            if not layer:
                return default_val

            total_weight = 0.0
            weighted_sum = 0.0

            for depth_entry in layer.get("depths", []):
                label = depth_entry.get("label")
                weight = depth_weights.get(label, 0.0)
                mean_val = depth_entry.get("values", {}).get("mean")

                if mean_val is not None:
                    weighted_sum += mean_val * weight
                    total_weight += weight

            if total_weight > 0.0:
                return weighted_sum / total_weight
            return default_val

        # Extract weighted values in SoilGrids mapped units
        raw_ph = get_weighted_value("phh2o", 72.0)
        raw_soc = get_weighted_value("soc", 65.0)
        raw_clay = get_weighted_value("clay", 420.0)
        raw_sand = get_weighted_value("sand", 240.0)
        raw_silt = get_weighted_value("silt", 340.0)
        raw_bdod = get_weighted_value("bdod", 135.0)
        raw_cec = get_weighted_value("cec", 360.0)

        # Unit conversions:
        soil_ph = round(raw_ph / 10.0, 2)
        organic_carbon_pct = round(raw_soc / 100.0, 3)
        clay_pct = round(raw_clay / 10.0, 2)
        sand_pct = round(raw_sand / 10.0, 2)
        silt_pct = round(raw_silt / 10.0, 2)
        bulk_density_g_cm3 = round(raw_bdod / 100.0, 2)
        cation_exchange_capacity_cmol_kg = round(raw_cec / 10.0, 2)

        # Normalize texture fractions
        texture_sum = clay_pct + sand_pct + silt_pct
        if texture_sum > 0:
            clay_pct = round((clay_pct / texture_sum) * 100.0, 2)
            sand_pct = round((sand_pct / texture_sum) * 100.0, 2)
            silt_pct = round(100.0 - clay_pct - sand_pct, 2)

        return DistrictSoilProfile(
            district=district_name,
            latitude=lat,
            longitude=lon,
            sampling_point_type="rural_agricultural_centroid",
            depth_interval="0-30cm_weighted_mean",
            soil_ph=soil_ph,
            organic_carbon_pct=organic_carbon_pct,
            clay_pct=clay_pct,
            sand_pct=sand_pct,
            silt_pct=silt_pct,
            bulk_density_g_cm3=bulk_density_g_cm3,
            cation_exchange_capacity_cmol_kg=cation_exchange_capacity_cmol_kg,
        )

    def _process_single_district(
        self, dist_name: str, force_download: bool
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        district_meta = MAHARASHTRA_DISTRICTS.get(dist_name)
        if not district_meta:
            return None, {"district": dist_name, "error": "District metadata not registered"}

        candidates = [(district_meta.longitude, district_meta.latitude)] + district_meta.fallback_coords

        for lon, lat in candidates:
            data = self.fetch_soilgrids_point(
                district_name=dist_name,
                lon=lon,
                lat=lat,
                force_download=force_download,
            )
            if data is not None:
                profile = self.calculate_topsoil_weighted_mean(
                    district_name=dist_name,
                    soil_json=data,
                    lon=lon,
                    lat=lat,
                )
                return profile.model_dump(), None

        return None, {
            "district": dist_name,
            "error": "All coordinates returned nodata/unresponsive",
        }

    def process_all_districts(
        self,
        districts: List[str],
        force_download: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch and build topsoil profiles across all target districts concurrently."""
        profiles = []
        errors = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(
                executor.map(
                    lambda d: self._process_single_district(d, force_download),
                    districts,
                )
            )

        for prof, err in results:
            if prof:
                profiles.append(prof)
            if err:
                errors.append(err)

        df_soil = pd.DataFrame(profiles)
        if not df_soil.empty:
            df_soil = df_soil.sort_values(by="district").reset_index(drop=True)

        interim_path = os.path.join(self.config.INTERIM_DATA_DIR, "soil_maharashtra.csv")
        df_soil.to_csv(interim_path, index=False)

        metadata = {
            "districts_requested": len(districts),
            "successful_profiles": len(profiles),
            "errors": errors,
            "interim_output_path": interim_path,
        }

        return df_soil, metadata
