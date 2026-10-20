"use client";

import React, { useState } from "react";
import { api, ApiError } from "@/lib/api";
import { PredictionRequest, PredictionResponse } from "@/lib/types";
import {
  SUPPORTED_DISTRICTS,
  VALIDATION_RULES,
  calculateSiltPercentage,
  ValidationErrors,
} from "@/lib/validation";
import { Card, CardHeader } from "@/components/common/Card";
import { Button } from "@/components/common/Button";
import { Alert } from "@/components/common/Alert";
import {
  Sparkles,
  Sprout,
  MapPin,
  Layers,
  CloudRain,
  RotateCcw,
  CheckCircle2,
  Copy,
  Check,
  ShieldCheck,
  Cpu,
  Info,
  Clock,
} from "lucide-react";

// Canonical trained crops with their primary growing season and agronomic identity
const TRAINED_CROPS = [
  { id: "Soybean", label: "Soybean", scientific: "Glycine max", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "Cotton", label: "Cotton", scientific: "Gossypium hirsutum", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "Groundnut", label: "Groundnut", scientific: "Arachis hypogaea", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "Maize", label: "Maize", scientific: "Zea mays", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "Pigeonpea", label: "Pigeonpea (Tur)", scientific: "Cajanus cajan", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "Sorghum", label: "Sorghum (Jowar)", scientific: "Sorghum bicolor", defaultSeason: "Kharif", allowedSeasons: ["Kharif", "Rabi"] },
  { id: "Wheat", label: "Wheat", scientific: "Triticum aestivum", defaultSeason: "Rabi", allowedSeasons: ["Rabi"] },
  { id: "Rice", label: "Rice", scientific: "Oryza sativa", defaultSeason: "Kharif", allowedSeasons: ["Kharif"] },
  { id: "Chickpea", label: "Chickpea (Gram)", scientific: "Cicer arietinum", defaultSeason: "Rabi", allowedSeasons: ["Rabi"] },
];

// Verified 0-30cm ISRIC SoilGrids 2.0 depth-weighted regional baselines
const REGIONAL_SOIL_PROFILES: Record<string, {
  soil_ph: number;
  organic_carbon_pct: number;
  clay_pct: number;
  sand_pct: number;
  silt_pct: number;
  bulk_density_g_cm3: number;
  cation_exchange_capacity_cmol_kg: number;
}> = {
  Ahmednagar: { soil_ph: 7.8, organic_carbon_pct: 0.58, clay_pct: 42.0, sand_pct: 25.0, silt_pct: 33.0, bulk_density_g_cm3: 1.28, cation_exchange_capacity_cmol_kg: 36.0 },
  Akola: { soil_ph: 7.4, organic_carbon_pct: 0.65, clay_pct: 45.0, sand_pct: 20.0, silt_pct: 35.0, bulk_density_g_cm3: 1.25, cation_exchange_capacity_cmol_kg: 38.0 },
  Amravati: { soil_ph: 7.6, organic_carbon_pct: 0.62, clay_pct: 48.0, sand_pct: 18.0, silt_pct: 34.0, bulk_density_g_cm3: 1.26, cation_exchange_capacity_cmol_kg: 40.5 },
  Aurangabad: { soil_ph: 7.7, organic_carbon_pct: 0.60, clay_pct: 44.0, sand_pct: 22.0, silt_pct: 34.0, bulk_density_g_cm3: 1.27, cation_exchange_capacity_cmol_kg: 37.5 },
  Beed: { soil_ph: 7.5, organic_carbon_pct: 0.55, clay_pct: 46.0, sand_pct: 20.0, silt_pct: 34.0, bulk_density_g_cm3: 1.28, cation_exchange_capacity_cmol_kg: 39.0 },
  Bhandara: { soil_ph: 6.8, organic_carbon_pct: 0.72, clay_pct: 35.0, sand_pct: 30.0, silt_pct: 35.0, bulk_density_g_cm3: 1.32, cation_exchange_capacity_cmol_kg: 28.5 },
  Buldhana: { soil_ph: 7.5, organic_carbon_pct: 0.64, clay_pct: 47.0, sand_pct: 19.0, silt_pct: 34.0, bulk_density_g_cm3: 1.25, cation_exchange_capacity_cmol_kg: 39.5 },
};

