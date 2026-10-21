"""Keep-Alive and self-triggering diagnostic and control endpoints."""

from fastapi import APIRouter, status
from app.services.keep_alive import keep_alive_service

router = APIRouter()


@router.get("", tags=["KeepAlive"])
@router.get("/status", tags=["KeepAlive"])
def get_keep_alive_status():
    """Retrieve operational metrics, heartbeat status, and capacity details."""
    return keep_alive_service.get_status()


@router.post("/trigger", status_code=status.HTTP_200_OK, tags=["KeepAlive"])
async def trigger_keep_alive_ping():
    """Manually dispatch an immediate keep-alive probe to refresh server activity."""
    result = await keep_alive_service.ping_once()
    return {
        "message": "Keep-alive trigger probe dispatched",
        "result": result,
        "current_status": keep_alive_service.get_status(),
    }
