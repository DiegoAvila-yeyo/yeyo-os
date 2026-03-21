"""
Tests para MemoryCache — Micro-fase 2.2
Tests unitarios sin Redis real + tests de integración con Redis real.
"""

import pytest
import json
from src.memory.cache import MemoryCache, MEMORY_KEY_PREFIX, HOT_SET_KEY, DEFAULT_TTL
from src.memory.models import Memory


class TestMemoryCacheUnit:
    """Tests unitarios sin Redis real."""

    def test_default_redis_url(self):
        cache = MemoryCache()
        assert cache.redis_url == "redis://localhost:6379"

    def test_custom_redis_url(self):
        cache = MemoryCache(redis_url="redis://custom:6380")
        assert cache.redis_url == "redis://custom:6380"

    def test_default_ttl_is_one_hour(self):
        assert DEFAULT_TTL == 3600

    def test_key_prefix(self):
        assert MEMORY_KEY_PREFIX == "yeyoos:memory:"

    @pytest.mark.asyncio
    async def test_get_returns_none_without_connection(self):
        cache = MemoryCache()
        result = await cache.get("some-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_hot_memories_returns_empty_without_connection(self):
        cache = MemoryCache()
        result = await cache.get_hot_memories()
        assert result == []

    @pytest.mark.asyncio
    async def test_health_check_false_without_connection(self):
        cache = MemoryCache()
        result = await cache.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_set_does_nothing_without_connection(self):
        cache = MemoryCache()
        mem = Memory(content="test", type="fact", tier="HOT", checksum="a" * 64)
        # No debe lanzar excepción
        await cache.set(mem)

    @pytest.mark.asyncio
    async def test_invalidate_does_nothing_without_connection(self):
        cache = MemoryCache()
        await cache.invalidate("some-id")  # No debe lanzar excepción

    @pytest.mark.asyncio
    async def test_get_multiple_returns_empty_without_connection(self):
        cache = MemoryCache()
        result = await cache.get_multiple(["id1", "id2"])
        assert result == []

    @pytest.mark.asyncio
    async def test_get_stats_returns_not_connected_without_connection(self):
        cache = MemoryCache()
        stats = await cache.get_stats()
        assert stats["connected"] is False


@pytest.mark.integration
class TestMemoryCacheIntegration:
    """Tests de integración con Redis real."""

    @pytest.fixture
    async def cache(self):
        import os
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        c = MemoryCache(redis_url=redis_url)
        await c.connect()
        yield c
        await c.clear_all()
        await c.disconnect()

    @pytest.mark.asyncio
    async def test_health_check_true(self, cache):
        assert await cache.health_check() is True

    @pytest.mark.asyncio
    async def test_set_and_get_memory(self, cache):
        mem = Memory(
            id="test-cache-001",
            content="Memoria en caché",
            type="fact",
            tier="HOT",
            checksum="a" * 64,
        )
        await cache.set(mem)
        found = await cache.get("test-cache-001")
        assert found is not None
        assert found.content == "Memoria en caché"
        assert found.tier == "HOT"

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache):
        result = await cache.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate_removes_from_cache(self, cache):
        mem = Memory(
            id="test-cache-002",
            content="To be invalidated",
            type="fact",
            tier="HOT",
            checksum="b" * 64,
        )
        await cache.set(mem)
        assert await cache.get("test-cache-002") is not None
        await cache.invalidate("test-cache-002")
        assert await cache.get("test-cache-002") is None

    @pytest.mark.asyncio
    async def test_get_hot_memories_returns_ids(self, cache):
        mem = Memory(
            id="test-cache-003",
            content="HOT memory",
            type="preference",
            tier="HOT",
            checksum="c" * 64,
        )
        await cache.set(mem)
        hot_ids = await cache.get_hot_memories()
        assert "test-cache-003" in hot_ids

    @pytest.mark.asyncio
    async def test_get_multiple(self, cache):
        for i in range(3):
            mem = Memory(
                id=f"test-multi-{i}",
                content=f"Multi test {i}",
                type="fact",
                tier="HOT",
                checksum=str(i) * 64,
            )
            await cache.set(mem)
        results = await cache.get_multiple(
            ["test-multi-0", "test-multi-1", "test-multi-2"]
        )
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_warm_cache_only_hot(self, cache):
        hot_mem = Memory(
            id="test-warm-hot",
            content="HOT",
            type="fact",
            tier="HOT",
            checksum="d" * 64,
        )
        warm_mem = Memory(
            id="test-warm-warm",
            content="WARM",
            type="fact",
            tier="WARM",
            checksum="e" * 64,
        )
        await cache.warm_cache([hot_mem, warm_mem])
        assert await cache.get("test-warm-hot") is not None
        assert await cache.get("test-warm-warm") is None

    @pytest.mark.asyncio
    async def test_get_stats(self, cache):
        stats = await cache.get_stats()
        assert stats["connected"] is True
        assert "hot_memories_count" in stats

    @pytest.mark.asyncio
    async def test_clear_all(self, cache):
        mem = Memory(
            id="test-clear",
            content="Clear test",
            type="fact",
            tier="HOT",
            checksum="f" * 64,
        )
        await cache.set(mem)
        await cache.clear_all()
        assert await cache.get("test-clear") is None
