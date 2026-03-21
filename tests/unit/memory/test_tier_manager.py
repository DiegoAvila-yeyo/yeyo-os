"""
Tests para TierManager — Micro-fase 2.4
Tests unitarios con mocks para no depender de PG/Redis.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from src.memory.tier_manager import (
    TierManager,
    HOT_PROMOTION_MIN_ACCESS,
    HOT_DEMOTION_INACTIVITY_HOURS,
    COLD_DEMOTION_INACTIVITY_DAYS,
)
from src.memory.models import Memory


@pytest.fixture
def mock_flash_memory():
    fm = AsyncMock()
    fm.pool = MagicMock()
    fm._row_to_memory = MagicMock()
    return fm


@pytest.fixture
def mock_cache():
    return AsyncMock()


@pytest.fixture
def tier_manager(mock_flash_memory, mock_cache):
    return TierManager(mock_flash_memory, mock_cache)


class TestEvaluateMemory:
    """Tests de evaluación individual de memorias."""

    @pytest.mark.asyncio
    async def test_warm_to_hot_frequent_access(self, tier_manager):
        """WARM con 5+ accesos en 24h debe promover a HOT."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            content="Frecuente", type="preference", tier="WARM",
            access_count=6, accessed_at=now - timedelta(hours=1),
            checksum="a" * 64,
        )
        assert await tier_manager.evaluate_memory(memory) == "HOT"

    @pytest.mark.asyncio
    async def test_warm_stays_warm_low_access(self, tier_manager):
        """WARM con pocos accesos se mantiene WARM."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            content="Poco acceso", type="fact", tier="WARM",
            access_count=2, accessed_at=now - timedelta(hours=1),
            checksum="b" * 64,
        )
        assert await tier_manager.evaluate_memory(memory) == "WARM"

    @pytest.mark.asyncio
    async def test_hot_to_warm_inactivity(self, tier_manager):
        """HOT sin acceso en 2h debe degradar a WARM."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            content="Inactivo", type="fact", tier="HOT",
            access_count=10, accessed_at=now - timedelta(hours=3),
            checksum="c" * 64,
        )
        assert await tier_manager.evaluate_memory(memory) == "WARM"

    @pytest.mark.asyncio
    async def test_hot_stays_hot_recent_access(self, tier_manager):
        """HOT con acceso reciente se mantiene HOT."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            content="Reciente", type="preference", tier="HOT",
            access_count=10, accessed_at=now - timedelta(minutes=30),
            checksum="d" * 64,
        )
        assert await tier_manager.evaluate_memory(memory) == "HOT"

    @pytest.mark.asyncio
    async def test_warm_to_cold_inactivity(self, tier_manager):
        """WARM sin acceso en 7 días debe degradar a COLD."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            content="Muy inactivo", type="conversation", tier="WARM",
            access_count=1, accessed_at=now - timedelta(days=10),
            checksum="e" * 64,
        )
        assert await tier_manager.evaluate_memory(memory) == "COLD"

    @pytest.mark.asyncio
    async def test_cold_to_warm_recent_access(self, tier_manager):
        """COLD con acceso reciente (<1h) debe promover a WARM."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            content="Revivido", type="fact", tier="COLD",
            access_count=1, accessed_at=now - timedelta(minutes=30),
            checksum="f" * 64,
        )
        assert await tier_manager.evaluate_memory(memory) == "WARM"

    @pytest.mark.asyncio
    async def test_cold_stays_cold_no_access(self, tier_manager):
        """COLD sin acceso reciente se mantiene COLD."""
        now = datetime.now(timezone.utc)
        memory = Memory(
            content="Fría", type="fact", tier="COLD",
            access_count=0, accessed_at=now - timedelta(days=30),
            checksum="0" * 64,
        )
        assert await tier_manager.evaluate_memory(memory) == "COLD"

    @pytest.mark.asyncio
    async def test_never_deletes(self, tier_manager):
        """Ninguna evaluación debe resultar en eliminación."""
        tiers = ["HOT", "WARM", "COLD"]
        now = datetime.now(timezone.utc)
        for tier in tiers:
            memory = Memory(
                content="No delete test", type="fact", tier=tier,
                access_count=0, accessed_at=now - timedelta(days=365),
                checksum="1" * 64,
            )
            result = await tier_manager.evaluate_memory(memory)
            assert result in tiers


class TestTierManagerHelpers:
    """Tests para métodos auxiliares."""

    def test_is_promotion_cold_to_warm(self):
        assert TierManager._is_promotion("COLD", "WARM") is True

    def test_is_promotion_warm_to_hot(self):
        assert TierManager._is_promotion("WARM", "HOT") is True

    def test_is_not_promotion_hot_to_warm(self):
        assert TierManager._is_promotion("HOT", "WARM") is False

    def test_is_not_promotion_same_tier(self):
        assert TierManager._is_promotion("WARM", "WARM") is False

    def test_thresholds_configured(self):
        assert HOT_PROMOTION_MIN_ACCESS == 5
        assert HOT_DEMOTION_INACTIVITY_HOURS == 2
        assert COLD_DEMOTION_INACTIVITY_DAYS == 7
