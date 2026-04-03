"""
Test critical bug fixes for ChatNodeService

Verifies:
1. CRITICAL #1: Retry logic handles all OllamaError types
2. CRITICAL #2: Exception handlers return correct error codes
3. LOW: tokens_used validation
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.nodes.chat.service_integration import ChatNodeService
from src.nodes.chat.types import (
    ChatNodeError,
    ChatNodeOutput,
    ErrorCode,
    ConversationTone,
    ConversationType,
)
from src.nodes.chat.exceptions import (
    OllamaError,
    OllamaOutOfMemoryError,
    OllamaInvalidResponseError,
    OllamaUnreachableError,
    SystemPromptGenerationError,
    AgentValidationError,
    InvalidConfidenceError,
    DatabaseError,
    RequestTimeoutError,
)


class TestCriticalFix1_RetryLogic:
    """Test that ALL OllamaError types are retried."""

    @pytest.fixture
    def service(self):
        return ChatNodeService()

    @pytest.mark.asyncio
    async def test_retry_on_out_of_memory_error(self, service):
        """Test retry logic handles OllamaOutOfMemoryError."""
        attempt_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise OllamaOutOfMemoryError("Out of memory")
            return "Success"

        with patch.object(service, "_do_ollama_call", side_effect=mock_call):
            result = await service._call_ollama_with_retry(
                system_prompt="test",
                user_message="test",
                message_history=[]
            )

        # Should succeed on retry
        assert result == "Success"
        assert attempt_count == 3  # Failed 2 times, succeeded on 3rd

    @pytest.mark.asyncio
    async def test_retry_on_invalid_response_error(self, service):
        """Test retry logic handles OllamaInvalidResponseError."""
        attempt_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise OllamaInvalidResponseError("Invalid response")
            return "Valid response"

        with patch.object(service, "_do_ollama_call", side_effect=mock_call):
            result = await service._call_ollama_with_retry(
                system_prompt="test",
                user_message="test",
                message_history=[]
            )

        assert result == "Valid response"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_retry_fails_after_max_attempts(self, service):
        """Test that retry gives up after max attempts."""
        attempt_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise OllamaOutOfMemoryError("Always fails")

        with patch.object(service, "_do_ollama_call", side_effect=mock_call):
            with pytest.raises(OllamaOutOfMemoryError):
                await service._call_ollama_with_retry(
                    system_prompt="test",
                    user_message="test",
                    message_history=[]
                )

        assert attempt_count == service.OLLAMA_RETRY_ATTEMPTS


class TestCriticalFix2_ExceptionHandlers:
    """Test that exception handlers return correct error codes."""

    @pytest.fixture
    def service(self):
        return ChatNodeService()

    @pytest.mark.asyncio
    async def test_system_prompt_generation_error_code(self, service):
        """Test SystemPromptGenerationError returns correct error code."""
        with patch.object(service, "_validate_input", return_value=Mock(is_valid=True)):
            with patch.object(service, "_load_conversation_context", return_value=Mock()):
                with patch.object(service, "_get_system_prompt", side_effect=SystemPromptGenerationError("Failed")):
                    result = await service.process_message("test")

        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_SYSTEM_PROMPT_GENERATION

    @pytest.mark.asyncio
    async def test_agent_validation_error_code(self, service):
        """Test AgentValidationError returns correct error code."""
        with patch.object(service, "_validate_input", return_value=Mock(is_valid=True)):
            with patch.object(service, "_load_conversation_context", return_value=Mock()):
                with patch.object(service, "_get_system_prompt", return_value="prompt"):
                    with patch.object(service, "_call_ollama_with_retry", return_value="response"):
                        with patch.object(service, "_validate_ollama_output", side_effect=AgentValidationError("Failed")):
                            result = await service.process_message("test")

        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_AGENT_VALIDATION_FAILED

    @pytest.mark.asyncio
    async def test_ollama_out_of_memory_error_code(self, service):
        """Test OllamaOutOfMemoryError returns correct error code."""
        with patch.object(service, "_validate_input", return_value=Mock(is_valid=True)):
            with patch.object(service, "_load_conversation_context", return_value=Mock()):
                with patch.object(service, "_get_system_prompt", return_value="prompt"):
                    with patch.object(service, "_call_ollama_with_retry", side_effect=OllamaOutOfMemoryError("OOM")):
                        result = await service.process_message("test")

        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_OLLAMA_OUT_OF_MEMORY

    @pytest.mark.asyncio
    async def test_ollama_invalid_response_error_code(self, service):
        """Test OllamaInvalidResponseError returns correct error code."""
        with patch.object(service, "_validate_input", return_value=Mock(is_valid=True)):
            with patch.object(service, "_load_conversation_context", return_value=Mock()):
                with patch.object(service, "_get_system_prompt", return_value="prompt"):
                    with patch.object(service, "_call_ollama_with_retry", side_effect=OllamaInvalidResponseError("Invalid")):
                        result = await service.process_message("test")

        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE

    @pytest.mark.asyncio
    async def test_invalid_confidence_error_code(self, service):
        """Test InvalidConfidenceError returns correct error code."""
        with patch.object(service, "_validate_input", return_value=Mock(is_valid=True)):
            with patch.object(service, "_load_conversation_context", return_value=Mock()):
                with patch.object(service, "_get_system_prompt", return_value="prompt"):
                    with patch.object(service, "_call_ollama_with_retry", return_value="response"):
                        with patch.object(service, "_validate_ollama_output", return_value=Mock(is_valid=True)):
                            with patch.object(service, "_store_in_memory", side_effect=InvalidConfidenceError("Invalid confidence")):
                                result = await service.process_message("test")

        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_INVALID_CONFIDENCE

    @pytest.mark.asyncio
    async def test_database_error_code(self, service):
        """Test DatabaseError returns correct error code."""
        with patch.object(service, "_validate_input", return_value=Mock(is_valid=True)):
            with patch.object(service, "_load_conversation_context", side_effect=DatabaseError("DB error")):
                result = await service.process_message("test")

        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_DATABASE

    @pytest.mark.asyncio
    async def test_request_timeout_error_code(self, service):
        """Test RequestTimeoutError returns correct error code."""
        with patch.object(service, "_validate_input", return_value=Mock(is_valid=True)):
            with patch.object(service, "_load_conversation_context", return_value=Mock()):
                with patch.object(service, "_get_system_prompt", return_value="prompt"):
                    with patch.object(service, "_call_ollama_with_retry", side_effect=RequestTimeoutError("Timeout")):
                        result = await service.process_message("test")

        assert isinstance(result, ChatNodeError)
        assert result.error_code == ErrorCode.ERROR_REQUEST_TIMEOUT


class TestLowFix_TokensValidation:
    """Test tokens_used non-negative validation."""

    def test_negative_tokens_rejected(self):
        """Test ChatNodeOutput rejects negative tokens_used."""
        with pytest.raises(ValueError, match="tokens_used must be non-negative"):
            ChatNodeOutput(
                response="test",
                confidence=0.8,
                reasoning="test",
                tokens_used=-100
            )

    def test_zero_tokens_accepted(self):
        """Test ChatNodeOutput accepts zero tokens_used."""
        output = ChatNodeOutput(
            response="test",
            confidence=0.8,
            reasoning="test",
            tokens_used=0
        )
        assert output.tokens_used == 0

    def test_positive_tokens_accepted(self):
        """Test ChatNodeOutput accepts positive tokens_used."""
        output = ChatNodeOutput(
            response="test",
            confidence=0.8,
            reasoning="test",
            tokens_used=100
        )
        assert output.tokens_used == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
