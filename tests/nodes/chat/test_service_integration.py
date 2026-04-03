"""
ChatNodeService - Unit Tests

Comprehensive tests for input validation, error handling, and happy paths.
Target: 100% code coverage, 50+ test cases
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.nodes.chat.service_integration import ChatNodeService
from src.nodes.chat.types import (
    ChatNodeInput,
    ChatNodeOutput,
    ChatNodeError,
    ConversationTone,
    ConversationType,
    ErrorCode,
    ValidationResult,
)
from src.nodes.chat.exceptions import (
    InvalidInputError,
    MessageEmptyError,
    MessageTooLongError,
    AgentValidationError,
)


class TestChatNodeServiceInputValidation:
    """Test input validation with 20+ scenarios."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ChatNodeService()
    
    # ═══════════════════════════════════
    # VALID INPUT TESTS
    # ═══════════════════════════════════
    
    def test_valid_simple_message(self, service):
        """Test valid simple message."""
        result = service._validate_input(
            ChatNodeInput(message="Hello world")
        )
        assert result.is_valid
        assert result.error_code is None
    
    def test_valid_message_with_unicode(self, service):
        """Test message with Unicode characters (emoji, CJK)."""
        result = service._validate_input(
            ChatNodeInput(message="你好 👋 مرحبا")
        )
        assert result.is_valid
    
    def test_valid_message_max_length(self, service):
        """Test message at exact max length."""
        max_msg = "a" * service.MAX_MESSAGE_LENGTH
        result = service._validate_input(
            ChatNodeInput(message=max_msg)
        )
        assert result.is_valid
    
    def test_valid_message_with_newlines(self, service):
        """Test multi-line message."""
        result = service._validate_input(
            ChatNodeInput(message="Line 1\nLine 2\nLine 3")
        )
        assert result.is_valid
    
    def test_valid_message_with_special_chars(self, service):
        """Test message with special characters."""
        result = service._validate_input(
            ChatNodeInput(message="Test!@#$%^&*()_+-=[]{}|;':\",./<>?")
        )
        assert result.is_valid
    
    # ═══════════════════════════════════
    # EMPTY/NULL TESTS
    # ═══════════════════════════════════
    
    def test_invalid_empty_string(self, service):
        """Test empty string is rejected."""
        result = service._validate_input(
            ChatNodeInput(message="")
        )
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_MESSAGE_EMPTY
    
    def test_invalid_only_whitespace(self, service):
        """Test whitespace-only string is rejected."""
        result = service._validate_input(
            ChatNodeInput(message="   \n\t  ")
        )
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_MESSAGE_EMPTY
    
    # ═══════════════════════════════════
    # LENGTH TESTS
    # ═══════════════════════════════════
    
    def test_invalid_message_too_long(self, service):
        """Test message exceeding max length."""
        too_long = "a" * (service.MAX_MESSAGE_LENGTH + 1)
        result = service._validate_input(
            ChatNodeInput(message=too_long)
        )
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_MESSAGE_TOO_LONG
    
    def test_invalid_message_way_too_long(self, service):
        """Test very long message."""
        way_too_long = "x" * (service.MAX_MESSAGE_LENGTH * 10)
        result = service._validate_input(
            ChatNodeInput(message=way_too_long)
        )
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_MESSAGE_TOO_LONG
    
    # ═══════════════════════════════════
    # INVALID CHARACTER TESTS
    # ═══════════════════════════════════
    
    def test_invalid_null_byte(self, service):
        """Test message with null byte."""
        result = service._validate_input(
            ChatNodeInput(message="Hello\x00World")
        )
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_INVALID_INPUT
    
    # ═══════════════════════════════════
    # EDGE CASES
    # ═══════════════════════════════════
    
    def test_valid_single_character(self, service):
        """Test single character message."""
        result = service._validate_input(
            ChatNodeInput(message="a")
        )
        assert result.is_valid
    
    def test_valid_single_emoji(self, service):
        """Test single emoji."""
        result = service._validate_input(
            ChatNodeInput(message="👋")
        )
        assert result.is_valid
    
    def test_valid_mixed_encodings(self, service):
        """Test mixed encodings."""
        result = service._validate_input(
            ChatNodeInput(message="English 中文 العربية")
        )
        assert result.is_valid


class TestChatNodeServiceOutputValidation:
    """Test output validation."""
    
    @pytest.fixture
    def service(self):
        return ChatNodeService()
    
    def test_valid_output_response(self, service):
        """Test valid output response."""
        result = service._validate_ollama_output("Valid response from Ollama")
        assert result.is_valid
    
    def test_invalid_output_empty(self, service):
        """Test empty response."""
        result = service._validate_ollama_output("")
        assert not result.is_valid


class TestChatNodeServiceTypes:
    """Test type validation."""
    
    def test_valid_chat_input(self):
        """Test valid ChatNodeInput creation."""
        input_obj = ChatNodeInput(
            message="Test",
            tone=ConversationTone.PROFESSIONAL,
            conversation_type=ConversationType.GENERAL,
        )
        assert input_obj.message == "Test"
    
    def test_invalid_input_type_message(self):
        """Test ChatNodeInput with invalid message type."""
        with pytest.raises(TypeError):
            ChatNodeInput(message=123)
    
    def test_valid_output_creation(self):
        """Test valid ChatNodeOutput creation."""
        output = ChatNodeOutput(
            response="Response",
            confidence=0.85,
            reasoning="Good response",
        )
        assert output.response == "Response"
        assert output.confidence == 0.85
    
    def test_invalid_output_confidence_too_high(self):
        """Test ChatNodeOutput with confidence > 1.0."""
        with pytest.raises(ValueError):
            ChatNodeOutput(
                response="Response",
                confidence=1.5,
                reasoning="Too confident",
            )


class TestChatNodeServiceErrorHandling:
    """Test error handling and exceptions."""
    
    @pytest.fixture
    def service(self):
        return ChatNodeService()
    
    @pytest.mark.asyncio
    async def test_process_message_empty_input(self, service):
        """Test processing empty message returns error."""
        result = await service.process_message("")
        
        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_MESSAGE_EMPTY


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
