# Universal Crop Yield Prediction from Weather, Soil, and Agroclimatic Intelligence

A production-grade machine learning platform for predicting agricultural crop yield in tonnes per hectare ($\text{t/ha}$) from historical weather patterns, soil physicochemical properties, crop identity, and growing-season information.

Initially developed for Kharif soybean in Maharashtra, the system has been upgraded to a **dynamic, multi-crop, multi-region agroclimatic intelligence platform** supporting multiple staple crops, temporal and spatial cross-validation, dynamic dataset discovery, and end-to-end transparency.

---

## 1. Project Overview & Architecture

The system is decoupled into two independently deployable applications plus a reproducible machine learning engine:

- **Frontend (`frontend/`)**: Modern Next.js application (React 19, TypeScript, Tailwind CSS v4) featuring:
  - Interactive yield estimation form with automatic dynamic sample loading and district soil pre-filling.
  - Comprehensive model transparency and explainability dashboard with interactive feature importance and residual diagnostics.
  - Scientific methodology explorer documenting data sources, preprocessing, validation protocols, and limitations.
  - Dynamic dataset discovery dashboard profiling live datasets, district crop portfolios, and soil distributions.
  - Designed for continuous deployment to **Vercel**.
- **Backend (`backend/`)**: High-performance Python FastAPI service featuring:
  - Strict Pydantic v2 validation for single-crop and multi-crop observation schemas.
  - Lifespan model caching and metadata introspection with zero per-request disk overhead.
  - Dynamic dataset discovery engine (`/api/v1/discovery/*`) that introspects raw and processed datasets without hardcoded category registries.
  - Backward-compatible serving supporting both legacy single-crop soybean queries and multi-crop requests with out-of-domain category safeguards.
  - Designed for deployment to **Render** or containerized cloud runtimes.
- **ML & Data Engine (`data/`, `backend/app/ml/`, `reports/model_analysis/`)**:
  - Reproducible ETL pipelines integrating ICRISAT District Level Data (DLD), NASA POWER daily agroclimatology, and ISRIC SoilGrids 2.0 (0–30 cm weighted profile).
  - Strict chronological (1990–2012 Train, 2013–2017 Test) and spatial (Leave-One-District-Out across 7 agroclimatic zones) validation protocols.
  - Explainable AI artifacts including impurity-based feature importance, test-set permutation importance, predicted vs. actual regressions, and residual distributions.

---

## 2. API Endpoints & Specification

