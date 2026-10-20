from fastapi import APIRouter
from app.api.v1.endpoints import health, prediction

api_router = APIRouter()
api_router.include_router(health.router, prefix="", tags=["Health"])
api_router.include_router(prediction.router, prefix="", tags=["Prediction"])
