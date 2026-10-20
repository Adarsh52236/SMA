"""NASA POWER Daily Agroclimatology Ingestion and Seasonal Aggregator.

Retrieves daily meteorological observations from NASA POWER for Maharashtra
districts and aggregates them across the Kharif growing season (June 1 - October 31).
Calculates cumulative rainfall, mean temperatures, solar insolation,
relative humidity, consecutive dry days, and heat stress days.
"""

import os
import json
import time
import requests
import pandas as pd
from typing import Dict, Any, List, Tuple
from app.data.config import data_config
from app.data.districts import MAHARASHTRA_DISTRICTS, DistrictMetadata
from app.data.schemas import SeasonalWeatherRecord


class WeatherIngestionService:
    """Ingestion and seasonal aggregation service for NASA POWER agroclimatology."""

    def __init__(self, config=data_config):
        self.config = config
        self.raw_weather_dir = os.path.join(self.config.RAW_DATA_DIR, "weather")
        os.makedirs(self.raw_weather_dir, exist_ok=True)
        os.makedirs(self.config.INTERIM_DATA_DIR, exist_ok=True)

    def fetch_district_daily_weather(
        self,
        district_name: str,
        start_year: int,
        end_year: int,
        force_download: bool = False,
    ) -> Dict[str, Any]:
        """Fetch daily weather parameters from NASA POWER or local JSON cache."""
        district_meta = MAHARASHTRA_DISTRICTS.get(district_name)
        if not district_meta:
            raise ValueError(f"Unknown district '{district_name}' for weather retrieval.")

        safe_name = district_name.lower().replace(" ", "_")
        cache_file = os.path.join(
            self.raw_weather_dir, f"nasa_power_{safe_name}_{start_year}_{end_year}.json"
        )

        if os.path.exists(cache_file) and not force_download:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        start_date = f"{start_year}0101"
        end_date = f"{end_year}1231"
        params = [
            "PRECTOTCORR",
            "T2M_MAX",
            "T2M_MIN",
            "ALLSKY_SFC_SW_DWN",
            "RH2M",
        ]

        query_url = (
            f"{self.config.NASA_POWER_BASE_URL}?"
            f"parameters={','.join(params)}&"
            f"community=AG&"
            f"longitude={district_meta.longitude}&"
            f"latitude={district_meta.latitude}&"
            f"start={start_date}&"
            f"end={end_date}&"
            f"format=JSON"
        )

        last_error = None
        for attempt in range(self.config.MAX_RETRIES):
            try:
                response = requests.get(
                    query_url,
                    timeout=self.config.REQUEST_TIMEOUT_SECONDS,
                )
                if response.status_code == 200:
                    data = response.json()
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    return data
                elif response.status_code == 429:
                    time.sleep(self.config.RETRY_BACKOFF_FACTOR * (attempt + 1) * 2)
                else:
                    response.raise_for_status()
            except Exception as e:
                last_error = e
                time.sleep(self.config.RETRY_BACKOFF_FACTOR * (attempt + 1))

        raise RuntimeError(
            f"Failed to fetch NASA POWER data for {district_name} after {self.config.MAX_RETRIES} attempts. Error: {last_error}"
        )

    def aggregate_kharif_season(
        self,
        district_name: str,
        weather_json: Dict[str, Any],
        start_year: int,
        end_year: int,
    ) -> List[SeasonalWeatherRecord]:
        """Aggregate daily parameters into Kharif seasonal indices per year."""
        params_dict = (
            weather_json.get("properties", {}).get("parameter", {})
        )
        precip_series = params_dict.get("PRECTOTCORR", {})
        tmax_series = params_dict.get("T2M_MAX", {})
        tmin_series = params_dict.get("T2M_MIN", {})
        solar_series = params_dict.get("ALLSKY_SFC_SW_DWN", {})
        rh_series = params_dict.get("RH2M", {})

        seasonal_records = []

        start_md = self.config.KHARIF_START_MONTH_DAY.replace("-", "")
        end_md = self.config.KHARIF_END_MONTH_DAY.replace("-", "")

        for year in range(start_year, end_year + 1):
            season_start = f"{year}{start_md}"
            season_end = f"{year}{end_md}"

            # Filter dates in Kharif window
            dates = [d for d in sorted(precip_series.keys()) if season_start <= d <= season_end]
            if not dates:
                continue

            precip_vals = []
            tmax_vals = []
            tmin_vals = []
            solar_vals = []
            rh_vals = []
            missing_count = 0

            # Dry spell tracker (consecutive days with rain < 2.5mm)
            current_dry_streak = 0
            max_dry_streak = 0
            heat_stress_count = 0

            for d in dates:
                p = precip_series.get(d, -999.0)
                tx = tmax_series.get(d, -999.0)
                tn = tmin_series.get(d, -999.0)
                sol = solar_series.get(d, -999.0)
                rh = rh_series.get(d, -999.0)

                # Check for NASA POWER nodata flag (-999.0)
                if any(v == -999.0 for v in [p, tx, tn, sol, rh]):
                    missing_count += 1
                    continue

                precip_vals.append(p)
                tmax_vals.append(tx)
                tmin_vals.append(tn)
                solar_vals.append(sol)
                rh_vals.append(rh)

                # Dry spell logic
                if p < 2.5:
                    current_dry_streak += 1
                    if current_dry_streak > max_dry_streak:
                        max_dry_streak = current_dry_streak
                else:
                    current_dry_streak = 0

                # Heat stress (temp max >= 35°C during vegetative/reproductive stage)
                if tx >= 35.0:
                    heat_stress_count += 1

            valid_days = len(precip_vals)
            if valid_days == 0:
                continue

            rec = SeasonalWeatherRecord(
                district=district_name,
                year=year,
                season=self.config.TARGET_SEASON,
                start_date=f"{year}-{self.config.KHARIF_START_MONTH_DAY}",
                end_date=f"{year}-{self.config.KHARIF_END_MONTH_DAY}",
                total_days=len(dates),
                missing_days=missing_count,
                cumulative_rainfall_mm=round(sum(precip_vals), 2),
                mean_temp_max_c=round(sum(tmax_vals) / valid_days, 2),
                mean_temp_min_c=round(sum(tmin_vals) / valid_days, 2),
                mean_solar_radiation_mj_m2=round(sum(solar_vals) / valid_days, 2),
                mean_relative_humidity_pct=round(sum(rh_vals) / valid_days, 2),
                consecutive_dry_days_max=max_dry_streak,
                heat_stress_days=heat_stress_count,
            )
            seasonal_records.append(rec)

        return seasonal_records

    def process_all_districts(
        self,
        districts: List[str],
        start_year: int = 1990,
        end_year: int = 2017,
        force_download: bool = False,
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Fetch and aggregate seasonal weather across all requested districts."""
        all_records = []
        errors = []

        for dist_name in districts:
            try:
                weather_json = self.fetch_district_daily_weather(
                    district_name=dist_name,
                    start_year=start_year,
                    end_year=end_year,
                    force_download=force_download,
                )
                recs = self.aggregate_kharif_season(
                    district_name=dist_name,
                    weather_json=weather_json,
                    start_year=start_year,
                    end_year=end_year,
                )
                all_records.extend([r.model_dump() for r in recs])
            except Exception as e:
                errors.append({"district": dist_name, "error": str(e)})

        df_weather = pd.DataFrame(all_records)
        if not df_weather.empty:
            df_weather = df_weather.sort_values(by=["district", "year"]).reset_index(drop=True)

        interim_path = os.path.join(
            self.config.INTERIM_DATA_DIR, "weather_kharif_maharashtra.csv"
        )
        df_weather.to_csv(interim_path, index=False)

        metadata = {
            "districts_requested": len(districts),
            "successful_districts": len(districts) - len(errors),
            "errors": errors,
            "total_seasonal_records": len(df_weather),
            "years_range": [start_year, end_year],
            "interim_output_path": interim_path,
        }

        return df_weather, metadata
