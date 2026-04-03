"""
Test suite for _load_conversation_context() implementation.

Tests the conversation context loading from database.
Target: 10 comprehensive test cases covering:
- Loading existing conversation
- Handling missing conversations
- Message history loading
- User preferences
- Conversation statistics
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, timezone

from src.nodes.chat.service_integration import ChatNodeService
from src.nodes.chat.types import ConversationContext, ConversationType, ConversationTone
from src.nodes.chat.exceptions import DatabaseError, MemoryInjectionError


class TestLoadConversationContext:
    """Test _load_conversation_context() context loading."""

    @pytest.fixture
    def service(self):
        return ChatNodeService()

    # ═══════════════════════════════════════════════════════════
    # SUCCESSFUL LOADING TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_load_existing_conversation(self, service):
        """Test loading existing conversation."""
        mock_db = AsyncMock()
        mock_db.get_conversation = AsyncMock(return_value={
            "id": "conv-123",
            "message_count": 10,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=1),
        })
        mock_db.get_messages = AsyncMock(return_value=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ])
        mock_db.get_user_preferences = AsyncMock(return_value={
            "language": "en",
            "verbosity": "medium",
        })
        
        with patch("src.db.get_database", return_value=mock_db):
            context = await service._load_conversation_context(
                conversation_id="conv-123",
                user_id="user-456",
                conversation_type=ConversationType.GENERAL,
                tone=ConversationTone.PROFESSIONAL,
            )
        
        assert context is not None
        assert isinstance(context, ConversationContext)
        assert context.conversation_id == "conv-123"
        assert context.message_count == 10

    @pytest.mark.asyncio
    async def test_load_new_conversation(self, service):
        """Test loading context for new conversation (no ID)."""
        mock_db = AsyncMock()
        mock_get_database = AsyncMock(return_value=mock_db)
        with patch("src.db.get_database", mock_get_database):
            context = await service._load_conversation_context(
                conversation_id=None,
                user_id="user-789",
                conversation_type=ConversationType.SUPPORT,
                tone=ConversationTone.FRIENDLY,
            )
        
        assert context is not None
        assert context.message_count == 0
        assert context.history_last_20_messages == []

    @pytest.mark.asyncio
    async def test_load_conversation_with_history(self, service):
        """Test loads message history (last 20)."""
        mock_db = AsyncMock()
        messages = [
            {"role": "user", "content": f"Message {i}"} if i % 2 == 0
            else {"role": "assistant", "content": f"Response {i}"}
            for i in range(20)
        ]
        
        mock_db.get_conversation = AsyncMock(return_value={"id": "conv-123", "message_count": 50})
        mock_db.get_messages = AsyncMock(return_value=messages)
        mock_db.get_user_preferences = AsyncMock(return_value={})
        
        with patch("src.db.get_database", return_value=mock_db):
            context = await service._load_conversation_context(
                conversation_id="conv-123",
                user_id="user-456",
                conversation_type=ConversationType.GENERAL,
                tone=ConversationTone.PROFESSIONAL,
            )
        
        assert len(context.history_last_20_messages) == 20

    @pytest.mark.asyncio
    async def test_load_conversation_stats(self, service):
        """Test loads conversation statistics."""
        created = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_db = AsyncMock()
        mock_db.get_conversation = AsyncMock(return_value={
            "id": "conv-123",
            "message_count": 15,
            "created_at": created,
        })
        mock_db.get_messages = AsyncMock(return_value=[])
        mock_db.get_user_preferences = AsyncMock(return_value={})
        
        with patch("src.db.get_database", return_value=mock_db):
            context = await service._load_conversation_context(
                conversation_id="conv-123",
                user_id="user-456",
                conversation_type=ConversationType.GENERAL,
                tone=ConversationTone.PROFESSIONAL,
            )
        
        assert context.message_count == 15
        stats = context.get_conversation_stats()
        assert stats["message_count"] == 15

    @pytest.mark.asyncio
    async def test_load_user_preferences(self, service):
        """Test loads user preferences."""
        preferences = {
            "language": "es",
            "tone": "formal",
            "response_length": "short",
        }
        
        mock_db = AsyncMock()
        mock_db.get_conversation = AsyncMock(return_value={"id": "conv-123", "message_count": 5})
        mock_db.get_messages = AsyncMock(return_value=[])
        mock_db.get_user_preferences = AsyncMock(return_value=preferences)
        
        with patch("src.db.get_database", return_value=mock_db):
            context = await service._load_conversation_context(
                conversation_id="conv-123",
                user_id="user-456",
                conversation_type=ConversationType.GENERAL,
                tone=ConversationTone.PROFESSIONAL,
            )
        
        assert context.user_preferences == preferences

    # ═══════════════════════════════════════════════════════════
    # ERROR HANDLING TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_database_connection_error(self, service):
        """Test database connection error handling."""
        mock_db = AsyncMock()
        mock_db.get_conversation = AsyncMock(side_effect=ConnectionError("DB down"))
        
        with patch("src.db.get_database", return_value=mock_db):
            with pytest.raises(DatabaseError):
                await service._load_conversation_context(
                    conversation_id="conv-123",
                    user_id="user-456",
                    conversation_type=ConversationType.GENERAL,
                    tone=ConversationTone.PROFESSIONAL,
                )

    @pytest.mark.asyncio
    async def test_database_module_not_available(self, service):
        """Test when database module is not available."""
        with patch("src.db.get_database", side_effect=ImportError("DB module not found")):
            with pytest.raises(MemoryInjectionError):
                await service._load_conversation_context(
                    conversation_id="conv-123",
                    user_id="user-456",
                    conversation_type=ConversationType.GENERAL,
                    tone=ConversationTone.PROFESSIONAL,
                )

    @pytest.mark.asyncio
    async def test_conversation_not_found(self, service):
        """Test handling non-existent conversation."""
        mock_db = AsyncMock()
        mock_db.get_conversation = AsyncMock(return_value=None)
        
        with patch("src.db.get_database", return_value=mock_db):
            context = await service._load_conversation_context(
                conversation_id="conv-nonexistent",
                user_id="user-456",
                conversation_type=ConversationType.GENERAL,
                tone=ConversationTone.PROFESSIONAL,
            )
        
        # Should return empty context for non-existent conversation
        assert context.message_count == 0

    # ═══════════════════════════════════════════════════════════
    # EDGE CASE TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_load_conversation_no_user_id(self, service):
        """Test loading conversation without user_id (anonymous)."""
        mock_db = AsyncMock()
        mock_db.get_conversation = AsyncMock(return_value={"id": "conv-123", "message_count": 3})
        mock_db.get_messages = AsyncMock(return_value=[])
        mock_db.get_user_preferences = AsyncMock(return_value={})
        
        with patch("src.db.get_database", return_value=mock_db):
            context = await service._load_conversation_context(
                conversation_id="conv-123",
                user_id=None,
                conversation_type=ConversationType.GENERAL,
                tone=ConversationTone.PROFESSIONAL,
            )
        
        assert context is not None
        assert context.user_id is None

    @pytest.mark.asyncio
    async def test_load_conversation_partial_preferences(self, service):
        """Test loading when some preferences missing."""
        mock_db = AsyncMock()
        mock_db.get_conversation = AsyncMock(return_value={"id": "conv-123", "message_count": 1})
        mock_db.get_messages = AsyncMock(return_value=[])
        mock_db.get_user_preferences = AsyncMock(return_value={})  # Empty preferences
        
        with patch("src.db.get_database", return_value=mock_db):
            context = await service._load_conversation_context(
                conversation_id="conv-123",
                user_id="user-456",
                conversation_type=ConversationType.GENERAL,
                tone=ConversationTone.PROFESSIONAL,
            )
        
        # Should have empty dict but not fail
        assert context.user_preferences == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


