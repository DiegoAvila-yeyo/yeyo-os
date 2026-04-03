"""
Test suite for _validate_ollama_output() implementation.

Tests the output validation logic that ensures Ollama responses meet quality standards.
Target: 12 comprehensive test cases covering:
- Valid responses
- Format validation
- Quality checks
- Edge cases
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.nodes.chat.service_integration import ChatNodeService
from src.nodes.chat.types import ErrorCode, ValidationResult
from src.nodes.chat.exceptions import AgentValidationError


class TestValidateOllamaOutput:
    """Test _validate_ollama_output() output validation."""

    @pytest.fixture
    def service(self):
        return ChatNodeService()

    # ═══════════════════════════════════════════════════════════
    # VALID RESPONSE TESTS
    # ═══════════════════════════════════════════════════════════

    def test_valid_simple_response(self, service):
        """Test valid simple response passes validation."""
        result = service._validate_ollama_output("This is a valid response")
        assert result.is_valid
        assert result.error_code is None

    def test_valid_long_response(self, service):
        """Test valid long response passes validation."""
        long_response = "a" * 10000
        result = service._validate_ollama_output(long_response)
        assert result.is_valid

    def test_valid_response_with_newlines(self, service):
        """Test response with newlines passes validation."""
        response = "Line 1\nLine 2\nLine 3"
        result = service._validate_ollama_output(response)
        assert result.is_valid

    def test_valid_response_with_special_chars(self, service):
        """Test response with special characters passes validation."""
        response = "Response with <html> & \"quotes\" and \\backslashes\\"
        result = service._validate_ollama_output(response)
        assert result.is_valid

    def test_valid_response_with_unicode(self, service):
        """Test response with unicode characters passes validation."""
        response = "Response with 中文 和 emojis 🚀"
        result = service._validate_ollama_output(response)
        assert result.is_valid

    # ═══════════════════════════════════════════════════════════
    # INVALID RESPONSE TESTS
    # ═══════════════════════════════════════════════════════════

    def test_invalid_response_not_string(self, service):
        """Test non-string response fails validation."""
        result = service._validate_ollama_output(12345)
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE

    def test_invalid_response_empty_string(self, service):
        """Test empty string fails validation."""
        result = service._validate_ollama_output("")
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE

    def test_invalid_response_whitespace_only(self, service):
        """Test whitespace-only response fails validation."""
        result = service._validate_ollama_output("   \n\t  ")
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE

    def test_invalid_response_none(self, service):
        """Test None response fails validation."""
        result = service._validate_ollama_output(None)
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE

    # ═══════════════════════════════════════════════════════════
    # AGENT VALIDATION TESTS
    # ═══════════════════════════════════════════════════════════

    def test_agent_validation_success(self, service):
        """Test successful agent validation."""
        mock_agent = Mock()
        mock_agent.validate_output = Mock(return_value={"valid": True})
        
        with patch("src.nodes.chat.service_integration.ConversationAgent", return_value=mock_agent):
            result = service._validate_ollama_output("Valid response")
        
        assert result.is_valid
        mock_agent.validate_output.assert_called_once()

    def test_agent_validation_fails(self, service):
        """Test failed agent validation."""
        mock_agent = Mock()
        mock_agent.validate_output = Mock(return_value={"valid": False, "reason": "Hallucination detected"})
        
        with patch("src.nodes.chat.service_integration.ConversationAgent", return_value=mock_agent):
            result = service._validate_ollama_output("Response with hallucination")
        
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_AGENT_VALIDATION_FAILED

    def test_agent_validation_error_propagates(self, service):
        """Test agent validation error is properly handled."""
        mock_agent = Mock()
        mock_agent.validate_output = Mock(side_effect=AgentValidationError("Validation failed"))
        
        with patch("src.nodes.chat.service_integration.ConversationAgent", return_value=mock_agent):
            result = service._validate_ollama_output("Response")
        
        assert not result.is_valid
        assert result.error_code == ErrorCode.ERROR_AGENT_VALIDATION_FAILED

    # ═══════════════════════════════════════════════════════════
    # EDGE CASE TESTS
    # ═══════════════════════════════════════════════════════════

    def test_response_with_leading_trailing_spaces(self, service):
        """Test response with leading/trailing spaces is trimmed properly."""
        response = "   Valid response with spaces   "
        result = service._validate_ollama_output(response)
        # Should be valid after trimming
        assert result.is_valid

    def test_response_single_character(self, service):
        """Test single character response passes validation."""
        result = service._validate_ollama_output("a")
        assert result.is_valid

    def test_response_single_emoji(self, service):
        """Test single emoji response passes validation."""
        result = service._validate_ollama_output("🚀")
        assert result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
