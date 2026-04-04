"""
YeyoOS — OllamaEmbeddingService (Adaptador ligero para dev)

Genera embeddings usando la API de Ollama en lugar de sentence-transformers.
Compatible con la interfaz de EmbeddingService para inyección sin cambios.
"""

import logging
from typing import Optional

import httpx

logger = logging.getLogger("yeyoos.embeddings.ollama")


class OllamaEmbeddingService:
    """
    Servicio de embeddings que usa Ollama /api/embed.
    Drop-in replacement para EmbeddingService cuando
    sentence-transformers no está disponible.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        timeout: float = 30.0,
    ):
        self.host = host
        self.model = model
        self.timeout = timeout
        self._dimension: Optional[int] = None
        self._client = httpx.Client(timeout=self.timeout)

    @property
    def dimension(self) -> int:
        return self._dimension or 768

    def generate(self, text: str) -> list[float]:
        """Genera embedding para un texto via Ollama."""
        if not text or not text.strip():
            return [0.0] * self.dimension

        try:
            response = self._client.post(
                f"{self.host}/api/embed",
                json={"model": self.model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [[]])
            if embeddings and embeddings[0]:
                result = embeddings[0]
                if self._dimension is None:
                    self._dimension = len(result)
                return result
            return [0.0] * self.dimension
        except Exception as e:
            logger.warning(f"Error generando embedding: {e}")
            return [0.0] * self.dimension

    def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para múltiples textos."""
        return [self.generate(t) for t in texts]

    def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Calcula similitud coseno entre dos embeddings."""
        if not embedding1 or not embedding2:
            return 0.0
        dot = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a * a for a in embedding1) ** 0.5
        norm2 = sum(b * b for b in embedding2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return self.model

    def is_loaded(self) -> bool:
        return True
