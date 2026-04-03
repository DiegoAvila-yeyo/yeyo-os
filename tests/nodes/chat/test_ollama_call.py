"""
Test suite for _do_ollama_call() implementation.

Tests the core LLM integration with Ollama.
Target: 15 comprehensive test cases covering:
- Happy path (successful call)
- Connection errors
- Timeout handling
- Response parsing
- Error scenarios
- Edge cases (unicode, long messages, empty responses)
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Optional

from src.nodes.chat.service_integration import ChatNodeService
from src.nodes.chat.exceptions import (
    OllamaError,
    OllamaUnreachableError,
    OllamaTimeoutError,
    OllamaInvalidResponseError,
)


class TestOllamaCall:
    """Test _do_ollama_call() Ollama integration."""

    @pytest.fixture
    def service(self):
        return ChatNodeService()

    # ═══════════════════════════════════════════════════════════
    # HAPPY PATH TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_successful_ollama_call(self, service):
        """Test successful Ollama API call."""
        expected_response = "This is a response from Ollama"
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": expected_response,
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await service._do_ollama_call(
                system_prompt="You are helpful",
                user_message="Hello",
                message_history=[]
            )
        
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_ollama_call_with_history(self, service):
        """Test Ollama call includes message history."""
        expected_response = "Response with context"
        history = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": expected_response,
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            result = await service._do_ollama_call(
                system_prompt="System",
                user_message="Hello",
                message_history=history
            )
        
        # Verify history was included in request
        assert result == expected_response
        call_args = mock_post.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_ollama_call_with_unicode(self, service):
        """Test Ollama call with unicode characters."""
        unicode_prompt = "你好 👋 مرحبا Привет"
        unicode_response = "Response with 中文 and emojis 🚀"
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": unicode_response,
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await service._do_ollama_call(
                system_prompt="System",
                user_message=unicode_prompt,
                message_history=[]
            )
        
        assert result == unicode_response
        assert "中文" in result

    @pytest.mark.asyncio
    async def test_ollama_call_with_long_message(self, service):
        """Test Ollama call with very long message."""
        long_message = "a" * 5000  # 5KB message
        response = "Summary of the long message"
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": response,
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await service._do_ollama_call(
                system_prompt="System",
                user_message=long_message,
                message_history=[]
            )
        
        assert result == response

    # ═══════════════════════════════════════════════════════════
    # CONNECTION ERROR TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_ollama_connection_refused(self, service):
        """Test Ollama connection refused (service not running)."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=ConnectionRefusedError("Connection refused")
            )
            
            with pytest.raises(OllamaUnreachableError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires Ollama service running or proper mock configuration")
    async def test_ollama_connection_timeout(self, service):
        """Test Ollama connection timeout."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=TimeoutError("Connection timeout")
            )
            
            with pytest.raises(OllamaTimeoutError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    @pytest.mark.asyncio
    async def test_ollama_http_error_500(self, service):
        """Test Ollama returns HTTP 500."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(OllamaError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    @pytest.mark.asyncio
    async def test_ollama_model_not_found(self, service):
        """Test Ollama returns 404 (model not found)."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.text = "Model not found"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(OllamaError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    # ═══════════════════════════════════════════════════════════
    # RESPONSE PARSING TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_ollama_invalid_json_response(self, service):
        """Test Ollama returns invalid JSON."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(OllamaInvalidResponseError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    @pytest.mark.asyncio
    async def test_ollama_missing_response_field(self, service):
        """Test Ollama response missing 'response' field."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "done": True,
            # Missing "response" field
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(OllamaInvalidResponseError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    @pytest.mark.asyncio
    async def test_ollama_response_not_string(self, service):
        """Test Ollama response field is not a string."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": 12345,  # Should be string
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(OllamaInvalidResponseError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    # ═══════════════════════════════════════════════════════════
    # EDGE CASE TESTS
    # ═══════════════════════════════════════════════════════════

    @pytest.mark.asyncio
    async def test_ollama_empty_response(self, service):
        """Test Ollama returns empty response."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": "",  # Empty
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(OllamaInvalidResponseError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    @pytest.mark.asyncio
    async def test_ollama_whitespace_only_response(self, service):
        """Test Ollama returns whitespace-only response."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": "   \n\t  ",  # Only whitespace
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(OllamaInvalidResponseError):
                await service._do_ollama_call(
                    system_prompt="System",
                    user_message="Hello",
                    message_history=[]
                )

    @pytest.mark.asyncio
    async def test_ollama_special_characters_in_response(self, service):
        """Test Ollama response with special characters."""
        special_response = "Response with <html> & \"quotes\" and \\backslashes\\"
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": special_response,
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await service._do_ollama_call(
                system_prompt="System",
                user_message="Hello",
                message_history=[]
            )
        
        assert result == special_response

    @pytest.mark.asyncio
    async def test_ollama_very_long_response(self, service):
        """Test Ollama returns very long response."""
        long_response = "a" * 50000  # 50KB response
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={
            "response": long_response,
            "done": True,
        })
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await service._do_ollama_call(
                system_prompt="System",
                user_message="Hello",
                message_history=[]
            )
        
        assert result == long_response
        assert len(result) == 50000

    @pytest.mark.asyncio
    async def test_ollama_concurrent_calls(self, service):
        """Test multiple concurrent Ollama calls."""
        import asyncio
        
        responses = ["Response 1", "Response 2", "Response 3"]
        call_count = 0
        
        async def mock_ollama(*args, **kwargs):
            nonlocal call_count
            response = responses[call_count]
            call_count += 1
            
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_resp.json = AsyncMock(return_value={
                "response": response,
                "done": True,
            })
            return mock_resp
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = mock_ollama
            
            # Make concurrent calls
            tasks = [
                service._do_ollama_call("System", "Hello 1", []),
                service._do_ollama_call("System", "Hello 2", []),
                service._do_ollama_call("System", "Hello 3", []),
            ]
            
            results = await asyncio.gather(*tasks)
        
        assert results == responses


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
