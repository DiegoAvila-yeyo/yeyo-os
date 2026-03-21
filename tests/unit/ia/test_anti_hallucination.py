"""
Tests para AntiHallucination — Micro-fase 2.11
Tests unitarios con mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.ia.anti_hallucination import (
    AntiHallucination,
    VerificationResult,
    MIN_TOKENS_FOR_VERIFICATION,
)
from src.ia.interfaces import IAProvider, IAResponse
from src.memory.models import Memory


@pytest.fixture
def mock_ia():
    return AsyncMock(spec=IAProvider)


@pytest.fixture
def mock_memory():
    fm = AsyncMock()
    fm.search_semantic = AsyncMock(return_value=[])
    return fm


@pytest.fixture
def mock_embeddings():
    emb = MagicMock()
    emb.generate.return_value = [0.1] * 384
    return emb


@pytest.fixture
def anti_hallucination(mock_ia, mock_memory, mock_embeddings):
    return AntiHallucination(
        ia_provider=mock_ia,
        flash_memory=mock_memory,
        embeddings=mock_embeddings,
    )


class TestShouldVerify:
    """Tests de umbral de verificación."""

    @pytest.mark.asyncio
    async def test_short_response_skipped(self, anti_hallucination):
        """Respuestas <50 tokens no se verifican."""
        assert await anti_hallucination.should_verify("Hola") is False

    @pytest.mark.asyncio
    async def test_empty_response_skipped(self, anti_hallucination):
        assert await anti_hallucination.should_verify("") is False

    @pytest.mark.asyncio
    async def test_none_response_skipped(self, anti_hallucination):
        assert await anti_hallucination.should_verify(None) is False

    @pytest.mark.asyncio
    async def test_long_response_verified(self, anti_hallucination):
        """Respuestas >50 tokens sí se verifican."""
        long_text = "palabra " * 60  # ~60 tokens
        assert await anti_hallucination.should_verify(long_text) is True

    def test_threshold_is_50(self):
        assert MIN_TOKENS_FOR_VERIFICATION == 50


class TestVerify:
    """Tests de verificación completa."""

    @pytest.mark.asyncio
    async def test_short_response_returns_verified(self, anti_hallucination):
        """Respuestas cortas se marcan como verificadas sin análisis."""
        result = await anti_hallucination.verify("Respuesta corta")
        assert result.verified is True
        assert result.skipped is True
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_no_facts_returns_verified(self, anti_hallucination):
        """Sin hechos conocidos, se asume correcto con confianza 0.8."""
        long_response = "Esta es una respuesta larga " * 20
        result = await anti_hallucination.verify(long_response)
        assert result.verified is True
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_contradiction_detected(
        self, anti_hallucination, mock_ia, mock_memory
    ):
        """Contradicción con hechos conocidos se detecta."""
        mock_memory.search_semantic.return_value = [
            Memory(
                content="El usuario se llama Diego",
                type="fact",
                checksum="a" * 64,
            ),
        ]
        mock_ia.chat.return_value = IAResponse(
            content='{"has_contradiction": true, "contradictions": ["Llama al usuario Juan pero su nombre es Diego"], "confidence": 0.3, "corrections": ["Usar Diego en vez de Juan"]}',
            model="qwen2.5:3b",
            tokens_used=30,
            latency_ms=100.0,
        )

        long_response = "Hola Juan, como te mencioné anteriormente " * 10
        result = await anti_hallucination.verify(long_response)
        assert result.verified is False
        assert len(result.flags) > 0
        assert len(result.corrections) > 0
        assert result.confidence < 1.0

    @pytest.mark.asyncio
    async def test_no_contradiction(
        self, anti_hallucination, mock_ia, mock_memory
    ):
        """Respuesta consistente con hechos pasa la verificación."""
        mock_memory.search_semantic.return_value = [
            Memory(
                content="El usuario se llama Diego",
                type="fact",
                checksum="a" * 64,
            ),
        ]
        mock_ia.chat.return_value = IAResponse(
            content='{"has_contradiction": false, "contradictions": [], "confidence": 0.95, "corrections": []}',
            model="qwen2.5:3b",
            tokens_used=20,
            latency_ms=100.0,
        )

        long_response = "Hola Diego, espero que estés bien " * 10
        result = await anti_hallucination.verify(long_response)
        assert result.verified is True
        assert result.confidence > 0.9


class TestVerificationResult:
    """Tests del modelo VerificationResult."""

    def test_to_dict(self):
        result = VerificationResult(
            verified=True,
            confidence=0.95,
            flags=["flag1"],
            corrections=["fix1"],
        )
        d = result.to_dict()
        assert d["verified"] is True
        assert d["confidence"] == 0.95
        assert "flag1" in d["flags"]

    def test_confidence_clamped_max(self):
        result = VerificationResult(verified=True, confidence=1.5)
        assert result.confidence == 1.0

    def test_confidence_clamped_min(self):
        result = VerificationResult(verified=True, confidence=-0.5)
        assert result.confidence == 0.0

    def test_default_values(self):
        result = VerificationResult(verified=True, confidence=0.8)
        assert result.flags == []
        assert result.corrections == []
        assert result.skipped is False
        assert result.reason == ""

    @pytest.mark.asyncio
    async def test_ia_error_handled_gracefully(
        self, anti_hallucination, mock_ia, mock_memory
    ):
        """Error de IA no crashea — retorna resultado con baja confianza."""
        mock_memory.search_semantic.return_value = [
            Memory(content="Hecho", type="fact", checksum="a" * 64),
        ]
        mock_ia.chat.side_effect = Exception("Ollama caído")

        long_response = "Respuesta que necesita verificación " * 20
        result = await anti_hallucination.verify(long_response)
        assert result.verified is True  # Default: no bloquear
        assert result.confidence == 0.5  # Baja confianza
        assert len(result.flags) > 0  # Flag de error
