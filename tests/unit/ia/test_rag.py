"""
Tests para RAGPipeline — Micro-fase 2.12
Tests unitarios con mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.ia.rag import RAGPipeline, RAGResult
from src.ia.interfaces import IAProvider, IAResponse
from src.ia.anti_hallucination import VerificationResult
from src.memory.models import Memory


@pytest.fixture
def mock_ia():
    ia = AsyncMock(spec=IAProvider)
    ia.chat.return_value = IAResponse(
        content="Respuesta del RAG pipeline",
        model="qwen2.5:3b",
        tokens_used=30,
        latency_ms=200.0,
    )
    return ia


@pytest.fixture
def mock_memory():
    fm = AsyncMock()
    fm.search_semantic.return_value = [
        Memory(
            id="src-1",
            content="Python es el lenguaje favorito del usuario",
            type="preference",
            checksum="a" * 64,
        ),
    ]
    return fm


@pytest.fixture
def mock_embeddings():
    emb = MagicMock()
    emb.generate.return_value = [0.1] * 384
    return emb


@pytest.fixture
def mock_verifier():
    v = AsyncMock()
    v.verify.return_value = VerificationResult(
        verified=True, confidence=0.95
    )
    return v


@pytest.fixture
def rag_pipeline(mock_ia, mock_memory, mock_embeddings, mock_verifier):
    return RAGPipeline(
        ia=mock_ia,
        memory=mock_memory,
        embeddings=mock_embeddings,
        anti_hallucination=mock_verifier,
    )


class TestRAGQuery:
    """Tests del pipeline completo."""

    @pytest.mark.asyncio
    async def test_query_returns_rag_result(self, rag_pipeline):
        result = await rag_pipeline.query("¿Qué lenguaje prefiero?")
        assert isinstance(result, RAGResult)

    @pytest.mark.asyncio
    async def test_query_has_answer(self, rag_pipeline):
        result = await rag_pipeline.query("¿Cuál es mi nombre?")
        assert isinstance(result.answer, str)
        assert len(result.answer) > 0

    @pytest.mark.asyncio
    async def test_query_includes_sources(self, rag_pipeline):
        result = await rag_pipeline.query("¿Qué lenguaje prefiero?")
        assert isinstance(result.sources, list)
        assert len(result.sources) > 0

    @pytest.mark.asyncio
    async def test_query_has_confidence(self, rag_pipeline):
        result = await rag_pipeline.query("Test")
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_query_is_verified(self, rag_pipeline):
        result = await rag_pipeline.query("Test")
        assert result.verified is True

    @pytest.mark.asyncio
    async def test_empty_question(self, rag_pipeline):
        result = await rag_pipeline.query("")
        assert "No recibí" in result.answer

    @pytest.mark.asyncio
    async def test_no_sources_low_confidence(
        self, mock_ia, mock_embeddings, mock_verifier
    ):
        """Sin fuentes, la confianza debe ser 0.5."""
        empty_memory = AsyncMock()
        empty_memory.search_semantic.return_value = []
        pipeline = RAGPipeline(
            ia=mock_ia,
            memory=empty_memory,
            embeddings=mock_embeddings,
            anti_hallucination=mock_verifier,
        )
        result = await pipeline.query("Algo sin memorias")
        assert result.confidence <= 0.5

    @pytest.mark.asyncio
    async def test_verification_failure_reduces_confidence(
        self, mock_ia, mock_memory, mock_embeddings
    ):
        """Verificación fallida reduce la confianza."""
        failing_verifier = AsyncMock()
        failing_verifier.verify.return_value = VerificationResult(
            verified=False, confidence=0.3, flags=["Contradicción"]
        )
        pipeline = RAGPipeline(
            ia=mock_ia,
            memory=mock_memory,
            embeddings=mock_embeddings,
            anti_hallucination=failing_verifier,
        )
        result = await pipeline.query("Test contradicción")
        assert result.verified is False
        assert result.confidence < 1.0

    @pytest.mark.asyncio
    async def test_without_verifier(self, mock_ia, mock_memory, mock_embeddings):
        """Sin verificador, el pipeline funciona igual."""
        pipeline = RAGPipeline(
            ia=mock_ia,
            memory=mock_memory,
            embeddings=mock_embeddings,
            anti_hallucination=None,
        )
        result = await pipeline.query("Test sin verificador")
        assert result.verified is True


class TestRAGResult:
    """Tests del modelo RAGResult."""

    def test_to_dict_structure(self):
        result = RAGResult(
            answer="Respuesta",
            sources=[
                Memory(content="Fuente", type="fact", checksum="a" * 64),
            ],
            confidence=0.9,
            verified=True,
            tokens_used=50,
        )
        d = result.to_dict()
        assert "answer" in d
        assert "sources" in d
        assert "confidence" in d
        assert "verified" in d
        assert "tokens_used" in d

    def test_confidence_clamped(self):
        result = RAGResult(answer="Test", confidence=1.5)
        assert result.confidence == 1.0

    def test_default_values(self):
        result = RAGResult(answer="Test")
        assert result.sources == []
        assert result.verified is True
        assert result.tokens_used == 0


class TestConfidenceCalculation:
    """Tests de cálculo de confianza."""

    def test_no_sources_half_confidence(self, rag_pipeline):
        conf = rag_pipeline._calculate_confidence([], "answer")
        assert conf == 0.5

    def test_one_source_increases_confidence(self, rag_pipeline):
        sources = [Memory(content="A", type="fact", checksum="a" * 64)]
        conf = rag_pipeline._calculate_confidence(sources, "answer")
        assert conf > 0.5

    def test_five_sources_max_confidence(self, rag_pipeline):
        sources = [
            Memory(content=f"S{i}", type="fact", checksum=f"{i}" * 64)
            for i in range(5)
        ]
        conf = rag_pipeline._calculate_confidence(sources, "answer")
        assert conf == 1.0

    def test_confidence_never_exceeds_one(self, rag_pipeline):
        sources = [
            Memory(content=f"S{i}", type="fact", checksum=f"{i}" * 64)
            for i in range(10)
        ]
        conf = rag_pipeline._calculate_confidence(sources, "answer")
        assert conf <= 1.0
