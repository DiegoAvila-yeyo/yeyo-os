"""
Tests para BackgroundTaskManager — Micro-fase 2.17
Tests unitarios con mocks.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.background import (
    BackgroundTaskManager,
    TIER_EVALUATION_INTERVAL,
    CACHE_WARMING_INTERVAL,
    EMBEDDING_GENERATION_INTERVAL,
    REDIS_CLEANUP_INTERVAL,
)


@pytest.fixture
def mock_tier_manager():
    tm = AsyncMock()
    tm.evaluate_all.return_value = {
        "promoted": 2, "demoted": 1, "unchanged": 10, "errors": 0
    }
    return tm


@pytest.fixture
def mock_cache():
    c = AsyncMock()
    c.warm_cache.return_value = None
    c.get_stats.return_value = {"connected": True}
    return c


@pytest.fixture
def mock_flash_memory():
    fm = AsyncMock()
    fm.recall_by_type.return_value = []
    fm.recall.return_value = []
    fm.pool = MagicMock()
    return fm


@pytest.fixture
def mock_embeddings():
    emb = MagicMock()
    emb.generate_batch.return_value = []
    return emb


@pytest.fixture
def task_manager(mock_tier_manager, mock_cache, mock_flash_memory, mock_embeddings):
    return BackgroundTaskManager(
        tier_manager=mock_tier_manager,
        cache=mock_cache,
        flash_memory=mock_flash_memory,
        embeddings=mock_embeddings,
    )


class TestBackgroundTaskManagerBasic:
    """Tests básicos."""

    def test_not_running_initially(self, task_manager):
        assert task_manager.is_running is False

    def test_no_tasks_initially(self, task_manager):
        assert task_manager.task_count == 0

    def test_intervals_configured(self):
        assert TIER_EVALUATION_INTERVAL == 300  # 5 min
        assert CACHE_WARMING_INTERVAL == 3600  # 1h
        assert EMBEDDING_GENERATION_INTERVAL == 86400  # 24h
        assert REDIS_CLEANUP_INTERVAL == 86400  # 24h


class TestStartStop:
    """Tests de inicio y parada."""

    @pytest.mark.asyncio
    async def test_start_creates_tasks(self, task_manager):
        await task_manager.start()
        assert task_manager.is_running is True
        assert task_manager.task_count > 0
        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_tasks(self, task_manager):
        await task_manager.start()
        await task_manager.stop()
        assert task_manager.is_running is False
        assert task_manager.task_count == 0

    @pytest.mark.asyncio
    async def test_double_start_warning(self, task_manager):
        await task_manager.start()
        await task_manager.start()  # No debe crashear
        assert task_manager.is_running is True
        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start(self, task_manager):
        await task_manager.stop()  # No debe crashear
        assert task_manager.is_running is False

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, task_manager):
        """Las tareas deben detenerse limpiamente."""
        await task_manager.start()
        assert task_manager.task_count == 4
        await task_manager.stop()
        assert task_manager.task_count == 0


class TestPartialDependencies:
    """Tests con dependencias parciales."""

    @pytest.mark.asyncio
    async def test_no_tier_manager(self, mock_cache, mock_flash_memory, mock_embeddings):
        tm = BackgroundTaskManager(
            tier_manager=None,
            cache=mock_cache,
            flash_memory=mock_flash_memory,
            embeddings=mock_embeddings,
        )
        await tm.start()
        assert tm.task_count == 3  # Sin tier evaluation
        await tm.stop()

    @pytest.mark.asyncio
    async def test_no_cache(self, mock_tier_manager, mock_flash_memory, mock_embeddings):
        tm = BackgroundTaskManager(
            tier_manager=mock_tier_manager,
            cache=None,
            flash_memory=mock_flash_memory,
            embeddings=mock_embeddings,
        )
        await tm.start()
        assert tm.task_count == 2  # Sin warming ni cleanup
        await tm.stop()

    @pytest.mark.asyncio
    async def test_minimal_dependencies(self, mock_tier_manager):
        tm = BackgroundTaskManager(tier_manager=mock_tier_manager)
        await tm.start()
        assert tm.task_count == 1  # Solo tier evaluation
        await tm.stop()

    @pytest.mark.asyncio
    async def test_no_dependencies(self):
        tm = BackgroundTaskManager()
        await tm.start()
        assert tm.task_count == 0
        await tm.stop()


class TestTaskExecution:
    """Tests de ejecución de tareas."""

    @pytest.mark.asyncio
    async def test_tier_evaluation_callable(self, task_manager, mock_tier_manager):
        await task_manager._evaluate_tiers()
        mock_tier_manager.evaluate_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_warming_callable(self, task_manager, mock_flash_memory):
        await task_manager._warm_cache()
        mock_flash_memory.recall_by_type.assert_called()

    @pytest.mark.asyncio
    async def test_task_error_doesnt_crash(self, task_manager, mock_tier_manager):
        """Un error en una tarea no debe crashear el manager."""
        mock_tier_manager.evaluate_all.side_effect = Exception("DB error")
        await task_manager._evaluate_tiers()  # No debe lanzar excepción
