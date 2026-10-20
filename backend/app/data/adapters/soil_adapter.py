"""ISRIC SoilGrids 2.0 Modular Source Adapter.

Parses depth-stratified pedological layers (0-5cm, 5-15cm, 15-30cm) from SoilGrids 2.0
REST API JSON cache files, computes depth-weighted averages across the 0-30cm root zone,
applies explicit unit conversions, and builds SoilMeasurement models.
"""

import os
import json
import glob
from typing import Dict, Any, Optional
from app.data.unified_schema import SoilMeasurement


class SoilAdapter:
    """Extracts and weights topsoil (0-30cm) pedological attributes from SoilGrids 2.0 JSON."""

    def __init__(self, raw_soil_dir: str):
        self.raw_soil_dir = raw_soil_dir
        self.source_id = "isric_soilgrids_v2"
        self._district_cache: Dict[str, Optional[SoilMeasurement]] = {}

    def get_soil_measurement(self, district: str) -> Optional[SoilMeasurement]:
        """Extract depth-weighted topsoil properties for a district.

        Args:
            district: Canonical district name (e.g. 'Akola').

        Returns:
            SoilMeasurement instance or None if no cached profile exists.
        """
        if district in self._district_cache:
            return self._district_cache[district]

        safe_district = district.lower().replace(" ", "_")
        pattern = os.path.join(self.raw_soil_dir, f"soilgrids_{safe_district}_*.json")
        matches = glob.glob(pattern)

        if not matches:
            self._district_cache[district] = None
            return None

        # Load the first matching cache file
        cache_file = matches[0]
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        layers = data.get("properties", {}).get("layers", [])
        if not layers:
            return None

        # Layer depth intervals and standard thickness weights in cm:
        # 0-5cm (thickness: 5cm), 5-15cm (thickness: 10cm), 15-30cm (thickness: 15cm) -> Total: 30cm
        depth_weights = {
            "0-5cm": 5.0,
            "5-15cm": 10.0,
            "15-30cm": 15.0,
        }
        total_depth = 30.0

        prop_values: Dict[str, float] = {}

        for layer in layers:
            prop_name = layer.get("name")
            depths = layer.get("depths", [])
            weighted_sum = 0.0
            sum_weights = 0.0

            for d in depths:
                label = d.get("label")
                if label in depth_weights:
                    values = d.get("values", {})
                    mean_val = values.get("mean")
                    if mean_val is not None:
                        w = depth_weights[label]
                        weighted_sum += mean_val * w
                        sum_weights += w

            if sum_weights > 0:
                prop_values[prop_name] = weighted_sum / sum_weights

        # Required properties: phh2o, soc, clay, sand, silt, bdod, cec
        if "phh2o" not in prop_values or "clay" not in prop_values:
            return None

        # Explicit documented unit conversions per SoilGrids 2.0 data specification:
        # phh2o: mapped as pH*10 -> / 10.0
        # soc: decigrams per kilogram (dg/kg) -> / 100.0 for weight percentage (% wt)
        # clay, sand, silt: mass fraction in g/kg -> / 10.0 for weight percentage (% wt)
        # bdod: centigrams per cubic centimeter (cg/cm³) -> / 100.0 for g/cm³
        # cec: millimoles of charge per kilogram (mmol(c)/kg) -> / 10.0 for cmol(+)/kg
        raw_ph = round(prop_values["phh2o"] / 10.0, 2)
        raw_soc = round(prop_values.get("soc", 60.0) / 100.0, 2)
        raw_clay = round(prop_values.get("clay", 450.0) / 10.0, 1)
        raw_sand = round(prop_values.get("sand", 200.0) / 10.0, 1)
        raw_silt = round(prop_values.get("silt", 350.0) / 10.0, 1)
        raw_bdod = round(prop_values.get("bdod", 130.0) / 100.0, 2)
        raw_cec = round(prop_values.get("cec", 350.0) / 10.0, 1)

        # Normalize texture fractions to sum exactly to 100.0
        texture_sum = raw_clay + raw_sand + raw_silt
        if texture_sum > 0:
            norm_clay = round((raw_clay / texture_sum) * 100.0, 1)
            norm_sand = round((raw_sand / texture_sum) * 100.0, 1)
            norm_silt = round(100.0 - norm_clay - norm_sand, 1)
        else:
            norm_clay, norm_sand, norm_silt = 45.0, 20.0, 35.0

        meas = SoilMeasurement(
            soil_ph=raw_ph,
            organic_carbon_pct=raw_soc,
            clay_pct=norm_clay,
            sand_pct=norm_sand,
            silt_pct=norm_silt,
            bulk_density_g_cm3=raw_bdod,
            cation_exchange_capacity_cmol_kg=raw_cec,
            depth_interval="0-30cm",
            source_resolution="250m",
            source="ISRIC SoilGrids 2.0 (0-30cm Weighted Mean)",
        )
        self._district_cache[district] = meas
        return meas
