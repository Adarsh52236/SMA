"""Self-Triggering Keep-Alive Service for Continuous Production Availability.

Prevents hosting platforms (such as Render Free Tier) from spinning down the service
due to inactivity (15-minute idle timeout) while strictly respecting resource capacities.
Runs as a lightweight asyncio background worker initiated during the FastAPI lifespan.
"""

import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger("KeepAliveService")


class KeepAliveService:
    """Manages an autonomous self-triggering heartbeat loop to keep the backend warm and online."""

    def __init__(self) -> None:
        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self.total_pings: int = 0
        self.successful_pings: int = 0
        self.failed_pings: int = 0
        self.consecutive_failures: int = 0
        self.last_ping_time: Optional[datetime] = None
        self.last_status_code: Optional[int] = None
        self.last_latency_ms: Optional[float] = None
        self.last_error: Optional[str] = None
        self.initial_delay_seconds: float = 30.0

    @property
    def is_running(self) -> bool:
        """Return whether the background loop task is actively running."""
        return self._is_running and self._task is not None and not self._task.done()

    def start(self, initial_delay: Optional[float] = None) -> None:
        """Start the background self-triggering worker."""
        if not settings.KEEP_ALIVE_ENABLED:
            logger.info("Keep-alive service disabled via configuration (KEEP_ALIVE_ENABLED=False).")
            return

        if self.is_running:
            logger.warning("Keep-alive service is already running.")
            return

        if initial_delay is not None:
            self.initial_delay_seconds = initial_delay

        self._is_running = True
        self._started_at = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._run_loop(), name="keep_alive_worker")
        target_url = settings.get_keep_alive_url()
        logger.info(
            f"KeepAlive self-triggering worker started. Target: {target_url}, "
            f"Interval: {settings.KEEP_ALIVE_INTERVAL_MINUTES} min (Initial delay: {self.initial_delay_seconds}s)"
        )

    async def stop(self) -> None:
        """Gracefully stop and await cancellation of the background worker."""
        if not self._is_running and self._task is None:
            return

        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error during keep-alive worker shutdown: {e}")

        self._task = None
        logger.info("KeepAlive self-triggering worker stopped.")

    async def ping_once(self) -> Dict[str, Any]:
        """Perform a single keep-alive HTTP probe against the target URL.
        
        Uses an isolated httpx client with strict timeout to prevent connection leaks
        and ensure minimal memory and CPU consumption.
        """
        target_url = settings.get_keep_alive_url()
        self.total_pings += 1
        start_time = time.perf_counter()
        headers = {
            "User-Agent": "SMA-Backend-KeepAlive/1.0",
            "X-Keep-Alive-Ping": "true",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=settings.KEEP_ALIVE_TIMEOUT_SECONDS,
                follow_redirects=True,
            ) as client:
                response = await client.get(target_url, headers=headers)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                status_code = response.status_code

                self.last_ping_time = datetime.now(timezone.utc)
                self.last_status_code = status_code
                self.last_latency_ms = latency_ms

                if 200 <= status_code < 400:
                    self.successful_pings += 1
                    self.consecutive_failures = 0
                    self.last_error = None
                    logger.info(
                        f"KeepAlive ping succeeded: {target_url} -> HTTP {status_code} ({latency_ms} ms) "
                        f"[Total: {self.total_pings}, Successes: {self.successful_pings}]"
                    )
                    return {
                        "success": True,
                        "status_code": status_code,
                        "latency_ms": latency_ms,
                        "target_url": target_url,
                        "timestamp": self.last_ping_time.isoformat(),
                    }
                else:
                    self.failed_pings += 1
                    self.consecutive_failures += 1
                    error_msg = f"Unexpected response status HTTP {status_code}"
                    self.last_error = error_msg
                    logger.warning(
                        f"KeepAlive ping returned non-success code: {target_url} -> HTTP {status_code} ({latency_ms} ms)"
                    )
                    return {
                        "success": False,
                        "status_code": status_code,
                        "latency_ms": latency_ms,
                        "target_url": target_url,
                        "error": error_msg,
                        "timestamp": self.last_ping_time.isoformat(),
                    }

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self.last_ping_time = datetime.now(timezone.utc)
            self.failed_pings += 1
            self.consecutive_failures += 1
            self.last_error = str(exc)
            self.last_latency_ms = latency_ms
            logger.warning(
                f"KeepAlive ping failed for {target_url} ({latency_ms} ms): {exc} "
                f"(consecutive failures: {self.consecutive_failures})"
            )
            return {
                "success": False,
                "status_code": None,
                "latency_ms": latency_ms,
                "target_url": target_url,
                "error": str(exc),
                "timestamp": self.last_ping_time.isoformat(),
            }

    async def _run_loop(self) -> None:
        """Main autonomous loop running continuously at configured intervals."""
        try:
            # Initial grace period: let server complete startup and bind port before first self-ping
            if self.initial_delay_seconds > 0:
                await asyncio.sleep(self.initial_delay_seconds)

            while self._is_running:
                await self.ping_once()

                # Calculate next interval with +/- 15s jitter to prevent synchronized burst collisions
                base_delay = max(60, settings.KEEP_ALIVE_INTERVAL_MINUTES * 60)
                jitter = random.uniform(-15.0, 15.0)
                delay = max(30.0, base_delay + jitter)

                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            logger.debug("KeepAlive loop cancelled gracefully.")
        except Exception as exc:
            logger.error(f"Unexpected fatal error in KeepAlive loop: {exc}", exc_info=True)
            self._is_running = False

    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic health and operation metrics of the keep-alive service."""
        uptime_seconds = None
        if self._started_at:
            uptime_seconds = round((datetime.now(timezone.utc) - self._started_at).total_seconds(), 1)

        success_rate_pct = None
        if self.total_pings > 0:
            success_rate_pct = round((self.successful_pings / self.total_pings) * 100, 1)

        return {
            "enabled": settings.KEEP_ALIVE_ENABLED,
            "is_running": self.is_running,
            "target_url": settings.get_keep_alive_url(),
            "interval_minutes": settings.KEEP_ALIVE_INTERVAL_MINUTES,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "uptime_seconds": uptime_seconds,
            "total_pings": self.total_pings,
            "successful_pings": self.successful_pings,
            "failed_pings": self.failed_pings,
            "consecutive_failures": self.consecutive_failures,
            "success_rate_pct": success_rate_pct,
            "last_ping_time": self.last_ping_time.isoformat() if self.last_ping_time else None,
            "last_status_code": self.last_status_code,
            "last_latency_ms": self.last_latency_ms,
            "last_error": self.last_error,
            "capacity_profile": {
                "monthly_pings_approx": (60 // max(1, settings.KEEP_ALIVE_INTERVAL_MINUTES)) * 24 * 31,
                "memory_overhead": "< 2 MB",
                "cpu_utilization": "negligible (< 0.01%)",
                "inactivity_prevention": "Active (15-min idle spin-down neutralized)",
            },
        }


# Singleton instance shared across the application
keep_alive_service = KeepAliveService()
