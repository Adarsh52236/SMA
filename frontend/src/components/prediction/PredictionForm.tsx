"use client";

import React, { useState, useEffect } from "react";
import {
  PredictionRequest,
  PredictionResponse,
  PredictionPolicy,
  DynamicPresetSample,
  CategoryCombination,
} from "@/lib/types";
import {
  SUPPORTED_DISTRICTS,
  SUPPORTED_CROPS,
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
  Cpu,
  ShieldCheck,
  Compass,
  Database,
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
  const [policy, setPolicy] = useState<PredictionPolicy>("conservative");
  const [formData, setFormData] = useState<PredictionRequest>({
    crop: "Soybean",
    state: "Maharashtra",
    district: "Akola",
    season: "Kharif",
    year: 2024,
    prediction_policy: "conservative",
    model_strategy: "legacy_soybean",
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

  // Dynamic discovery states
  const [discoveredCrops, setDiscoveredCrops] = useState<string[]>([]);
  const [discoveredDistricts, setDiscoveredDistricts] = useState<string[]>([]);
  const [observedCombinations, setObservedCombinations] = useState<CategoryCombination[]>([]);
  const [dynamicPresets, setDynamicPresets] = useState<DynamicPresetSample[]>([]);
  const [isLoadingDiscovery, setIsLoadingDiscovery] = useState<boolean>(true);
  const [discoverySource, setDiscoverySource] = useState<string>("fallback");

  // Custom freeform category states for exploratory mode
  const [isCustomCrop, setIsCustomCrop] = useState<boolean>(false);
  const [customCropValue, setCustomCropValue] = useState<string>("");
  const [isCustomDistrict, setIsCustomDistrict] = useState<boolean>(false);
  const [customDistrictValue, setCustomDistrictValue] = useState<string>("");

  const [autoSilt, setAutoSilt] = useState<boolean>(true);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);

  // Fetch dynamic categories and empirical presets on component mount
  useEffect(() => {
    let isMounted = true;
    async function loadDynamicCatalog() {
      try {
        const [catRes, sampleRes] = await Promise.all([
          api.getDiscoveredCategories().catch(() => null),
          api.getDynamicPresets().catch(() => null),
        ]);

        if (!isMounted) return;

        if (catRes && catRes.categories) {
          if (catRes.categories.crop && catRes.categories.crop.length > 0) {
            setDiscoveredCrops(catRes.categories.crop);
          }
          if (catRes.categories.district && catRes.categories.district.length > 0) {
            setDiscoveredDistricts(catRes.categories.district);
          }
          if (catRes.observed_combinations) {
            setObservedCombinations(catRes.observed_combinations);
          }
          setDiscoverySource("backend_discovery");
        }

        if (sampleRes && sampleRes.presets && sampleRes.presets.length > 0) {
          setDynamicPresets(sampleRes.presets);
        }
      } catch {
        // Fallback to static registry defaults
      } finally {
        if (isMounted) setIsLoadingDiscovery(false);
      }
    }
    loadDynamicCatalog();
    return () => {
      isMounted = false;
    };
  }, []);

  // Update policy and sync with formData
  const handlePolicyChange = (newPolicy: PredictionPolicy) => {
    setPolicy(newPolicy);
    setFormData((prev) => ({ ...prev, prediction_policy: newPolicy }));
    setErrors({});
  };

  // Derive active crop and district options
  const activeCropsList = discoveredCrops.length > 0 ? discoveredCrops : SUPPORTED_CROPS.map((c) => c.label);
  const activeDistrictsList = discoveredDistricts.length > 0 ? discoveredDistricts : Array.from(SUPPORTED_DISTRICTS);

  // Derive allowed seasons for currently selected crop dynamically
  const availableSeasons: string[] = React.useMemo(() => {
    const selected = (formData.crop || "").trim().toLowerCase();
    const combos = observedCombinations.filter(
      (c) =>
        (c.feature_a === "crop" && c.value_a.toLowerCase() === selected && c.feature_b === "season") ||
        (c.feature_b === "crop" && c.value_b.toLowerCase() === selected && c.feature_a === "season")
    );
    if (combos.length > 0) {
      const derived = Array.from(new Set(combos.map((c) => (c.feature_a === "season" ? c.value_a : c.value_b))));
      if (derived.length > 0) return derived;
    }
    // Default fallback seasons
    if (selected === "wheat" || selected === "chickpea") return ["Rabi"];
    return ["Kharif", "Rabi"];
  }, [formData.crop, observedCombinations]);

  // Field change handlers
  const handleScopeChange = (field: keyof PredictionRequest, value: string | number) => {
    setFormData((prev) => {
      const next = { ...prev, [field]: value };
      if (field === "crop") {
        const cropStr = String(value).toLowerCase();
        if (cropStr === "soybean") {
          next.model_strategy = prev.model_strategy || "legacy_soybean";
        } else {
          next.model_strategy = "shared_multicrop";
        }
        // Auto-select first compatible season if current season not in available list
        if (!availableSeasons.includes(next.season || "")) {
          next.season = availableSeasons[0] || "Kharif";
        }
      }
      return next;
    });

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
      setFormData({
        ...preset.data,
        prediction_policy: policy,
      });
      setIsCustomCrop(false);
      setIsCustomDistrict(false);
      setErrors({});
      setApiError(null);
    }
  };

  const loadDynamicSample = (sample: DynamicPresetSample) => {
    const vals = sample.sample_values;
    setFormData((prev) => ({
      ...prev,
      crop: String(vals.crop || prev.crop),
      district: String(vals.district || prev.district),
      season: String(vals.season || prev.season || "Kharif"),
      year: Number(vals.year || prev.year),
      prediction_policy: policy,
      soil: {
        soil_ph: Number(vals.soil_ph ?? prev.soil.soil_ph),
        organic_carbon_pct: Number(vals.organic_carbon_pct ?? prev.soil.organic_carbon_pct),
        clay_pct: Number(vals.clay_pct ?? prev.soil.clay_pct),
        sand_pct: Number(vals.sand_pct ?? prev.soil.sand_pct),
        silt_pct: Number(vals.silt_pct ?? prev.soil.silt_pct),
        bulk_density_g_cm3: Number(vals.bulk_density_g_cm3 ?? prev.soil.bulk_density_g_cm3),
        cation_exchange_capacity_cmol_kg: Number(
          vals.cation_exchange_capacity_cmol_kg ?? prev.soil.cation_exchange_capacity_cmol_kg
        ),
      },
      weather: {
        cumulative_rainfall_mm: Number(vals.cumulative_rainfall_mm ?? prev.weather.cumulative_rainfall_mm),
        mean_temp_max_c: Number(vals.mean_temp_max_c ?? prev.weather.mean_temp_max_c),
        mean_temp_min_c: Number(vals.mean_temp_min_c ?? prev.weather.mean_temp_min_c),
        mean_solar_radiation_mj_m2: Number(
          vals.mean_solar_radiation_mj_m2 ?? prev.weather.mean_solar_radiation_mj_m2
        ),
        mean_relative_humidity_pct: Number(
          vals.mean_relative_humidity_pct ?? prev.weather.mean_relative_humidity_pct
        ),
        consecutive_dry_days_max: Number(
          vals.consecutive_dry_days_max ?? prev.weather.consecutive_dry_days_max
        ),
        heat_stress_days: Number(vals.heat_stress_days ?? prev.weather.heat_stress_days),
      },
    }));
    setIsCustomCrop(false);
    setIsCustomDistrict(false);
    setErrors({});
    setApiError(null);
  };

  const resetForm = () => {
    setFormData({
      ...ILLUSTRATIVE_PRESETS[0].data,
      prediction_policy: policy,
    });
    setIsCustomCrop(false);
    setIsCustomDistrict(false);
    setErrors({});
    setApiError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);

    // Apply custom crop or district if entered
    const submissionData: PredictionRequest = {
      ...formData,
      crop: isCustomCrop && customCropValue.trim() ? customCropValue.trim() : formData.crop,
      district: isCustomDistrict && customDistrictValue.trim() ? customDistrictValue.trim() : formData.district,
      prediction_policy: policy,
    };

    // 1. Client-side dynamic validation
    const validationErrors = validatePredictionRequest(submissionData, {
      supportedDistricts: activeDistrictsList,
      supportedCrops: activeCropsList.map((label) => ({ id: label.toLowerCase(), label })),
      policy,
    });

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
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
      const response = await api.predictCropYield(submissionData);
      onSuccess(response, submissionData);
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
      {/* Policy Selector Banner */}
      <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Prediction Governance Policy
            </h3>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 font-semibold uppercase tracking-wider">
              {policy}
            </span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-xl">
            {policy === "conservative"
              ? "Conservative Mode: strictly restricts inference to combinations meeting verified SoilGrids baseline requirements and training data distributions."
              : "Exploratory Mode: enables inference for novel crops, unverified districts (e.g., Thane, Kalyan, Nagpur), and out-of-distribution values with explicit coverage disclaimers."}
          </p>
        </div>

        <div className="flex items-center gap-2 p-1 rounded-xl bg-zinc-100 dark:bg-zinc-800 self-stretch md:self-auto">
          <button
            type="button"
            onClick={() => handlePolicyChange("conservative")}
            className={`flex-1 md:flex-none flex items-center justify-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              policy === "conservative"
                ? "bg-white dark:bg-zinc-900 text-emerald-800 dark:text-emerald-300 shadow-xs"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Conservative
          </button>
          <button
            type="button"
            onClick={() => handlePolicyChange("exploratory")}
            className={`flex-1 md:flex-none flex items-center justify-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              policy === "exploratory"
                ? "bg-white dark:bg-zinc-900 text-amber-700 dark:text-amber-300 shadow-xs"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200"
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            Exploratory
          </button>
        </div>
      </div>

      {/* Discovered Presets & Real Dataset Samples */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200/80 dark:border-emerald-800/60">
        <div className="flex items-center gap-2.5">
          <Sparkles className="w-5 h-5 text-emerald-700 dark:text-emerald-400 shrink-0" />
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-semibold text-emerald-950 dark:text-emerald-200">
                Data-Driven Scenario Presets
              </h4>
              {discoverySource === "backend_discovery" && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-200/70 dark:bg-emerald-900/60 text-emerald-900 dark:text-emerald-200 font-mono">
                  Live Discovered
                </span>
              )}
            </div>
            <p className="text-xs text-emerald-800/80 dark:text-emerald-400/80">
              Sampled directly from authentic dataset observations across verified agricultural seasons.
            </p>
          </div>
        </div>

        <div className="flex items-center flex-wrap gap-2 w-full sm:w-auto">
          {dynamicPresets.length > 0
            ? dynamicPresets.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => loadDynamicSample(s)}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg bg-white dark:bg-zinc-900 border border-emerald-300 dark:border-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-900/40 text-emerald-900 dark:text-emerald-200 transition-colors shadow-2xs"
                  title={s.description}
                >
                  {s.name}
                </button>
              ))
            : ILLUSTRATIVE_PRESETS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => loadPreset(p.id)}
                  className="px-2.5 py-1 text-xs font-medium rounded-lg bg-white dark:bg-zinc-900 border border-emerald-300 dark:border-emerald-700 hover:bg-emerald-50 dark:hover:bg-emerald-900/40 text-emerald-900 dark:text-emerald-200 transition-colors shadow-2xs"
                >
                  {p.crop} ({p.district})
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
          title="1. Crop Selection & Geographic Scope"
          subtitle={
            isLoadingDiscovery
              ? "Discovering valid crops and geographic boundaries from backend schema engine..."
              : discoverySource === "backend_discovery"
              ? `Discovered ${activeCropsList.length} crops and ${activeDistrictsList.length} regions dynamically from dataset schema.`
              : "Select supported crop and verified Maharashtra district with SoilGrids baseline profile."
          }
          badge={<MapPin className="w-4 h-4 text-emerald-600" />}
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {/* Target Crop Selector */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="crop"
                className="block text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300"
              >
                Target Crop <span className="text-rose-500">*</span>
              </label>
              {policy === "exploratory" && (
                <button
                  type="button"
                  onClick={() => setIsCustomCrop(!isCustomCrop)}
                  className="text-[11px] text-emerald-700 dark:text-emerald-400 hover:underline"
                >
                  {isCustomCrop ? "Select existing" : "+ Novel crop"}
                </button>
              )}
            </div>

            {isCustomCrop ? (
              <input
                id="crop"
                type="text"
                placeholder="e.g. Sorghum, Mustard"
                value={customCropValue}
                onChange={(e) => setCustomCropValue(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50/40 dark:bg-amber-950/20 text-zinc-900 dark:text-zinc-100 text-sm font-medium focus:ring-2 focus:ring-amber-500 outline-none"
              />
            ) : (
              <select
                id="crop"
                value={formData.crop}
                onChange={(e) => handleScopeChange("crop", e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
              >
                {activeCropsList.map((cropName) => (
                  <option key={cropName} value={cropName}>
                    {cropName}
                  </option>
                ))}
              </select>
            )}
            <span className="text-[11px] text-zinc-500 mt-1 block">
              {isCustomCrop
                ? "Novel crop evaluated via exploratory feature routing"
                : `${activeCropsList.length} dynamically discovered crops`}
            </span>
            {errors.crop && (
              <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{errors.crop}</p>
            )}
          </div>

          {/* District Selection */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label
                htmlFor="district"
                className="block text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300"
              >
                District <span className="text-rose-500">*</span>
              </label>
              {policy === "exploratory" && (
                <button
                  type="button"
                  onClick={() => setIsCustomDistrict(!isCustomDistrict)}
                  className="text-[11px] text-emerald-700 dark:text-emerald-400 hover:underline"
                >
                  {isCustomDistrict ? "Select existing" : "+ Novel district"}
                </button>
              )}
            </div>

            {isCustomDistrict ? (
              <input
                id="district"
                type="text"
                placeholder="e.g. Nagpur, Thane"
                value={customDistrictValue}
                onChange={(e) => setCustomDistrictValue(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-amber-300 dark:border-amber-700 bg-amber-50/40 dark:bg-amber-950/20 text-zinc-900 dark:text-zinc-100 text-sm font-medium focus:ring-2 focus:ring-amber-500 outline-none"
              />
            ) : (
              <select
                id="district"
                value={formData.district}
                onChange={(e) => handleScopeChange("district", e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
              >
                {activeDistrictsList.map((dist) => (
                  <option key={dist} value={dist}>
                    {dist}
                  </option>
                ))}
              </select>
            )}
            <span className="text-[11px] text-zinc-500 mt-1 block">
              {isCustomDistrict
                ? "Unverified district tested under exploratory policy"
                : `${activeDistrictsList.length} districts in active catalog`}
            </span>
            {errors.district && (
              <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{errors.district}</p>
            )}
          </div>

          {/* Growing Season */}
          <div>
            <label
              htmlFor="season"
              className="block text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300 mb-1.5"
            >
              Growing Season
            </label>
            <select
              id="season"
              value={formData.season}
              onChange={(e) => handleScopeChange("season", e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 text-sm font-medium focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
            >
              {availableSeasons.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-zinc-500 mt-1 block">
              Discovered for {formData.crop || "selected crop"}
            </span>
            {errors.season && (
              <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{errors.season}</p>
            )}
          </div>

          {/* Harvest Year */}
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
            <span className="text-[11px] text-zinc-500 mt-1 block">Harvest year [1990–2035]</span>
            {errors.year && (
              <p className="text-xs text-rose-600 dark:text-rose-400 mt-1">{errors.year}</p>
            )}
          </div>
        </div>

        {/* Model Strategy & Governance Status Strip */}
        <div className="mt-5 pt-5 border-t border-zinc-200 dark:border-zinc-800 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700/60">
            <div className="flex items-center gap-2 mb-1.5">
              <Cpu className="w-4 h-4 text-emerald-600" />
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-700 dark:text-zinc-300">
                Model Strategy
              </label>
            </div>
            <select
              value={formData.model_strategy || "legacy_soybean"}
              onChange={(e) => handleScopeChange("model_strategy", e.target.value)}
              disabled={formData.crop?.toLowerCase() !== "soybean"}
              className="w-full px-3 py-2 rounded-lg border border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-xs font-medium focus:ring-2 focus:ring-emerald-500 outline-none disabled:bg-zinc-100 dark:disabled:bg-zinc-800 disabled:text-zinc-500"
            >
              {formData.crop?.toLowerCase() === "soybean" ? (
                <>
                  <option value="legacy_soybean">Legacy Production Soybean Pipeline (Trained 1990–2010)</option>
                  <option value="shared_multicrop">Phase 4/6 Universal Multi-Crop Random Forest (Trained 1990–2010)</option>
                </>
              ) : (
                <option value="shared_multicrop">Phase 4/6 Universal Multi-Crop Random Forest</option>
              )}
            </select>
            <p className="text-[11px] text-zinc-500 mt-1.5">
              {formData.crop?.toLowerCase() === "soybean"
                ? "Soybean can be evaluated using either the baseline production model or the shared multi-crop pipeline."
                : `Non-soybean crops (${formData.crop}) route exclusively to the verified shared multi-crop model.`}
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200/80 dark:border-emerald-900/50 flex items-start gap-2.5">
            <Database className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div className="text-xs text-emerald-950 dark:text-emerald-200 leading-relaxed">
              <strong>Dynamic Schema Engine:</strong> Categories and feature bindings are inferred directly from dataset profiles. Adding rows for new crops or regions will automatically expand this catalog without code modifications.
            </div>
          </div>
        </div>
      </Card>

      {/* 2. Seasonal Weather Indicators Card */}
      <Card>
        <CardHeader
          title={`2. Seasonal Agroclimatology (${formData.season || "Kharif"})`}
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
