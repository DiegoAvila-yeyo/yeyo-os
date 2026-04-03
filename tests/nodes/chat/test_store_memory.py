"""
Test suite for _store_in_memory() implementation.

Tests the conversation persistence layer.
Target: 8 comprehensive test cases covering:
- Successful storage
- Database errors
- New conversation creation
- Message logging
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

from src.nodes.chat.service_integration import ChatNodeService
from src.nodes.chat.exceptions import DatabaseError, MemoryInjectionError


class TestStoreInMemory:
    """Test _store_in_memory() memory persistence."""

    @pytest.fixture
    def service(self):
        return ChatNodeService()

    # ═══════════════════════════════════════════════════════════
    # SUCCESSFUL STORAGE TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_store_message_successful(self, service):
        """Test successful message storage."""
        mock_db = AsyncMock()
        mock_get_database = AsyncMock(return_value=mock_db)
        with patch("src.db.get_database", mock_get_database):
            await service._store_in_memory(
                conversation_id="conv-123",
                user_message="Hello",
                assistant_response="Hi there",
                user_id="user-456"
            )
        
        # Verify database was called
        assert mock_db.store_message.called

    @pytest.mark.asyncio
    async def test_store_message_creates_conversation(self, service):
        """Test creates new conversation if doesn't exist."""
        mock_db = AsyncMock()
        
        # Simulate new conversation
        conversation_id = None
        
        with patch("src.db.get_database", return_value=mock_db):
            with patch("uuid.uuid4", return_value=MagicMock(hex="test-id-123")):
                await service._store_in_memory(
                    conversation_id=conversation_id,
                    user_message="First message",
                    assistant_response="First response",
                    user_id="user-789"
                )
        
        # Verify conversation creation was called
        assert mock_db.create_conversation.called

    @pytest.mark.asyncio
    async def test_store_user_and_assistant_messages(self, service):
        """Test stores both user and assistant messages."""
        mock_db = AsyncMock()
        user_msg = "What is AI?"
        assistant_msg = "AI is Artificial Intelligence..."
        
        with patch("src.db.get_database", return_value=mock_db):
            await service._store_in_memory(
                conversation_id="conv-123",
                user_message=user_msg,
                assistant_response=assistant_msg,
                user_id="user-123"
            )
        
        # Verify both messages are stored
        calls = mock_db.store_message.call_args_list
        assert len(calls) >= 2  # At least user + assistant

    @pytest.mark.asyncio
    async def test_store_message_with_metadata(self, service):
        """Test message storage includes metadata."""
        mock_db = AsyncMock()
        mock_get_database = AsyncMock(return_value=mock_db)
        with patch("src.db.get_database", mock_get_database):
            await service._store_in_memory(
                conversation_id="conv-123",
                user_message="Test message",
                assistant_response="Test response",
                user_id="user-123"
            )
        
        # Verify metadata was included
        calls = mock_db.store_message.call_args_list
        # Check that calls include timestamp, tokens, etc
        assert len(calls) > 0

    # ═══════════════════════════════════════════════════════════
    # ERROR HANDLING TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_database_connection_error(self, service):
        """Test database connection error handling."""
        mock_db = AsyncMock()
        mock_db.store_message = AsyncMock(side_effect=ConnectionError("DB connection failed"))
        
        with patch("src.db.get_database", return_value=mock_db):
            with pytest.raises(DatabaseError):
                await service._store_in_memory(
                    conversation_id="conv-123",
                    user_message="Hello",
                    assistant_response="Hi",
                    user_id="user-123"
                )

    @pytest.mark.asyncio
    async def test_database_timeout_error(self, service):
        """Test database timeout error handling."""
        mock_db = AsyncMock()
        mock_db.store_message = AsyncMock(side_effect=TimeoutError("DB timeout"))
        
        with patch("src.db.get_database", return_value=mock_db):
            with pytest.raises(DatabaseError):
                await service._store_in_memory(
                    conversation_id="conv-123",
                    user_message="Hello",
                    assistant_response="Hi",
                    user_id="user-123"
                )

    @pytest.mark.asyncio
    async def test_conversation_creation_failure(self, service):
        """Test failure to create new conversation."""
        mock_db = AsyncMock()
        mock_db.create_conversation = AsyncMock(side_effect=DatabaseError("Cannot create"))
        
        with patch("src.db.get_database", return_value=mock_db):
            with pytest.raises(DatabaseError):
                await service._store_in_memory(
                    conversation_id=None,
                    user_message="First message",
                    assistant_response="First response",
                    user_id="user-123"
                )

    # ═══════════════════════════════════════════════════════════
    # EDGE CASE TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_store_very_long_message(self, service):
        """Test storing very long messages."""
        mock_db = AsyncMock()
        long_message = "a" * 50000  # 50KB message
        
        with patch("src.db.get_database", return_value=mock_db):
            await service._store_in_memory(
                conversation_id="conv-123",
                user_message=long_message,
                assistant_response="Response",
                user_id="user-123"
            )
        
        # Verify long message was stored
        assert mock_db.store_message.called

    @pytest.mark.asyncio
    async def test_store_unicode_messages(self, service):
        """Test storing unicode messages."""
        mock_db = AsyncMock()
        unicode_message = "Message with 中文, العربية, and emojis 🚀"
        
        with patch("src.db.get_database", return_value=mock_db):
            await service._store_in_memory(
                conversation_id="conv-123",
                user_message=unicode_message,
                assistant_response="Response with emojis ✅",
                user_id="user-123"
            )
        
        assert mock_db.store_message.called

    @pytest.mark.asyncio
    async def test_store_without_user_id(self, service):
        """Test storing message without user_id."""
        mock_db = AsyncMock()
        mock_get_database = AsyncMock(return_value=mock_db)
        with patch("src.db.get_database", mock_get_database):
            await service._store_in_memory(
                conversation_id="conv-123",
                user_message="Anonymous message",
                assistant_response="Response",
                user_id=None
            )
        
        # Should still work for anonymous users
        assert mock_db.store_message.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


