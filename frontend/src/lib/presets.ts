import { PredictionRequest } from "./types";

export interface IllustrativePreset {
  id: string;
  name: string;
  district: string;
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
    id: "akola_normal",
    name: "Akola — Moderate Monsoon Sample",
    district: "Akola",
    description: "Illustrative Kharif scenario for Akola district with typical rainfall and heavy vertisol clay soil.",
    data: {
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
    },
  },
  {
    id: "amravati_dryspell",
    name: "Amravati — Extended Dry Spell Sample",
    district: "Amravati",
    description: "Illustrative scenario reflecting prolonged mid-season dry spell conditions (16 consecutive dry days).",
    data: {
      crop: "Soybean",
      state: "Maharashtra",
      district: "Amravati",
      season: "Kharif",
      year: 2024,
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
        cumulative_rainfall_mm: 680.0,
        mean_temp_max_c: 33.2,
        mean_temp_min_c: 23.1,
        mean_solar_radiation_mj_m2: 19.4,
        mean_relative_humidity_pct: 69.5,
        consecutive_dry_days_max: 16,
        heat_stress_days: 9,
      },
    },
  },
];
