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

export type PredictionPolicy = "conservative" | "exploratory";

export interface PredictionRequest {
  crop?: string;
  state?: string;
  district: string;
  season?: string;
  year: number;
  model_strategy?: "legacy_soybean" | "shared_multicrop" | null;
  prediction_policy?: PredictionPolicy;
  custom_features?: Record<string, string | number>;
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
  prediction_policy?: string | null;
  coverage_status?: string | null;
  is_out_of_distribution?: boolean;
  out_of_distribution_features?: string[];
  qualitative_label?: string | null;
  explanation?: string | null;
  uncertainty_note?: string | null;
  prediction_timing: string;
  timing_description: string;
  prediction_interval: Record<string, number> | null;
  feature_contributions: Record<string, number> | null;
  global_feature_importance: GlobalFeatureImportanceItem[] | null;
  limitations: string[];
  evaluation_summary?: Record<string, unknown> | null;
  request_id?: string | null;
}

export interface NumericStats {
  min: number;
  max: number;
  mean: number;
  std: number;
  p25: number;
  p50: number;
  p75: number;
  outlier_count_iqr: number;
  zero_count: number;
}

export interface CategoricalStats {
  cardinality: number;
  top_categories: Record<string, number>;
  rare_categories: string[];
}

export interface ColumnProfile {
  name: string;
  dtype: string;
  null_count: number;
  null_pct: number;
  unique_count: number;
  unique_pct: number;
  is_constant: boolean;
  inferred_role: string;
  confidence_role: number;
  inferred_units?: string | null;
  description?: string | null;
  numeric_stats?: NumericStats | null;
  categorical_stats?: CategoricalStats | null;
  is_leakage_risk: boolean;
  leakage_reason?: string | null;
}

export interface CategoryCombination {
  feature_a: string;
  value_a: string;
  feature_b: string;
  value_b: string;
  observation_count: number;
  representation_status: "well_represented" | "sparse" | "insufficient";
  mean_target_value?: number | null;
}

export interface DataQualityReport {
  total_rows: number;
  total_columns: number;
  duplicate_rows: number;
  duplicate_rows_pct: number;
  constant_columns: string[];
  high_null_columns: string[];
  detected_leakage_columns: string[];
  quality_score_pct: number;
  warnings: string[];
}

export interface DynamicPresetSample {
  name: string;
  description: string;
  sample_values: Record<string, string | number>;
  observed_target?: number | null;
  source_row_index?: number;
}

export interface DatasetProfile {
  dataset_name: string;
  file_format: string;
  sha256_hash: string;
  row_count: number;
  col_count: number;
  memory_bytes: number;
  columns: Record<string, ColumnProfile>;
  target_candidates: Array<{ name: string; score: number; rationale: string }>;
  selected_target?: string | null;
  target_is_ambiguous: boolean;
  ambiguity_explanation?: string | null;
  discovered_categories: Record<string, string[]>;
  observed_combinations: CategoryCombination[];
  quality_report: DataQualityReport;
  dynamic_presets: DynamicPresetSample[];
  human_readable_summary: string;
}

export interface DynamicCategoriesResponse {
  status: string;
  categories: Record<string, string[]>;
  observed_combinations: CategoryCombination[];
  source_dataset?: string | null;
}

export interface DynamicPresetsResponse {
  status: string;
  presets: DynamicPresetSample[];
  count: number;
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
