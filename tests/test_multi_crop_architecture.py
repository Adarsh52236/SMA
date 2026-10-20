"""Comprehensive Test Suite for Multi-Crop Data Architecture & Adapters (Phase 2).

Tests canonical schemas, crop registry resolution, growing season calendar calculations,
unit conversions, validation rules, adapter parsing, and backward compatibility.
"""

import os
import tempfile
import pytest
import datetime
from pydantic import ValidationError

from app.data.crop_registry import (
    CROP_REGISTRY,
    CropCategory,
    resolve_crop,
    list_registered_crops,
)
from app.data.season_registry import (
    SEASON_REGISTRY,
    SeasonName,
    resolve_season,
    calculate_season_weather_window,
)
from app.data.unified_schema import (
    UnifiedCropObservation,
    WeatherMeasurement,
    SoilMeasurement,
    convert_yield_to_t_ha,
)
from app.data.adapters.icrisat_dld_adapter import IcrisatDldAdapter
from app.data.adapters.weather_adapter import WeatherAdapter
from app.data.adapters.soil_adapter import SoilAdapter


# --- 1. Crop Registry & Alias Normalization Tests ---

def test_all_10_target_crops_registered():
    """Verify all 10 required agricultural crops exist in CROP_REGISTRY with correct categories."""
    expected_crops = {
        "soybean": CropCategory.OILSEED,
        "rice": CropCategory.CEREAL,
        "wheat": CropCategory.CEREAL,
        "cotton": CropCategory.CASH_CROP,
        "maize": CropCategory.CEREAL,
        "chickpea": CropCategory.PULSE,
        "groundnut": CropCategory.OILSEED,
        "pigeon_pea": CropCategory.PULSE,
        "sugarcane": CropCategory.CASH_CROP,
        "sorghum": CropCategory.CEREAL,
    }
    for crop_id, expected_category in expected_crops.items():
        assert crop_id in CROP_REGISTRY, f"Crop '{crop_id}' missing from registry."
        spec = CROP_REGISTRY[crop_id]
        assert spec.category == expected_category
        assert spec.typical_yield_range_t_ha[0] > 0
        assert spec.typical_yield_range_t_ha[1] > spec.typical_yield_range_t_ha[0]


def test_crop_alias_resolution():
    """Verify case-insensitive and source-specific alias resolution for ICRISAT/DES."""
    test_cases = [
        ("SOYABEAN", "soybean"),
        ("Soybean", "soybean"),
        ("RICE", "rice"),
        ("paddy", "rice"),
        ("WHEAT", "wheat"),
        ("cotton", "cotton"),
        ("GRAM", "chickpea"),
        ("BENGAL GRAM", "chickpea"),
        ("TUR", "pigeon_pea"),
        ("ARHAR", "pigeon_pea"),
        ("JOWAR", "sorghum"),
        ("KHARIF SORGHUM", "sorghum"),
        ("RABI SORGHUM", "sorghum"),
        ("PEANUT", "groundnut"),
        ("CORN", "maize"),
        ("SUGARCANE", "sugarcane"),
    ]
    for raw_name, expected_id in test_cases:
        resolved = resolve_crop(raw_name)
        assert resolved is not None, f"Failed to resolve alias '{raw_name}'."
        assert resolved.crop_id == expected_id


def test_unknown_crop_resolution_returns_none():
    """Verify unsupported or non-existent crops return None without throwing."""
    assert resolve_crop("Pineapple") is None
    assert resolve_crop("Dragonfruit") is None
    assert resolve_crop("") is None
    assert resolve_crop(None) is None


# --- 2. Season Registry & Meteorological Window Tests ---

def test_season_calendar_window_calculation():
    """Verify Kharif, Summer, and cross-calendar-year Rabi weather aggregation windows."""
    # Kharif: same calendar year (June 1 - October 31)
    k_start, k_end = calculate_season_weather_window("Kharif", 2016)
    assert k_start == datetime.date(2016, 6, 1)
    assert k_end == datetime.date(2016, 10, 31)

    # Rabi: crosses calendar years! Sown Nov (year - 1), harvested March (year)
    r_start, r_end = calculate_season_weather_window("Rabi", 2017)
    assert r_start == datetime.date(2016, 11, 1)
    assert r_end == datetime.date(2017, 3, 31)

    # Summer: same calendar year (Feb 1 - May 31)
    s_start, s_end = calculate_season_weather_window("Summer", 2015)
    assert s_start == datetime.date(2015, 2, 1)
    assert s_end == datetime.date(2015, 5, 31)


def test_season_resolution_aliases():
    """Verify season alias resolution (e.g. 'monsoon' -> Kharif, 'winter' -> Rabi)."""
    assert resolve_season("monsoon").canonical_name == SeasonName.KHARIF
    assert resolve_season("winter").canonical_name == SeasonName.RABI
    assert resolve_season("zaid").canonical_name == SeasonName.SUMMER
    assert resolve_season("UnknownSeason") is None


