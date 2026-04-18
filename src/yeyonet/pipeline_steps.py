"""
YeyoNet — Definiciones y ejecutores para pasos de pipeline.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Awaitable, Callable

from src.media.image_generator import get_generation_progress, get_image_service

IMAGE_PROGRESS_POLL_INTERVAL = 0.5
IMAGE_PROMPT_RING_FLOW_ID = "image_prompt_ring_v1"
ProgressReporter = Callable[[int, str], Awaitable[None]]

PIPELINE_STEP_REQUIREMENTS: dict[str, dict] = {
    "prepare_prompt": {},
    "generate_image": {"needs_gpu": True, "min_ram_gb": 2.0},
    "store_result": {},
    "publish_result": {},
}

PIPELINE_FLOW_DEFINITIONS: dict[str, list[dict]] = {
    IMAGE_PROMPT_RING_FLOW_ID: [
        {"step_type": "prepare_prompt", "requirements": PIPELINE_STEP_REQUIREMENTS["prepare_prompt"]},
        {"step_type": "generate_image", "requirements": PIPELINE_STEP_REQUIREMENTS["generate_image"]},
        {"step_type": "store_result", "requirements": PIPELINE_STEP_REQUIREMENTS["store_result"]},
        {"step_type": "publish_result", "requirements": PIPELINE_STEP_REQUIREMENTS["publish_result"]},
    ]
}


async def _noop_progress(progress: int, detail: str) -> None:
    return None


def get_pipeline_flow_definition(flow_id: str) -> list[dict]:
    if flow_id not in PIPELINE_FLOW_DEFINITIONS:
        raise ValueError(f"Unsupported pipeline flow: {flow_id}")
    return [dict(step) for step in PIPELINE_FLOW_DEFINITIONS[flow_id]]


def list_pipeline_flows() -> list[dict]:
    return [
        {
            "flow_id": flow_id,
            "step_count": len(steps),
            "steps": [step["step_type"] for step in steps],
        }
        for flow_id, steps in PIPELINE_FLOW_DEFINITIONS.items()
    ]


def get_pipeline_step_requirements(step_type: str) -> dict:
    return dict(PIPELINE_STEP_REQUIREMENTS.get(step_type, {}))


def normalize_image_payload(payload: dict) -> dict:
    prompt = str(payload.get("prompt", "")).strip()
    if not prompt:
        raise ValueError("prompt is required")

    negative_prompt = str(payload.get("negative_prompt", "")).strip()
    width = int(payload.get("width", 512))
    height = int(payload.get("height", 512))
    steps = int(payload.get("steps", 20))
    guidance_scale = float(payload.get("guidance_scale", 7.5))
    seed = payload.get("seed")

    if not 256 <= width <= 1024:
        raise ValueError("width must be between 256 and 1024")
    if not 256 <= height <= 1024:
        raise ValueError("height must be between 256 and 1024")
    if not 1 <= steps <= 100:
        raise ValueError("steps must be between 1 and 100")
    if not 1.0 <= guidance_scale <= 20.0:
        raise ValueError("guidance_scale must be between 1.0 and 20.0")

    if seed is not None:
        seed = int(seed)

    return {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "guidance_scale": guidance_scale,
        "seed": seed,
    }


async def execute_image_generation(
    payload: dict,
    report_progress: ProgressReporter | None = None,
) -> dict:
    reporter = report_progress or _noop_progress
    normalized = normalize_image_payload(payload)
    service = get_image_service()

    await reporter(5, "Preparando generador de imagen")

    generation_task = asyncio.create_task(
        service.generate(
            prompt=normalized["prompt"],
            negative_prompt=normalized["negative_prompt"],
            steps=normalized["steps"],
            guidance_scale=normalized["guidance_scale"],
            width=normalized["width"],
            height=normalized["height"],
            seed=normalized["seed"],
        )
    )

    last_progress = None
    last_detail = None

    while not generation_task.done():
        progress = get_generation_progress()
        if progress.get("active"):
            current_step = progress.get("step", 0)
            total_steps = progress.get("total_steps", normalized["steps"])
            pct = max(10, min(95, int(progress.get("percent", 0))))
            detail = f"Generando imagen ({current_step}/{total_steps})"
        else:
            pct = 10
            detail = "Cargando modelo"

        if pct != last_progress or detail != last_detail:
            await reporter(pct, detail)
            last_progress = pct
            last_detail = detail

        await asyncio.sleep(IMAGE_PROGRESS_POLL_INTERVAL)

    result = await generation_task
    if not result.success:
        raise RuntimeError(result.error or "Image generation failed")

    await reporter(100, "Imagen generada")
    return {
        "type": "image",
        "status": "generated",
        "prompt": normalized["prompt"],
        "negative_prompt": normalized["negative_prompt"],
        "width": result.width,
        "height": result.height,
        "steps": result.steps_used,
        "guidance_scale": normalized["guidance_scale"],
        "seed": normalized["seed"],
        "model": result.model,
        "device": result.device,
        "image_b64": f"data:image/png;base64,{result.image_b64}",
    }


class PipelineStepExecutor:
    """Ejecutor local de pasos unitarios del pipeline circular."""

    def __init__(self):
        self._executors: dict[str, Callable[[dict, ProgressReporter], Awaitable[dict]]] = {
            "prepare_prompt": self._exec_prepare_prompt,
            "generate_image": self._exec_generate_image,
            "store_result": self._exec_store_result,
            "publish_result": self._exec_publish_result,
        }

    async def execute(
        self,
        step_type: str,
        input_payload: dict,
        report_progress: ProgressReporter | None = None,
    ) -> dict:
        if step_type not in self._executors:
            raise ValueError(f"Unsupported pipeline step: {step_type}")
        reporter = report_progress or _noop_progress
        return await self._executors[step_type](input_payload, reporter)

    async def _exec_prepare_prompt(self, input_payload: dict, report_progress: ProgressReporter) -> dict:
        await report_progress(25, "Normalizando prompt")
        normalized = normalize_image_payload(input_payload)
        await report_progress(100, "Prompt listo")
        return {
            "type": "prepared_prompt",
            "status": "prepared",
            **normalized,
        }

    async def _exec_generate_image(self, input_payload: dict, report_progress: ProgressReporter) -> dict:
        return await execute_image_generation(input_payload, report_progress)

    async def _exec_store_result(self, input_payload: dict, report_progress: ProgressReporter) -> dict:
        image_b64 = str(input_payload.get("image_b64", "")).strip()
        if not image_b64:
            raise ValueError("image_b64 is required")

        await report_progress(40, "Preparando artefacto final")
        await report_progress(100, "Resultado persistible listo")
        return {
            "type": "stored_image",
            "status": "stored",
            "artifact_kind": "image",
            "prompt": input_payload.get("prompt", ""),
            "negative_prompt": input_payload.get("negative_prompt", ""),
            "width": input_payload.get("width"),
            "height": input_payload.get("height"),
            "steps": input_payload.get("steps"),
            "guidance_scale": input_payload.get("guidance_scale"),
            "seed": input_payload.get("seed"),
            "model": input_payload.get("model"),
            "device": input_payload.get("device"),
            "image_b64": image_b64,
            "stored_at": datetime.now(UTC).isoformat(),
            "content_bytes_estimate": max(0, (len(image_b64) * 3) // 4),
        }

    async def _exec_publish_result(self, input_payload: dict, report_progress: ProgressReporter) -> dict:
        image_b64 = str(input_payload.get("image_b64", "")).strip()
        if not image_b64:
            raise ValueError("image_b64 is required")

        await report_progress(50, "Empaquetando respuesta final")
        await report_progress(100, "Respuesta publicada")
        return {
            "status": "completed",
            "type": "image",
            "prompt": input_payload.get("prompt", ""),
            "negative_prompt": input_payload.get("negative_prompt", ""),
            "width": input_payload.get("width"),
            "height": input_payload.get("height"),
            "steps": input_payload.get("steps"),
            "guidance_scale": input_payload.get("guidance_scale"),
            "seed": input_payload.get("seed"),
            "model": input_payload.get("model"),
            "device": input_payload.get("device"),
            "artifact_kind": input_payload.get("artifact_kind", "image"),
            "image_b64": image_b64,
            "published_at": datetime.now(UTC).isoformat(),
            "published_by_pipeline": True,
        }
