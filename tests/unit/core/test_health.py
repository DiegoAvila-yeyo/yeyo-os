"""Tests para Health Check System — Micro-fase 1.12"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock
from src.core.health import HealthChecker, ServiceCheck


@pytest.fixture
def checker():
    return HealthChecker(cache_ttl_seconds=10.0, service_timeout_seconds=5.0)


class TestServiceCheck:
    def test_create_service_check(self):
        sc = ServiceCheck(name="test", status="up", latency_ms=5.3)
        assert sc.name == "test"
        assert sc.status == "up"
        assert sc.latency_ms == 5.3

    def test_to_dict(self):
        d = ServiceCheck(name="test", status="up", latency_ms=5.3).to_dict()
        assert d["status"] == "up"
        assert d["latency_ms"] == 5.3

    def test_to_dict_with_error(self):
        d = ServiceCheck(name="test", status="down", error="connection refused").to_dict()
        assert d["error"] == "connection refused"

    def test_default_status_is_unknown(self):
        assert ServiceCheck(name="test").status == "unknown"


class TestHealthChecker:
    @pytest.mark.asyncio
    async def test_check_all_returns_dict(self, checker):
        result = await checker.check_all()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_check_all_has_required_fields(self, checker):
        result = await checker.check_all()
        assert "status" in result
        assert "services" in result
        assert "uptime_seconds" in result
        assert "version" in result

    @pytest.mark.asyncio
    async def test_version_is_correct(self, checker):
        result = await checker.check_all()
        assert result["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_has_all_services(self, checker):
        services = (await checker.check_all())["services"]
        assert "postgresql" in services
        assert "redis" in services
        assert "ollama" in services
        assert "gpu" in services
        assert "filesystem" in services

    @pytest.mark.asyncio
    async def test_uptime_is_positive(self, checker):
        assert (await checker.check_all())["uptime_seconds"] >= 0


class TestHealthStatus:
    @pytest.mark.asyncio
    async def test_all_down_is_unhealthy(self):
        checker = HealthChecker()
        checker._check_postgresql = AsyncMock(return_value=False)
        checker._check_redis = AsyncMock(return_value=False)
        checker._check_ollama = AsyncMock(return_value=False)
        checker._check_gpu = AsyncMock(return_value=False)
        checker._check_filesystem = AsyncMock(return_value=False)
        assert (await checker.check_all())["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_all_up_is_healthy(self):
        checker = HealthChecker()
        checker._check_postgresql = AsyncMock(return_value=True)
        checker._check_redis = AsyncMock(return_value=True)
        checker._check_ollama = AsyncMock(return_value=True)
        checker._check_gpu = AsyncMock(return_value=True)
        checker._check_filesystem = AsyncMock(return_value=True)
        assert (await checker.check_all())["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_one_down_is_degraded(self):
        checker = HealthChecker()
        checker._check_postgresql = AsyncMock(return_value=True)
        checker._check_redis = AsyncMock(return_value=False)
        checker._check_ollama = AsyncMock(return_value=True)
        checker._check_gpu = AsyncMock(return_value=True)
        checker._check_filesystem = AsyncMock(return_value=True)
        result = await checker.check_all()
        assert result["status"] == "degraded"
        assert result["down_count"] == 1

    @pytest.mark.asyncio
    async def test_two_down_is_unhealthy(self):
        checker = HealthChecker()
        checker._check_postgresql = AsyncMock(return_value=False)
        checker._check_redis = AsyncMock(return_value=False)
        checker._check_ollama = AsyncMock(return_value=True)
        checker._check_gpu = AsyncMock(return_value=True)
        checker._check_filesystem = AsyncMock(return_value=True)
        result = await checker.check_all()
        assert result["status"] == "unhealthy"
        assert result["down_count"] == 2


class TestHealthCache:
    @pytest.mark.asyncio
    async def test_cache_returns_same_result(self):
        checker = HealthChecker(cache_ttl_seconds=10.0)
        for attr in ["_check_postgresql", "_check_redis", "_check_ollama", "_check_gpu", "_check_filesystem"]:
            setattr(checker, attr, AsyncMock(return_value=True))
        r1 = await checker.check_all()
        r2 = await checker.check_all()
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_cache_expires(self):
        checker = HealthChecker(cache_ttl_seconds=0.1)
        for attr in ["_check_postgresql", "_check_redis", "_check_ollama", "_check_gpu", "_check_filesystem"]:
            setattr(checker, attr, AsyncMock(return_value=True))
        r1 = await checker.check_all()
        await asyncio.sleep(0.15)
        r2 = await checker.check_all()
        assert r1 is not r2

    @pytest.mark.asyncio
    async def test_invalidate_cache(self):
        checker = HealthChecker(cache_ttl_seconds=60.0)
        for attr in ["_check_postgresql", "_check_redis", "_check_ollama", "_check_gpu", "_check_filesystem"]:
            setattr(checker, attr, AsyncMock(return_value=True))
        r1 = await checker.check_all()
        checker.invalidate_cache()
        r2 = await checker.check_all()
        assert r1 is not r2


class TestHealthTimeout:
    @pytest.mark.asyncio
    async def test_slow_service_times_out(self):
        checker = HealthChecker(service_timeout_seconds=0.1)

        async def slow_check():
            await asyncio.sleep(5.0)
            return True

        checker._check_postgresql = slow_check
        checker._check_redis = AsyncMock(return_value=True)
        checker._check_ollama = AsyncMock(return_value=True)
        checker._check_gpu = AsyncMock(return_value=True)
        checker._check_filesystem = AsyncMock(return_value=True)

        result = await checker.check_all()
        pg = result["services"]["postgresql"]
        assert pg["status"] == "down"
        assert "Timeout" in pg.get("error", "")
