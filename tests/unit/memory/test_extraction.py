"""
Tests para MemoryExtractor — Micro-fase 2.9
Tests unitarios con mock de IAProvider.
"""

import pytest
import json
from unittest.mock import AsyncMock
from src.memory.extraction import (
    MemoryExtractor,
    MIN_TOKENS_FOR_EXTRACTION,
)
from src.ia.interfaces import IAProvider, IAResponse


@pytest.fixture
def mock_ia():
    return AsyncMock(spec=IAProvider)


@pytest.fixture
def extractor(mock_ia):
    return MemoryExtractor(ia_provider=mock_ia)


class TestShouldExtract:
    """Tests de la heurística should_extract."""

    @pytest.mark.asyncio
    async def test_empty_message(self, extractor):
        assert await extractor.should_extract("") is False

    @pytest.mark.asyncio
    async def test_none_message(self, extractor):
        assert await extractor.should_extract(None) is False

    @pytest.mark.asyncio
    async def test_short_message(self, extractor):
        """Mensajes < 20 tokens no se extraen."""
        assert await extractor.should_extract("Hola") is False

    @pytest.mark.asyncio
    async def test_preference_detected(self, extractor):
        assert await extractor.should_extract(
            "Me gusta programar en Python porque es muy elegante y productivo"
        ) is True

    @pytest.mark.asyncio
    async def test_fact_detected(self, extractor):
        assert await extractor.should_extract(
            "Mi nombre es Diego y trabajo en una empresa de tecnología"
        ) is True

    @pytest.mark.asyncio
    async def test_correction_detected(self, extractor):
        assert await extractor.should_extract(
            "No, en realidad mi nombre no es Juan, es Diego. Siempre lo confunden."
        ) is True

    @pytest.mark.asyncio
    async def test_long_message_always_extracted(self, extractor):
        """Mensajes >50 tokens siempre se intentan extraer."""
        long_msg = "palabra " * 60  # ~60 tokens
        assert await extractor.should_extract(long_msg) is True

    @pytest.mark.asyncio
    async def test_min_tokens_threshold(self):
        assert MIN_TOKENS_FOR_EXTRACTION == 20


class TestExtractFromMessage:
    """Tests de extracción completa."""

    @pytest.mark.asyncio
    async def test_extracts_preference(self, extractor, mock_ia):
        mock_ia.chat.return_value = IAResponse(
            content='[{"content": "Prefiere Python", "type": "preference", "metadata": {}}]',
            model="qwen2.5:3b",
            tokens_used=20,
            latency_ms=100.0,
        )
        result = await extractor.extract_from_message(
            "Me gusta mucho programar en Python, es mi lenguaje favorito para todo",
            "¡Genial! Python es muy versátil.",
        )
        assert len(result) == 1
        assert result[0]["type"] == "preference"
        assert "Python" in result[0]["content"]

    @pytest.mark.asyncio
    async def test_extracts_fact(self, extractor, mock_ia):
        mock_ia.chat.return_value = IAResponse(
            content='[{"content": "Se llama Diego", "type": "fact", "metadata": {}}]',
            model="qwen2.5:3b",
            tokens_used=15,
            latency_ms=100.0,
        )
        result = await extractor.extract_from_message(
            "Mi nombre es Diego y soy programador senior en una startup",
            "¡Hola Diego! Encantado de conocerte.",
        )
        assert len(result) == 1
        assert result[0]["type"] == "fact"

    @pytest.mark.asyncio
    async def test_extracts_correction(self, extractor, mock_ia):
        mock_ia.chat.return_value = IAResponse(
            content='[{"content": "Su nombre es Diego, no Juan", "type": "correction", "metadata": {}}]',
            model="qwen2.5:3b",
            tokens_used=20,
            latency_ms=100.0,
        )
        result = await extractor.extract_from_message(
            "No, en realidad mi nombre no es Juan, es Diego. Por favor recuérdalo.",
            "Disculpa, Diego. Lo tendré en cuenta.",
        )
        assert len(result) == 1
        assert result[0]["type"] == "correction"

    @pytest.mark.asyncio
    async def test_short_message_returns_empty(self, extractor):
        result = await extractor.extract_from_message("OK", "OK")
        assert result == []

    @pytest.mark.asyncio
    async def test_no_memories_found(self, extractor, mock_ia):
        mock_ia.chat.return_value = IAResponse(
            content="[]",
            model="qwen2.5:3b",
            tokens_used=5,
            latency_ms=50.0,
        )
        result = await extractor.extract_from_message(
            "Me gusta el clima de hoy, está muy agradable para salir a caminar por el parque",
            "Sí, el clima es agradable.",
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_malformed_json_returns_empty(self, extractor, mock_ia):
        mock_ia.chat.return_value = IAResponse(
            content="esto no es json para nada",
            model="qwen2.5:3b",
            tokens_used=5,
            latency_ms=50.0,
        )
        result = await extractor.extract_from_message(
            "Me gusta Python mucho, es mi lenguaje favorito de todos los tiempos",
            "Genial!",
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_extraction_format_correct(self, extractor, mock_ia):
        mock_ia.chat.return_value = IAResponse(
            content='[{"content": "Test", "type": "fact", "metadata": {"key": "val"}}]',
            model="qwen2.5:3b",
            tokens_used=10,
            latency_ms=50.0,
        )
        result = await extractor.extract_from_message(
            "Mi nombre es Test y tengo treinta años, vivo en una ciudad grande",
            "Hola Test",
        )
        assert len(result) == 1
        assert "content" in result[0]
        assert "type" in result[0]
        assert "metadata" in result[0]

    @pytest.mark.asyncio
    async def test_invalid_type_filtered(self, extractor, mock_ia):
        mock_ia.chat.return_value = IAResponse(
            content='[{"content": "Test", "type": "invalid_type", "metadata": {}}]',
            model="qwen2.5:3b",
            tokens_used=10,
            latency_ms=50.0,
        )
        result = await extractor.extract_from_message(
            "Me gusta Python mucho, es mi lenguaje favorito de todos los tiempos",
            "Genial",
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_ia_error_returns_empty(self, extractor, mock_ia):
        mock_ia.chat.side_effect = Exception("Ollama error")
        result = await extractor.extract_from_message(
            "Mi nombre es Diego y soy programador, trabajo en tecnología",
            "Hola Diego",
        )
        assert result == []
