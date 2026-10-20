# System Architecture & Technical Specifications

## 1. High-Level Architecture Overview

The **Crop Yield Prediction System** is structured as a decoupled, independently deployable full-stack application designed for agricultural analytics and decision support:

```
┌─────────────────────────────────────────────────────────────┐
│                       Client Browser                        │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / JSON
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Frontend (Next.js / Vercel)                 │
│  - React 19 + TypeScript + Tailwind CSS                     │
│  - Responsive Agricultural Dashboard & Prediction Form      │
│  - Model Performance Metrics & Feature Importance Charts   │
│  - Client-side input validation and error boundaries        │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API (/api/v1/*)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Backend (FastAPI / Render)                  │
│  - FastAPI with Pydantic v2 validation                      │
│  - Uvicorn ASGI server with structured error handling       │
│  - Model inference lifecycle & memory management           │
│  - Explainability & uncertainty calculation engine          │
└──────────────────────────────┬──────────────────────────────┘
                               │ In-Memory Pipeline
                               ▼
┌─────────────────────────────────────────────────────────────┐
│            Trained ML Artifacts (scikit-learn)              │
│  - Preprocessor: ColumnTransformer (Scalers, Encoders)      │
│  - Estimator: Tuned Regressor (Random Forest / GBR)         │
│  - Serialized via joblib (~15-40 MB footprint)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Design & Decoupled Deployability

### Frontend (`frontend/`)
- **Framework**: Next.js (App Router), React 19, TypeScript, Tailwind CSS.
- **Role**: User-facing interactive dashboard for agronomists, policy analysts, and farmers.
- **Deployment**: Vercel (stateless edge/serverless static generation + client components).
- **Configuration**: Uses `NEXT_PUBLIC_API_URL` to route requests dynamically to the backend without hardcoded localhost URLs.

### Backend (`backend/`)
- **Framework**: Python 3.11+, FastAPI, Pydantic v2, Uvicorn.
- **Role**: Validates parameters, executes model inference, outputs prediction intervals, and provides governance metadata.
- **Deployment**: Render Web Service (containerized or native Python runtime).
- **Cold-Start Resilience**: 
  - Lightweight serialization using `joblib` with gzip compression level 3.
  - Startup lifespan event caches the model in worker memory so per-request latency is under 15ms once warm.
  - Frontend includes automatic retry with heartbeat visual feedback during backend spin-up.

---

## 3. API Contract Specification (`/api/v1`)

### Endpoints

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `GET` | `/` | Root service metadata and documentation links | 200 |
| `GET` | `/api/v1/health` | Service health, version, timestamp, and model status | 200 |
| `POST` | `/api/v1/predict` | Predict crop yield (t/ha) with uncertainty and limitations | 200, 422, 503 |
| `GET` | `/api/v1/metadata/districts` | List supported districts in Maharashtra with baseline stats | 200 |
| `GET` | `/api/v1/models/metrics` | Held-out validation and test metrics (MAE, RMSE, R²) | 200 |

### Prediction Payload Schema
```json
{
  "crop": "Soybean",
  "state": "Maharashtra",
  "district": "Latur",
  "season": "Kharif",
  "year": 2024,
  "soil": {
    "soil_ph": 7.2,
    "organic_carbon_pct": 0.65,
    "clay_pct": 42.0,
    "sand_pct": 25.0,
    "bulk_density_g_cm3": 1.35,
    "cation_exchange_capacity_cmol_kg": 38.5
  },
  "weather": {
    "cumulative_rainfall_mm": 850.5,
    "mean_temp_max_c": 31.8,
    "mean_temp_min_c": 22.4,
    "mean_solar_radiation_mj_m2": 18.6,
    "mean_relative_humidity_pct": 76.2
  }
}
```

---

## 4. Security & Error Handling Strategy

1. **No Hardcoded Secrets or Credentials**: All environment variables use `.env` loading with fallback defaults.
2. **Strict Schema Constraints**: Pydantic validates physical boundaries (e.g. pH between 3.5 and 10.0, soil clay + sand <= 100%, min temp <= max temp).
3. **Graceful Service Degradation**: When a model artifact is uninitialized, the backend responds with structured HTTP 503 rather than producing fabricated predictions.
4. **CORS Governance**: Configured via `BACKEND_CORS_ORIGINS` to allow only authorized frontend origins in production.
