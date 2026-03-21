"""
Tests para AssociationEngine — Micro-fase 2.10
Tests unitarios con mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.memory.associations import (
    AssociationEngine,
    AUTO_ASSOCIATION_THRESHOLD,
    MAX_AUTO_ASSOCIATIONS,
)
from src.memory.models import Memory


@pytest.fixture
def mock_flash_memory():
    fm = AsyncMock()
    fm.pool = MagicMock()
    fm._row_to_memory = MagicMock()
    fm.search_semantic = AsyncMock(return_value=[])
    return fm


@pytest.fixture
def mock_embeddings():
    emb = MagicMock()
    emb.generate.return_value = [0.1] * 384
    emb.similarity.return_value = 0.8
    return emb


@pytest.fixture
def engine(mock_flash_memory, mock_embeddings):
    return AssociationEngine(
        flash_memory=mock_flash_memory,
        embeddings=mock_embeddings,
    )


class TestAssociationEngineBasic:
    """Tests básicos."""

    def test_threshold_configured(self):
        assert AUTO_ASSOCIATION_THRESHOLD == 0.6

    def test_max_auto_associations(self):
        assert MAX_AUTO_ASSOCIATIONS == 5

    @pytest.mark.asyncio
    async def test_self_association_blocked(self, engine):
        """No se puede crear asociación consigo mismo."""
        with pytest.raises(ValueError, match="consigo mismo"):
            await engine.create_association("id-1", "id-1", "self")

    @pytest.mark.asyncio
    async def test_invalid_strength_rejected(self, engine):
        with pytest.raises(ValueError, match="strength"):
            await engine.create_association("id-1", "id-2", "test", strength=1.5)

    @pytest.mark.asyncio
    async def test_negative_strength_rejected(self, engine):
        with pytest.raises(ValueError, match="strength"):
            await engine.create_association("id-1", "id-2", "test", strength=-0.1)


class TestInferRelationType:
    """Tests de inferencia de tipo de relación."""

    def test_correction_relation(self):
        m1 = Memory(content="A", type="correction", checksum="a" * 64)
        m2 = Memory(content="B", type="fact", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "corrects"

    def test_correction_priority(self):
        """correction tiene prioridad sobre otros tipos."""
        m1 = Memory(content="A", type="correction", checksum="a" * 64)
        m2 = Memory(content="B", type="preference", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "corrects"

    def test_similar_preference(self):
        m1 = Memory(content="A", type="preference", checksum="a" * 64)
        m2 = Memory(content="B", type="preference", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "similar_preference"

    def test_related_fact(self):
        m1 = Memory(content="A", type="fact", checksum="a" * 64)
        m2 = Memory(content="B", type="fact", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "related_fact"

    def test_related_skill(self):
        m1 = Memory(content="A", type="skill", checksum="a" * 64)
        m2 = Memory(content="B", type="fact", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "related_skill"

    def test_skill_with_preference(self):
        m1 = Memory(content="A", type="skill", checksum="a" * 64)
        m2 = Memory(content="B", type="preference", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "related_skill"

    def test_semantic_similar_default(self):
        m1 = Memory(content="A", type="conversation", checksum="a" * 64)
        m2 = Memory(content="B", type="fact", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "semantic_similar"

    def test_two_conversations(self):
        m1 = Memory(content="A", type="conversation", checksum="a" * 64)
        m2 = Memory(content="B", type="conversation", checksum="b" * 64)
        assert AssociationEngine._infer_relation_type(m1, m2) == "semantic_similar"


class TestAutoAssociate:
    """Tests de auto-asociación."""

    @pytest.mark.asyncio
    async def test_auto_associate_empty_when_no_similar(self, engine):
        memory = Memory(
            id="new-mem",
            content="Algo único",
            type="fact",
            checksum="a" * 64,
        )
        engine.memory.search_semantic.return_value = []
        result = await engine.auto_associate(memory)
        assert result == []

    @pytest.mark.asyncio
    async def test_auto_associate_skips_self(self, engine):
        memory = Memory(
            id="new-mem",
            content="Test",
            type="fact",
            checksum="a" * 64,
        )
        # search_semantic retorna la misma memoria
        engine.memory.search_semantic.return_value = [memory]
        result = await engine.auto_associate(memory)
        assert result == []

    @pytest.mark.asyncio
    async def test_auto_associate_calls_embeddings(self, engine, mock_embeddings):
        memory = Memory(
            content="Test content",
            type="fact",
            checksum="a" * 64,
        )
        engine.memory.search_semantic.return_value = []
        await engine.auto_associate(memory)
        mock_embeddings.generate.assert_called_once_with(memory.content)


class TestGetAssociationGraph:
    """Tests del grafo de asociaciones."""

    @pytest.mark.asyncio
    async def test_graph_structure(self, engine, mock_flash_memory):
        mock_flash_memory.get_by_id.return_value = Memory(
            id="root",
            content="Root memory",
            type="fact",
            checksum="a" * 64,
        )

        # Mock pool.acquire para el grafo
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=False)
        mock_flash_memory.pool.acquire.return_value = mock_context

        graph = await engine.get_association_graph("root", depth=1)
        assert "root" in graph
        assert "nodes" in graph
        assert "edges" in graph
        assert "total_nodes" in graph
        assert "total_edges" in graph
        assert graph["depth"] == 1

    @pytest.mark.asyncio
    async def test_graph_empty_when_no_memory(self, engine, mock_flash_memory):
        mock_flash_memory.get_by_id.return_value = None

        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = []
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=False)
        mock_flash_memory.pool.acquire.return_value = mock_context

        graph = await engine.get_association_graph("nonexistent", depth=1)
        assert graph["total_nodes"] == 0
        assert graph["total_edges"] == 0
