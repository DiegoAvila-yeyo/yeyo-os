"""Tests para GPU Scheduler — Micro-fase 1.8"""

import pytest
import asyncio
from src.core.gpu_scheduler import GPUScheduler, GPUPriority, GPUTask


@pytest.fixture
def scheduler():
    return GPUScheduler(total_vram_mb=3072, compositor_reserved_mb=200)


class TestGPUPriority:
    def test_priority_order(self):
        assert GPUPriority.P0_COMPOSITOR < GPUPriority.P1_USER
        assert GPUPriority.P1_USER < GPUPriority.P2_BACKGROUND
        assert GPUPriority.P2_BACKGROUND < GPUPriority.P3_IDLE

    def test_four_priority_levels(self):
        assert len(GPUPriority) == 4

    def test_compositor_is_highest(self):
        assert GPUPriority.P0_COMPOSITOR == 0

    def test_idle_is_lowest(self):
        assert GPUPriority.P3_IDLE == 3


class TestGPUTask:
    def test_create_task(self):
        task = GPUTask(name="ollama-inference", priority=GPUPriority.P1_USER, vram_needed_mb=1800)
        assert task.name == "ollama-inference"
        assert task.priority == GPUPriority.P1_USER
        assert task.vram_needed_mb == 1800
        assert task.status == "pending"

    def test_task_has_unique_id(self):
        t1 = GPUTask(name="task1")
        t2 = GPUTask(name="task2")
        assert t1.id != t2.id

    def test_task_ordering(self):
        t_user = GPUTask(priority=GPUPriority.P1_USER)
        t_bg = GPUTask(priority=GPUPriority.P2_BACKGROUND)
        assert t_user < t_bg


class TestGPUSchedulerBasic:
    def test_default_vram(self, scheduler):
        assert scheduler.total_vram_mb == 3072

    def test_compositor_reserved(self, scheduler):
        assert scheduler.compositor_reserved_mb == 200

    def test_available_vram(self, scheduler):
        assert scheduler.available_vram_mb == 2872

    def test_initial_free_vram(self, scheduler):
        assert scheduler.free_vram_mb == 2872

    def test_initial_no_tasks(self, scheduler):
        assert scheduler.get_task_count() == 0

    def test_get_status(self, scheduler):
        status = scheduler.get_status()
        assert status["total_vram_mb"] == 3072
        assert status["compositor_reserved_mb"] == 200
        assert status["available_vram_mb"] == 2872
        assert status["used_vram_mb"] == 0
        assert status["free_vram_mb"] == 2872
        assert status["current_tasks"] == []
        assert status["queue_size"] == 0


class TestGPUSchedulerSubmit:
    @pytest.mark.asyncio
    async def test_submit_task_returns_id(self, scheduler):
        task = GPUTask(name="test", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=500)
        task_id = await scheduler.submit(task)
        assert task_id == task.id

    @pytest.mark.asyncio
    async def test_submit_task_uses_vram(self, scheduler):
        task = GPUTask(name="test", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=1000)
        await scheduler.submit(task)
        assert scheduler._used_vram_mb == 1000
        assert scheduler.free_vram_mb == 1872

    @pytest.mark.asyncio
    async def test_submit_task_is_running(self, scheduler):
        task = GPUTask(name="test", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=500)
        await scheduler.submit(task)
        assert task.status == "running"

    @pytest.mark.asyncio
    async def test_submit_exceeds_total_raises(self, scheduler):
        task = GPUTask(name="impossible", priority=GPUPriority.P1_USER, vram_needed_mb=5000)
        with pytest.raises(ValueError):
            await scheduler.submit(task)

    @pytest.mark.asyncio
    async def test_release_frees_vram(self, scheduler):
        task = GPUTask(name="test", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=1000)
        task_id = await scheduler.submit(task)
        await scheduler.release(task_id)
        assert scheduler.free_vram_mb == 2872
        assert scheduler.get_task_count() == 0


class TestGPUSchedulerCompositor:
    @pytest.mark.asyncio
    async def test_compositor_vram_always_reserved(self, scheduler):
        task = GPUTask(name="big-task", priority=GPUPriority.P1_USER, vram_needed_mb=2872)
        await scheduler.submit(task)
        assert scheduler._used_vram_mb == 2872
        assert scheduler.total_vram_mb - scheduler._used_vram_mb - scheduler.compositor_reserved_mb >= 0

    @pytest.mark.asyncio
    async def test_cannot_use_compositor_vram(self, scheduler):
        task = GPUTask(name="too-big", priority=GPUPriority.P1_USER, vram_needed_mb=2873)
        with pytest.raises(ValueError):
            await scheduler.submit(task)


