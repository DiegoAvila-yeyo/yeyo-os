"""
Tests para EmbeddingService — Micro-fase 2.3
El modelo se descarga automáticamente la primera vez (~90MB).
"""

import pytest
import numpy as np
from src.ia.embeddings import EmbeddingService


@pytest.fixture(scope="module")
def embedding_service():
    """Fixture con scope=module para no recargar modelo en cada test."""
    return EmbeddingService()


class TestEmbeddingServiceBasic:
    """Tests básicos sin cargar modelo."""

    def test_default_model_name(self):
        service = EmbeddingService()
        assert service.get_model_name() == "all-MiniLM-L6-v2"

    def test_dimension_is_384(self):
        service = EmbeddingService()
        assert service.get_dimension() == 384

    def test_not_loaded_initially(self):
        service = EmbeddingService()
        assert service.is_loaded() is False

    def test_custom_model_name(self):
        service = EmbeddingService(model_name="custom-model")
        assert service.get_model_name() == "custom-model"


class TestEmbeddingServiceGenerate:
    """Tests que requieren cargar el modelo."""

    def test_generate_returns_list(self, embedding_service):
        result = embedding_service.generate("Hola mundo")
        assert isinstance(result, list)

    def test_generate_correct_dimension(self, embedding_service):
        result = embedding_service.generate("Test de dimensión")
        assert len(result) == 384

    def test_generate_all_floats(self, embedding_service):
        result = embedding_service.generate("Test de tipos")
        assert all(isinstance(x, float) for x in result)

    def test_generate_empty_text_returns_zeros(self, embedding_service):
        result = embedding_service.generate("")
        assert len(result) == 384
        assert all(x == 0.0 for x in result)

    def test_generate_whitespace_returns_zeros(self, embedding_service):
        result = embedding_service.generate("   ")
        assert all(x == 0.0 for x in result)

    def test_model_loaded_after_generate(self, embedding_service):
        embedding_service.generate("trigger load")
        assert embedding_service.is_loaded() is True

    def test_generate_normalized(self, embedding_service):
        """Embeddings normalizados deben tener norma ~1.0."""
        result = embedding_service.generate("Test normalización")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 0.01


class TestEmbeddingServiceBatch:
    """Tests de generación en batch."""

    def test_batch_returns_list_of_lists(self, embedding_service):
        results = embedding_service.generate_batch(["Hola", "Mundo"])
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)

    def test_batch_correct_dimensions(self, embedding_service):
        results = embedding_service.generate_batch(["Uno", "Dos", "Tres"])
        assert all(len(r) == 384 for r in results)

    def test_batch_empty_list(self, embedding_service):
        results = embedding_service.generate_batch([])
        assert results == []

    def test_batch_handles_empty_strings(self, embedding_service):
        results = embedding_service.generate_batch(["Hola", "", "Mundo"])
        assert len(results) == 3
        assert len(results[0]) == 384
        assert all(x == 0.0 for x in results[1])  # vacío = zeros
        assert len(results[2]) == 384


class TestEmbeddingSimilarity:
    """Tests de similitud coseno."""

    def test_identical_texts_high_similarity(self, embedding_service):
        emb1 = embedding_service.generate("Python es genial")
        emb2 = embedding_service.generate("Python es genial")
        sim = embedding_service.similarity(emb1, emb2)
        assert sim > 0.99

    def test_similar_texts_high_similarity(self, embedding_service):
        emb1 = embedding_service.generate("Me gusta programar en Python")
        emb2 = embedding_service.generate("Disfruto codear con Python")
        sim = embedding_service.similarity(emb1, emb2)
        assert sim > 0.5

    def test_different_texts_low_similarity(self, embedding_service):
        emb1 = embedding_service.generate("Programación en Python")
        emb2 = embedding_service.generate("Receta de torta de chocolate")
        sim = embedding_service.similarity(emb1, emb2)
        assert sim < 0.5

    def test_similarity_range(self, embedding_service):
        emb1 = embedding_service.generate("Test rango")
        emb2 = embedding_service.generate("Otro texto")
        sim = embedding_service.similarity(emb1, emb2)
        assert -1.0 <= sim <= 1.0

    def test_similarity_zero_vectors(self, embedding_service):
        zeros = [0.0] * 384
        emb = embedding_service.generate("Algo")
        sim = embedding_service.similarity(zeros, emb)
        assert sim == 0.0

    def test_runs_on_cpu(self, embedding_service):
        """Verificar que el modelo corre en CPU, no GPU."""
        import os
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
