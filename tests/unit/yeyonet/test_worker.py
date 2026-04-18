import asyncio
from types import SimpleNamespace

import pytest

import src.yeyonet.pipeline_steps as pipeline_steps
import src.yeyonet.worker as worker_module
from src.yeyonet.protocol import MessageType
from src.yeyonet.worker import WorkerExecutor


class FakeImageService:
    def __init__(self, result, delay: float = 0.03):
        self._result = result
        self._delay = delay
        self.calls: list[dict] = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        await asyncio.sleep(self._delay)
        return self._result


@pytest.mark.asyncio
async def test_exec_image_uses_real_image_service(monkeypatch):
    service = FakeImageService(
        SimpleNamespace(
            success=True,
            image_b64="abc123",
            width=512,
            height=512,
            model="runwayml/stable-diffusion-v1-5",
            device="cuda",
            steps_used=12,
            error="",
        )
    )
    progress_states = [
        {"active": False, "step": 0, "total_steps": 0, "percent": 0},
        {"active": True, "step": 4, "total_steps": 12, "percent": 33},
        {"active": True, "step": 12, "total_steps": 12, "percent": 100},
    ]

    def fake_progress():
        if progress_states:
            return progress_states.pop(0)
        return {"active": False, "step": 0, "total_steps": 0, "percent": 0}

    sent_messages = []

    async def send_fn(msg):
        sent_messages.append(msg)
        return True

    monkeypatch.setattr(pipeline_steps, "get_image_service", lambda: service)
    monkeypatch.setattr(pipeline_steps, "get_generation_progress", fake_progress)
    monkeypatch.setattr(pipeline_steps, "IMAGE_PROGRESS_POLL_INTERVAL", 0.01)

    worker = WorkerExecutor("sat-1", send_fn)
    result = await worker._exec_image(
        "job-1",
        {
            "prompt": "a cinematic robot",
            "negative_prompt": "blurry",
            "width": 512,
            "height": 512,
            "steps": 12,
            "guidance_scale": 8.5,
            "seed": 42,
        },
    )

    assert service.calls == [
        {
            "prompt": "a cinematic robot",
            "negative_prompt": "blurry",
            "steps": 12,
            "guidance_scale": 8.5,
            "width": 512,
            "height": 512,
            "seed": 42,
        }
    ]
    assert result == {
        "type": "image",
        "status": "generated",
        "prompt": "a cinematic robot",
        "negative_prompt": "blurry",
        "width": 512,
        "height": 512,
        "steps": 12,
        "guidance_scale": 8.5,
        "seed": 42,
        "model": "runwayml/stable-diffusion-v1-5",
        "device": "cuda",
        "image_b64": "data:image/png;base64,abc123",
    }
    assert len(sent_messages) >= 4
    assert all(msg.type == MessageType.JOB_PROGRESS for msg in sent_messages)
    assert sent_messages[0].payload["detail"] == "Preparando generador de imagen"
    assert sent_messages[-1].payload["progress"] == 100
    assert sent_messages[-1].payload["detail"] == "Imagen generada"


@pytest.mark.asyncio
async def test_exec_image_raises_on_generator_error(monkeypatch):
    service = FakeImageService(
        SimpleNamespace(
            success=False,
            image_b64="",
            width=0,
            height=0,
            model="",
            device="cuda",
            steps_used=0,
            error="GPU OOM",
        ),
        delay=0,
    )

    monkeypatch.setattr(pipeline_steps, "get_image_service", lambda: service)
    monkeypatch.setattr(
        pipeline_steps,
        "get_generation_progress",
        lambda: {"active": False, "step": 0, "total_steps": 0, "percent": 0},
    )
    monkeypatch.setattr(pipeline_steps, "IMAGE_PROGRESS_POLL_INTERVAL", 0)

    worker = WorkerExecutor("sat-1")
    with pytest.raises(RuntimeError, match="GPU OOM"):
        await worker._exec_image("job-1", {"prompt": "a robot"})


@pytest.mark.asyncio
async def test_exec_image_validates_payload(monkeypatch):
    monkeypatch.setattr(pipeline_steps, "get_image_service", lambda: None)

    worker = WorkerExecutor("sat-1")

    with pytest.raises(ValueError, match="prompt is required"):
        await worker._exec_image("job-1", {"prompt": "   "})

    with pytest.raises(ValueError, match="width must be between 256 and 1024"):
        await worker._exec_image("job-1", {"prompt": "a robot", "width": 128})


@pytest.mark.asyncio
async def test_exec_pipeline_step_wraps_step_output():
    sent_messages = []

    async def send_fn(msg):
        sent_messages.append(msg)
        return True

    worker = WorkerExecutor("sat-1", send_fn)
    result = await worker._exec_pipeline_step(
        "job-2",
        {
            "step_type": "prepare_prompt",
            "input": {"prompt": "  a ring pilot  ", "steps": 10},
        },
    )

    assert result["step_type"] == "prepare_prompt"
    assert result["output"]["status"] == "prepared"
    assert result["output"]["prompt"] == "a ring pilot"
    assert sent_messages[0].type == MessageType.JOB_PROGRESS
    assert sent_messages[-1].payload["detail"] == "Prompt listo"
