import type {
  PredictionRequest,
  PredictionResponse,
  ModelMetadataResponse,
  HealthResponse,
  ReadinessResponse,
} from "./types";

const RAW_API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// Clean trailing slashes and optional trailing /api/v1 to prevent duplicate path segments
export const API_BASE_URL = RAW_API_URL.replace(/\/+$/, "").replace(/\/api\/v1$/, "");

export class ApiError extends Error {
  public status: number;
  public detail?: string;
  public isOffline: boolean;
  public isModelUnavailable: boolean;

  constructor(message: string, status: number = 0, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.isOffline = status === 0;
    this.isModelUnavailable = status === 503;
  }
}

async function requestWithTimeout<T>(
  endpoint: string,
  options: RequestInit = {},
  timeoutMs: number = 15000
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let detailMessage: string | undefined;
      try {
        const errorBody = await response.json();
        if (typeof errorBody.detail === "string") {
          detailMessage = errorBody.detail;
        } else if (Array.isArray(errorBody.detail)) {
          // Format Pydantic field validation errors
          detailMessage = errorBody.detail
            .map((err: { loc?: string[]; msg?: string }) => {
              const field = err.loc ? err.loc.slice(1).join(".") : "field";
              return `${field}: ${err.msg || "invalid value"}`;
            })
            .join("; ");
        } else if (errorBody.message) {
          detailMessage = errorBody.message;
        }
      } catch {
        detailMessage = response.statusText || "Server error";
      }

      if (response.status === 503) {
        throw new ApiError(
          detailMessage || "The prediction model artifact is currently unavailable on the backend.",
          503,
          detailMessage
        );
      }

      if (response.status === 422) {
        throw new ApiError(
          detailMessage || "The input parameters failed validation against the model schema.",
          422,
          detailMessage
        );
      }

      throw new ApiError(
        detailMessage || `API request failed with HTTP ${response.status}`,
        response.status,
        detailMessage
      );
    }

    return (await response.json()) as T;
  } catch (error: unknown) {
    clearTimeout(timeoutId);

    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(
        "Request timed out after 15 seconds. If using Render, the backend service may be waking up from a cold start.",
        408
      );
    }

    const err = error as Error;
    // Network / CORS / Offline error
    throw new ApiError(
      `Cannot connect to backend API at ${API_BASE_URL}. Ensure the FastAPI server is running and CORS is configured. (${err.message})`,
      0,
      err.message
    );
  }
}

export const api = {
  /**
   * Liveness probe: checks general server responsiveness.
   */
  async checkHealth(): Promise<HealthResponse> {
    return requestWithTimeout<HealthResponse>("/api/v1/health", { method: "GET" }, 8000);
  },

  /**
   * Readiness probe: checks whether the model artifact is loaded and ready for inference.
   */
  async checkReadiness(): Promise<ReadinessResponse> {
    return requestWithTimeout<ReadinessResponse>("/api/v1/ready", { method: "GET" }, 8000);
  },

  /**
   * Governance and transparency metadata: model details, validation metrics, feature importances.
   */
  async getModelMetadata(): Promise<ModelMetadataResponse> {
    return requestWithTimeout<ModelMetadataResponse>("/api/v1/model/metadata", { method: "GET" }, 10000);
  },

  /**
   * Run crop yield prediction using the trained model pipeline with optional exploratory policy.
   */
  async predictCropYield(payload: PredictionRequest): Promise<PredictionResponse> {
    return requestWithTimeout<PredictionResponse>(
      "/api/v1/predict",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      15000
    );
  },

  /**
   * Dataset Discovery: retrieve machine-readable dataset profile, column roles, and quality report.
   */
  async getDatasetProfile(): Promise<import("./types").DatasetProfile> {
    return requestWithTimeout<import("./types").DatasetProfile>("/api/v1/discovery/profile", { method: "GET" }, 10000);
  },

  /**
   * Discovered Categories: dynamically retrieve available crops, districts, and observed cross-tabulations.
   */
  async getDiscoveredCategories(): Promise<import("./types").DynamicCategoriesResponse> {
    return requestWithTimeout<import("./types").DynamicCategoriesResponse>(
      "/api/v1/discovery/categories",
      { method: "GET" },
      8000
    );
  },

  /**
   * Dynamic Presets: retrieve authentic observations directly sampled from discovered datasets.
   */
  async getDynamicPresets(): Promise<import("./types").DynamicPresetsResponse> {
    return requestWithTimeout<import("./types").DynamicPresetsResponse>("/api/v1/discovery/samples", { method: "GET" }, 8000);
  },

  /**
   * Inspect Uploaded Dataset: profile a novel CSV/Parquet file dynamically on the fly.
   */
  async inspectDataset(file: File): Promise<import("./types").DatasetProfile> {
    const formData = new FormData();
    formData.append("file", file);
    const url = `${API_BASE_URL}/api/v1/discovery/inspect`;
    const response = await fetch(url, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }));
      throw new ApiError(err.detail || "Failed to inspect dataset", response.status);
    }
    return response.json();
  },
};