The FastAPI service exposes the following endpoints under `/api/v1`:

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/` | Root service metadata and discovery links | `200` |
| `GET` | `/api/v1/health` | Liveness probe returning operational status and `model_loaded` flag | `200` |
| `GET` | `/api/v1/ready` | Readiness probe verifying model readiness and metadata loading | `200`, `503` |
| `POST` | `/api/v1/predict` | Predicts end-of-season crop yield in $\text{t/ha}$ (single & multi-crop) | `200`, `422`, `503` |
| `GET` | `/api/v1/model/metadata` | Public model governance manifest, hyperparameters, and validation metrics | `200`, `503` |
| `GET` | `/api/v1/discovery/profile` | Dataset profiling summary (rows, columns, crops, districts, temporal coverage) | `200` |
| `GET` | `/api/v1/discovery/categories` | Discovered categorical values, crop lists, and district-crop matrix | `200` |
| `GET` | `/api/v1/discovery/samples` | Representative historical records for interactive form pre-filling | `200` |
| `GET` | `/api/v1/discovery/inspect` | Granular summary statistics and missingness rates for any dataset column | `200`, `400` |
| `GET` | `/docs` | Interactive Swagger UI API documentation | `200` |

---

## 3. Supported Crops & Dynamic Intelligence

### Core Crops & Region
The production multi-crop model is trained and validated across 7 major crops in Maharashtra:
- **Crops**: Soybean, Cotton, Groundnut, Maize, Pigeonpea (Tur), Sorghum (Jowar), Wheat.
- **Districts**: Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Buldhana.

### Self-Discovering & Dynamic Architecture
Rather than relying on brittle, hardcoded crop-season pairings or fixed dropdown lists:
- The system discovers categories directly from processed agroclimatic datasets at startup.
- Unseen categories or out-of-domain crops are handled via a robust fallback policy (`allow_unseen=True`), replacing unobserved one-hot indicators with zero vectors and attaching explicit limitation notices to the prediction response.

---

## 4. Model Evaluation & Benchmark Results

All evaluation metrics are calculated on genuine held-out evaluation splits and reconciled across all project phases. Never mix temporal holdout scores with spatial cross-validation scores.

### Evaluation Splits
- **Temporal Holdout**: Train: 1990–2012 ($N = 1,068$), Test: 2013–2017 ($N = 225$).
- **Spatial Holdout**: Leave-One-District-Out cross-validation across all 7 districts ($N = 1,293$).
- **Legacy Soybean Baseline**: Train: 1990–2010 ($N = 147$), Test: 2011–2017 ($N = 47$).

### Benchmark Comparison Table

| Model Architecture | Split Protocol | Test RMSE ($\text{t/ha}$) | Test MAE ($\text{t/ha}$) | Test $R^2$ | Status |
|---|---|---|---|---|---|
| **Shared Random Forest** | **Spatial (LODO)** | **0.4332** | **0.3013** | **0.5093** | **Selected Spatial Winner** |
| Crop-Specific Random Forest | Spatial (LODO) | 0.4410 | 0.3088 | 0.4916 | Evaluated |
| Historical Crop Mean Baseline | Spatial (LODO) | 0.4521 | 0.3204 | 0.4656 | Baseline |
| Global Mean Baseline | Spatial (LODO) | 0.6186 | 0.4705 | 0.0000 | Baseline |
| **Shared Random Forest** | **Temporal (2013–17)** | **0.5520** | **0.3788** | **0.4295** | **Lowest Temporal MAE** |
| Crop-Specific Random Forest | Temporal (2013–17) | 0.5973 | 0.4277 | 0.3315 | Evaluated |
| Historical Crop-District Mean | Temporal (2013–17) | 0.5337 | 0.3802 | 0.4670 | Baseline |
| Historical Crop Mean Baseline | Temporal (2013–17) | 0.5847 | 0.4190 | 0.3592 | Baseline |
| Global Mean Baseline | Temporal (2013–17) | 0.7303 | 0.5703 | 0.0000 | Baseline |

### Key Model Insights
1. **Spatial Generalization**: On unseen geographic districts, the **Shared Multi-Crop Random Forest** is the top-performing model ($R^2 = 0.5093$, RMSE $= 0.4332$ t/ha), decisively outperforming crop-specific models by pooling regional weather and soil relationships across crops.
2. **Temporal Generalization**: On future seasons (2013–2017 holdout), Shared Random Forest achieves the lowest Mean Absolute Error ($0.3788$ t/ha).
3. **Primary Drivers**: Feature importance analysis shows that crop identity (Maize and Cotton one-hot flags) and agroclimatic moisture drivers (`mean_relative_humidity_pct`, `mean_solar_radiation_mj_m2`, `mean_temp_max_c`, `cumulative_rainfall_mm`) account for over 70% of model predictive power.
4. **Analysis Artifacts**: Detailed CSVs and high-resolution plots are available in [`reports/model_analysis/`](reports/model_analysis/):
   - `top10_feature_importance.png` & `top10_feature_importance.csv`
   - `test_permutation_importance.png` & `test_permutation_importance.csv`
   - `predicted_vs_actual.png`
   - `residuals_plot.png`
   - `rmse_mae_comparison.png` & `model_comparison.csv`
   - `hyperparameters.json`

---

## 5. Prediction Timing & Scientific Limitations

> [!IMPORTANT]
> **Prediction Timing Disclosure**:
> The model utilizes growing-season weather features aggregated across the full Kharif monsoon cycle (June 1 through October 31) or Rabi season. Therefore, the API output is an **end-of-season yield estimate using observed weather**, not an early-season forecast or pre-sowing prediction.
> Silently substituting forecast values, long-term averages, or arbitrary weather defaults for missing observations is strictly prohibited.

### Operational Caveats
1. **Soil Baseline**: Soil variables reflect 0–30 cm depth-weighted averages from ISRIC SoilGrids 2.0. They represent static regional edaphic potential rather than micro-parcel soil laboratory tests.
2. **Extreme Climate Shocks**: Regional climate anomalies that exceed historical distributions (e.g. statewide severe drought years) may exhibit higher residual variance.
3. **Spatial Scope**: Primary validation covers Maharashtra. Predictions for regions outside the training domain operate under unobserved domain policy with attached uncertainty warnings.

---

## 6. Illustrative Request & Response Examples

### POST `/api/v1/predict` Request Example

```json
{
  "crop": "Cotton",
  "state": "Maharashtra",
  "district": "Akola",
  "season": "Kharif",
  "year": 2024,
  "soil": {
    "soil_ph": 7.8,
    "organic_carbon_pct": 0.55,
    "clay_pct": 52.0,
    "sand_pct": 18.0,
    "silt_pct": 30.0,
    "bulk_density_g_cm3": 1.28,
    "cation_exchange_capacity_cmol_kg": 44.0
  },
  "weather": {
    "cumulative_rainfall_mm": 780.0,
    "mean_temp_max_c": 32.5,
    "mean_temp_min_c": 22.8,
    "mean_solar_radiation_mj_m2": 19.2,
    "mean_relative_humidity_pct": 74.0,
    "consecutive_dry_days_max": 9,
    "heat_stress_days": 5
  }
}
```

### Response Example (`200 OK`)

```json
{
  "crop": "Cotton",
  "state": "Maharashtra",
  "district": "Akola",
  "season": "Kharif",
  "year": 2024,
  "predicted_yield_t_ha": 0.3541,
  "target_units": "tonnes per hectare (t/ha)",
  "model_name": "Shared_MultiCrop_Random_Forest",
  "model_version": "1.0.0",
  "prediction_timing": "end_of_season_estimate",
  "timing_description": "End-of-season yield estimate using observed seasonal weather. Reflects retrospective harvest-time meteorological conditions.",
  "prediction_interval": {
    "lower_bound_t_ha": 0.0820,
    "upper_bound_t_ha": 0.6262,
    "confidence_level": 0.90
  },
  "limitations": [
    "End-of-season yield estimate using observed weather; not an early-season or pre-sowing forecast.",
    "Soil properties represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages.",
    "Validated within Maharashtra agroclimatic conditions; spatial extrapolation outside supported districts carries higher uncertainty."
  ],
  "request_id": "pred-9f8e7d6c5b4a"
}
```

---

## 7. Local Setup & Quickstart

### Prerequisites
- Python `3.11+`
- Node.js `v20+` or `v22+` and `npm`
- Git

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Verify required model artifacts exist:
   ```
   backend/models/crop_yield_model.joblib
   backend/models/model_metadata.json
   backend/models/experiments/multicrop/shared_rf/model.joblib
   backend/models/experiments/multicrop/multicrop_experiment_metadata.json
   ```
5. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
6. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Interactive Swagger API docs will be live at: `http://localhost:8000/docs`.

