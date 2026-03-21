"""
YeyoOS — EmbeddingService (Pipeline de Embeddings en CPU)
Micro-fase 2.3 — Capa 2: Cerebro

Genera embeddings vectoriales con sentence-transformers.
IMPORTANTE: Corre en CPU. La GPU es exclusiva para Ollama/SD.
Modelo: all-MiniLM-L6-v2 → 384 dimensiones.
"""

import logging
import os
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger("yeyoos.embeddings")

# Forzar CPU para sentence-transformers
os.environ["CUDA_VISIBLE_DEVICES"] = ""


class EmbeddingService:
    """
    Servicio de generación de embeddings para búsqueda semántica.
    Usa sentence-transformers en CPU (GPU reservada para Ollama).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.dimension: int = 384  # Dimensión fija del modelo all-MiniLM-L6-v2
        self._loaded = False

    def _ensure_loaded(self):
        """Carga el modelo lazy (solo cuando se necesita por primera vez)."""
        if not self._loaded:
            logger.info(f"Cargando modelo de embeddings: {self.model_name} (CPU)")
            self.model = SentenceTransformer(
                self.model_name,
                device="cpu",
            )
            self._loaded = True
            logger.info(f"Modelo cargado: {self.model_name} ({self.dimension}d)")

    def generate(self, text: str) -> list[float]:
        """
        Genera embedding para un texto.
        Retorna vector de 384 dimensiones normalizado.
        Textos vacíos retornan vector de zeros.
        """
        if not text or not text.strip():
            return [0.0] * self.dimension

        self._ensure_loaded()
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding.tolist()

    def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Genera embeddings para múltiples textos en batch.
        Más eficiente que llamar generate() individualmente.
        Textos vacíos retornan vector de zeros en su posición.
        """
        if not texts:
            return []

        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return [[0.0] * self.dimension for _ in texts]

        self._ensure_loaded()
        embeddings = self.model.encode(
            valid_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )

        result = [[0.0] * self.dimension for _ in texts]
        for idx, emb in zip(valid_indices, embeddings):
            result[idx] = emb.tolist()

        return result

    def similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """
        Calcula similitud coseno entre dos embeddings.
        Retorna valor entre -1.0 y 1.0.
        Retorna 0.0 si alguno de los vectores es cero.
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def get_dimension(self) -> int:
        """Retorna la dimensión del embedding."""
        return self.dimension

    def get_model_name(self) -> str:
        """Retorna el nombre del modelo de embeddings."""
        return self.model_name

    def is_loaded(self) -> bool:
        """Verifica si el modelo está cargado en memoria."""
        return self._loaded
