"""Tests para YeyoNet job_orchestrator."""
import json
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.yeyonet.job_orchestrator import JobOrchestrator, JOB_REQUIREMENTS
from src.yeyonet.models import JobType, JobStatus
from src.yeyonet.protocol import MessageType, NetMessage


def _make_pool():
    pool = MagicMock()
    conn = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = ctx
    return pool, conn


class TestJobOrchestratorCreateJob:
    """Tests for create_job."""

    @pytest.mark.asyncio
    async def test_create_job_returns_job(self):
        pool, conn = _make_pool()
        conn.execute.return_value = "INSERT 0 1"

        orch = JobOrchestrator(pool)
        job = await orch.create_job(
            job_type=JobType.IMAGE_GENERATE,
            payload={"prompt": "a cat"},
            priority=8,
        )

        assert job.type == JobType.IMAGE_GENERATE
        assert job.payload == {"prompt": "a cat"}
        assert job.priority == 8
        assert job.status == JobStatus.QUEUED
        uuid.UUID(job.id)

    @pytest.mark.asyncio
    async def test_create_job_with_requested_by(self):
        pool, conn = _make_pool()
        conn.execute.return_value = "INSERT 0 1"
        req_by = str(uuid.uuid4())

        orch = JobOrchestrator(pool)
        job = await orch.create_job(
            job_type=JobType.TEXT_INFERENCE,
            payload={},
            requested_by=req_by,
        )

        assert job.requested_by == req_by


class TestJobOrchestratorFindBestNode:
    """Tests for _find_best_node scoring logic."""

    @pytest.mark.asyncio
    async def test_no_relay_returns_none(self):
        pool, conn = _make_pool()
        orch = JobOrchestrator(pool, relay=None)
        result = await orch._find_best_node("image_generate", conn)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_connected_nodes_returns_none(self):
        pool, conn = _make_pool()
        relay = MagicMock()
        relay.get_connected_ids.return_value = []

        orch = JobOrchestrator(pool, relay=relay)
        result = await orch._find_best_node("image_generate", conn)
        assert result is None

    @pytest.mark.asyncio
    async def test_selects_node_with_best_score(self):
        pool, conn = _make_pool()
        node_a = str(uuid.uuid4())
        node_b = str(uuid.uuid4())

        relay = MagicMock()
        relay.get_connected_ids.return_value = [node_a, node_b]

        conn.fetch.return_value = [
            {
                "id": uuid.UUID(node_a),
                "resources": json.dumps({
                    "cpu_percent": 80,
                    "ram_free_gb": 2.0,
                    "gpu_name": None,
                    "active_jobs": 3,
                }),
                "mode": "completo",
            },
            {
                "id": uuid.UUID(node_b),
                "resources": json.dumps({
                    "cpu_percent": 10,
                    "ram_free_gb": 16.0,
                    "gpu_name": "RTX 4090",
                    "active_jobs": 0,
                }),
                "mode": "completo",
            },
        ]

        orch = JobOrchestrator(pool, relay=relay)
        best = await orch._find_best_node("custom", conn)

        # node_b has lower CPU, more RAM, GPU, no active jobs → higher score
        assert best == node_b

    @pytest.mark.asyncio
    async def test_skips_node_without_gpu_for_gpu_job(self):
        pool, conn = _make_pool()
        node_a = str(uuid.uuid4())

        relay = MagicMock()
        relay.get_connected_ids.return_value = [node_a]

        conn.fetch.return_value = [
            {
                "id": uuid.UUID(node_a),
                "resources": json.dumps({
                    "cpu_percent": 10,
                    "ram_free_gb": 16.0,
                    "gpu_name": None,  # no GPU
                    "active_jobs": 0,
                }),
                "mode": "completo",
            },
        ]

        orch = JobOrchestrator(pool, relay=relay)
        best = await orch._find_best_node("image_generate", conn)
        assert best is None  # image_generate needs GPU

    @pytest.mark.asyncio
    async def test_skips_node_with_insufficient_ram(self):
        pool, conn = _make_pool()
        node_a = str(uuid.uuid4())

        relay = MagicMock()
        relay.get_connected_ids.return_value = [node_a]

        conn.fetch.return_value = [
            {
                "id": uuid.UUID(node_a),
                "resources": json.dumps({
                    "cpu_percent": 10,
                    "ram_free_gb": 1.0,  # needs 4.0 for text_inference
                    "gpu_name": None,
                    "ollama_models": ["llama3"],
                    "active_jobs": 0,
                }),
                "mode": "completo",
            },
        ]

        orch = JobOrchestrator(pool, relay=relay)
        best = await orch._find_best_node("text_inference", conn)
        assert best is None

    @pytest.mark.asyncio
    async def test_skips_node_without_ollama_for_inference(self):
        pool, conn = _make_pool()
        node_a = str(uuid.uuid4())

        relay = MagicMock()
        relay.get_connected_ids.return_value = [node_a]

        conn.fetch.return_value = [
            {
                "id": uuid.UUID(node_a),
                "resources": json.dumps({
                    "cpu_percent": 10,
                    "ram_free_gb": 8.0,
                    "gpu_name": None,
                    "ollama_models": [],  # no ollama models
                    "active_jobs": 0,
                }),
                "mode": "completo",
            },
        ]

        orch = JobOrchestrator(pool, relay=relay)
        best = await orch._find_best_node("text_inference", conn)
        assert best is None


