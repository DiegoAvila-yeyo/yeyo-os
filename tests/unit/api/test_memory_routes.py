"""
Tests para Memory API Endpoints — Micro-fase 2.16
Tests unitarios con TestClient de FastAPI.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.routes.memory import (
    router,
    get_flash_memory,
    get_embedding_service,
    get_association_engine,
)
from src.memory.models import Memory


@pytest.fixture
def mock_flash_memory():
    fm = AsyncMock()
    fm.search_semantic.return_value = [
        Memory(
            id="mem-1",
            content="Python es mi favorito",
            type="preference",
            checksum="a" * 64,
            access_count=5,
        ),
    ]
    fm.get_by_id.return_value = Memory(
        id="mem-1",
        content="Python es mi favorito",
        type="preference",
        checksum="a" * 64,
        access_count=5,
    )
    fm.get_stats.return_value = {
        "total_memories": 42,
        "by_tier": {"HOT": 5, "WARM": 30, "COLD": 7},
        "by_type": {"fact": 20, "preference": 12, "conversation": 10},
        "total_associations": 15,
    }
    return fm


@pytest.fixture
def mock_embedding_service():
    emb = MagicMock()
    emb.generate.return_value = [0.1] * 384
    return emb


@pytest.fixture
def mock_association_engine():
    ae = AsyncMock()
    ae.find_related.return_value = [
        Memory(
            id="mem-2",
            content="JavaScript también me gusta",
            type="preference",
            checksum="b" * 64,
        ),
    ]
    return ae


@pytest.fixture
def client(mock_flash_memory, mock_embedding_service, mock_association_engine):
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_flash_memory] = lambda: mock_flash_memory
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service
    app.dependency_overrides[get_association_engine] = lambda: mock_association_engine

    return TestClient(app)


class TestSearchEndpoint:
    """Tests de GET /api/v1/memory/search."""

    def test_search_returns_results(self, client):
        response = client.get("/api/v1/memory/search?q=Python")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert "query" in data
        assert data["query"] == "Python"

    def test_search_requires_query(self, client):
        response = client.get("/api/v1/memory/search")
        assert response.status_code == 422

    def test_search_empty_query_rejected(self, client):
        response = client.get("/api/v1/memory/search?q=")
        assert response.status_code == 422


class TestStatsEndpoint:
    """Tests de GET /api/v1/memory/stats."""

    def test_stats_returns_data(self, client):
        response = client.get("/api/v1/memory/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_memories" in data
        assert "by_tier" in data
        assert "by_type" in data
        assert "total_associations" in data

    def test_stats_has_correct_total(self, client):
        response = client.get("/api/v1/memory/stats")
        data = response.json()
        assert data["total_memories"] == 42


class TestGetMemoryEndpoint:
    """Tests de GET /api/v1/memory/{id}."""

    def test_get_memory_by_id(self, client):
        response = client.get("/api/v1/memory/mem-1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "mem-1"
        assert data["content"] == "Python es mi favorito"

    def test_get_memory_not_found(self, client, mock_flash_memory):
        mock_flash_memory.get_by_id.return_value = None
        response = client.get("/api/v1/memory/nonexistent")
        assert response.status_code == 404


class TestAssociationsEndpoint:
    """Tests de GET /api/v1/memory/{id}/associations."""

    def test_get_associations(self, client):
        response = client.get("/api/v1/memory/mem-1/associations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


class TestDeleteForbidden:
    """Tests de DELETE — DEBE ESTAR PROHIBIDO."""

    def test_delete_returns_405(self, client):
        """DELETE de memoria DEBE retornar 405 Method Not Allowed."""
        response = client.delete("/api/v1/memory/mem-1")
        assert response.status_code == 405

    def test_delete_has_explanation(self, client):
        """DELETE debe incluir mensaje explicando por qué está prohibido."""
        response = client.delete("/api/v1/memory/mem-1")
        data = response.json()
        assert "PROHIBIDO" in data["detail"] or "NUNCA" in data["detail"]

    def test_delete_any_id_forbidden(self, client):
        """DELETE debe ser prohibido para CUALQUIER ID."""
        for test_id in ["mem-1", "mem-999", "any-id", "test"]:
            response = client.delete(f"/api/v1/memory/{test_id}")
            assert response.status_code == 405


class TestAllEndpointsExist:
    """Verificar que todos los endpoints existen."""

    def test_search_exists(self, client):
        response = client.get("/api/v1/memory/search?q=test")
        assert response.status_code != 404

    def test_stats_exists(self, client):
        response = client.get("/api/v1/memory/stats")
        assert response.status_code != 404

    def test_get_by_id_exists(self, client):
        response = client.get("/api/v1/memory/test-id")
        assert response.status_code != 404

    def test_associations_exists(self, client):
        response = client.get("/api/v1/memory/test-id/associations")
        assert response.status_code != 404

    def test_delete_exists_but_forbidden(self, client):
        response = client.delete("/api/v1/memory/test-id")
        assert response.status_code == 405
