"use client";

import React, { useState } from "react";
import { PredictionRequest, PredictionResponse } from "@/lib/types";
import {
  SUPPORTED_DISTRICTS,
  VALIDATION_RULES,
  validatePredictionRequest,
  calculateSiltPercentage,
  ValidationErrors,
} from "@/lib/validation";
import { ILLUSTRATIVE_PRESETS } from "@/lib/presets";
import { api, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/common/Card";
import { Button } from "@/components/common/Button";
import { Alert } from "@/components/common/Alert";
import {
  MapPin,
  CloudRain,
  Layers,
  Sparkles,
  RotateCcw,
  HelpCircle,
  Calculator,
} from "lucide-react";

interface PredictionFormProps {
  onSuccess: (result: PredictionResponse, request: PredictionRequest) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export function PredictionForm({
  onSuccess,
  isLoading,
  setIsLoading,
}: PredictionFormProps) {
  const [formData, setFormData] = useState<PredictionRequest>({
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
  });

  const [autoSilt, setAutoSilt] = useState<boolean>(true);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);

  // Field change handlers
  const handleScopeChange = (field: keyof PredictionRequest, value: string | number) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const handleSoilChange = (field: keyof typeof formData.soil, value: number) => {
    setFormData((prev) => {
      const nextSoil = { ...prev.soil, [field]: value };
      if (autoSilt && (field === "clay_pct" || field === "sand_pct")) {
        const clay = field === "clay_pct" ? value : nextSoil.clay_pct;
        const sand = field === "sand_pct" ? value : nextSoil.sand_pct;
        nextSoil.silt_pct = calculateSiltPercentage(clay, sand);
      }
      return { ...prev, soil: nextSoil };
    });

    const errorKey = `soil.${field}`;
    if (errors[errorKey]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[errorKey];
        return next;
      });
    }
  };

  const handleWeatherChange = (field: keyof typeof formData.weather, value: number) => {
    setFormData((prev) => ({
      ...prev,
      weather: { ...prev.weather, [field]: value },
    }));

    const errorKey = `weather.${field}`;
    if (errors[errorKey]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[errorKey];
        return next;
      });
    }
  };

  const loadPreset = (presetId: string) => {
    const preset = ILLUSTRATIVE_PRESETS.find((p) => p.id === presetId);
    if (preset) {
      setFormData(preset.data);
      setErrors({});
      setApiError(null);
    }
  };

  const resetForm = () => {
    setFormData(ILLUSTRATIVE_PRESETS[0].data);
    setErrors({});
    setApiError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    // 1. Client-side validation
    const validationErrors = validatePredictionRequest(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      // Scroll to first error
      const firstErrorKey = Object.keys(validationErrors)[0];
      const element = document.getElementById(firstErrorKey);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
        element.focus();
      }
      return;
    }

    // 2. Submit to backend API
    setIsLoading(true);
    try {
      const response = await api.predictCropYield(formData);
      onSuccess(response, formData);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setApiError(err.message);
      } else {
        setApiError("An unexpected network error occurred while submitting your prediction.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-8" noValidate>
      {/* Illustrative Presets Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200/80 dark:border-emerald-800/60">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-5 h-5 text-emerald-700 dark:text-emerald-400 shrink-0" />
          <div>
            <h4 className="text-sm font-semibold text-emerald-950 dark:text-emerald-200">
              Illustrative Sample Scenarios
            </h4>
            <p className="text-xs text-emerald-800/80 dark:text-emerald-400/80">
              Populate form with validated example figures for rapid interactive testing.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          {ILLUSTRATIVE_PRESETS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => loadPreset(p.id)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-white dark:bg-zinc-900 border border-emerald-300 dark:border-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-900/40 text-emerald-900 dark:text-emerald-200 transition-colors shadow-2xs"
            >
              {p.district} Sample
            </button>
          ))}
          <button
            type="button"
            onClick={resetForm}
            className="p-1.5 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 hover:bg-white/80 dark:hover:bg-zinc-800 rounded-lg transition-colors"
            title="Reset to default"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {apiError && (
        <Alert
          variant="error"
          title="Inference Request Failed"
          onClose={() => setApiError(null)}
        >
          {apiError}
        </Alert>
      )}

      {/* 1. Geographic & Crop Scope Card */}
      <Card>
        <CardHeader
          title="1. Crop & Geographic Location"
          subtitle="Select verified Maharashtra district with SoilGrids baseline profile."
          badge={<MapPin className="w-4 h-4 text-emerald-600" />}
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Crop */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-600 dark:text-zinc-400 mb-1.5">
              Crop Target
            </label>
            <input
              type="text"
              value={formData.crop}
              disabled
              className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-sm font-medium cursor-not-allowed"
            />
            <span className="text-[11px] text-zinc-400 mt-1 block">Trained for rainfed soybean</span>
          </div>

          {/* State */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-600 dark:text-zinc-400 mb-1.5">
              State Domain
            </label>
            <input
              type="text"
              value={formData.state}
              disabled
              className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-sm font-medium cursor-not-allowed"
            />
            <span className="text-[11px] text-zinc-400 mt-1 block">Maharashtra, India</span>
          </div>

          {/* District Selection */}
          <div>
            <label
              htmlFor="district"
              className="block text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300 mb-1.5"
            >
              District <span className="text-rose-500">*</span>
            </label>
            <select
              id="district"
              value={formData.district}
              onChange={(e) => handleScopeChange("district", e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
            >
              {SUPPORTED_DISTRICTS.map((dist) => (
                <option key={dist} value={dist}>
                  {dist}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-zinc-500 mt-1 block">
              7 districts with SoilGrids profiles
            </span>
            {errors.district && (
              <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{errors.district}</p>
            )}
          </div>

          {/* Season & Year */}
          <div>
            <label
              htmlFor="year"
              className="block text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300 mb-1.5"
            >
              Harvest Year <span className="text-rose-500">*</span>
            </label>
            <input
              id="year"
              type="number"
              min={VALIDATION_RULES.year.min}
              max={VALIDATION_RULES.year.max}
              value={formData.year}
              onChange={(e) => handleScopeChange("year", parseInt(e.target.value) || 2024)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
            />
            <span className="text-[11px] text-zinc-500 mt-1 block">Kharif harvest year</span>
            {errors.year && (
              <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{errors.year}</p>
            )}
          </div>
        </div>
      </Card>

      {/* 2. Kharif Seasonal Weather Indicators Card */}
      <Card>
        <CardHeader
          title="2. Kharif Seasonal Agroclimatology (June 1 – October 31)"
          subtitle="Observed weather indicators across the 153-day growing season. End-of-season inputs required."
          badge={<CloudRain className="w-4 h-4 text-emerald-600" />}
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {/* Cumulative Rainfall */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="weather.cumulative_rainfall_mm"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Rainfall Total (mm)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0–5000 mm]</span>
            </div>
            <input
              id="weather.cumulative_rainfall_mm"
              type="number"
              step="0.1"
              value={formData.weather.cumulative_rainfall_mm}
              onChange={(e) => handleWeatherChange("cumulative_rainfall_mm", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Cumulative monsoon precipitation</p>
            {errors["weather.cumulative_rainfall_mm"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["weather.cumulative_rainfall_mm"]}</p>
            )}
          </div>

          {/* Max Temperature */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="weather.mean_temp_max_c"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Mean Max Temp (°C)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[15–50 °C]</span>
            </div>
            <input
              id="weather.mean_temp_max_c"
              type="number"
              step="0.1"
              value={formData.weather.mean_temp_max_c}
              onChange={(e) => handleWeatherChange("mean_temp_max_c", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Mean daily daytime peak</p>
            {errors["weather.mean_temp_max_c"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["weather.mean_temp_max_c"]}</p>
            )}
          </div>

          {/* Min Temperature */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="weather.mean_temp_min_c"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Mean Min Temp (°C)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[5–35 °C]</span>
            </div>
            <input
              id="weather.mean_temp_min_c"
              type="number"
              step="0.1"
              value={formData.weather.mean_temp_min_c}
              onChange={(e) => handleWeatherChange("mean_temp_min_c", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Mean nighttime low (must be ≤ max)</p>
            {errors["weather.mean_temp_min_c"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["weather.mean_temp_min_c"]}</p>
            )}
          </div>

          {/* Relative Humidity */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="weather.mean_relative_humidity_pct"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Relative Humidity (%)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[10–100%]</span>
            </div>
            <input
              id="weather.mean_relative_humidity_pct"
              type="number"
              step="0.1"
              value={formData.weather.mean_relative_humidity_pct}
              onChange={(e) => handleWeatherChange("mean_relative_humidity_pct", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Highest ranking model predictor</p>
            {errors["weather.mean_relative_humidity_pct"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["weather.mean_relative_humidity_pct"]}</p>
            )}
          </div>

          {/* Solar Radiation */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="weather.mean_solar_radiation_mj_m2"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Solar Radiation (MJ/m²/d)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[5–35]</span>
            </div>
            <input
              id="weather.mean_solar_radiation_mj_m2"
              type="number"
              step="0.1"
              value={formData.weather.mean_solar_radiation_mj_m2}
              onChange={(e) => handleWeatherChange("mean_solar_radiation_mj_m2", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Surface downward insolation</p>
            {errors["weather.mean_solar_radiation_mj_m2"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["weather.mean_solar_radiation_mj_m2"]}</p>
            )}
          </div>

          {/* Consecutive Dry Days */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="weather.consecutive_dry_days_max"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Max Dry Spell (days)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0–153 days]</span>
            </div>
            <input
              id="weather.consecutive_dry_days_max"
              type="number"
              value={formData.weather.consecutive_dry_days_max}
              onChange={(e) => handleWeatherChange("consecutive_dry_days_max", parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Longest streak &lt; 2.5mm/day</p>
            {errors["weather.consecutive_dry_days_max"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["weather.consecutive_dry_days_max"]}</p>
            )}
          </div>

          {/* Heat Stress Days */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="weather.heat_stress_days"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Heat Stress Days (&gt;35°C)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0–153 days]</span>
            </div>
            <input
              id="weather.heat_stress_days"
              type="number"
              value={formData.weather.heat_stress_days}
              onChange={(e) => handleWeatherChange("heat_stress_days", parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Days exceeding 35°C threshold</p>
            {errors["weather.heat_stress_days"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["weather.heat_stress_days"]}</p>
            )}
          </div>
        </div>
      </Card>

      {/* 3. Topsoil Pedological Properties Card */}
      <Card>
        <CardHeader
          title="3. Soil Physical & Chemical Properties (0–30 cm Topsoil)"
          subtitle="ISRIC SoilGrids 2.0 depth-weighted averages. Establishes the regional edaphic yield potential."
          badge={<Layers className="w-4 h-4 text-emerald-600" />}
          action={
            <label className="inline-flex items-center gap-2 text-xs font-medium text-zinc-600 dark:text-zinc-400 cursor-pointer">
              <input
                type="checkbox"
                checked={autoSilt}
                onChange={(e) => setAutoSilt(e.target.checked)}
                className="rounded border-zinc-300 text-emerald-600 focus:ring-emerald-500"
              />
              <span>Auto-derive silt (100 - clay - sand)</span>
            </label>
          }
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {/* Soil pH */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="soil.soil_ph"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Soil pH in H2O
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[3.5–10.0]</span>
            </div>
            <input
              id="soil.soil_ph"
              type="number"
              step="0.1"
              value={formData.soil.soil_ph}
              onChange={(e) => handleSoilChange("soil_ph", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Water-soluble acidity/alkalinity</p>
            {errors["soil.soil_ph"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["soil.soil_ph"]}</p>
            )}
          </div>

          {/* Organic Carbon */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="soil.organic_carbon_pct"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Organic Carbon (% wt)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0.0–10.0%]</span>
            </div>
            <input
              id="soil.organic_carbon_pct"
              type="number"
              step="0.01"
              value={formData.soil.organic_carbon_pct}
              onChange={(e) => handleSoilChange("organic_carbon_pct", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Fine earth organic fraction</p>
            {errors["soil.organic_carbon_pct"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["soil.organic_carbon_pct"]}</p>
            )}
          </div>

          {/* Clay % */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="soil.clay_pct"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Clay Fraction (%)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0–100%]</span>
            </div>
            <input
              id="soil.clay_pct"
              type="number"
              step="0.1"
              value={formData.soil.clay_pct}
              onChange={(e) => handleSoilChange("clay_pct", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">&lt;2µm particles (vertisol heavy)</p>
            {errors["soil.clay_pct"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["soil.clay_pct"]}</p>
            )}
          </div>

          {/* Sand % */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="soil.sand_pct"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Sand Fraction (%)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0–100%]</span>
            </div>
            <input
              id="soil.sand_pct"
              type="number"
              step="0.1"
              value={formData.soil.sand_pct}
              onChange={(e) => handleSoilChange("sand_pct", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">50–2000µm particle fraction</p>
            {errors["soil.sand_pct"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["soil.sand_pct"]}</p>
            )}
          </div>

          {/* Silt % */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="soil.silt_pct"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Silt Fraction (%)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0–100%]</span>
            </div>
            <input
              id="soil.silt_pct"
              type="number"
              step="0.1"
              disabled={autoSilt}
              value={formData.soil.silt_pct ?? 0}
              onChange={(e) => handleSoilChange("silt_pct", parseFloat(e.target.value) || 0)}
              className={`w-full px-3 py-2 rounded-lg border text-sm outline-none ${
                autoSilt
                  ? "bg-zinc-100 dark:bg-zinc-800 text-zinc-500 border-zinc-200 dark:border-zinc-700 cursor-not-allowed"
                  : "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 border-zinc-300 dark:border-zinc-700 focus:ring-2 focus:ring-emerald-500"
              }`}
            />
            <p className="text-[11px] text-zinc-500 mt-1">
              {autoSilt ? "Auto-computed: 100 - clay - sand" : "2–50µm particle fraction"}
            </p>
            {errors["soil.silt_pct"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["soil.silt_pct"]}</p>
            )}
          </div>

          {/* Bulk Density */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="soil.bulk_density_g_cm3"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                Bulk Density (g/cm³)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0.8–2.2]</span>
            </div>
            <input
              id="soil.bulk_density_g_cm3"
              type="number"
              step="0.01"
              value={formData.soil.bulk_density_g_cm3}
              onChange={(e) => handleSoilChange("bulk_density_g_cm3", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Fine earth density</p>
            {errors["soil.bulk_density_g_cm3"] && (
              <p className="text-xs text-rose-600 mt-1">{errors["soil.bulk_density_g_cm3"]}</p>
            )}
          </div>

          {/* Cation Exchange Capacity */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="soil.cation_exchange_capacity_cmol_kg"
                className="text-xs font-semibold text-zinc-700 dark:text-zinc-300"
              >
                CEC (cmol(+)/kg)
              </label>
              <span className="text-[11px] font-mono text-zinc-400">[0–120]</span>
            </div>
            <input
              id="soil.cation_exchange_capacity_cmol_kg"
              type="number"
              step="0.1"
              value={formData.soil.cation_exchange_capacity_cmol_kg}
              onChange={(e) => handleSoilChange("cation_exchange_capacity_cmol_kg", parseFloat(e.target.value) || 0)}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
            />
            <p className="text-[11px] text-zinc-500 mt-1">Nutrient retention capacity at pH 7</p>
            {errors["soil.cation_exchange_capacity_cmol_kg"] && (
              <p className="text-xs text-rose-600 mt-1">
                {errors["soil.cation_exchange_capacity_cmol_kg"]}
              </p>
            )}
          </div>
        </div>
      </Card>

      {/* Submission Action Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-5 rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs">
        <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          <HelpCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>
            Model inference executes against the serialized Random Forest pipeline on FastAPI.
          </span>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <Button
            type="button"
            variant="outline"
            onClick={resetForm}
            disabled={isLoading}
            className="w-full sm:w-auto"
          >
            Reset
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="lg"
            isLoading={isLoading}
            leftIcon={<Calculator className="w-4 h-4" />}
            className="w-full sm:w-auto shadow-md"
          >
            Predict Crop Yield
          </Button>
        </div>
      </div>
    </form>
  );
}
