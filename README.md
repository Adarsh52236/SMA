# Crop Yield Prediction from Weather and Soil

A production-minded machine learning platform for predicting agricultural crop yield in tonnes per hectare ($\text{t/ha}$) from historical weather patterns, soil properties, crop type, and growing-season information.

Initial geographic focus: **Maharashtra, India**.  
Initial crop focus: **Soybean (*Glycine max*) during the Kharif season**, with extensible architecture for Rice and additional crops.

---

## 1. Project Overview & Architecture

The system is decoupled into two independently deployable applications:
- **Frontend (`frontend/`)**: Modern Next.js application (React 19, TypeScript, Tailwind CSS) providing an interactive agricultural dashboard, yield estimation form, model transparency diagnostics, and decision-support caveats. Designed for deployment to **Vercel**.
- **Backend (`backend/`)**: High-performance Python FastAPI service with Pydantic v2 validation, lifespan model caching, health/readiness probes, and structured endpoints. Designed for deployment to **Render**.
- **ML & Data Engine (`data/`, `backend/app/ml/`, `reports/modeling/`)**: Reproducible data ingestion pipelines (DES crop yield statistics, NASA POWER daily agroclimatology, ISRIC SoilGrids 2.0), strict chronological validation splits (1990–2010 Train, 2011–2014 Val, 2015–2017 Test), scikit-learn pipelines, and permutation feature importance explainability.

For in-depth architectural and data strategies, refer to:
- [System Architecture](docs/architecture.md)
- [Data Strategy & Crop Selection](docs/data_strategy.md)
- [Implementation Plan & Acceptance Criteria](docs/implementation_plan.md)
- [ML Evaluation Report](reports/modeling/evaluation_report.md)

---

## 2. API Endpoints & Specification

The FastAPI service exposes the following endpoints under `/api/v1`:

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/` | Root service metadata and discovery links | `200` |
| `GET` | `/api/v1/health` | Liveness probe returning operational status and `model_loaded` flag | `200` |
| `GET` | `/api/v1/ready` | Readiness probe distinguishing app liveness from model readiness | `200`, `503` |
| `POST` | `/api/v1/predict` | Predicts end-of-season crop yield in $\text{t/ha}$ | `200`, `422`, `503` |
| `GET` | `/api/v1/model/metadata` | Public model governance manifest, validation metrics, and feature importances | `200`, `503` |
| `GET` | `/docs` | Interactive Swagger UI API documentation | `200` |

---

## 3. Prediction Timing & Scientific Limitations

> [!IMPORTANT]
> **Prediction Timing Disclosure**:
> The model utilizes growing-season weather features aggregated across the full Kharif monsoon cycle (June 1 through October 31). Therefore, the API output is an **end-of-season yield estimate using observed weather**, not an early-season forecast or pre-sowing prediction.
> Silently substituting forecast values, long-term averages, or arbitrary weather defaults for missing observations is strictly prohibited.

### Key Operational Caveats:
1. **Domain Scope**: Validated exclusively for rainfed **Soybean** during the **Kharif** season across 7 Maharashtra districts: `Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Buldhana`.
2. **Soil Baseline**: Soil variables reflect 0–30cm weighted averages from ISRIC SoilGrids 2.0. They represent static regional edaphic potential rather than micro-parcel soil tests.
3. **Extreme Weather Shocks**: Regional climate anomalies that exceed historical extremes (e.g. statewide 2015 drought) may exhibit higher residual error.

---

## 4. Illustrative Request & Response Examples

*(Note: The following values are purely illustrative and for documentation testing purposes).*

### POST `/api/v1/predict` Request Example

```json
{
  "crop": "Soybean",
  "state": "Maharashtra",
  "district": "Akola",
  "season": "Kharif",
  "year": 2024,
  "soil": {
    "soil_ph": 7.4,
    "organic_carbon_pct": 0.65,
    "clay_pct": 45.0,
    "sand_pct": 20.0,
    "silt_pct": 35.0,
    "bulk_density_g_cm3": 1.25,
    "cation_exchange_capacity_cmol_kg": 38.0
  },
  "weather": {
    "cumulative_rainfall_mm": 850.5,
    "mean_temp_max_c": 31.8,
    "mean_temp_min_c": 22.4,
    "mean_solar_radiation_mj_m2": 18.6,
    "mean_relative_humidity_pct": 76.2,
    "consecutive_dry_days_max": 8,
    "heat_stress_days": 4
  }
}
```

### Response Example (`200 OK`)

```json
{
  "crop": "Soybean",
  "state": "Maharashtra",
  "district": "Akola",
  "season": "Kharif",
  "year": 2024,
  "predicted_yield_t_ha": 1.0384,
  "target_units": "tonnes per hectare (t/ha)",
  "model_name": "Random_Forest",
  "model_version": "0.1.0",
  "prediction_timing": "end_of_season_estimate",
  "timing_description": "End-of-season yield estimate using observed Kharif seasonal weather (June 1 - October 31). This model reflects retrospective or harvest-time meteorological conditions; it is not an early-season or pre-sowing forecast.",
  "prediction_interval": null,
  "feature_contributions": null,
  "global_feature_importance": [
    {
      "feature": "mean_relative_humidity_pct",
      "importance_mean_rmse": 0.1445,
      "importance_std_rmse": 0.0315
    },
    {
      "feature": "consecutive_dry_days_max",
      "importance_mean_rmse": 0.019,
      "importance_std_rmse": 0.0146
    },
    {
      "feature": "cumulative_rainfall_mm",
      "importance_mean_rmse": 0.0161,
      "importance_std_rmse": 0.0056
    }
  ],
  "limitations": [
    "End-of-season yield estimate using observed weather (June-October); not an early-season or pre-sowing forecast.",
    "Soil properties represent static 0-30cm ISRIC SoilGrids 2.0 weighted averages.",
    "Validated within Maharashtra agroclimatic conditions; spatial extrapolation outside supported districts is prohibited."
  ],
  "request_id": "pred-4c3e21a8b9f0"
}
```

---

## 5. Local Setup & Quickstart

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
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Verify required model artifact files exist:
   ```
   backend/models/crop_yield_model.joblib
   backend/models/model_metadata.json
   ```
   *(If missing, generate them by running `python -m app.ml.train` from `backend/`).*
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

## 6. Running Verification & Automated Tests

### Backend Test Suite (44 Tests)
Execute all unit, integration, schema validation, ML training, and API serving tests:
```bash
pytest -v
```

### Frontend Code Quality
Run ESLint in the frontend directory:
```bash
cd frontend
npm run lint
```

---

## 7. Cloud Deployment Guide (Render & Vercel)

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
   - `BACKEND_CORS_ORIGINS`: `https://your-frontend-app.vercel.app`
   - `MODEL_DIR`: `models`