### Frontend Setup
1. In a separate terminal, navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Copy environment configuration:
   ```bash
   cp .env.example .env.local
   ```
4. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` in your browser.

---

## 8. Verification & Test Suite Execution

### Backend Test Suite (104 Tests)
Run all unit, integration, schema validation, ML training, multi-crop serving, and dynamic intelligence tests:
```bash
pytest tests/ -v
```

### Frontend Test Suite (14 Tests)
Run frontend React component, discovery, form, and client integration tests:
```bash
cd frontend
npm test
```

### Frontend Linting & Production Build
```bash
cd frontend
npm run lint
npm run build
```

### Reproduce Model Analysis Artifacts
Generate all model analysis figures, feature importances, permutation metrics, and comparisons:
```bash
python backend/app/ml/multicrop/generate_analysis_artifacts.py
```
Outputs are saved directly to `reports/model_analysis/`.

---

## 9. Cloud Deployment Guide (Render & Vercel)

### Backend Deployment (Render)
1. In the [Render Dashboard](https://dashboard.render.com/), create a new **Web Service**.
2. Connect your GitHub repository (`Adarsh52236/SMA`).
3. Set the following build settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Configure Environment Variables:
   - `ENVIRONMENT`: `production`
   - `BACKEND_CORS_ORIGINS`: `https://your-frontend-app.vercel.app,http://localhost:3000`
   - `MODEL_DIR`: `models`
5. Ensure model artifact files (`backend/models/crop_yield_model.joblib` and `backend/models/experiments/multicrop/shared_rf/model.joblib`) are tracked in Git or fetched during the build step.

### Frontend Deployment (Vercel)
1. Import the repository into [Vercel](https://vercel.com/).
2. Select Root Directory: `frontend`.
3. Set Environment Variable:
   - `NEXT_PUBLIC_API_URL`: `https://your-backend-api.onrender.com/api/v1`
4. Deploy.

---

## 10. Project Status & Deliverables Summary

| Phase | Milestone | Status | Key Artifacts |
|---|---|---|---|
| **Phase 1** | System Audit & Schema Invariance | **Completed** | `docs/architecture.md`, `UnifiedCropObservation` |
| **Phase 2** | Multi-Crop Architecture & Schema | **Completed** | `backend/app/schemas/unified_crop.py`, Crop & Season Registries |
| **Phase 3** | Dataset Assembly & Alignment | **Completed** | `data/processed/crop_yield_multicrop.csv`, `reports/data/coverage_matrix.json` |
| **Phase 4** | Modeling & Generalization Benchmarking | **Completed** | `backend/models/experiments/multicrop/`, Temporal & LODO evaluation |
| **Phase 5** | Serving & Multi-Crop Frontend | **Completed** | `/insights`, `/methodology`, Dynamic prefill |
| **Phase 6** | Dynamic Dataset Discovery & Self-Intelligence | **Completed** | `/discovery/*`, `/dataset`, dynamic category introspection |
| **Final Pass** | Reproducible Model Analysis & Verification | **Completed** | `reports/model_analysis/`, 104 backend tests, 14 frontend tests |
