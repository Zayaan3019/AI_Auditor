from __future__ import annotations

import asyncio
import psutil
import time
from typing import Any, Dict, Optional

from loguru import logger
from prometheus_client import Gauge, Info

# System metrics
SYSTEM_CPU_USAGE = Gauge("ai_auditor_system_cpu_percent", "System CPU usage percentage")
SYSTEM_MEMORY_USAGE = Gauge(
    "ai_auditor_system_memory_percent", "System memory usage percentage"
)
SYSTEM_DISK_USAGE = Gauge(
    "ai_auditor_system_disk_percent", "System disk usage percentage"
)

# Application metrics
APP_INFO = Info("ai_auditor_app", "Application information")
VECTOR_STORE_SIZE = Gauge(
    "ai_auditor_vector_store_documents", "Number of documents in vector store"
)
DRIFT_DETECTOR_TRAINED = Gauge(
    "ai_auditor_drift_detector_trained", "Whether drift detector is trained (0 or 1)"
)
DRIFT_DETECTOR_SAMPLES = Gauge(
    "ai_auditor_drift_detector_samples", "Number of samples in drift detector"
)
UPTIME_SECONDS = Gauge("ai_auditor_uptime_seconds", "Application uptime in seconds")


class HealthChecker:
    """Centralized health checking for all system components."""

    def __init__(self):
        self.start_time = time.time()
        self._checks: Dict[str, bool] = {}
        self._last_check: Dict[str, float] = {}

    async def check_all(self) -> Dict[str, Any]:
        """Run all health checks and return status.

        Returns:
            Dict with overall status and individual component statuses.
        """
        checks = {
            "vector_store": await self._check_vector_store(),
            "drift_detector": await self._check_drift_detector(),
            "system_resources": await self._check_system_resources(),
            "embeddings": await self._check_embeddings(),
        }

        overall_healthy = all(checks.values())

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "uptime_seconds": time.time() - self.start_time,
            "checks": checks,
            "timestamp": time.time(),
        }

    async def _check_vector_store(self) -> bool:
        """Check if vector store is operational."""
        try:
            from app.services.vector_store import VectorStoreManager

            vs = VectorStoreManager.get_instance()
            # Simple check: embeddings should be accessible
            embeddings = await vs.get_all_embeddings()
            return True
        except Exception as exc:
            logger.warning(f"Vector store health check failed: {exc}")
            return False

    async def _check_drift_detector(self) -> bool:
        """Check if drift detector is trained and ready."""
        try:
            from app.api.routes import drift_detector

            # Check if model exists
            return drift_detector._model is not None
        except Exception as exc:
            logger.warning(f"Drift detector health check failed: {exc}")
            return False

    async def _check_system_resources(self) -> bool:
        """Check if system resources are within acceptable limits."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent

            # Flag as unhealthy if any resource is critically high
            if cpu_percent > 95 or memory_percent > 95 or disk_percent > 95:
                logger.warning(
                    f"System resources critical: CPU={cpu_percent}%, "
                    f"Memory={memory_percent}%, Disk={disk_percent}%"
                )
                return False

            return True
        except Exception as exc:
            logger.warning(f"System resources check failed: {exc}")
            return False

    async def _check_embeddings(self) -> bool:
        """Check if embedding model is loaded and functional."""
        try:
            from app.services.vector_store import VectorStoreManager

            vs = VectorStoreManager.get_instance()
            await vs._ensure_embedding_client()
            return vs._embeddings_client is not None
        except Exception as exc:
            logger.warning(f"Embeddings health check failed: {exc}")
            return False


async def collect_metrics_background(interval: int = 30) -> None:
    """Background task to collect system and application metrics.

    Args:
        interval: Collection interval in seconds.
    """
    from app.core.config import settings

    # Set app info
    APP_INFO.info(
        {
            "name": settings.app_name,
            "version": "0.1.0",
            "environment": settings.environment,
        }
    )

    logger.info(f"Starting metrics collection with {interval}s interval")

    while True:
        try:
            # System metrics
            SYSTEM_CPU_USAGE.set(psutil.cpu_percent(interval=0.1))
            SYSTEM_MEMORY_USAGE.set(psutil.virtual_memory().percent)
            SYSTEM_DISK_USAGE.set(psutil.disk_usage("/").percent)

            # Application metrics
            UPTIME_SECONDS.set(time.time() - asyncio.get_event_loop().time())

            # Vector store metrics
            try:
                from app.services.vector_store import VectorStoreManager

                vs = VectorStoreManager.get_instance()
                embeddings = await vs.get_all_embeddings()
                VECTOR_STORE_SIZE.set(embeddings.shape[0] if embeddings.size > 0 else 0)
            except Exception:
                pass

            # Drift detector metrics
            try:
                from app.api.routes import drift_detector

                is_trained = 1 if drift_detector._model is not None else 0
                DRIFT_DETECTOR_TRAINED.set(is_trained)

                samples = len(drift_detector._embeddings)
                DRIFT_DETECTOR_SAMPLES.set(samples)
            except Exception:
                pass

        except Exception as exc:
            logger.error(f"Error collecting metrics: {exc}")

        await asyncio.sleep(interval)


# Global health checker instance
health_checker = HealthChecker()
