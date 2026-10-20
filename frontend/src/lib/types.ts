/**
 * TypeScript Data Models and Schema Contracts for Crop Yield Prediction.
 *
 * Exactly mirrors backend Pydantic v2 schemas:
 * - SoilProperties
 * - SeasonalWeather
 * - PredictionRequest
 * - PredictionResponse
 * - ModelMetadataResponse
 * - HealthResponse
 * - ReadinessResponse
 */

export interface SoilProperties {
  soil_ph: number;
  organic_carbon_pct: number;
  clay_pct: number;
  sand_pct: number;
  silt_pct?: number | null;
  bulk_density_g_cm3: number;
  cation_exchange_capacity_cmol_kg: number;
}

export interface SeasonalWeather {
  cumulative_rainfall_mm: number;
  mean_temp_max_c: number;
  mean_temp_min_c: number;
  mean_solar_radiation_mj_m2: number;
  mean_relative_humidity_pct: number;
  consecutive_dry_days_max: number;
  heat_stress_days: number;
}

export interface PredictionRequest {
  crop?: string;
  state?: string;
  district: string;
  season?: string;
  year: number;
  model_strategy?: "legacy_soybean" | "shared_multicrop" | null;
  soil: SoilProperties;
  weather: SeasonalWeather;
}

export interface GlobalFeatureImportanceItem {
  feature: string;
  importance_mean_rmse: number;
  importance_std_rmse: number;
}

export interface PredictionResponse {
  crop: string;
  state: string;
  district: string;
  season: string;
  year: number;
  predicted_yield_t_ha: number;
  predicted_yield_kg_ha?: number | null;
  target_units: string;
  model_name: string;
  model_version: string;
  model_strategy?: string | null;
  prediction_timing: string;
  timing_description: string;
  prediction_interval: Record<string, number> | null;
  feature_contributions: Record<string, number> | null;
  global_feature_importance: GlobalFeatureImportanceItem[] | null;
  limitations: string[];
  evaluation_summary?: Record<string, unknown> | null;
  request_id?: string | null;
}

export interface SupportedFeatureMeta {
  name: string;
  dtype: string;
  units: string;
  source: string;
  availability_time: string;
  description: string;
}

export interface CropCatalogItem {
  id: string;
  display_name: string;
  category: string;
  supported_seasons: string[];
  verified_districts: string[];
}

export interface ModelMetadataResponse {
  model_name: string;
  model_version: string;
  target: string;
  target_units: string;
  crop: string;
  state: string;
  season: string;
  prediction_timing: string;
  dataset_sha256: string;
  training_period: [number, number];
  validation_period: [number, number];
  test_period: [number, number];
  supported_districts: string[];
  supported_crops?: Record<string, CropCatalogItem>;
  available_strategies?: string[];
  multicrop_evaluation?: {
    temporal_split?: {
      evaluation_period: [number, number];
      test_samples: number;
      models: Record<string, { rmse_t_ha: number; mae_t_ha: number; r2_score: number }>;
    };
    spatial_leave_one_district_out?: {
      evaluation_type: string;
      districts_evaluated: string[];
      mean_metrics: Record<string, { rmse_t_ha: number; mae_t_ha: number; r2_score: number }>;
    };
    per_crop_temporal?: Record<
      string,
      {
        test_samples: number;
        mean_yield_t_ha: number;
        shared_rf: { rmse_t_ha: number; mae_t_ha: number; r2_score: number };
        crop_district_mean_baseline: { rmse_t_ha: number; mae_t_ha: number; r2_score: number };
      }
    >;
  };
  supported_features: SupportedFeatureMeta[];
  validation_metrics: {
    mae_t_ha: number;
    rmse_t_ha: number;
    r2_score: number;
    sample_count?: number;
  };
  test_metrics: {
    mae_t_ha: number;
    rmse_t_ha: number;
    r2_score: number;
    sample_count?: number;
  };
  global_feature_importance: GlobalFeatureImportanceItem[];
  limitations: string[];
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
  environment: string;
  model_loaded: boolean;
  message: string;
}

export interface ReadinessResponse {
  status: "ready" | "not_ready";
  model_name?: string;
  model_version?: string;
  target_crop?: string;
  target_state?: string;
  detail?: string;
}

export interface HistoryItem {
  id: string;
  timestamp: string;
  request: PredictionRequest;
  response: PredictionResponse;
}

export interface ApiStatus {
  isChecking: boolean;
  backendReachable: boolean;
  modelReady: boolean;
  modelName?: string;
  lastChecked: Date | null;
  errorMessage?: string;
}
