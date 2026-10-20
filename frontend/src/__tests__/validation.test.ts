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
