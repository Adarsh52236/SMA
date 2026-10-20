# Crop Yield Prediction from Weather and Soil

A production-minded machine learning prototype for predicting agricultural crop yield in tonnes per hectare ($\text{t/ha}$) from historical weather patterns, soil properties, crop type, and growing-season information.

Initial geographic focus: **Maharashtra, India**.  
Initial crop focus: **Soybean (*Glycine max*) during the Kharif season**, with extensible architecture for Rice and additional crops.

---

## 1. Project Overview & Architecture

The system is decoupled into two independently deployable applications:
- **Frontend (`frontend/`)**: Modern Next.js application (React 19, TypeScript, Tailwind CSS) providing an interactive agricultural dashboard, yield estimation form, model transparency diagnostics, and decision-support caveats. Designed for deployment to **Vercel**.
- **Backend (`backend/`)**: High-performance Python FastAPI service with Pydantic v2 validation, model loading lifecycle, and structured endpoints. Designed for deployment to **Render**.
- **Data & Modeling (`data/`, `notebooks/`, `backend/app/ml/`)**: Reproducible data ingestion pipelines (DES crop yield statistics, NASA POWER daily agroclimatology, ISRIC SoilGrids 2.0), strict chronological validation splits, scikit-learn model pipelines, and explainability.

For in-depth architectural and data strategies, refer to:
- [System Architecture](docs/architecture.md)
- [Data Strategy & Crop Selection](docs/data_strategy.md)
- [Implementation Plan & Acceptance Criteria](docs/implementation_plan.md)

---

## 2. Repository Structure

```
SMA/
├── .gitignore                    # Root gitignore for Python, Node, data, and models
├── README.md                     # Project documentation & local setup instructions
├── pytest.ini                    # Root pytest configuration
├── docs/                         # Architecture, data strategy, and planning documentation
│   ├── architecture.md           # System design, API contracts, deployment specs
│   ├── data_strategy.md          # Data sources (DES, NASA POWER, SoilGrids), alignment
│   └── implementation_plan.md    # Multi-phase roadmap and acceptance criteria
├── data/                         # Data directory (ignored from Git except .gitkeep)
│   ├── raw/                      # Immutable raw downloads
│   ├── interim/                  # Cleaned and intermediate aggregated data
│   └── processed/                # Final aligned modeling datasets
├── notebooks/                    # EDA, feature engineering, and model diagnostic notebooks
├── reports/                      # Validation reports, model evaluation summaries
├── backend/                      # Python FastAPI application
│   ├── .env.example              # Environment variables template
│   ├── requirements.txt          # Production dependencies (FastAPI, scikit-learn, etc.)
│   ├── requirements-dev.txt      # Testing and development tools
│   ├── models/                   # Serialized model artifacts (.joblib)
│   └── app/
│       ├── main.py               # FastAPI entrypoint with CORS and lifespan events
│       ├── core/
│       │   └── config.py         # Pydantic BaseSettings configuration
│       ├── schemas/              # Pydantic v2 schemas
│       │   ├── health.py         # Health check response schema
│       │   └── prediction.py     # Weather, soil, request, and response schemas
│       ├── api/
│       │   └── v1/
│       │       ├── router.py     # Aggregated v1 endpoints
│       │       └── endpoints/
│       │           ├── health.py # GET /api/v1/health
│       │           └── prediction.py # POST /api/v1/predict
│       └── ml/                   # ML inference abstractions and pipeline utilities
├── frontend/                     # Next.js TypeScript Tailwind frontend
│   ├── .env.example              # Frontend environment variables template
│   ├── package.json              # Next.js scripts and dependencies
│   ├── tsconfig.json             # TypeScript configuration
│   └── src/
│       └── app/                  # App Router components, layouts, and styles
└── tests/                        # Backend and integration test suite
    ├── test_health.py            # Health and root endpoint unit tests
    └── test_schemas.py           # Pydantic bounds checking and error handling tests
```

---

## 3. Local Setup & Quickstart

### Prerequisites
- Python `3.11+`
- Node.js `v20+` or `v22+` and `npm`
- Git

### Backend Setup
1. Open a terminal in the project root:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   # On Windows
   python -m venv .venv
   .venv\Scripts\activate

   # On Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
5. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Interactive Swagger API docs will be accessible at: `http://localhost:8000/docs`

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

## 4. Running Verification & Tests

### Backend Tests
Execute unit and schema validation tests from the project root:
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

## 5. Deployment Guide

### Backend (Render)
- Deploy as a **Web Service** pointing to the `backend/` directory.
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set Environment Variables:
  - `ENVIRONMENT=production`
  - `BACKEND_CORS_ORIGINS=https://your-frontend-app.vercel.app`

### Frontend (Vercel)
- Deploy the `frontend/` directory to **Vercel**.
- Framework preset: **Next.js**.
- Set Environment Variables:
  - `NEXT_PUBLIC_API_URL=https://your-backend-api.onrender.com/api/v1`

---

## 6. Project Roadmap & Current Status

- **Phase 1: Project Skeleton & Architecture Setup** (Status: **Completed**)
- **Phase 2: Data Acquisition & Preprocessing Pipeline** (Status: **Next Step**)
- **Phase 3: Machine Learning Modeling & Explainability** (Status: **Pending**)
- **Phase 4: Production Backend Serving & API Features** (Status: **Pending**)
- **Phase 5: Next.js Interactive Dashboard UI** (Status: **Pending**)
- **Phase 6: QA, E2E Testing & Cloud Deployment** (Status: **Pending**)
