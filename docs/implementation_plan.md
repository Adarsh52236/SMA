# Implementation Plan & Phase Acceptance Criteria

## Phase 1: Project Skeleton & Engineering Foundation (CURRENT STAGE)
**Objective**: Establish the dual-stack repository architecture, development environments, automated testing, API contracts, and architectural documentation.

- [x] Inspect existing directory, runtimes, and local toolchain.
- [x] Initialize Git version control and configure root `.gitignore`.
- [x] Propose decoupled architecture (Next.js frontend + FastAPI backend).
- [x] Create project directories (`backend/`, `frontend/`, `data/`, `notebooks/`, `reports/`, `docs/`, `tests/`).
- [x] Bootstrap Next.js 16 / React 19 / TypeScript / Tailwind CSS frontend.
- [x] Implement initial FastAPI application with versioned router, CORS middleware, and health endpoint.
- [x] Define typed Pydantic v2 schemas for crop, district, soil properties, and seasonal weather.
- [x] Establish backend unit tests verifying schema validation, range checks, and safe missing-model handling.
- [x] Document architecture, data acquisition strategy, and phase acceptance criteria.

**Phase 1 Acceptance Criteria**:
- `pytest` executes and passes all test cases cleanly.
- `npm run lint` in `frontend/` executes without errors.
- No placeholder/fabricated predictions or synthetic models exist in the repository.

---

## Phase 2: Data Acquisition & Preprocessing Pipeline
**Objective**: Ingest official historical crop statistics for Maharashtra, extract corresponding NASA POWER daily agroclimatology, extract ISRIC SoilGrids profiles, and align datasets.

**Tasks**:
1. Implement reproducible data acquisition scripts in `backend/app/data/`:
   - `fetch_crop_data.py`: Process official DES / APY crop statistics for Maharashtra (1998–present).
   - `fetch_weather_data.py`: Extract daily NASA POWER weather for district centroids and aggregate over Kharif season (June 1 - October 31).
   - `fetch_soil_data.py`: Map ISRIC SoilGrids 2.0 topsoil parameters (pH, organic carbon, clay, sand, bulk density, CEC) for Maharashtra agricultural zones.
2. Clean and align datasets on `(state, district, crop, season, year)`.
3. Save raw data in `data/raw/`, intermediate steps in `data/interim/`, and the final modeling dataset in `data/processed/crop_yield_maharashtra.csv`.
4. Create an EDA notebook (`notebooks/crop_yield_prediction.ipynb`) auditing missing values, geographic coverage, yield distributions, and multicollinearity across crops.

**Phase 2 Acceptance Criteria**:
- Verified non-synthetic dataset containing genuine historical records from official sources.
- Summary data profile documented with row counts, district coverage, yield summary statistics ($t/ha$), and zero data leakage.

---

## Phase 3: Machine Learning Modeling, Evaluation & Explainability
**Objective**: Train, benchmark, validate, and serialize yield prediction models with strict chronological splits and explainability.

**Tasks**:
1. **Splitting Strategy**:
   - Chronological train/validation/test split (e.g. Train: 1998–2017, Validation: 2018–2020, Test: 2021–2023) to prevent temporal data leakage.
   - Spatial holdout check (withhold 2-3 distinct districts) to evaluate out-of-district generalization.
2. **Model Implementations**:
   - Baseline: Historical District Mean / State Mean Regressor.
   - Linear Model: Ridge / ElasticNet Regression with standard scaling.
   - Tree Ensemble: Random Forest Regressor.
   - Boosting: Gradient Boosting Regressor / LightGBM.
3. **Evaluation Protocol**:
   - Calculate Mean Absolute Error (MAE in $t/ha$), Root Mean Squared Error (RMSE in $t/ha$), and $R^2$ score across all sets.
   - Model selection based strictly on validation RMSE and spatial generalization.
4. **Explainability & Diagnostics**:
   - Extract permutation feature importance and Tree SHAP values.
   - Generate actual-versus-predicted plots and residual analysis.
5. **Artifact Export**:
   - Save the best pipeline (preprocessors + estimator) as a compressed `.joblib` file in `backend/models/`.
   - Export evaluation metrics and feature importances as a JSON manifest for backend and frontend consumption.

**Phase 3 Acceptance Criteria**:
- Candidate models benchmarked against the mean baseline on held-out test data.
- Feature importance analysis generated distinguishing correlation from causation.
- Model artifact and metrics manifest exported without manual hardcoding.

---

## Phase 4: Production FastAPI Backend & Model Serving
**Objective**: Wire the trained model pipeline into the FastAPI backend with health monitoring, prediction intervals, and Render deployment configuration.

**Tasks**:
1. Implement model loader and cached inference engine in `backend/app/ml/inference.py`.
2. Connect `POST /api/v1/predict` to the loaded pipeline.
3. Add `GET /api/v1/models/metrics` serving held-out evaluation metrics.
4. Add `GET /api/v1/metadata/districts` providing district defaults and soil presets.
5. Provide Render configuration (`render.yaml` / Dockerfile) and test production Uvicorn startup.
6. Write integration tests for prediction responses, input sanitization, and edge-case handling.

**Phase 4 Acceptance Criteria**:
- Prediction endpoint returns legitimate model predictions with bounds and uncertainty.
- Test coverage over 90% across backend API modules.
- Backend loads model artifact in $<1$ second and responds in $<25\text{ ms}$.

---

## Phase 5: Next.js Interactive Dashboard UI
**Objective**: Build a responsive agricultural dashboard with interactive prediction, feature importance charts, model performance display, and advisory limitations.

**Tasks**:
1. Configure UI components using Tailwind CSS and Lucide icons.
2. Create state-of-the-art layout:
   - Navigation bar with environment and backend health indicators.
   - District & growing season selector with auto-filling SoilGrids district presets.
   - Weather scenario input sliders/fields with realistic meteorological bounds.
   - Live yield prediction card displaying $t/ha$ with confidence intervals.
   - Model transparency view: Actual vs. Predicted scatter plot, MAE/RMSE/R² cards, and feature importance bar charts.
   - Agricultural decision-support limitation alerts.
3. Integrate with backend via React Query / native fetch with loading skeletons, network retry, and graceful Render cold-start handling.

**Phase 5 Acceptance Criteria**:
- Interactive form successfully predicts yield by calling backend API.
- Visualizations render genuine model performance metrics and feature rankings.
- Responsive layout verified across desktop and mobile screen viewports.

---

## Phase 6: QA, End-to-End Testing & Deployment
**Objective**: Perform end-to-end integration testing, verify Vercel and Render deployments, and document operations.

**Tasks**:
1. End-to-end integration tests between frontend and backend.
2. Verify environment variable handling for production (Vercel `NEXT_PUBLIC_API_URL` -> Render backend).
3. Validate cold start behavior, memory consumption, and error logging.
4. Finalize comprehensive `README.md` with production deployment walkthrough.

**Phase 6 Acceptance Criteria**:
- Both frontend and backend independently verified in production environments.
- 100% passing tests across all test suites.