# --- 3. Yield Unit Conversion Tests ---

def test_yield_unit_conversions():
    """Verify explicit mathematical conversion of diverse agricultural yield units to t/ha."""
    assert convert_yield_to_t_ha(1500.0, "kg/ha") == 1.5
    assert convert_yield_to_t_ha(2.35, "t/ha") == 2.35
    assert convert_yield_to_t_ha(20.0, "q/ha") == 2.0
    assert convert_yield_to_t_ha(15000.0, "hg/ha") == 1.5

    # Rejection of invalid/unknown units
    with pytest.raises(ValueError, match="Unsupported or unrecognized yield unit"):
        convert_yield_to_t_ha(10.0, "gallons/acre")


# --- 4. Canonical Unified Observation Schema Validation Tests ---

def test_valid_multi_crop_observations_across_categories():
    """Verify valid observations from multiple crop categories (cereal, pulse, oilseed, cash_crop)."""
    # Oilseed (Soybean)
    obs_soybean = UnifiedCropObservation(
        observation_id="synth_akola_soybean_kharif_2016",
        crop_name="Soybean",
        crop_id="soybean",
        crop_category=CropCategory.OILSEED,
        state="Maharashtra",
        district="Akola",
        crop_year=2016,
        season="Kharif",
        yield_t_ha=1.25,
        source_dataset="synthetic_test_fixture",
    )
    assert obs_soybean.crop_category == CropCategory.OILSEED
    assert "missing_weather" in obs_soybean.missingness_flags
    assert "missing_soil" in obs_soybean.missingness_flags

    # Cereal (Wheat - Rabi)
    obs_wheat = UnifiedCropObservation(
        observation_id="synth_ahmednagar_wheat_rabi_2017",
        crop_name="Wheat",
        crop_id="wheat",
        crop_category=CropCategory.CEREAL,
        state="Maharashtra",
        district="Ahmednagar",
        crop_year=2017,
        season="Rabi",
        yield_t_ha=2.40,
        source_dataset="synthetic_test_fixture",
    )
    assert obs_wheat.crop_category == CropCategory.CEREAL

    # Pulse (Chickpea - Rabi)
    obs_chickpea = UnifiedCropObservation(
        observation_id="synth_amravati_chickpea_rabi_2017",
        crop_name="Chickpea (Gram)",
        crop_id="chickpea",
        crop_category=CropCategory.PULSE,
        state="Maharashtra",
        district="Amravati",
        crop_year=2017,
        season="Rabi",
        yield_t_ha=0.85,
        source_dataset="synthetic_test_fixture",
    )
    assert obs_chickpea.crop_category == CropCategory.PULSE

    # Cash Crop (Cotton - Kharif)
    obs_cotton = UnifiedCropObservation(
        observation_id="synth_wardha_cotton_kharif_2016",
        crop_name="Cotton",
        crop_id="cotton",
        crop_category=CropCategory.CASH_CROP,
        state="Maharashtra",
        district="Wardha",
        crop_year=2016,
        season="Kharif",
        yield_t_ha=0.45,
        source_dataset="synthetic_test_fixture",
    )
    assert obs_cotton.crop_category == CropCategory.CASH_CROP


def test_missing_weather_and_soil_nullable_preservation():
    """Verify raw observations with missing weather or soil are preserved without failure."""
    obs = UnifiedCropObservation(
        observation_id="synth_minimal_obs_1",
        crop_name="Rice (Paddy)",
        crop_id="rice",
        crop_category=CropCategory.CEREAL,
        state="Maharashtra",
        district="Bhandara",
        crop_year=2015,
        season="Kharif",
        yield_t_ha=1.80,
        weather=None,
        soil=None,
        source_dataset="synthetic_test_fixture",
    )
    assert obs.weather is None
    assert obs.soil is None
    assert "missing_weather" in obs.missingness_flags
    assert "missing_soil" in obs.missingness_flags
    assert obs.quality_score == 0.4  # Partial score for agricultural yield record only


def test_temperature_inversion_validation_error():
    """Verify WeatherMeasurement rejects min_temp > max_temp."""
    with pytest.raises(ValidationError, match="cannot exceed maximum temperature"):
        WeatherMeasurement(
            mean_temp_max_c=25.0,
            mean_temp_min_c=28.0,  # Invalid: min > max
        )


def test_soil_texture_sum_validation_error():
    """Verify SoilMeasurement rejects texture fractions that do not sum to ~100%."""
    with pytest.raises(ValidationError, match="must sum to approximately 100%"):
        SoilMeasurement(
            clay_pct=50.0,
            sand_pct=50.0,
            silt_pct=30.0,  # Total: 130% -> Invalid
        )


