import test from "node:test";
import assert from "node:assert/strict";
import {
  validatePredictionRequest,
  calculateSiltPercentage,
  SUPPORTED_DISTRICTS,
} from "../lib/validation.ts";
import { API_BASE_URL, ApiError } from "../lib/api.ts";

test("API client base URL is formatted cleanly without trailing slash", () => {
  assert.equal(typeof API_BASE_URL, "string");
  assert.ok(!API_BASE_URL.endsWith("/"));
});

test("ApiError classifies HTTP status codes correctly", () => {
  const offlineErr = new ApiError("Offline", 0);
  assert.equal(offlineErr.isOffline, true);
  assert.equal(offlineErr.isModelUnavailable, false);

  const unavailableErr = new ApiError("Model unloaded", 503);
  assert.equal(unavailableErr.isOffline, false);
  assert.equal(unavailableErr.isModelUnavailable, true);

  const validationErr = new ApiError("Validation failed", 422);
  assert.equal(validationErr.status, 422);
});

test("calculateSiltPercentage derives silt accurately", () => {
  const silt = calculateSiltPercentage(45.0, 20.0);
  assert.equal(silt, 35.0);

  const silt2 = calculateSiltPercentage(50.0, 50.0);
  assert.equal(silt2, 0.0);

  const siltNegative = calculateSiltPercentage(60.0, 50.0);
  assert.equal(siltNegative, 0.0); // Bounded at 0
});

test("validatePredictionRequest passes valid illustrative Akola payload", () => {
  const validPayload = {
    crop: "Soybean",
    state: "Maharashtra",
    district: "Akola",
    season: "Kharif",
    year: 2024,
    soil: {
      soil_ph: 7.4,
      organic_carbon_pct: 0.65,
      clay_pct: 45.0,
      sand_pct: 20.0,
      silt_pct: 35.0,
      bulk_density_g_cm3: 1.25,
      cation_exchange_capacity_cmol_kg: 38.0,
    },
    weather: {
      cumulative_rainfall_mm: 850.5,
      mean_temp_max_c: 31.8,
      mean_temp_min_c: 22.4,
      mean_solar_radiation_mj_m2: 18.6,
      mean_relative_humidity_pct: 76.2,
      consecutive_dry_days_max: 8,
      heat_stress_days: 4,
    },
  };

  const errors = validatePredictionRequest(validPayload);
  assert.equal(Object.keys(errors).length, 0);
});

test("validatePredictionRequest rejects unsupported district", () => {
  const payload = {
    crop: "Soybean",
    state: "Maharashtra",
    district: "UnsupportedDistrict",
    season: "Kharif",
    year: 2024,
    soil: {
      soil_ph: 7.4,
      organic_carbon_pct: 0.65,
      clay_pct: 45.0,
      sand_pct: 20.0,
      silt_pct: 35.0,
      bulk_density_g_cm3: 1.25,
      cation_exchange_capacity_cmol_kg: 38.0,
    },
    weather: {
      cumulative_rainfall_mm: 850.5,
      mean_temp_max_c: 31.8,
      mean_temp_min_c: 22.4,
      mean_solar_radiation_mj_m2: 18.6,
      mean_relative_humidity_pct: 76.2,
      consecutive_dry_days_max: 8,
      heat_stress_days: 4,
    },
  };

  const errors = validatePredictionRequest(payload);
  assert.ok(errors.district);
  assert.match(errors.district, /not supported/);
});

test("validatePredictionRequest rejects clay + sand > 100%", () => {
  const payload = {
    crop: "Soybean",
    state: "Maharashtra",
    district: "Akola",
    season: "Kharif",
    year: 2024,
    soil: {
      soil_ph: 7.4,
      organic_carbon_pct: 0.65,
      clay_pct: 65.0,
      sand_pct: 45.0, // 65 + 45 = 110 > 100
      silt_pct: 0.0,
      bulk_density_g_cm3: 1.25,
      cation_exchange_capacity_cmol_kg: 38.0,
    },
    weather: {
      cumulative_rainfall_mm: 850.5,
      mean_temp_max_c: 31.8,
      mean_temp_min_c: 22.4,
      mean_solar_radiation_mj_m2: 18.6,
      mean_relative_humidity_pct: 76.2,
      consecutive_dry_days_max: 8,
      heat_stress_days: 4,
    },
  };

  const errors = validatePredictionRequest(payload);
  assert.ok(errors["soil.sand_pct"]);
  assert.match(errors["soil.sand_pct"], /cannot exceed 100%/);
});

test("validatePredictionRequest rejects min temperature > max temperature", () => {
  const payload = {
    crop: "Soybean",
    state: "Maharashtra",
    district: "Akola",
    season: "Kharif",
    year: 2024,
    soil: {
      soil_ph: 7.4,
      organic_carbon_pct: 0.65,
      clay_pct: 45.0,
      sand_pct: 20.0,
      silt_pct: 35.0,
      bulk_density_g_cm3: 1.25,
      cation_exchange_capacity_cmol_kg: 38.0,
    },
    weather: {
      cumulative_rainfall_mm: 850.5,
      mean_temp_max_c: 25.0,
      mean_temp_min_c: 32.0, // min > max
      mean_solar_radiation_mj_m2: 18.6,
      mean_relative_humidity_pct: 76.2,
      consecutive_dry_days_max: 8,
      heat_stress_days: 4,
    },
  };

  const errors = validatePredictionRequest(payload);
  assert.ok(errors["weather.mean_temp_min_c"]);
  assert.match(errors["weather.mean_temp_min_c"], /cannot exceed max/);
});

