"""
Tests para ChatService — Micro-fase 2.5
Tests unitarios con mock de IAProvider.
"""

import pytest
from unittest.mock import AsyncMock
from src.chat.service import ChatService, DEFAULT_SYSTEM_PROMPT
from src.ia.interfaces import IAProvider, IAMessage, IAResponse


@pytest.fixture
def mock_ia_provider():
    provider = AsyncMock(spec=IAProvider)
    provider.chat.return_value = IAResponse(
        content="Hola, soy YeyoOS",
        model="qwen2.5:3b",
        tokens_used=15,
        latency_ms=100.0,
    )
    return provider


@pytest.fixture
def chat_service(mock_ia_provider):
    return ChatService(ia_provider=mock_ia_provider)


class TestChatServiceBasic:
    """Tests básicos del ChatService."""

    def test_has_default_system_prompt(self, chat_service):
        assert "YeyoOS" in chat_service.get_system_prompt()

    def test_default_system_prompt_content(self):
        assert "YeyoOS" in DEFAULT_SYSTEM_PROMPT
        assert "español" in DEFAULT_SYSTEM_PROMPT
        assert "conciso" in DEFAULT_SYSTEM_PROMPT

    def test_custom_system_prompt(self, mock_ia_provider):
        service = ChatService(ia_provider=mock_ia_provider, system_prompt="Custom prompt")
        assert service.get_system_prompt() == "Custom prompt"

    def test_set_system_prompt(self, chat_service):
        chat_service.set_system_prompt("Nuevo prompt")
        assert chat_service.get_system_prompt() == "Nuevo prompt"


class TestChatServiceMessages:
    """Tests de envío de mensajes."""

    @pytest.mark.asyncio
    async def test_send_message_returns_string(self, chat_service):
        result = await chat_service.send_message("Hola")
        assert isinstance(result, str)
        assert result == "Hola, soy YeyoOS"

    @pytest.mark.asyncio
    async def test_send_message_includes_system_prompt(self, chat_service, mock_ia_provider):
        await chat_service.send_message("Test")
        call_args = mock_ia_provider.chat.call_args
        messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
        assert messages[0].role == "system"
        assert "YeyoOS" in messages[0].content

    @pytest.mark.asyncio
    async def test_send_message_includes_user_input(self, chat_service, mock_ia_provider):
        await chat_service.send_message("Hola mundo")
        call_args = mock_ia_provider.chat.call_args
        messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
        assert messages[-1].role == "user"
        assert messages[-1].content == "Hola mundo"

    @pytest.mark.asyncio
    async def test_send_empty_message(self, chat_service):
        result = await chat_service.send_message("")
        assert "No recibí" in result

    @pytest.mark.asyncio
    async def test_send_whitespace_message(self, chat_service):
        result = await chat_service.send_message("   ")
        assert "No recibí" in result

    @pytest.mark.asyncio
    async def test_send_message_strips_input(self, chat_service, mock_ia_provider):
        await chat_service.send_message("  Hola  ")
        call_args = mock_ia_provider.chat.call_args
        messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
        assert messages[-1].content == "Hola"

    @pytest.mark.asyncio
    async def test_send_message_error_propagates(self, mock_ia_provider):
        mock_ia_provider.chat.side_effect = Exception("Ollama caído")
        service = ChatService(ia_provider=mock_ia_provider)
        with pytest.raises(Exception, match="Ollama caído"):
            await service.send_message("Test")


class TestChatServiceStreaming:
    """Tests de streaming."""

    @pytest.mark.asyncio
    async def test_stream_returns_chunks(self, mock_ia_provider):
        async def fake_stream(*args, **kwargs):
            for chunk in ["Hola", " ", "mundo"]:
                yield chunk

        mock_ia_provider.chat_stream = fake_stream
        service = ChatService(ia_provider=mock_ia_provider)

        chunks = []
        async for chunk in service.send_message_stream("Test"):
            chunks.append(chunk)
        assert len(chunks) == 3
        assert "".join(chunks) == "Hola mundo"

    @pytest.mark.asyncio
    async def test_stream_empty_message(self, chat_service):
        chunks = []
        async for chunk in chat_service.send_message_stream(""):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert "No recibí" in chunks[0]


class TestChatServiceHistory:
    """Tests de chat con historial."""

    @pytest.mark.asyncio
    async def test_send_with_history(self, chat_service, mock_ia_provider):
        history = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola!"},
        ]
        await chat_service.send_with_history("¿Cómo estás?", history)
        call_args = mock_ia_provider.chat.call_args
        messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
        assert len(messages) == 4  # system + 2 history + user
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[2].role == "assistant"
        assert messages[3].role == "user"
        assert messages[3].content == "¿Cómo estás?"

    @pytest.mark.asyncio
    async def test_send_with_empty_history(self, chat_service, mock_ia_provider):
        await chat_service.send_with_history("Test", history=None)
        call_args = mock_ia_provider.chat.call_args
        messages = call_args[0][0] if call_args[0] else call_args[1]["messages"]
        assert len(messages) == 2  # system + user
