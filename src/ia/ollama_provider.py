"""
YeyoOS — OllamaProvider (Adaptador Hexagonal)
Micro-fase 1.1 — Capa 1: Esqueleto

Implementación concreta de IAProvider para Ollama.
Traduce las llamadas abstractas a la API REST de Ollama.
"""

import time
import os
import json
from typing import AsyncIterator

import httpx

from .interfaces import IAProvider, IAMessage, IAResponse


class OllamaProvider(IAProvider):
    """Adaptador concreto para Ollama local."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        embedding_model: str | None = None,
        timeout: float = 120.0,
    ):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        self.embedding_model = embedding_model or os.getenv(
            "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"
        )
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
    ) -> IAResponse:
        """Genera respuesta usando /api/generate con GPU scheduling."""
        from src.core.gpu_scheduler import GPUScheduler, GPUPriority, GPUTask

        # Create GPU task
        task = GPUTask(
            name="ollama-generate",
            priority=GPUPriority.P2_BACKGROUND,
            vram_needed_mb=1800,
        )

        scheduler = await GPUScheduler.get_instance()
        task_id = await scheduler.submit(task)

        try:
            start = time.monotonic()
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": 512},
            }
            if system:
                payload["system"] = system

            response = await self.client.post(
                f"{self.host}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            latency = (time.monotonic() - start) * 1000
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            return IAResponse(
                content=data.get("response", ""),
                model=self.model,
                tokens_used=tokens,
                latency_ms=round(latency, 2),
            )
        finally:
            await scheduler.release(task_id, status="completed")

    async def chat(
        self,
        messages: list[IAMessage],
        temperature: float = 0.7,
    ) -> IAResponse:
        """Genera respuesta usando /api/chat con historial y GPU scheduling."""
        from src.core.gpu_scheduler import GPUScheduler, GPUPriority, GPUTask

        # Create GPU task
        task = GPUTask(
            name="ollama-chat",
            priority=GPUPriority.P2_BACKGROUND,
            vram_needed_mb=1800,
        )

        scheduler = await GPUScheduler.get_instance()
        task_id = await scheduler.submit(task)

        try:
            start = time.monotonic()
            formatted_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]

            response = await self.client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": formatted_messages,
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": 512},
                },
            )
            response.raise_for_status()
            data = response.json()

            latency = (time.monotonic() - start) * 1000
            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)

            return IAResponse(
                content=data.get("message", {}).get("content", ""),
                model=self.model,
                tokens_used=tokens,
                latency_ms=round(latency, 2),
            )
        finally:
            await scheduler.release(task_id, status="completed")

    async def chat_stream(
        self,
        messages: list[IAMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Genera respuesta en streaming con GPU scheduling."""
        from src.core.gpu_scheduler import GPUScheduler, GPUPriority, GPUTask

        task = GPUTask(
            name="ollama-chat-stream",
            priority=GPUPriority.P2_BACKGROUND,
            vram_needed_mb=1800,
        )

        scheduler = await GPUScheduler.get_instance()
        task_id = await scheduler.submit(task)

        try:
            formatted_messages = [
                {"role": msg.role, "content": msg.content} for msg in messages
            ]

            async with self.client.stream(
                "POST",
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": formatted_messages,
                    "stream": True,
                    "options": {"temperature": temperature, "num_predict": 512},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
        finally:
            await scheduler.release(task_id, status="completed")

    async def get_embedding(self, text: str) -> list[float]:
        """Genera embedding usando /api/embed."""
        response = await self.client.post(
            f"{self.host}/api/embed",
            json={
                "model": self.embedding_model,
                "input": text,
            },
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings", [[]])
        return embeddings[0] if embeddings else []

    async def health_check(self) -> bool:
        """Verifica que Ollama está corriendo consultando /api/tags."""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def get_model_name(self) -> str:
        """Retorna el nombre del modelo configurado."""
        return self.model

    def get_max_tokens(self) -> int:
        """Retorna el budget máximo de tokens para YeyoOS."""
        return 4000

    async def close(self):
        """Cierra el cliente HTTP."""
        await self.client.aclose()