test("All 7 supported districts are defined in whitelist", () => {
  assert.equal(SUPPORTED_DISTRICTS.length, 7);
  assert.deepEqual([...SUPPORTED_DISTRICTS], [
    "Ahmednagar",
    "Akola",
    "Amravati",
    "Aurangabad",
    "Beed",
    "Bhandara",
    "Buldhana",
  ]);
});

test("validatePredictionRequest validates all 7 supported crops successfully with appropriate seasons", () => {
  const cropTestCases = [
    { crop: "Soybean", season: "Kharif", district: "Akola" },
    { crop: "Rice", season: "Kharif", district: "Bhandara" },
    { crop: "Wheat", season: "Rabi", district: "Ahmednagar" },
    { crop: "Cotton", season: "Kharif", district: "Amravati" },
    { crop: "Maize", season: "Kharif", district: "Aurangabad" },
    { crop: "Chickpea", season: "Rabi", district: "Beed" },
    { crop: "Groundnut", season: "Kharif", district: "Buldhana" },
  ];

  for (const { crop, season, district } of cropTestCases) {
    const payload = {
      crop,
      state: "Maharashtra",
      district,
      season,
      year: 2024,
      soil: {
        soil_ph: 7.2,
        organic_carbon_pct: 0.60,
        clay_pct: 40.0,
        sand_pct: 25.0,
        silt_pct: 35.0,
        bulk_density_g_cm3: 1.26,
        cation_exchange_capacity_cmol_kg: 35.0,
      },
      weather: {
        cumulative_rainfall_mm: season === "Kharif" ? 800.0 : 80.0,
        mean_temp_max_c: 30.0,
        mean_temp_min_c: 20.0,
        mean_solar_radiation_mj_m2: 18.0,
        mean_relative_humidity_pct: 70.0,
        consecutive_dry_days_max: 10,
        heat_stress_days: 2,
      },
    };

    const errors = validatePredictionRequest(payload);
    assert.equal(Object.keys(errors).length, 0, `Validation failed for ${crop} in ${season}: ${JSON.stringify(errors)}`);
  }
});

test("validatePredictionRequest rejects season mismatch (e.g. Wheat in Kharif)", () => {
  const payload = {
    crop: "Wheat",
    state: "Maharashtra",
    district: "Ahmednagar",
    season: "Kharif", // Wheat is strictly Rabi
    year: 2024,
    soil: {
      soil_ph: 7.4,
      organic_carbon_pct: 0.65,
      clay_pct: 45.0,
      sand_pct: 20.0,
      silt_pct: 35.0,
      bulk_density_g_cm3: 1.25,
      cation_exchange_capacity_cmol_kg: 38.0,
    },
    weather: {
      cumulative_rainfall_mm: 850.5,
      mean_temp_max_c: 31.8,
      mean_temp_min_c: 22.4,
      mean_solar_radiation_mj_m2: 18.6,
      mean_relative_humidity_pct: 76.2,
      consecutive_dry_days_max: 8,
      heat_stress_days: 4,
    },
  };

  const errors = validatePredictionRequest(payload);
  assert.ok(errors.season);
  assert.match(errors.season, /not supported for Wheat/);
});

test("validatePredictionRequest rejects unverified districts like Thane or Kalyan", () => {
  const thanePayload = {
    crop: "Rice",
    state: "Maharashtra",
    district: "Thane", // Historical yield exists, but lacks aligned SoilGrids profile
    season: "Kharif",
    year: 2024,
    soil: {
      soil_ph: 6.8,
      organic_carbon_pct: 0.70,
      clay_pct: 35.0,
      sand_pct: 30.0,
      silt_pct: 35.0,
      bulk_density_g_cm3: 1.30,
      cation_exchange_capacity_cmol_kg: 30.0,
    },
    weather: {
      cumulative_rainfall_mm: 1500.0,
      mean_temp_max_c: 31.0,
      mean_temp_min_c: 23.0,
      mean_solar_radiation_mj_m2: 17.0,
      mean_relative_humidity_pct: 85.0,
      consecutive_dry_days_max: 5,
      heat_stress_days: 1,
    },
  };

  const errors = validatePredictionRequest(thanePayload);
  assert.ok(errors.district);
  assert.match(errors.district, /not supported/);
  assert.match(errors.district, /Thane/);
});

test("validatePredictionRequest rejects unknown crops like Barley or Sugarcane", () => {
  const payload = {
    crop: "Barley",
    state: "Maharashtra",
    district: "Akola",
    season: "Rabi",
    year: 2024,
    soil: {
      soil_ph: 7.4,
      organic_carbon_pct: 0.65,
      clay_pct: 45.0,
      sand_pct: 20.0,
      silt_pct: 35.0,
      bulk_density_g_cm3: 1.25,
      cation_exchange_capacity_cmol_kg: 38.0,
    },
    weather: {
      cumulative_rainfall_mm: 100.0,
      mean_temp_max_c: 28.0,
      mean_temp_min_c: 15.0,
      mean_solar_radiation_mj_m2: 18.0,
      mean_relative_humidity_pct: 55.0,
      consecutive_dry_days_max: 20,
      heat_stress_days: 0,
    },
  };

  const errors = validatePredictionRequest(payload);
  assert.ok(errors.crop);
  assert.match(errors.crop, /Crop 'Barley' is not supported/);
});

