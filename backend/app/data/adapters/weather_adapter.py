"""NASA POWER Agroclimatology Modular Source Adapter.

Aggregates daily meteorological records from NASA POWER point API JSON files
into canonical WeatherMeasurement models for arbitrary crop growing seasons
(Kharif, Rabi, Summer, Whole Year), accounting for cross-calendar-year windows.
"""

import os
import json
import datetime
from typing import Dict, Any, Optional, Tuple
from app.data.unified_schema import WeatherMeasurement
from app.data.season_registry import calculate_season_weather_window


class WeatherAdapter:
    """Extracts and aggregates seasonal agroclimatology indicators from NASA POWER JSON."""

    def __init__(self, raw_weather_dir: str):
        self.raw_weather_dir = raw_weather_dir
        self.source_id = "nasa_power_daily"

    def get_weather_measurement(
        self,
        district: str,
        season: str,
        harvest_year: int,
    ) -> Optional[WeatherMeasurement]:
        """Extract seasonal weather features for a district, season, and harvest year.

        Args:
            district: Canonical district name (e.g. 'Akola').
            season: Named season (e.g. 'Kharif', 'Rabi', 'Summer').
            harvest_year: Harvest calendar year (e.g. 2015).

        Returns:
            WeatherMeasurement instance or None if source file / dates are unavailable.
        """
        safe_district = district.lower().replace(" ", "_")
        cache_file = os.path.join(
            self.raw_weather_dir, f"nasa_power_{safe_district}_1990_2017.json"
        )

        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        params = data.get("properties", {}).get("parameter", {})
        if not params:
            return None

        # Determine exact date window for the season
        try:
            start_date, end_date = calculate_season_weather_window(season, harvest_year)
        except ValueError:
            return None

        # Generate list of YYYYMMDD date keys
        curr_dt = start_date
        date_keys = []
        while curr_dt <= end_date:
            date_keys.append(curr_dt.strftime("%Y%m%d"))
            curr_dt += datetime.timedelta(days=1)

        total_days = len(date_keys)
        if total_days == 0:
            return None

        precip_vals = []
        tmax_vals = []
        tmin_vals = []
        srad_vals = []
        rh_vals = []
        missing_count = 0

        p_precip = params.get("PRECTOTCORR", {})
        p_tmax = params.get("T2M_MAX", {})
        p_tmin = params.get("T2M_MIN", {})
        p_srad = params.get("ALLSKY_SFC_SW_DWN", {})
        p_rh = params.get("RH2M", {})

        for dkey in date_keys:
            val_p = p_precip.get(dkey)
            val_tmax = p_tmax.get(dkey)
            val_tmin = p_tmin.get(dkey)
            val_srad = p_srad.get(dkey)
            val_rh = p_rh.get(dkey)

            # NASA POWER uses -999 for missing values
            if (
                val_p is None or val_p <= -900
                or val_tmax is None or val_tmax <= -900
                or val_tmin is None or val_tmin <= -900
            ):
                missing_count += 1
                continue

            precip_vals.append(max(0.0, float(val_p)))
            tmax_vals.append(float(val_tmax))
            tmin_vals.append(float(val_tmin))

            if val_srad is not None and val_srad > -900:
                srad_vals.append(max(0.0, float(val_srad)))
            if val_rh is not None and val_rh > -900:
                rh_vals.append(max(0.0, min(100.0, float(val_rh))))

        # If more than 20% of days are missing, reject
        if len(precip_vals) < 0.8 * total_days:
            return None

        # Compute aggregates
        cum_rainfall = round(sum(precip_vals), 2)
        mean_tmax = round(sum(tmax_vals) / len(tmax_vals), 2)
        mean_tmin = round(sum(tmin_vals) / len(tmin_vals), 2)
        mean_srad = round(sum(srad_vals) / len(srad_vals), 2) if srad_vals else 17.5
        mean_rh = round(sum(rh_vals) / len(rh_vals), 2) if rh_vals else 70.0

        # Consecutive dry days (streak of days with rainfall < 2.5mm)
        max_dry_streak = 0
        current_dry_streak = 0
        for p in precip_vals:
            if p < 2.5:
                current_dry_streak += 1
                if current_dry_streak > max_dry_streak:
                    max_dry_streak = current_dry_streak
            else:
                current_dry_streak = 0

        # Heat stress days (days where T2M_MAX >= 35°C)
        heat_stress_days = sum(1 for t in tmax_vals if t >= 35.0)

        return WeatherMeasurement(
            cumulative_rainfall_mm=cum_rainfall,
            mean_temp_max_c=mean_tmax,
            mean_temp_min_c=mean_tmin,
            mean_solar_radiation_mj_m2=mean_srad,
            mean_relative_humidity_pct=mean_rh,
            consecutive_dry_days_max=max_dry_streak,
            heat_stress_days=heat_stress_days,
            weather_window_start=start_date.isoformat(),
            weather_window_end=end_date.isoformat(),
            weather_days_total=total_days,
            weather_days_missing=missing_count,
            source="NASA POWER Agroclimatology Daily",
        )
