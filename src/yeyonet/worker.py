"""
YeyoNet — WorkerExecutor.
Ejecuta trabajos asignados en el nodo local.
Cada tipo de job tiene su propia estrategia de ejecución.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from typing import Callable, Awaitable

from src.media.image_generator import get_generation_progress, get_image_service

from .models import JobType
from .protocol import MessageType, NetMessage, make_job_progress, make_job_result

logger = logging.getLogger("yeyonet.worker")

IMAGE_PROGRESS_POLL_INTERVAL = 0.5


class WorkerExecutor:
    """
    Ejecuta jobs localmente y reporta progreso/resultado.
    Se registra como handler en YeyoNetClient para recibir jobs asignados.
    """

    def __init__(self, node_id: str, send_fn: Callable[[NetMessage], Awaitable[bool]] | None = None):
        self._node_id = node_id
        self._send = send_fn
        self._active_jobs: dict[str, asyncio.Task] = {}
        self._executors: dict[str, Callable] = {
            "image_generate": self._exec_image,
            "video_render": self._exec_video,
            "text_inference": self._exec_text,
            "training_step": self._exec_training,
            "custom": self._exec_custom,
        }

    @property
    def active_count(self) -> int:
        return len(self._active_jobs)

    def set_send_fn(self, fn: Callable[[NetMessage], Awaitable[bool]]) -> None:
        self._send = fn

    async def handle_job_assign(self, msg: NetMessage) -> None:
        """Handler para JOB_ASSIGN — recibido del Central."""
        job_id = msg.payload.get("job_id", "")
        job_type = msg.payload.get("job_type", "")

        if job_type not in self._executors:
            await self._report_result(job_id, False, error=f"Unsupported job type: {job_type}")
            return

        logger.info(f"[worker] Job recibido: {job_id[:8]}... tipo={job_type}")
        task = asyncio.create_task(self._run_job(job_id, job_type, msg.payload))
        self._active_jobs[job_id] = task

    async def handle_job_cancel(self, msg: NetMessage) -> None:
        """Handler para JOB_CANCEL."""
        job_id = msg.payload.get("job_id", "")
        task = self._active_jobs.pop(job_id, None)
        if task:
            task.cancel()
            logger.info(f"[worker] Job cancelado: {job_id[:8]}...")

    async def _run_job(self, job_id: str, job_type: str, payload: dict) -> None:
        """Ejecuta un job con manejo de errores."""
        try:
            executor = self._executors[job_type]
            result = await executor(job_id, payload)
            await self._report_result(job_id, True, data=result)
        except asyncio.CancelledError:
            logger.info(f"[worker] Job {job_id[:8]}... cancelado")
        except Exception as e:
            logger.error(f"[worker] Job {job_id[:8]}... error: {e}")
            await self._report_result(job_id, False, error=str(e))
        finally:
            self._active_jobs.pop(job_id, None)

    async def _report_progress(self, job_id: str, progress: int, detail: str = "") -> None:
        if self._send:
            await self._send(make_job_progress(self._node_id, job_id, progress, detail))

    async def _report_result(self, job_id: str, success: bool, data: dict | None = None, error: str = "") -> None:
        if self._send:
            await self._send(make_job_result(self._node_id, job_id, success, data, error))

    # ─── Executors por tipo ──────────────────────────────────

    async def _exec_image(self, job_id: str, payload: dict) -> dict:
        """Genera una imagen real usando el backend local de Stable Diffusion."""
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

        service = get_image_service()
        await self._report_progress(job_id, 5, "Preparando generador de imagen")

        generation_task = asyncio.create_task(
            service.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                steps=steps,
                guidance_scale=guidance_scale,
                width=width,
                height=height,
                seed=seed,
            )
        )

        last_progress = None
        last_detail = None
        while not generation_task.done():
            progress = get_generation_progress()
            if progress.get("active"):
                current_step = progress.get("step", 0)
                total_steps = progress.get("total_steps", steps)
                pct = max(10, min(95, int(progress.get("percent", 0))))
                detail = f"Generando imagen ({current_step}/{total_steps})"
            else:
                pct = 10
                detail = "Cargando modelo"

            if pct != last_progress or detail != last_detail:
                await self._report_progress(job_id, pct, detail)
                last_progress = pct
                last_detail = detail

            await asyncio.sleep(IMAGE_PROGRESS_POLL_INTERVAL)

        result = await generation_task
        if not result.success:
            raise RuntimeError(result.error or "Image generation failed")

        await self._report_progress(job_id, 100, "Imagen generada")
        return {
            "type": "image",
            "status": "generated",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": result.width,
            "height": result.height,
            "steps": result.steps_used,
            "guidance_scale": guidance_scale,
            "seed": seed,
            "model": result.model,
            "device": result.device,
            "image_b64": f"data:image/png;base64,{result.image_b64}",
        }

    async def _exec_video(self, job_id: str, payload: dict) -> dict:
        """Renderiza un chunk de video con FFmpeg."""
        input_path = payload.get("input_path", "")
        output_path = payload.get("output_path", "")
        chunk_start = payload.get("chunk_start_s", 0)
        chunk_end = payload.get("chunk_end_s", 10)
        effects = payload.get("effects", [])

        await self._report_progress(job_id, 10, "Preparando render")

        if not input_path or not os.path.exists(input_path):
            # Placeholder for when actual video files are involved
            duration = chunk_end - chunk_start
            await self._report_progress(job_id, 50, f"Renderizando {duration}s")
            await asyncio.sleep(1)  # Simulated
            await self._report_progress(job_id, 90, "Finalizando")

            return {
                "type": "video_chunk",
                "chunk_start_s": chunk_start,
                "chunk_end_s": chunk_end,
                "output_path": output_path or f"/tmp/chunk_{chunk_start}_{chunk_end}.mp4",
                "status": "placeholder_rendered",
            }

        # Real FFmpeg render
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(chunk_start),
            "-to", str(chunk_end),
            "-i", input_path,
        ]
        if not output_path:
            output_path = tempfile.mktemp(suffix=".mp4")
        cmd.extend(["-c:v", "libx264", "-preset", "fast", output_path])

        await self._report_progress(job_id, 30, "FFmpeg renderizando")
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await proc.communicate()
        await self._report_progress(job_id, 90, "Render completo")

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()[:200]}")

        return {
            "type": "video_chunk",
            "chunk_start_s": chunk_start,
            "chunk_end_s": chunk_end,
            "output_path": output_path,
            "status": "rendered",
        }

    async def _exec_text(self, job_id: str, payload: dict) -> dict:
        """Ejecuta inferencia de texto via Ollama local."""
        prompt = payload.get("prompt", "")
        system = payload.get("system", "")
        model = payload.get("model", "qwen2.5:3b")
        temperature = payload.get("temperature", 0.7)

        await self._report_progress(job_id, 10, f"Inferencia con {model}")

        try:
            import httpx
            ollama_host = payload.get("ollama_host", "http://localhost:11434")
            async with httpx.AsyncClient(timeout=120.0) as client:
                body = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                }
                if system:
                    body["system"] = system

                await self._report_progress(job_id, 30, "Generando respuesta")
                resp = await client.post(f"{ollama_host}/api/generate", json=body)
                data = resp.json()

                return {
                    "type": "text",
                    "response": data.get("response", ""),
                    "model": model,
                    "tokens": data.get("eval_count", 0),
                    "duration_ms": data.get("total_duration", 0) // 1_000_000,
                }
        except Exception as e:
            raise RuntimeError(f"Ollama inference failed: {e}")

    async def _exec_training(self, job_id: str, payload: dict) -> dict:
        """Ejecuta un paso de entrenamiento LoRA (placeholder)."""
        await self._report_progress(job_id, 10, "Preparando training")
        # TODO: Integrar con Unsloth/Axolotl
        await asyncio.sleep(2)
        await self._report_progress(job_id, 50, "Training en progreso")
        await asyncio.sleep(2)
        return {
            "type": "training",
            "status": "placeholder_completed",
            "loss": 0.05,
        }

    async def _exec_custom(self, job_id: str, payload: dict) -> dict:
        """Ejecuta un comando custom."""
        command = payload.get("command", "")
        if not command:
            raise ValueError("No command specified")

        await self._report_progress(job_id, 10, f"Ejecutando: {command[:50]}")
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return {
            "type": "custom",
            "returncode": proc.returncode,
            "stdout": stdout.decode()[:5000],
            "stderr": stderr.decode()[:2000],
        }