def test_unregistered_crop_rejection():
    """Verify UnifiedCropObservation rejects unregistered crop IDs."""
    with pytest.raises(ValidationError, match="is not registered in CROP_REGISTRY"):
        UnifiedCropObservation(
            observation_id="synth_invalid_crop",
            crop_name="Avocado",
            crop_id="avocado",
            crop_category=CropCategory.OTHER,
            state="Maharashtra",
            district="Akola",
            crop_year=2015,
            season="Kharif",
            yield_t_ha=2.0,
            source_dataset="synthetic_test_fixture",
        )


# --- 5. Modular Adapter Tests ---

def test_icrisat_dld_adapter_synthetic_fixture():
    """Verify IcrisatDldAdapter parses records, maps aliases, dedups, and builds audit report."""
    csv_content = (
        "Year,Dist Name,Crop,Area(1000 ha),Production(1000 tons),Yield(Kg per ha)\n"
        "2015,Akola,SOYABEAN,120.5,144.6,1200\n"
        "2015,Akola,SOYABEAN,120.5,144.6,1200\n"  # Duplicate row
        "2016,Amarawati,RICE,50.0,75.0,1500\n"
        "2016,Bhir,WHEAT,40.0,80.0,2000\n"
        "2016,Akola,UNKNOWN_CROP,10.0,5.0,500\n"  # Unregistered crop
        "2016,Akola,COTTON,100.0,-5.0,-50\n"     # Negative yield (invalid)
    )

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv") as tmp:
        tmp.write(csv_content)
        tmp_path = tmp.name

    try:
        adapter = IcrisatDldAdapter()
        obs_list, report = adapter.ingest(tmp_path, min_year=2015, max_year=2016)

        assert report.total_records_read == 6
        assert report.deduplicated_records == 1
        assert report.accepted_records == 3  # Soybean, Rice, Wheat accepted
        assert report.rejected_records == 2  # UNKNOWN_CROP and negative yield rejected

        # Verify normalized fields of first accepted record (Soybean)
        soy_obs = next(o for o in obs_list if o.crop_id == "soybean")
        assert soy_obs.yield_t_ha == 1.2  # 1200 kg/ha -> 1.2 t/ha
        assert soy_obs.reported_area_ha == 120500.0  # 120.5 * 1000
        assert soy_obs.reported_production_tonnes == 144600.0  # 144.6 * 1000
        assert soy_obs.district == "Akola"
        assert soy_obs.season == "Kharif"

        # Verify normalized fields of Rice (Amravati alias Amarawati)
        rice_obs = next(o for o in obs_list if o.crop_id == "rice")
        assert rice_obs.district == "Amravati"  # Alias resolved
        assert rice_obs.yield_t_ha == 1.5

        # Verify normalized fields of Wheat (Beed alias Bhir)
        wheat_obs = next(o for o in obs_list if o.crop_id == "wheat")
        assert wheat_obs.district == "Beed"  # Alias resolved
        assert wheat_obs.season == "Rabi"    # Wheat default season is Rabi
        assert wheat_obs.yield_t_ha == 2.0

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_weather_adapter_against_real_akola_cache():
    """Verify WeatherAdapter extracts seasonal weather metrics from real raw NASA POWER JSON cache."""
    raw_weather_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "raw", "weather")
    )
    if not os.path.exists(os.path.join(raw_weather_dir, "nasa_power_akola_1990_2017.json")):
        pytest.skip("NASA POWER raw cache not present; skipping live file adapter test.")

    adapter = WeatherAdapter(raw_weather_dir)
    weather_kharif = adapter.get_weather_measurement("Akola", "Kharif", 2016)

    assert weather_kharif is not None
    assert weather_kharif.cumulative_rainfall_mm > 0.0
    assert weather_kharif.mean_temp_max_c > weather_kharif.mean_temp_min_c
    assert weather_kharif.consecutive_dry_days_max >= 0
    assert weather_kharif.heat_stress_days >= 0
    assert weather_kharif.weather_window_start == "2016-06-01"
    assert weather_kharif.weather_window_end == "2016-10-31"


def test_soil_adapter_against_real_akola_cache():
    """Verify SoilAdapter extracts depth-weighted topsoil properties from real raw SoilGrids JSON cache."""
    raw_soil_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "raw", "soil")
    )
    if not os.path.exists(raw_soil_dir):
        pytest.skip("SoilGrids raw cache not present; skipping live file adapter test.")

    adapter = SoilAdapter(raw_soil_dir)
    soil_profile = adapter.get_soil_measurement("Akola")

    assert soil_profile is not None
    assert 6.0 <= soil_profile.soil_ph <= 8.5
    assert soil_profile.organic_carbon_pct > 0.0
    # Textures must sum exactly to ~100
    texture_sum = soil_profile.clay_pct + soil_profile.sand_pct + soil_profile.silt_pct
    assert abs(texture_sum - 100.0) < 0.5