5. Ensure model artifact files (`crop_yield_model.joblib` and `model_metadata.json`) are present in `backend/models/` or generated during build via a release step (`python -m app.ml.train`).

### Frontend Deployment (Vercel)
1. Import the repository into [Vercel](https://vercel.com/).
2. Select Root Directory: `frontend`.
3. Set Environment Variable:
   - `NEXT_PUBLIC_API_URL`: `https://your-backend-api.onrender.com/api/v1`
4. Deploy.

---

## 8. Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| `503 Service Unavailable` on `/predict` | Model artifact not found or unloaded | Verify `backend/models/crop_yield_model.joblib` exists. Check `/api/v1/ready` for specific diagnostic message. |
| `422 Unprocessable Content` on district | District not in supported list | Only the 7 districts with verified SoilGrids profiles (`Ahmednagar, Akola, Amravati, Aurangabad, Beed, Bhandara, Buldhana`) are supported in Phase 4. |
| `422 Unprocessable Content` on weather | Missing dry spell or heat stress | Ensure both `consecutive_dry_days_max` and `heat_stress_days` are provided. Defaults are not fabricated. |
| CORS Origin blocked in browser | Frontend URL not whitelisted | Add frontend origin to `BACKEND_CORS_ORIGINS` in `backend/.env`. |

---

## 9. Project Roadmap & Current Status

- **Phase 1: Project Skeleton & Architecture Setup** (Status: **Completed**)
- **Phase 2: Data Acquisition & Preprocessing Pipeline** (Status: **Completed**)
- **Phase 3: Machine Learning Modeling & Explainability** (Status: **Completed**)
- **Phase 4: Production Backend Serving & API Features** (Status: **Completed**)
- **Phase 5: Next.js Interactive Dashboard UI** (Status: **Next Step**)
- **Phase 6: QA, E2E Testing & Cloud Deployment** (Status: **Pending**)
