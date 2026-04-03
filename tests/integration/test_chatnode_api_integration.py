"""
Integration tests: ChatPanel Frontend → API → ChatNodeService

Phase 3.1.1 - Frontend Integration (Option B)
Tests verify that the /api/v1/chat/stream endpoint correctly calls ChatNodeService
and streams responses in SSE format.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.chat import (
    router,
    get_chat_service,
    get_conversation_manager,
    get_feedback_service,
)
from src.nodes.chat.types import ChatNodeOutput, ChatNodeError, ErrorCode


@pytest.fixture
def mock_chat_service():
    """Mock chat service (legacy)."""
    service = AsyncMock()
    service.send_message.return_value = "Respuesta de YeyoOS"
    
    async def mock_stream(**kwargs):
        yield "chunk1"
        yield "chunk2"
    
    service.send_message_stream = mock_stream
    return service


@pytest.fixture
def mock_conv_manager():
    """Mock conversation manager."""
    cm = AsyncMock()
    cm.create_conversation.return_value = "conv-test-123"
    cm.get_history.return_value = []
    cm.add_message.return_value = None
    return cm


@pytest.fixture
def mock_feedback_service():
    """Mock feedback service."""
    fs = AsyncMock()
    return fs


@pytest.fixture
def client(mock_chat_service, mock_conv_manager, mock_feedback_service):
    """FastAPI test client."""
    app = FastAPI()
    app.include_router(router)
    
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
    app.dependency_overrides[get_conversation_manager] = lambda: mock_conv_manager
    app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service
    
    return TestClient(app)


class TestChatNodeAPIIntegration:
    """Tests for ChatNode integration with FastAPI endpoint."""
    
    @patch('src.api.routes.chat.ChatNodeService')
    def test_stream_endpoint_calls_chatnode_service(self, mock_chatnode_class, client):
        """Verify /api/v1/chat/stream calls ChatNodeService.process_message()"""
        # Setup mock
        mock_service_instance = AsyncMock()
        mock_chatnode_class.return_value = mock_service_instance
        
        mock_output = ChatNodeOutput(
            response="Hello from ChatNode",
            confidence=0.85,
            reasoning="Test response",
            suggestions=[],
            tokens_used=5,
            conversation_id="conv-test-123",
            message_id="msg-123",
        )
        mock_service_instance.process_message.return_value = mock_output
        
        # Send request
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "Hello ChatNode"},
        )
        
        # Verify
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        
        # Check that ChatNodeService was instantiated
        mock_chatnode_class.assert_called_once()
        
        # Check that process_message was called with correct params
        mock_service_instance.process_message.assert_called_once()
        call_kwargs = mock_service_instance.process_message.call_args[1]
        assert call_kwargs['message'] == "Hello ChatNode"
        assert call_kwargs['conversation_id'] == "conv-test-123"
    
    @patch('src.api.routes.chat.ChatNodeService')
    def test_stream_response_format_sse(self, mock_chatnode_class, client):
        """Verify streaming response is in SSE format"""
        # Setup
        mock_service_instance = AsyncMock()
        mock_chatnode_class.return_value = mock_service_instance
        
        mock_output = ChatNodeOutput(
            response="This is a test response",
            confidence=0.75,
            reasoning="Testing",
            suggestions=[],
            tokens_used=5,
            conversation_id="conv-123",
            message_id="msg-123",
        )
        mock_service_instance.process_message.return_value = mock_output
        
        # Send request
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "test"},
        )
        
        # Verify SSE format
        assert response.status_code == 200
        content = response.text
        
        # Should have "data: " prefixes
        assert "data: " in content
        
        # Should have METADATA chunk with conversation_id
        assert "METADATA:conversation_id:" in content
        
        # Should end with [DONE]
        assert "data: [DONE]" in content
    
    @patch('src.api.routes.chat.ChatNodeService')
    def test_stream_handles_chatnode_error(self, mock_chatnode_class, client):
        """Verify error responses from ChatNode are handled correctly"""
        # Setup
        mock_service_instance = AsyncMock()
        mock_chatnode_class.return_value = mock_service_instance
        
        error_response = ChatNodeError(
            error="Invalid input",
            error_code=ErrorCode.ERROR_INVALID_INPUT,
            conversation_id="conv-123",
            user_id=None,
        )
        mock_service_instance.process_message.return_value = error_response
        
        # Send request (with valid message - validation happens before ChatNode)
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "test message for error handling"},
        )
        
        # Verify error is returned
        assert response.status_code == 200  # Still 200 for SSE
        content = response.text
        
        # Should contain ERROR marker
        assert "data: ERROR:" in content
        # Should contain user-friendly message (not technical error)
        assert "El mensaje no es" in content or "error_invalid_input" in content
        assert "data: [DONE]" in content
    
    @patch('src.api.routes.chat.ChatNodeService')
    def test_stream_persists_conversation_id(self, mock_chatnode_class, client, mock_conv_manager):
        """Verify conversation_id is saved and persisted"""
        # Setup
        mock_service_instance = AsyncMock()
        mock_chatnode_class.return_value = mock_service_instance
        
        mock_output = ChatNodeOutput(
            response="Response",
            confidence=0.75,
            reasoning="Test",
            suggestions=[],
            tokens_used=3,
            conversation_id="conv-123",
            message_id="msg-1",
        )
        mock_service_instance.process_message.return_value = mock_output
        
        # Send request with explicit conversation_id
        response = client.post(
            "/api/v1/chat/stream",
            json={
                "message": "Test",
                "conversation_id": "conv-123",
            },
        )
        
        # Verify conversation manager was called
        assert response.status_code == 200
        mock_conv_manager.add_message.assert_called()
        
        # Check that both user and assistant messages were added
        calls = mock_conv_manager.add_message.call_args_list
        assert len(calls) >= 2  # At least user + assistant
        
        # First call should be user message
        assert calls[0][0] == ("conv-123", "user", "Test")
        
        # Last call should be assistant message
        assert calls[-1][0][1] == "assistant"
    
    @patch('src.api.routes.chat.ChatNodeService')
    def test_stream_creates_new_conversation_if_not_provided(self, mock_chatnode_class, client, mock_conv_manager):
        """Verify new conversation is created if conversation_id not provided"""
        # Setup
        mock_service_instance = AsyncMock()
        mock_chatnode_class.return_value = mock_service_instance
        
        mock_output = ChatNodeOutput(
            response="Response",
            confidence=0.75,
            reasoning="Test",
            suggestions=[],
            tokens_used=3,
            conversation_id="conv-test-123",
            message_id="msg-1",
        )
        mock_service_instance.process_message.return_value = mock_output
        
        # Send request WITHOUT conversation_id
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "Test"},
        )
        
        # Verify
        assert response.status_code == 200
        mock_conv_manager.create_conversation.assert_called_once()


class TestStreamResponseContent:
    """Tests for proper response content and chunking."""
    
    @patch('src.api.routes.chat.ChatNodeService')
    def test_long_response_is_chunked(self, mock_chatnode_class, client):
        """Verify long responses are chunked for smooth streaming"""
        # Setup with long response
        mock_service_instance = AsyncMock()
        mock_chatnode_class.return_value = mock_service_instance
        
        long_text = "A" * 1000  # 1000 character response
        mock_output = ChatNodeOutput(
            response=long_text,
            confidence=0.75,
            reasoning="Test",
            suggestions=[],
            tokens_used=150,
            conversation_id="conv-123",
            message_id="msg-1",
        )
        mock_service_instance.process_message.return_value = mock_output
        
        # Send request
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "test"},
        )
        
        # Verify response
        assert response.status_code == 200
        content = response.text
        
        # Should have multiple chunks (50 chars per chunk based on implementation)
        chunk_count = content.count("data: ")
        assert chunk_count > 1  # More than just [DONE]
        
        # Last should be [DONE]
        assert content.strip().endswith("data: [DONE]")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
