import { PredictionRequest } from "./types";

export interface IllustrativePreset {
  id: string;
  name: string;
  crop: string;
  district: string;
  season: string;
  description: string;
  data: PredictionRequest;
}

/**
 * Pre-configured illustrative inputs for demonstrating the inference interface.
 * IMPORTANT: These inputs are strictly illustrative examples for documentation
 * and interactive testing; they must never be mistaken for real-time farm sensor readings.
 */
export const ILLUSTRATIVE_PRESETS: IllustrativePreset[] = [
  {
    id: "akola_soybean",
    name: "Akola — Soybean (Kharif)",
    crop: "Soybean",
    district: "Akola",
    season: "Kharif",
    description: "Illustrative Kharif scenario for Akola district with typical rainfall and heavy vertisol clay soil.",
    data: {
      crop: "Soybean",
      state: "Maharashtra",
      district: "Akola",
      season: "Kharif",
      year: 2024,
      model_strategy: "shared_multicrop",
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
    },
  },
  {
    id: "bhandara_rice",
    name: "Bhandara — Rice (Kharif)",
    crop: "Rice",
    district: "Bhandara",
    season: "Kharif",
    description: "Illustrative scenario for eastern Maharashtra high-precipitation paddy basin.",
    data: {
      crop: "Rice",
      state: "Maharashtra",
      district: "Bhandara",
      season: "Kharif",
      year: 2024,
      model_strategy: "shared_multicrop",
      soil: {
        soil_ph: 6.8,
        organic_carbon_pct: 0.72,
        clay_pct: 35.0,
        sand_pct: 30.0,
        silt_pct: 35.0,
        bulk_density_g_cm3: 1.32,
        cation_exchange_capacity_cmol_kg: 28.5,
      },
      weather: {
        cumulative_rainfall_mm: 1250.0,
        mean_temp_max_c: 31.0,
        mean_temp_min_c: 23.5,
        mean_solar_radiation_mj_m2: 17.5,
        mean_relative_humidity_pct: 82.0,
        consecutive_dry_days_max: 5,
        heat_stress_days: 2,
      },
    },
  },
  {
    id: "ahmednagar_wheat",
    name: "Ahmednagar — Wheat (Rabi)",
    crop: "Wheat",
    district: "Ahmednagar",
    season: "Rabi",
    description: "Illustrative Rabi season irrigated scenario with cooler temperatures and moderate soils.",
    data: {
      crop: "Wheat",
      state: "Maharashtra",
      district: "Ahmednagar",
      season: "Rabi",
      year: 2024,
      model_strategy: "shared_multicrop",
      soil: {
        soil_ph: 7.8,
        organic_carbon_pct: 0.55,
        clay_pct: 42.0,
        sand_pct: 22.0,
        silt_pct: 36.0,
        bulk_density_g_cm3: 1.28,
        cation_exchange_capacity_cmol_kg: 34.0,
      },
      weather: {
        cumulative_rainfall_mm: 45.0,
        mean_temp_max_c: 28.5,
        mean_temp_min_c: 14.2,
        mean_solar_radiation_mj_m2: 19.8,
        mean_relative_humidity_pct: 54.0,
        consecutive_dry_days_max: 45,
        heat_stress_days: 0,
      },
    },
  },
  {
    id: "amravati_cotton",
    name: "Amravati — Cotton (Kharif)",
    crop: "Cotton",
    district: "Amravati",
    season: "Kharif",
    description: "Illustrative deep black cotton soil (Vertisol) scenario under monsoon conditions.",
    data: {
      crop: "Cotton",
      state: "Maharashtra",
      district: "Amravati",
      season: "Kharif",
      year: 2024,
      model_strategy: "shared_multicrop",
      soil: {
        soil_ph: 7.6,
        organic_carbon_pct: 0.58,
        clay_pct: 48.0,
        sand_pct: 18.0,
        silt_pct: 34.0,
        bulk_density_g_cm3: 1.28,
        cation_exchange_capacity_cmol_kg: 40.2,
      },
      weather: {
        cumulative_rainfall_mm: 780.0,
        mean_temp_max_c: 32.5,
        mean_temp_min_c: 22.8,
        mean_solar_radiation_mj_m2: 18.9,
        mean_relative_humidity_pct: 71.0,
        consecutive_dry_days_max: 12,
        heat_stress_days: 6,
      },
    },
  },
  {
    id: "beed_chickpea",
    name: "Beed — Chickpea (Rabi)",
    crop: "Chickpea",
    district: "Beed",
    season: "Rabi",
    description: "Illustrative rainfed post-monsoon pulse scenario in Marathwada.",
    data: {
      crop: "Chickpea",
      state: "Maharashtra",
      district: "Beed",
      season: "Rabi",
      year: 2024,
      model_strategy: "shared_multicrop",
      soil: {
        soil_ph: 7.9,
        organic_carbon_pct: 0.52,
        clay_pct: 44.0,
        sand_pct: 21.0,
        silt_pct: 35.0,
        bulk_density_g_cm3: 1.29,
        cation_exchange_capacity_cmol_kg: 36.5,
      },
      weather: {
        cumulative_rainfall_mm: 55.0,
        mean_temp_max_c: 29.2,
        mean_temp_min_c: 15.0,
        mean_solar_radiation_mj_m2: 19.5,
        mean_relative_humidity_pct: 52.0,
        consecutive_dry_days_max: 40,
        heat_stress_days: 1,
      },
    },
  },
];
