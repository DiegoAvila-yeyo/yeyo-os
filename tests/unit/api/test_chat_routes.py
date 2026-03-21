"""
Tests para Chat API Endpoints — Micro-fase 2.15
Tests unitarios con TestClient de FastAPI.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.routes.chat import (
    router,
    get_chat_service,
    get_conversation_manager,
    get_feedback_service,
)
from src.ia.interfaces import IAMessage


@pytest.fixture
def mock_chat_service():
    service = AsyncMock()
    service.send_message.return_value = "Respuesta de YeyoOS"

    async def mock_stream(**kwargs):
        yield "chunk1"
        yield "chunk2"

    service.send_message_stream = mock_stream
    return service


@pytest.fixture
def mock_conv_manager():
    cm = AsyncMock()
    cm.create_conversation.return_value = "conv-123"
    cm.get_history.return_value = []
    cm.list_conversations.return_value = [
        {"id": "conv-1", "title": "Test", "message_count": 0}
    ]
    cm.get_conversation.return_value = {
        "id": "conv-1",
        "title": "Test",
        "message_count": 0,
    }
    return cm


@pytest.fixture
def mock_feedback_service():
    fs = AsyncMock()
    fs.rate_response.return_value = {
        "id": "fb-1",
        "message_id": "msg-1",
        "rating": 5,
        "comment": "",
    }
    return fs


@pytest.fixture
def client(mock_chat_service, mock_conv_manager, mock_feedback_service):
    app = FastAPI()
    app.include_router(router)

    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
    app.dependency_overrides[get_conversation_manager] = lambda: mock_conv_manager
    app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service

    return TestClient(app)


class TestChatEndpoint:
    """Tests del endpoint POST /api/v1/chat."""

    def test_send_message(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hola YeyoOS"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert "message_id" in data

    def test_send_empty_message_rejected(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": ""},
        )
        assert response.status_code == 422  # Validation error

    def test_send_with_conversation_id(self, client):
        response = client.post(
            "/api/v1/chat",
            json={"message": "Test", "conversation_id": "conv-123"},
        )
        assert response.status_code == 200


class TestConversationEndpoints:
    """Tests de endpoints de conversaciones."""

    def test_list_conversations(self, client):
        response = client.get("/api/v1/chat/conversations")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_conversation(self, client):
        response = client.post(
            "/api/v1/chat/conversations",
            json={"title": "Mi conversación"},
        )
        assert response.status_code == 200
        assert "id" in response.json()

    def test_get_conversation(self, client):
        response = client.get("/api/v1/chat/conversations/conv-1")
        assert response.status_code == 200

    def test_get_conversation_not_found(self, client, mock_conv_manager):
        mock_conv_manager.get_conversation.return_value = None
        response = client.get(
            "/api/v1/chat/conversations/nonexistent"
        )
        assert response.status_code == 404


class TestFeedbackEndpoints:
    """Tests de endpoints de feedback."""

    def test_submit_feedback(self, client):
        response = client.post(
            "/api/v1/chat/msg-1/feedback",
            json={"rating": 5, "comment": "Excelente"},
        )
        assert response.status_code == 200

    def test_feedback_invalid_rating(self, client):
        response = client.post(
            "/api/v1/chat/msg-1/feedback",
            json={"rating": 0},
        )
        assert response.status_code == 422

    def test_feedback_rating_6_rejected(self, client):
        response = client.post(
            "/api/v1/chat/msg-1/feedback",
            json={"rating": 6},
        )
        assert response.status_code == 422

    def test_submit_correction(self, client, mock_feedback_service):
        mock_feedback_service.report_incorrect.return_value = {
            "feedback_id": "fb-1",
            "correction": "Es Diego",
            "memory_created": "mem-1",
        }
        response = client.post(
            "/api/v1/chat/msg-1/correction",
            json={"correction": "Es Diego, no Juan"},
        )
        assert response.status_code == 200


class TestAllEndpointsExist:
    """Verificar que todos los endpoints existen."""

    def test_chat_post_exists(self, client):
        response = client.post("/api/v1/chat", json={"message": "test"})
        assert response.status_code != 404

    def test_stream_post_exists(self, client):
        # stream usa async generator; con TestClient se ejecuta sincronamente
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "test"},
        )
        assert response.status_code != 404

    def test_conversations_get_exists(self, client):
        response = client.get("/api/v1/chat/conversations")
        assert response.status_code != 404

    def test_conversations_post_exists(self, client):
        response = client.post(
            "/api/v1/chat/conversations",
            json={"title": "test"},
        )
        assert response.status_code != 404

    def test_feedback_post_exists(self, client):
        response = client.post(
            "/api/v1/chat/msg-1/feedback",
            json={"rating": 3},
        )
        assert response.status_code != 404
