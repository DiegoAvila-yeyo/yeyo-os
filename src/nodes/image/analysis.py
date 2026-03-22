"""
YeyoOS — Image Analysis with LLaVA
Micro-fase 5.3 — Capa 5: Órganos

Análisis de imágenes usando LLaVA (modelo de visión) via Ollama.
Plan B: llava:3b si VRAM insuficiente para 7b.
"""

import base64
import httpx
from typing import Optional


# Modelos de visión en orden de preferencia
VISION_MODELS = [
    {"name": "llava:7b", "vram_mb": 2800},
    {"name": "llava:3b", "vram_mb": 1500},
]

OLLAMA_BASE_URL = "http://localhost:11434"


class ImageAnalysisService:
    """Servicio de análisis de imágenes con LLaVA."""

    def __init__(self, ollama_url: str = OLLAMA_BASE_URL):
        self._ollama_url = ollama_url
        self._active_model: Optional[str] = None

    async def analyze(
        self, image_data: bytes, question: str = "Describe esta imagen en detalle."
    ) -> dict:
        """
        Analiza una imagen con LLaVA.
        Intenta llava:7b primero, fallback a llava:3b.
        """
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        for model_info in VISION_MODELS:
            model_name = model_info["name"]
            try:
                result = await self._query_llava(
                    model=model_name,
                    image_b64=image_b64,
                    prompt=question,
                )
                self._active_model = model_name
                return {
                    "description": result,
                    "model_used": model_name,
                    "question": question,
                }
            except Exception:
                continue

        return {
            "error": "No se pudo analizar la imagen. Ningún modelo de visión disponible.",
            "fallback": "text_only",
        }

    async def _query_llava(
        self, model: str, image_b64: str, prompt: str
    ) -> str:
        """Consulta LLaVA via Ollama API."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def get_available_model(self) -> Optional[str]:
        """Retorna el modelo de visión disponible."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self._ollama_url}/api/tags")
                response.raise_for_status()
                models = [m["name"] for m in response.json().get("models", [])]
                for model_info in VISION_MODELS:
                    if model_info["name"] in models:
                        return model_info["name"]
            except Exception:
                pass
        return None
