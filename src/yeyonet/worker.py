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

from . import pipeline_steps
from .protocol import MessageType, NetMessage, make_job_progress, make_job_result

logger = logging.getLogger("yeyonet.worker")


class WorkerExecutor:
    """
    Ejecuta jobs localmente y reporta progreso/resultado.
    Se registra como handler en YeyoNetClient para recibir jobs asignados.
    """

    def __init__(self, node_id: str, send_fn: Callable[[NetMessage], Awaitable[bool]] | None = None):
        self._node_id = node_id
        self._send = send_fn
        self._active_jobs: dict[str, asyncio.Task] = {}
        self._pipeline_step_executor = pipeline_steps.PipelineStepExecutor()
        self._executors: dict[str, Callable] = {
            "image_generate": self._exec_image,
            "video_render": self._exec_video,
            "text_inference": self._exec_text,
            "training_step": self._exec_training,
            "custom": self._exec_custom,
            "pipeline_step": self._exec_pipeline_step,
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
        return await pipeline_steps.execute_image_generation(
            payload,
            lambda progress, detail: self._report_progress(job_id, progress, detail),
        )

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

    async def _exec_pipeline_step(self, job_id: str, payload: dict) -> dict:
        """Ejecuta un paso unitario del pipeline circular."""
        step_type = str(payload.get("step_type", "")).strip()
        if not step_type:
            raise ValueError("step_type is required")

        input_payload = payload.get("input")
        if not isinstance(input_payload, dict):
            raise ValueError("input must be an object")

        result = await self._pipeline_step_executor.execute(
            step_type=step_type,
            input_payload=input_payload,
            report_progress=lambda progress, detail: self._report_progress(job_id, progress, detail),
        )
        return {"step_type": step_type, "output": result}
