import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router
from app.services.model_service import model_service
from app.services.keep_alive import keep_alive_service

logger = logging.getLogger("CropYieldAPI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown.

    Loads the verified scikit-learn pipeline and metadata once on startup,
    caching it in memory to minimize prediction latency.
    Starts the autonomous self-triggering keep-alive background worker.
    """
    logger.info("Starting Crop Yield Prediction API. Initializing model service...")
    model_service.load_model()

    if settings.KEEP_ALIVE_ENABLED:
        logger.info("Starting autonomous KeepAlive self-triggering worker...")
        keep_alive_service.start()

    yield

    logger.info("Stopping KeepAlive worker...")
    await keep_alive_service.stop()
    logger.info("Shutting down Crop Yield Prediction API.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-minded API for predicting Maharashtra Kharif soybean yield "
        "from verified weather, soil properties, and growing-season information."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS middleware configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Safety catch-all preventing internal filesystem paths or tracebacks from leaking."""
    logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred while processing the request."},
    )


# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
def root():
    """Root endpoint providing service metadata."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "ready": f"{settings.API_V1_STR}/ready",
        "keep_alive": f"{settings.API_V1_STR}/keep-alive",
        "metadata": f"{settings.API_V1_STR}/model/metadata",
        "predict": f"{settings.API_V1_STR}/predict",
    }
