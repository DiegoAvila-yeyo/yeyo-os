"""
YeyoOS — Health Check System
Micro-fase 1.12 — Capa 1: Esqueleto

Sistema unificado que verifica el estado de todos los subsistemas.

Estados:
  healthy:   Todos los servicios funcionando
  degraded:  1 servicio caído
  unhealthy: 2+ servicios caídos

Cache: resultado cacheado 10 segundos.
Timeout: máximo 5 segundos por servicio.
"""

import asyncio
import time
import os
from typing import Any


class ServiceCheck:
    def __init__(
        self,
        name: str,
        status: str = "unknown",
        latency_ms: float = 0.0,
        details: dict[str, Any] | None = None,
        error: str | None = None,
    ):
        self.name = name
        self.status = status
        self.latency_ms = latency_ms
        self.details = details or {}
        self.error = error

    def to_dict(self) -> dict:
        result = {
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
        }
        if self.details:
            result["details"] = self.details
        if self.error:
            result["error"] = self.error
        return result


class HealthChecker:
    """Verificador unificado de salud del sistema."""

    def __init__(
        self,
        cache_ttl_seconds: float = 10.0,
        service_timeout_seconds: float = 5.0,
    ):
        self.cache_ttl = cache_ttl_seconds
        self.service_timeout = service_timeout_seconds
        self._cache: dict | None = None
        self._cache_time: float = 0.0
        self._start_time: float = time.time()

    def _is_cache_valid(self) -> bool:
        if self._cache is None:
            return False
        return (time.time() - self._cache_time) < self.cache_ttl

    async def check_all(self) -> dict:
        """Verifica todos los subsistemas. Retorna resultado cacheado si es válido."""
        if self._is_cache_valid():
            return self._cache

        checks = await asyncio.gather(
            self._check_service("postgresql", self._check_postgresql),
            self._check_service("redis", self._check_redis),
            self._check_service("ollama", self._check_ollama),
            self._check_service("gpu", self._check_gpu),
            self._check_service("filesystem", self._check_filesystem),
            return_exceptions=True,
        )

        services = {}
        for check in checks:
            if isinstance(check, ServiceCheck):
                services[check.name] = check.to_dict()
            elif isinstance(check, Exception):
                services["unknown"] = {"status": "down", "error": str(check)}

        down_count = sum(1 for s in services.values() if s.get("status") == "down")

        if down_count == 0:
            overall_status = "healthy"
        elif down_count == 1:
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"

        result = {
            "status": overall_status,
            "services": services,
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "version": "0.1.0",
            "checks_count": len(services),
            "down_count": down_count,
        }

        self._cache = result
        self._cache_time = time.time()
        return result

    async def _check_service(self, name: str, check_fn) -> ServiceCheck:
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(check_fn(), timeout=self.service_timeout)
            latency = (time.monotonic() - start) * 1000
            return ServiceCheck(name=name, status="up" if result else "down", latency_ms=latency)
        except asyncio.TimeoutError:
            latency = (time.monotonic() - start) * 1000
            return ServiceCheck(
                name=name, status="down", latency_ms=latency,
                error=f"Timeout after {self.service_timeout}s",
            )
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            return ServiceCheck(name=name, status="down", latency_ms=latency, error=str(e))

    async def _check_postgresql(self) -> bool:
        """Stub: implementación real en Capa 2."""
        return False

    async def _check_redis(self) -> bool:
        return False

    async def _check_ollama(self) -> bool:
        return False

    async def _check_gpu(self) -> bool:
        return os.path.exists("/usr/bin/nvidia-smi") or os.path.exists("/usr/local/bin/nvidia-smi")

    async def _check_filesystem(self) -> bool:
        try:
            test_file = "/tmp/yeyo_health_check"
            with open(test_file, "w") as f:
                f.write("ok")
            os.remove(test_file)
            return True
        except Exception:
            return False

    def invalidate_cache(self) -> None:
        self._cache = None
        self._cache_time = 0.0