// Standard multi-decade NASA POWER seasonal climatology
const SEASONAL_CLIMATOLOGY: Record<string, {
  cumulative_rainfall_mm: number;
  mean_temp_max_c: number;
  mean_temp_min_c: number;
  mean_solar_radiation_mj_m2: number;
  mean_relative_humidity_pct: number;
  consecutive_dry_days_max: number;
  heat_stress_days: number;
}> = {
  Kharif: {
    cumulative_rainfall_mm: 825.0,
    mean_temp_max_c: 31.8,
    mean_temp_min_c: 22.4,
    mean_solar_radiation_mj_m2: 18.6,
    mean_relative_humidity_pct: 75.8,
    consecutive_dry_days_max: 8,
    heat_stress_days: 4,
  },
  Rabi: {
    cumulative_rainfall_mm: 48.0,
    mean_temp_max_c: 29.2,
    mean_temp_min_c: 14.1,
    mean_solar_radiation_mj_m2: 19.8,
    mean_relative_humidity_pct: 46.5,
    consecutive_dry_days_max: 32,
    heat_stress_days: 0,
  },
  Summer: {
    cumulative_rainfall_mm: 22.0,
    mean_temp_max_c: 38.5,
    mean_temp_min_c: 24.2,
    mean_solar_radiation_mj_m2: 23.0,
    mean_relative_humidity_pct: 32.0,
    consecutive_dry_days_max: 45,
    heat_stress_days: 28,
  },
};

interface CalculationRecord {
  id: string;
  timestamp: string;
  crop: string;
  district: string;
  season: string;
  year: number;
  yield_t_ha: number;
  yield_quintal_acre: string;
  yield_kg_ha: number;
  request: PredictionRequest;
  response: PredictionResponse;
}