class TestJobOrchestratorRetry:
    """Tests for fail_job retry logic."""

    @pytest.mark.asyncio
    async def test_fail_job_retries_when_attempts_remain(self):
        pool, conn = _make_pool()
        job_id = str(uuid.uuid4())
        conn.fetchrow.return_value = {"attempt": 1, "max_attempts": 3}

        orch = JobOrchestrator(pool)
        await orch.fail_job(job_id, "some error")

        # Should re-queue (second execute call)
        calls = conn.execute.call_args_list
        assert len(calls) == 1
        query = calls[0][0][0]
        assert "status = 'queued'" in query

    @pytest.mark.asyncio
    async def test_fail_job_marks_failed_when_no_retries(self):
        pool, conn = _make_pool()
        job_id = str(uuid.uuid4())
        conn.fetchrow.return_value = {"attempt": 3, "max_attempts": 3}

        orch = JobOrchestrator(pool)
        await orch.fail_job(job_id, "final error")

        calls = conn.execute.call_args_list
        assert len(calls) == 1
        query = calls[0][0][0]
        assert "status = 'failed'" in query


class TestJobOrchestratorHandlers:
    """Tests for handle_job_progress and handle_job_result."""

    @pytest.mark.asyncio
    async def test_handle_job_progress(self):
        pool, conn = _make_pool()
        orch = JobOrchestrator(pool)
        job_id = str(uuid.uuid4())

        msg = NetMessage(
            type=MessageType.JOB_PROGRESS,
            from_node="sat-1",
            payload={"job_id": job_id, "progress": 50, "detail": "halfway"},
        )
        await orch.handle_job_progress(msg, "sat-1")

        conn.execute.assert_called_once()
        call_args = conn.execute.call_args[0]
        assert call_args[1] == 50  # progress clamped to min(50, 100)

    @pytest.mark.asyncio
    async def test_handle_job_result_success(self):
        pool, conn = _make_pool()
        orch = JobOrchestrator(pool)
        job_id = str(uuid.uuid4())

        msg = NetMessage(
            type=MessageType.JOB_RESULT,
            from_node="sat-1",
            payload={"job_id": job_id, "success": True, "data": {"url": "/img.png"}},
        )
        await orch.handle_job_result(msg, "sat-1")

        conn.execute.assert_called_once()
        query = conn.execute.call_args[0][0]
        assert "status = 'completed'" in query

    @pytest.mark.asyncio
    async def test_handle_job_result_failure(self):
        pool, conn = _make_pool()
        conn.fetchrow.return_value = {"attempt": 3, "max_attempts": 3}
        orch = JobOrchestrator(pool)
        job_id = str(uuid.uuid4())

        msg = NetMessage(
            type=MessageType.JOB_RESULT,
            from_node="sat-1",
            payload={"job_id": job_id, "success": False, "error": "GPU OOM"},
        )
        await orch.handle_job_result(msg, "sat-1")

        conn.execute.assert_called_once()
        query = conn.execute.call_args[0][0]
        assert "status = 'failed'" in query


class TestJobRequirements:
    """Tests for JOB_REQUIREMENTS constants."""

    def test_image_generate_needs_gpu(self):
        assert JOB_REQUIREMENTS["image_generate"]["needs_gpu"] is True

    def test_text_inference_needs_ollama(self):
        assert JOB_REQUIREMENTS["text_inference"]["needs_ollama"] is True

    def test_all_types_have_requirements(self):
        for jt in ["image_generate", "video_render", "text_inference",
                    "training_step", "memory_sync", "custom"]:
            assert jt in JOB_REQUIREMENTS