class TestGPUSchedulerPreemption:
    @pytest.mark.asyncio
    async def test_p1_preempts_p2(self, scheduler):
        bg_task = GPUTask(name="embeddings", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=1800)
        await scheduler.submit(bg_task)
        assert bg_task.status == "running"

        user_task = GPUTask(name="chat", priority=GPUPriority.P1_USER, vram_needed_mb=1800)
        await scheduler.submit(user_task)
        assert user_task.status == "running"
        assert bg_task.status == "preempted"

    @pytest.mark.asyncio
    async def test_p1_preempts_p3(self, scheduler):
        idle_task = GPUTask(name="optimization", priority=GPUPriority.P3_IDLE, vram_needed_mb=1500)
        await scheduler.submit(idle_task)

        user_task = GPUTask(name="chat", priority=GPUPriority.P1_USER, vram_needed_mb=1800)
        await scheduler.submit(user_task)
        assert user_task.status == "running"
        assert idle_task.status == "preempted"

    @pytest.mark.asyncio
    async def test_p2_preempts_p3(self, scheduler):
        idle_task = GPUTask(name="optimization", priority=GPUPriority.P3_IDLE, vram_needed_mb=2000)
        await scheduler.submit(idle_task)

        bg_task = GPUTask(name="embeddings", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=1800)
        await scheduler.submit(bg_task)
        assert bg_task.status == "running"
        assert idle_task.status == "preempted"

    @pytest.mark.asyncio
    async def test_p3_never_preempts(self, scheduler):
        bg_task = GPUTask(name="embeddings", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=2000)
        await scheduler.submit(bg_task)

        idle_task = GPUTask(name="optimization", priority=GPUPriority.P3_IDLE, vram_needed_mb=1500)
        await scheduler.submit(idle_task)
        assert bg_task.status == "running"
        assert idle_task.status == "pending"

    @pytest.mark.asyncio
    async def test_same_priority_no_preemption(self, scheduler):
        task1 = GPUTask(name="task1", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=2000)
        await scheduler.submit(task1)

        task2 = GPUTask(name="task2", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=1500)
        await scheduler.submit(task2)
        assert task1.status == "running"
        assert task2.status == "pending"


class TestGPUSchedulerRealScenarios:
    @pytest.mark.asyncio
    async def test_ollama_fits(self, scheduler):
        task = GPUTask(name="ollama-qwen", priority=GPUPriority.P1_USER, vram_needed_mb=1800)
        await scheduler.submit(task)
        assert task.status == "running"
        assert scheduler.free_vram_mb == 1072

    @pytest.mark.asyncio
    async def test_sd_fits(self, scheduler):
        task = GPUTask(name="sd-1.5", priority=GPUPriority.P1_USER, vram_needed_mb=2500)
        await scheduler.submit(task)
        assert task.status == "running"
        assert scheduler.free_vram_mb == 372

    @pytest.mark.asyncio
    async def test_ollama_plus_sd_impossible(self, scheduler):
        ollama = GPUTask(name="ollama", priority=GPUPriority.P1_USER, vram_needed_mb=1800)
        await scheduler.submit(ollama)

        sd = GPUTask(name="sd-1.5", priority=GPUPriority.P1_USER, vram_needed_mb=2500)
        await scheduler.submit(sd)
        assert sd.status == "pending"
        assert scheduler.get_task_count() == 1

    @pytest.mark.asyncio
    async def test_multiple_small_tasks(self, scheduler):
        tasks = [
            GPUTask(name=f"small-{i}", priority=GPUPriority.P2_BACKGROUND, vram_needed_mb=500)
            for i in range(5)
        ]
        for task in tasks:
            await scheduler.submit(task)
        running = [t for t in tasks if t.status == "running"]
        assert len(running) == 5

    @pytest.mark.asyncio
    async def test_release_processes_queue(self, scheduler):
        big_task = GPUTask(name="big", priority=GPUPriority.P1_USER, vram_needed_mb=2500)
        await scheduler.submit(big_task)

        small_task = GPUTask(name="small", priority=GPUPriority.P1_USER, vram_needed_mb=1000)
        await scheduler.submit(small_task)
        assert small_task.status == "pending"

        await scheduler.release(big_task.id)
        assert small_task.status == "running"