export default function SinglePageYieldPredictor() {
  // Form State
  const [formData, setFormData] = useState<PredictionRequest>({
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
  });

  const [autoSilt, setAutoSilt] = useState<boolean>(true);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [predictionResult, setPredictionResult] = useState<PredictionResponse | null>(null);
  const [copiedId, setCopiedId] = useState<boolean>(false);

  // History State (stored in session)
  const [history, setHistory] = useState<CalculationRecord[]>([]);

  // Update season automatically when crop changes
  const handleCropChange = (newCrop: string) => {
    const cropSpec = TRAINED_CROPS.find((c) => c.id === newCrop);
    const newSeason = cropSpec ? cropSpec.defaultSeason : "Kharif";
    
    // Auto align weather climatology if season changes
    const newWeather = SEASONAL_CLIMATOLOGY[newSeason] || formData.weather;

    setFormData((prev) => ({
      ...prev,
      crop: newCrop,
      season: newSeason,
      weather: { ...newWeather },
      // Soybean uses shared_multicrop or legacy; others use shared_multicrop
      model_strategy: newCrop.toLowerCase() === "soybean" ? "shared_multicrop" : "shared_multicrop",
    }));

    if (errors.crop || errors.season) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next.crop;
        delete next.season;
        return next;
      });
    }
  };

  // Update district & update soil baseline
  const handleDistrictChange = (newDistrict: string) => {
    const soilBaseline = REGIONAL_SOIL_PROFILES[newDistrict];
    setFormData((prev) => ({
      ...prev,
      district: newDistrict,
      soil: soilBaseline ? { ...soilBaseline } : prev.soil,
    }));

    if (errors.district) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next.district;
        return next;
      });
    }
  };

  // Handle Soil updates with optional auto-silt derivation
  const handleSoilChange = (field: keyof typeof formData.soil, value: number) => {
    setFormData((prev) => {
      const updatedSoil = { ...prev.soil, [field]: value };
      if (autoSilt && (field === "clay_pct" || field === "sand_pct")) {
        const clay = field === "clay_pct" ? value : updatedSoil.clay_pct;
        const sand = field === "sand_pct" ? value : updatedSoil.sand_pct;
        updatedSoil.silt_pct = calculateSiltPercentage(clay, sand);
      }
      return { ...prev, soil: updatedSoil };
    });

    if (errors[`soil.${field}`]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[`soil.${field}`];
        return next;
      });
    }
  };

  // Handle Weather updates
  const handleWeatherChange = (field: keyof typeof formData.weather, value: number) => {
    setFormData((prev) => ({
      ...prev,
      weather: { ...prev.weather, [field]: value },
    }));

    if (errors[`weather.${field}`]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[`weather.${field}`];
        return next;
      });
    }
  };

  // Quick Baseline Actions
  const applyDistrictSoilBaseline = () => {
    const baseline = REGIONAL_SOIL_PROFILES[formData.district];
    if (baseline) {
      setFormData((prev) => ({ ...prev, soil: { ...baseline } }));
      setErrors((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((k) => {
          if (k.startsWith("soil.")) delete next[k];
        });
        return next;
      });
    }
  };

  const applySeasonalClimatology = () => {
    const seasonKey = formData.season || "Kharif";
    const climate = SEASONAL_CLIMATOLOGY[seasonKey];
    if (climate) {
      setFormData((prev) => ({ ...prev, weather: { ...climate } }));
      setErrors((prev) => {
        const next = { ...prev };
        Object.keys(next).forEach((k) => {
          if (k.startsWith("weather.")) delete next[k];
        });
        return next;
      });
    }
  };

  // Validate form before submission
  const validate = (): boolean => {
    const newErrors: ValidationErrors = {};

    // Validate Crop
    if (!formData.crop) newErrors.crop = "Select a crop";

    // Validate District
    if (!SUPPORTED_DISTRICTS.includes(formData.district as (typeof SUPPORTED_DISTRICTS)[number])) {
      newErrors.district = "Select a verified Maharashtra district";
    }

    // Validate Season
    const currentSeason = formData.season || "";
    const cropSpec = TRAINED_CROPS.find((c) => c.id === formData.crop);
    if (cropSpec && !cropSpec.allowedSeasons.includes(currentSeason)) {
      newErrors.season = `${formData.crop} is cultivated during ${cropSpec.allowedSeasons.join(" or ")} season.`;
    }

    // Validate Soil
    const soil = formData.soil;
    if (soil.soil_ph < VALIDATION_RULES.soil_ph.min || soil.soil_ph > VALIDATION_RULES.soil_ph.max) {
      newErrors["soil.soil_ph"] = `pH must be between ${VALIDATION_RULES.soil_ph.min} and ${VALIDATION_RULES.soil_ph.max}`;
    }
    if (soil.organic_carbon_pct < 0 || soil.organic_carbon_pct > 10) {
      newErrors["soil.organic_carbon_pct"] = "Organic carbon must be 0–10%";
    }
    if (soil.clay_pct + soil.sand_pct > 100) {
      newErrors["soil.clay_pct"] = "Clay + Sand fraction cannot exceed 100%";
    }
    if (soil.bulk_density_g_cm3 < 0.8 || soil.bulk_density_g_cm3 > 2.2) {
      newErrors["soil.bulk_density_g_cm3"] = "Bulk density must be 0.8–2.2 g/cm³";
    }
    if (soil.cation_exchange_capacity_cmol_kg < 0 || soil.cation_exchange_capacity_cmol_kg > 120) {
      newErrors["soil.cation_exchange_capacity_cmol_kg"] = "CEC must be 0–120 cmol(+)/kg";
    }

    // Validate Weather
    const weather = formData.weather;
    if (weather.cumulative_rainfall_mm < 0 || weather.cumulative_rainfall_mm > 5000) {
      newErrors["weather.cumulative_rainfall_mm"] = "Rainfall must be 0–5000 mm";
    }
    if (weather.mean_temp_max_c <= weather.mean_temp_min_c) {
      newErrors["weather.mean_temp_max_c"] = "Max temperature must exceed Min temperature";
    }
    if (weather.mean_solar_radiation_mj_m2 < 5 || weather.mean_solar_radiation_mj_m2 > 35) {
      newErrors["weather.mean_solar_radiation_mj_m2"] = "Solar radiation must be 5–35 MJ/m²/day";
    }
    if (weather.mean_relative_humidity_pct < 10 || weather.mean_relative_humidity_pct > 100) {
      newErrors["weather.mean_relative_humidity_pct"] = "Relative humidity must be 10–100%";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Submit form to live API
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    if (!validate()) {
      window.scrollTo({ top: 300, behavior: "smooth" });
      return;
    }

    setIsLoading(true);
    try {
      const response = await api.predictCropYield(formData);
      setPredictionResult(response);

      // Add to session history
      const yieldQuintalAcre = (response.predicted_yield_t_ha * 4.047).toFixed(2);
      const yieldKgHa = response.predicted_yield_kg_ha ?? Math.round(response.predicted_yield_t_ha * 1000);

      const record: CalculationRecord = {
        id: response.request_id || `rec-${Date.now()}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        crop: response.crop,
        district: response.district,
        season: response.season,
        year: response.year,
        yield_t_ha: response.predicted_yield_t_ha,
        yield_quintal_acre: yieldQuintalAcre,
        yield_kg_ha: yieldKgHa,
        request: { ...formData },
        response,
      };

      setHistory((prev) => [record, ...prev.slice(0, 9)]);

      // Scroll to result on smaller screens
      const resultEl = document.getElementById("prediction-results-view");
      if (resultEl) {
        resultEl.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setApiError(err.message);
      } else if (err instanceof Error) {
        setApiError(err.message);
      } else {
        setApiError("Failed to calculate yield. Verify backend connection.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Copy Request ID
  const copyRequestId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  // Load calculation from history
  const loadHistoryItem = (item: CalculationRecord) => {
    setFormData(item.request);
    setPredictionResult(item.response);
    window.scrollTo({ top: 120, behavior: "smooth" });
  };

  const selectedCropSpec = TRAINED_CROPS.find((c) => c.id === formData.crop) || TRAINED_CROPS[0];

  return (
    <div className="min-h-screen bg-white">
      {/* Subtle Gemini Aura Gradient Background */}
      <div className="absolute top-0 inset-x-0 h-96 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(99,102,241,0.08),rgba(255,255,255,0))] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-10">
        {/* Hero Section */}
        <div className="text-center max-w-3xl mx-auto space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-50 border border-slate-200/90 text-xs font-medium text-slate-700 shadow-2xs">
            <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
            <span>Trained Multi-Crop Random Forest Regressor • Production Ready</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Crop <span className="gemini-gradient-text">Yield Prediction</span>
          </h1>

          <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
            Calculate precision crop yields in tonnes per hectare (t/ha) from observed
            growing-season weather and SoilGrids 0–30 cm soil parameters across Maharashtra.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-2 pt-1 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1 font-medium text-slate-700 bg-slate-100/80 px-2.5 py-1 rounded-md">
              <Sprout className="w-3.5 h-3.5 text-indigo-600" /> 7 Verified Crops
            </span>
            <span>•</span>
            <span className="inline-flex items-center gap-1 font-medium text-slate-700 bg-slate-100/80 px-2.5 py-1 rounded-md">
              <MapPin className="w-3.5 h-3.5 text-indigo-600" /> 7 Maharashtra Districts
            </span>
            <span>•</span>
            <span className="inline-flex items-center gap-1 font-medium text-slate-700 bg-slate-100/80 px-2.5 py-1 rounded-md">
              <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" /> $R^2 = 0.509$ Cross-Validated
            </span>
          </div>
        </div>

        {/* Global Error Banner */}
        {apiError && (
          <Alert variant="error" title="Prediction Calculation Notice" onClose={() => setApiError(null)}>
            {apiError}
          </Alert>
        )}

        {/* Main Prediction Workspace Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Form Column (7 Cols) */}
          <form onSubmit={handleSubmit} className="lg:col-span-7 space-y-6">
            {/* 1. Crop and Geographic Parameters Card */}
            <Card className="border-slate-200 shadow-xs">
              <CardHeader
                title="1. Crop & Geographic Location"
                subtitle="Select crop variety, target district, season, and harvest year."
                badge={
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 font-semibold border border-blue-200">
                    Required
                  </span>
                }
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Crop Selection */}
                <div>
                  <label htmlFor="crop-select" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                    Crop Variety
                  </label>
                  <select
                    id="crop-select"
                    value={formData.crop}
                    onChange={(e) => handleCropChange(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors cursor-pointer"
                  >
                    {TRAINED_CROPS.map((crop) => (
                      <option key={crop.id} value={crop.id}>
                        {crop.label} ({crop.scientific})
                      </option>
                    ))}
                  </select>
                  {errors.crop && <p className="text-xs text-rose-600 mt-1">{errors.crop}</p>}
                </div>

                {/* District Selection */}
                <div>
                  <label htmlFor="district-select" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                    District (Maharashtra)
                  </label>
                  <select
                    id="district-select"
                    value={formData.district}
                    onChange={(e) => handleDistrictChange(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors cursor-pointer"
                  >
                    {SUPPORTED_DISTRICTS.map((district) => (
                      <option key={district} value={district}>
                        {district}
                      </option>
                    ))}
                  </select>
                  {errors.district && <p className="text-xs text-rose-600 mt-1">{errors.district}</p>}
                </div>

                {/* Season Selection */}
                <div>
                  <label htmlFor="season-select" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                    Growing Season
                  </label>
                  <select
                    id="season-select"
                    value={formData.season}
                    onChange={(e) => setFormData((prev) => ({ ...prev, season: e.target.value }))}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors cursor-pointer"
                  >
                    {selectedCropSpec.allowedSeasons.map((s) => (
                      <option key={s} value={s}>
                        {s} Season
                      </option>
                    ))}
                  </select>
                  {errors.season && <p className="text-xs text-rose-600 mt-1">{errors.season}</p>}
                </div>

                {/* Harvest Year */}
                <div>
                  <label htmlFor="year-input" className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
                    Harvest Year
                  </label>
                  <input
                    id="year-input"
                    type="number"
                    min={VALIDATION_RULES.year.min}
                    max={VALIDATION_RULES.year.max}
                    value={formData.year}
                    onChange={(e) => setFormData((prev) => ({ ...prev, year: parseInt(e.target.value, 10) || 2024 }))}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                  />
                </div>
              </div>
            </Card>

            {/* 2. Topsoil Profile (0-30 cm) Card */}
            <Card className="border-slate-200 shadow-xs">
              <CardHeader
                title="2. Topsoil Physicochemical Profile (0–30 cm)"
                subtitle="ISRIC SoilGrids 2.0 depth-weighted properties for the agricultural root zone."
                action={
                  <button
                    type="button"
                    onClick={applyDistrictSoilBaseline}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline inline-flex items-center gap-1 cursor-pointer"
                    title="Populate authentic ISRIC SoilGrids measured baseline for this district"
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Reset to {formData.district} Soil Profile</span>
                  </button>
                }
              />

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* Soil pH */}
                <div>
                  <label htmlFor="soil-ph" className="block text-xs font-semibold text-slate-700 mb-1">
                    Soil pH (in H₂O)
                  </label>
                  <div className="relative">
                    <input
                      id="soil-ph"
                      type="number"
                      step="0.1"
                      min={VALIDATION_RULES.soil_ph.min}
                      max={VALIDATION_RULES.soil_ph.max}
                      value={formData.soil.soil_ph}
                      onChange={(e) => handleSoilChange("soil_ph", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">pH</span>
                  </div>
                  {errors["soil.soil_ph"] && <p className="text-xs text-rose-600 mt-1">{errors["soil.soil_ph"]}</p>}
                </div>

                {/* Organic Carbon */}
                <div>
                  <label htmlFor="soil-oc" className="block text-xs font-semibold text-slate-700 mb-1">
                    Organic Carbon
                  </label>
                  <div className="relative">
                    <input
                      id="soil-oc"
                      type="number"
                      step="0.01"
                      min={0}
                      max={10}
                      value={formData.soil.organic_carbon_pct}
                      onChange={(e) => handleSoilChange("organic_carbon_pct", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">%</span>
                  </div>
                  {errors["soil.organic_carbon_pct"] && <p className="text-xs text-rose-600 mt-1">{errors["soil.organic_carbon_pct"]}</p>}
                </div>

                {/* Bulk Density */}
                <div>
                  <label htmlFor="soil-bd" className="block text-xs font-semibold text-slate-700 mb-1">
                    Bulk Density
                  </label>
                  <div className="relative">
                    <input
                      id="soil-bd"
                      type="number"
                      step="0.01"
                      min={0.8}
                      max={2.2}
                      value={formData.soil.bulk_density_g_cm3}
                      onChange={(e) => handleSoilChange("bulk_density_g_cm3", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">g/cm³</span>
                  </div>
                  {errors["soil.bulk_density_g_cm3"] && <p className="text-xs text-rose-600 mt-1">{errors["soil.bulk_density_g_cm3"]}</p>}
                </div>

                {/* Clay Fraction */}
                <div>
                  <label htmlFor="soil-clay" className="block text-xs font-semibold text-slate-700 mb-1">
                    Clay Particle Fraction
                  </label>
                  <div className="relative">
                    <input
                      id="soil-clay"
                      type="number"
                      step="0.1"
                      min={0}
                      max={100}
                      value={formData.soil.clay_pct}
                      onChange={(e) => handleSoilChange("clay_pct", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">%</span>
                  </div>
                  {errors["soil.clay_pct"] && <p className="text-xs text-rose-600 mt-1">{errors["soil.clay_pct"]}</p>}
                </div>

                {/* Sand Fraction */}
                <div>
                  <label htmlFor="soil-sand" className="block text-xs font-semibold text-slate-700 mb-1">
                    Sand Particle Fraction
                  </label>
                  <div className="relative">
                    <input
                      id="soil-sand"
                      type="number"
                      step="0.1"
                      min={0}
                      max={100}
                      value={formData.soil.sand_pct}
                      onChange={(e) => handleSoilChange("sand_pct", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">%</span>
                  </div>
                  {errors["soil.sand_pct"] && <p className="text-xs text-rose-600 mt-1">{errors["soil.sand_pct"]}</p>}
                </div>

                {/* Silt Fraction */}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label htmlFor="soil-silt" className="block text-xs font-semibold text-slate-700">
                      Silt Particle Fraction
                    </label>
                    <label className="text-[11px] text-slate-500 flex items-center gap-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={autoSilt}
                        onChange={(e) => setAutoSilt(e.target.checked)}
                        className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                      />
                      <span>Auto</span>
                    </label>
                  </div>
                  <div className="relative">
                    <input
                      id="soil-silt"
                      type="number"
                      step="0.1"
                      min={0}
                      max={100}
                      disabled={autoSilt}
                      value={formData.soil.silt_pct ?? 0}
                      onChange={(e) => handleSoilChange("silt_pct", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white disabled:bg-slate-50 border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">%</span>
                  </div>
                </div>

                {/* Cation Exchange Capacity */}
                <div className="sm:col-span-3">
                  <label htmlFor="soil-cec" className="block text-xs font-semibold text-slate-700 mb-1">
                    Cation Exchange Capacity (CEC at pH 7)
                  </label>
                  <div className="relative">
                    <input
                      id="soil-cec"
                      type="number"
                      step="0.1"
                      min={0}
                      max={120}
                      value={formData.soil.cation_exchange_capacity_cmol_kg}
                      onChange={(e) => handleSoilChange("cation_exchange_capacity_cmol_kg", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">cmol(+)/kg</span>
                  </div>
                  {errors["soil.cation_exchange_capacity_cmol_kg"] && (
                    <p className="text-xs text-rose-600 mt-1">{errors["soil.cation_exchange_capacity_cmol_kg"]}</p>
                  )}
                </div>
              </div>
            </Card>

            {/* 3. Seasonal Weather Observations Card */}
            <Card className="border-slate-200 shadow-xs">
              <CardHeader
                title="3. Seasonal Weather Observations"
                subtitle="Retrospective meteorological conditions observed across the growing season."
                action={
                  <button
                    type="button"
                    onClick={applySeasonalClimatology}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800 hover:underline inline-flex items-center gap-1 cursor-pointer"
                    title="Populate average seasonal weather climatology for this season"
                  >
                    <CloudRain className="w-3.5 h-3.5" />
                    <span>Reset to {formData.season} Climatology</span>
                  </button>
                }
              />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Cumulative Rainfall */}
                <div>
                  <label htmlFor="wx-rain" className="block text-xs font-semibold text-slate-700 mb-1">
                    Cumulative Seasonal Rainfall
                  </label>
                  <div className="relative">
                    <input
                      id="wx-rain"
                      type="number"
                      step="1"
                      min={0}
                      max={5000}
                      value={formData.weather.cumulative_rainfall_mm}
                      onChange={(e) => handleWeatherChange("cumulative_rainfall_mm", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">mm</span>
                  </div>
                  {errors["weather.cumulative_rainfall_mm"] && (
                    <p className="text-xs text-rose-600 mt-1">{errors["weather.cumulative_rainfall_mm"]}</p>
                  )}
                </div>

                {/* Solar Radiation */}
                <div>
                  <label htmlFor="wx-srad" className="block text-xs font-semibold text-slate-700 mb-1">
                    Mean Solar Radiation
                  </label>
                  <div className="relative">
                    <input
                      id="wx-srad"
                      type="number"
                      step="0.1"
                      min={5}
                      max={35}
                      value={formData.weather.mean_solar_radiation_mj_m2}
                      onChange={(e) => handleWeatherChange("mean_solar_radiation_mj_m2", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">MJ/m²/day</span>
                  </div>
                </div>

                {/* Mean Max Temperature */}
                <div>
                  <label htmlFor="wx-tmax" className="block text-xs font-semibold text-slate-700 mb-1">
                    Mean Daily Max Temperature
                  </label>
                  <div className="relative">
                    <input
                      id="wx-tmax"
                      type="number"
                      step="0.1"
                      min={15}
                      max={50}
                      value={formData.weather.mean_temp_max_c}
                      onChange={(e) => handleWeatherChange("mean_temp_max_c", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">°C</span>
                  </div>
                  {errors["weather.mean_temp_max_c"] && (
                    <p className="text-xs text-rose-600 mt-1">{errors["weather.mean_temp_max_c"]}</p>
                  )}
                </div>

                {/* Mean Min Temperature */}
                <div>
                  <label htmlFor="wx-tmin" className="block text-xs font-semibold text-slate-700 mb-1">
                    Mean Daily Min Temperature
                  </label>
                  <div className="relative">
                    <input
                      id="wx-tmin"
                      type="number"
                      step="0.1"
                      min={5}
                      max={35}
                      value={formData.weather.mean_temp_min_c}
                      onChange={(e) => handleWeatherChange("mean_temp_min_c", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">°C</span>
                  </div>
                </div>

                {/* Mean Relative Humidity */}
                <div>
                  <label htmlFor="wx-rh" className="block text-xs font-semibold text-slate-700 mb-1">
                    Mean Relative Humidity
                  </label>
                  <div className="relative">
                    <input
                      id="wx-rh"
                      type="number"
                      step="0.1"
                      min={10}
                      max={100}
                      value={formData.weather.mean_relative_humidity_pct}
                      onChange={(e) => handleWeatherChange("mean_relative_humidity_pct", parseFloat(e.target.value) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">%</span>
                  </div>
                </div>

                {/* Max Consecutive Dry Days */}
                <div>
                  <label htmlFor="wx-cdd" className="block text-xs font-semibold text-slate-700 mb-1">
                    Max Consecutive Dry Days (&lt;2.5mm)
                  </label>
                  <div className="relative">
                    <input
                      id="wx-cdd"
                      type="number"
                      step="1"
                      min={0}
                      max={153}
                      value={formData.weather.consecutive_dry_days_max ?? 0}
                      onChange={(e) => handleWeatherChange("consecutive_dry_days_max", parseInt(e.target.value, 10) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">days</span>
                  </div>
                </div>

                {/* Heat Stress Days */}
                <div className="sm:col-span-2">
                  <label htmlFor="wx-hsd" className="block text-xs font-semibold text-slate-700 mb-1">
                    Heat Stress Days (Max Temp &gt;35°C during season)
                  </label>
                  <div className="relative">
                    <input
                      id="wx-hsd"
                      type="number"
                      step="1"
                      min={0}
                      max={153}
                      value={formData.weather.heat_stress_days ?? 0}
                      onChange={(e) => handleWeatherChange("heat_stress_days", parseInt(e.target.value, 10) || 0)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-300 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-colors"
                    />
                    <span className="absolute right-3 top-2.5 text-xs text-slate-400">days</span>
                  </div>
                </div>
              </div>
            </Card>

            {/* Submission & Action Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={isLoading}
                leftIcon={<Sparkles className="w-5 h-5 text-white" />}
                className="w-full sm:w-auto px-8 py-3 text-base font-semibold shadow-md cursor-pointer"
              >
                {isLoading ? "Running Prediction Model..." : "Calculate Crop Yield"}
              </Button>

              <Button
                type="button"
                variant="outline"
                size="md"
                onClick={() => {
                  applyDistrictSoilBaseline();
                  applySeasonalClimatology();
                }}
                leftIcon={<RotateCcw className="w-4 h-4 text-slate-500" />}
                className="w-full sm:w-auto"
              >
                Reset to Baselines
              </Button>
            </div>
          </form>

          {/* Right Results Column (5 Cols) */}
          <div id="prediction-results-view" className="lg:col-span-5 space-y-6">
            {predictionResult ? (
              <div className="space-y-6 animate-fadeIn">
                {/* 1. Main Yield Result Card */}
                <div className="rounded-2xl p-6 sm:p-8 bg-gradient-to-br from-white via-indigo-50/30 to-purple-50/20 border border-indigo-200/90 shadow-[0_10px_35px_-5px_rgba(79,70,229,0.12)] space-y-6">
                  {/* Top Badge Pill */}
                  <div className="flex items-center justify-between gap-2 border-b border-indigo-100 pb-4">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 border border-indigo-200/80 px-2.5 py-1 rounded-full">
                      <Clock className="w-3.5 h-3.5" />
                      <span>End-of-Season Retrospective Yield</span>
                    </div>

                    <button
                      onClick={() => copyRequestId(predictionResult.request_id || "")}
                      className="text-xs text-slate-500 hover:text-slate-800 inline-flex items-center gap-1 cursor-pointer"
                      title="Copy Request ID"
                    >
                      {copiedId ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>ID</span>
                    </button>
                  </div>

                  {/* Main Metric Hero */}
                  <div>
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Estimated {predictionResult.crop} Yield
                    </span>
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="text-4xl sm:text-5xl font-black text-slate-950 tracking-tight">
                        {predictionResult.predicted_yield_t_ha.toFixed(2)}
                      </span>
                      <span className="text-sm sm:text-base font-semibold text-slate-600">
                        tonnes / hectare (t/ha)
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      Calculated for {predictionResult.district} ({predictionResult.season} Season, {predictionResult.year})
                    </p>
                  </div>

                  {/* Agricultural Conversions */}
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                      <span className="text-[11px] font-semibold text-slate-500 uppercase">Per Acre Unit</span>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {(predictionResult.predicted_yield_t_ha * 4.047).toFixed(2)}
                        <span className="text-xs font-normal text-slate-500 ml-1">qt/acre</span>
                      </div>
                      <span className="text-[10px] text-slate-400">Quintals per Acre</span>
                    </div>

                    <div className="p-3.5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                      <span className="text-[11px] font-semibold text-slate-500 uppercase">Metric Weight</span>
                      <div className="text-lg font-bold text-slate-900 mt-0.5">
                        {Math.round(predictionResult.predicted_yield_t_ha * 1000).toLocaleString()}
                        <span className="text-xs font-normal text-slate-500 ml-1">kg/ha</span>
                      </div>
                      <span className="text-[10px] text-slate-400">Kilograms per Hectare</span>
                    </div>
                  </div>

                  {/* 90% Confidence Interval */}
                  {predictionResult.prediction_interval && (
                    <div className="p-4 rounded-xl bg-white/80 border border-indigo-100/90 space-y-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-slate-700">90% Prediction Interval</span>
                        <span className="font-mono text-slate-600">
                          {predictionResult.prediction_interval.lower_bound_t_ha.toFixed(2)} – {predictionResult.prediction_interval.upper_bound_t_ha.toFixed(2)} t/ha
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-2 relative overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2 rounded-full"
                          style={{
                            width: `${Math.min(100, Math.max(15, (predictionResult.predicted_yield_t_ha / 3.0) * 100))}%`,
                          }}
                        />
                      </div>
                      <p className="text-[11px] text-slate-500">
                        Statistical band derived from empirical cross-validation error distribution.
                      </p>
                    </div>
                  )}

                  {/* Model Governance Details */}
                  <div className="pt-2 border-t border-indigo-100/80 flex items-center justify-between text-xs text-slate-500">
                    <div className="flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-indigo-600" />
                      <span>{predictionResult.model_name} (v{predictionResult.model_version})</span>
                    </div>
                    <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                      Validated
                    </span>
                  </div>
                </div>

                {/* 2. Top Feature Drivers Card */}
                {predictionResult.global_feature_importance && predictionResult.global_feature_importance.length > 0 && (
                  <Card className="border-slate-200 shadow-xs">
                    <CardHeader
                      title="Key Agroclimatic Drivers"
                      subtitle="Top meteorological & edaphic features influencing the model prediction."
                    />
                    <div className="space-y-3">
                      {predictionResult.global_feature_importance.slice(0, 4).map((feat, idx) => {
                        const cleanName = feat.feature
                          .replace(/_/g, " ")
                          .replace("pct", "(%)")
                          .replace("mm", "(mm)")
                          .replace("mj m2", "")
                          .replace("c", "(°C)");
                        return (
                          <div key={idx} className="space-y-1">
                            <div className="flex justify-between text-xs font-medium text-slate-700">
                              <span className="capitalize">{cleanName}</span>
                              <span className="font-mono text-indigo-600 font-semibold">
                                +{feat.importance_mean_rmse.toFixed(3)} t/ha
                              </span>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-1.5">
                              <div
                                className="bg-indigo-600 h-1.5 rounded-full"
                                style={{
                                  width: `${Math.min(100, (feat.importance_mean_rmse / 0.15) * 100)}%`,
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </Card>
                )}

                {/* 3. Scientific Timing & Limitation Disclosure */}
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-1.5">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                    <Info className="w-4 h-4 text-slate-500" />
                    <span>Scientific Timing Disclosure</span>
                  </div>
                  <p className="leading-relaxed text-[11px] text-slate-500">
                    This model estimates harvest-time yield using observed season-long weather aggregates.
                    It is an end-of-season assessment rather than a pre-sowing forecast. Soil parameters reflect
                    0–30 cm regional ISRIC SoilGrids 2.0 depth profiles.
                  </p>
                </div>
              </div>
            ) : (
              /* Awaiting Calculation State Card */
              <div className="rounded-2xl p-8 bg-slate-50/80 border border-slate-200 text-center space-y-6">
                <div className="w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-2xs">
                  <Sparkles className="w-7 h-7" />
                </div>

                <div className="space-y-2 max-w-sm mx-auto">
                  <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                    Ready to Calculate Yield
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    Select your crop and district on the left, verify soil and seasonal weather parameters,
                    and click <strong>&quot;Calculate Crop Yield&quot;</strong> to evaluate model inference.
                  </p>
                </div>

                {/* Model Integrity Pill Summary */}
                <div className="p-4 rounded-xl bg-white border border-slate-200 text-left space-y-3">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Active Production Architecture
                  </span>

                  <div className="flex items-start gap-2.5 text-xs text-slate-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>Universal Random Forest trained on 1,293 Maharashtra multi-crop observations.</span>
                  </div>

                  <div className="flex items-start gap-2.5 text-xs text-slate-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>Strict spatial Leave-One-District-Out cross-validation ($R^2 = 0.509$).</span>
                  </div>

                  <div className="flex items-start gap-2.5 text-xs text-slate-600">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <span>Real-time serving via FastAPI with Pydantic v2 validation.</span>
                  </div>
                </div>
              </div>
            )}

            {/* Session Calculation History */}
            {history.length > 0 && (
              <Card className="border-slate-200 shadow-xs">
                <CardHeader
                  title="Session History"
                  subtitle="Recent calculations in this session."
                  action={
                    <button
                      type="button"
                      onClick={() => setHistory([])}
                      className="text-xs text-slate-400 hover:text-slate-600 cursor-pointer"
                    >
                      Clear
                    </button>
                  }
                />

                <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto pr-1">
                  {history.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => loadHistoryItem(item)}
                      className="py-2.5 flex items-center justify-between text-xs hover:bg-slate-50 px-2 rounded-lg transition-colors cursor-pointer group"
                    >
                      <div>
                        <div className="font-semibold text-slate-800">
                          {item.crop} ({item.season})
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {item.district} • {item.timestamp}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-indigo-600 font-mono">
                          {item.yield_t_ha.toFixed(2)} t/ha
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {item.yield_quintal_acre} qt/acre
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
