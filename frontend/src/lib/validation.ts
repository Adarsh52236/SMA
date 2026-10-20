import type { PredictionRequest } from "./types";

export const SUPPORTED_DISTRICTS = [
  "Ahmednagar",
  "Akola",
  "Amravati",
  "Aurangabad",
  "Beed",
  "Bhandara",
  "Buldhana",
] as const;

export type SupportedDistrict = (typeof SUPPORTED_DISTRICTS)[number];

export const SUPPORTED_CROPS = [
  { id: "soybean", label: "Soybean", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "rice", label: "Rice", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "wheat", label: "Wheat", defaultSeason: "Rabi", allowedSeasons: ["Rabi"] },
  { id: "cotton", label: "Cotton", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "maize", label: "Maize", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "chickpea", label: "Chickpea", defaultSeason: "Rabi", allowedSeasons: ["Rabi"] },
  { id: "groundnut", label: "Groundnut", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
] as const;

export type SupportedCropId = (typeof SUPPORTED_CROPS)[number]["id"];

export const CROP_ALLOWED_SEASONS: Record<string, string[]> = {
  soybean: ["Kharif"],
  rice: ["Kharif"],
  wheat: ["Rabi"],
  cotton: ["Kharif"],
  maize: ["Kharif"],
  chickpea: ["Rabi"],
  groundnut: ["Kharif"],
};

export interface FieldValidationRule {
  min: number;
  max: number;
  unit: string;
  label: string;
  description: string;
}

export const VALIDATION_RULES = {
  // Soil Properties (0-30cm ISRIC SoilGrids 2.0)
  soil_ph: {
    min: 3.5,
    max: 10.0,
    unit: "pH",
    label: "Soil pH",
    description: "pH in H2O solution [3.5, 10.0]",
  },
  organic_carbon_pct: {
    min: 0.0,
    max: 10.0,
    unit: "% wt",
    label: "Organic Carbon",
    description: "Soil organic carbon content [0.0, 10.0%]",
  },
  clay_pct: {
    min: 0.0,
    max: 100.0,
    unit: "% wt",
    label: "Clay Fraction",
    description: "Clay particle fraction (<2µm) [0, 100%]",
  },
  sand_pct: {
    min: 0.0,
    max: 100.0,
    unit: "% wt",
    label: "Sand Fraction",
    description: "Sand particle fraction (50-2000µm) [0, 100%]",
  },
  silt_pct: {
    min: 0.0,
    max: 100.0,
    unit: "% wt",
    label: "Silt Fraction",
    description: "Silt particle fraction (2-50µm) [0, 100%]",
  },
  bulk_density_g_cm3: {
    min: 0.8,
    max: 2.2,
    unit: "g/cm³",
    label: "Bulk Density",
    description: "Bulk density of fine earth fraction [0.8, 2.2 g/cm³]",
  },
  cation_exchange_capacity_cmol_kg: {
    min: 0.0,
    max: 120.0,
    unit: "cmol(+)/kg",
    label: "Cation Exchange Capacity",
    description: "CEC at pH 7 [0, 120 cmol(+)/kg]",
  },

  // Seasonal Weather
  cumulative_rainfall_mm: {
    min: 0.0,
    max: 5000.0,
    unit: "mm",
    label: "Cumulative Rainfall",
    description: "Total precipitation during growing season [0, 5000 mm]",
  },
  mean_temp_max_c: {
    min: 15.0,
    max: 50.0,
    unit: "°C",
    label: "Mean Max Temperature",
    description: "Mean daily maximum temperature [15, 50 °C]",
  },
  mean_temp_min_c: {
    min: 5.0,
    max: 35.0,
    unit: "°C",
    label: "Mean Min Temperature",
    description: "Mean daily minimum temperature [5, 35 °C]",
  },
  mean_solar_radiation_mj_m2: {
    min: 5.0,
    max: 35.0,
    unit: "MJ/m²/day",
    label: "Solar Radiation",
    description: "Mean surface downward insolation [5, 35 MJ/m²/day]",
  },
  mean_relative_humidity_pct: {
    min: 10.0,
    max: 100.0,
    unit: "%",
    label: "Relative Humidity",
    description: "Mean relative humidity at 2m [10, 100%]",
  },
  consecutive_dry_days_max: {
    min: 0,
    max: 153,
    unit: "days",
    label: "Max Consecutive Dry Days",
    description: "Longest dry spell (<2.5mm/day) across the growing season",
  },
  heat_stress_days: {
    min: 0,
    max: 153,
    unit: "days",
    label: "Heat Stress Days",
    description: "Count of days with max temperature >35°C during season",
  },
  year: {
    min: 1990,
    max: 2035,
    unit: "year",
    label: "Harvest Year",
    description: "Agricultural calendar year [1990, 2035]",
  },
};

export function calculateSiltPercentage(clay: number, sand: number): number {
  const silt = 100.0 - (clay + sand);
  return Math.max(0, Math.round(silt * 10) / 10);
}

export type ValidationErrors = Record<string, string>;

export function validatePredictionRequest(data: PredictionRequest): ValidationErrors {
  const errors: ValidationErrors = {};

  // District validation
  if (!SUPPORTED_DISTRICTS.includes(data.district as SupportedDistrict)) {
    errors.district = `District '${data.district}' is not supported. Supported: ${SUPPORTED_DISTRICTS.join(", ")}. Note that unverified regions (e.g., Thane, Kalyan) lack verified SoilGrids baseline profiles.`;
  }

  // Crop validation
  const cropRaw = data.crop || "Soybean";
  const cropNorm = cropRaw.trim().toLowerCase();
  const matchedCrop = SUPPORTED_CROPS.find((c) => c.id === cropNorm || c.label.toLowerCase() === cropNorm);
  if (!matchedCrop) {
    errors.crop = `Crop '${cropRaw}' is not supported. Supported crops: ${SUPPORTED_CROPS.map((c) => c.label).join(", ")}.`;
  }

  // State validation
  if (data.state && data.state.toLowerCase() !== "maharashtra") {
    errors.state = "Only 'Maharashtra' is supported.";
  }

  // Season validation per crop
  const season = data.season || (matchedCrop ? matchedCrop.defaultSeason : "Kharif");
  if (matchedCrop) {
    const allowed = CROP_ALLOWED_SEASONS[matchedCrop.id] || ["Kharif"];
    const seasonNorm = season.trim().charAt(0).toUpperCase() + season.trim().slice(1).toLowerCase();
    if (!allowed.includes(seasonNorm)) {
      errors.season = `Season '${season}' is not supported for ${matchedCrop.label}. Supported season(s): ${allowed.join(", ")}.`;
    }
  }

  // Year validation
  if (isNaN(data.year) || data.year < VALIDATION_RULES.year.min || data.year > VALIDATION_RULES.year.max) {
    errors.year = `Year must be between ${VALIDATION_RULES.year.min} and ${VALIDATION_RULES.year.max}.`;
  }

  // Soil properties validation
  const { soil } = data;
  for (const [key, rule] of Object.entries(VALIDATION_RULES)) {
    if (key in soil) {
      const val = soil[key as keyof typeof soil];
      if (val === undefined || val === null || isNaN(val as number)) {
        errors[`soil.${key}`] = `${rule.label} is required.`;
      } else if ((val as number) < rule.min || (val as number) > rule.max) {
        errors[`soil.${key}`] = `${rule.label} must be between ${rule.min} and ${rule.max} ${rule.unit}.`;
      }
    }
  }

  // Texture cross-validation
  if (soil.clay_pct !== undefined && soil.sand_pct !== undefined) {
    if (soil.clay_pct + soil.sand_pct > 100.0) {
      errors["soil.sand_pct"] = `Sum of clay (${soil.clay_pct}%) and sand (${soil.sand_pct}%) cannot exceed 100%.`;
    } else if (soil.silt_pct !== undefined && soil.silt_pct !== null) {
      const totalTexture = soil.clay_pct + soil.sand_pct + soil.silt_pct;
      if (totalTexture > 100.5 || totalTexture < 95.0) {
        errors["soil.silt_pct"] = `Soil texture (clay + sand + silt) must sum to ~100% (currently ${totalTexture.toFixed(1)}%).`;
      }
    }
  }

  // Weather properties validation
  const { weather } = data;
  for (const [key, rule] of Object.entries(VALIDATION_RULES)) {
    if (key in weather) {
      const val = weather[key as keyof typeof weather];
      if (val === undefined || val === null || isNaN(val as number)) {
        errors[`weather.${key}`] = `${rule.label} is required.`;
      } else if ((val as number) < rule.min || (val as number) > rule.max) {
        errors[`weather.${key}`] = `${rule.label} must be between ${rule.min} and ${rule.max} ${rule.unit}.`;
      }
    }
  }

  // Temperature cross-validation
  if (weather.mean_temp_min_c !== undefined && weather.mean_temp_max_c !== undefined) {
    if (weather.mean_temp_min_c > weather.mean_temp_max_c) {
      errors["weather.mean_temp_min_c"] = `Min temperature (${weather.mean_temp_min_c}°C) cannot exceed max temperature (${weather.mean_temp_max_c}°C).`;
    }
  }

  return errors;
}
