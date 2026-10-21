"""Unit and Integration Tests for Autonomous Keep-Alive Self-Triggering Feature."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.keep_alive import KeepAliveService, keep_alive_service

client = TestClient(app)


def test_keep_alive_settings_configuration():
    """Verify default keep-alive settings and target URL resolution."""
    assert settings.KEEP_ALIVE_ENABLED is True
    assert settings.KEEP_ALIVE_INTERVAL_MINUTES == 10
    assert settings.KEEP_ALIVE_ENDPOINT == "/api/v1/health"
    
    url = settings.get_keep_alive_url()
    assert "/api/v1/health" in url


def test_keep_alive_service_get_status():
    """Verify get_status returns complete diagnostic metrics."""
    status = keep_alive_service.get_status()
    assert "enabled" in status
    assert "is_running" in status
    assert "target_url" in status
    assert "interval_minutes" in status
    assert "total_pings" in status
    assert "successful_pings" in status
    assert "failed_pings" in status
    assert "capacity_profile" in status
    assert status["capacity_profile"]["inactivity_prevention"] == "Active (15-min idle spin-down neutralized)"


@pytest.mark.asyncio
async def test_keep_alive_ping_once_success():
    """Verify single probe execution on simulated successful HTTP 200 response."""
    test_service = KeepAliveService()
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await test_service.ping_once()
        
    assert result["success"] is True
    assert result["status_code"] == 200
    assert test_service.successful_pings == 1
    assert test_service.failed_pings == 0
    assert test_service.consecutive_failures == 0
    assert test_service.last_error is None


@pytest.mark.asyncio
async def test_keep_alive_ping_once_http_error():
    """Verify resilience when target server returns non-2xx status code."""
    test_service = KeepAliveService()
    
    mock_response = AsyncMock()
    mock_response.status_code = 503
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        result = await test_service.ping_once()
        
    assert result["success"] is False
    assert result["status_code"] == 503
    assert test_service.successful_pings == 0
    assert test_service.failed_pings == 1
    assert test_service.consecutive_failures == 1
    assert "503" in result["error"]


@pytest.mark.asyncio
async def test_keep_alive_ping_once_network_exception():
    """Verify that network exceptions are safely captured without crashing."""
    test_service = KeepAliveService()
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=Exception("Connection timed out")):
        result = await test_service.ping_once()
        
    assert result["success"] is False
    assert result["status_code"] is None
    assert "Connection timed out" in result["error"]
    assert test_service.failed_pings == 1
    assert test_service.consecutive_failures == 1


@pytest.mark.asyncio
async def test_keep_alive_lifecycle_start_and_stop():
    """Verify starting and stopping the background keep-alive task."""
    test_service = KeepAliveService()
    assert not test_service.is_running
    
    # Start with high initial delay so loop doesn't fire immediately
    test_service.start(initial_delay=3600.0)
    assert test_service.is_running
    
    # Starting while running should be idempotent
    test_service.start()
    assert test_service.is_running
    
    # Gracefully stop
    await test_service.stop()
    assert not test_service.is_running


def test_keep_alive_status_endpoint():
    """Verify GET /api/v1/keep-alive and /api/v1/keep-alive/status respond with 200."""
    response = client.get("/api/v1/keep-alive")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert "target_url" in data
    assert "interval_minutes" in data
    
    response_alias = client.get("/api/v1/keep-alive/status")
    assert response_alias.status_code == 200
    assert response_alias.json()["enabled"] is True


def test_keep_alive_trigger_endpoint():
    """Verify POST /api/v1/keep-alive/trigger triggers a probe and returns status."""
    with patch.object(keep_alive_service, "ping_once", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = {
            "success": True,
            "status_code": 200,
            "latency_ms": 12.5,
            "target_url": "http://127.0.0.1:8000/api/v1/health",
            "timestamp": "2026-10-21T00:00:00Z",
        }
        response = client.post("/api/v1/keep-alive/trigger")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Keep-alive trigger probe dispatched"
        assert data["result"]["success"] is True
        assert "current_status" in data


def test_health_endpoint_includes_keep_alive():
    """Verify that GET /api/v1/health incorporates keep_alive metrics."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "keep_alive" in data
    assert data["keep_alive"]["enabled"] is True
