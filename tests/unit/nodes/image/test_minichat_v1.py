"""Tests para MiniChat v1 — Micro-fase 5.4"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.nodes.image.minichat.service import MiniChatV1Service


class TestMiniChatV1:

    @pytest.mark.asyncio
    async def test_open_generates_greeting(self):
        service = MiniChatV1Service()
        service._analysis_service.analyze = AsyncMock(return_value={
            "description": "A beautiful sunset over the ocean",
            "model_used": "llava:7b",
        })
        result = await service.open_for_image(b"fake_image")
        assert "message" in result
        assert len(service._messages) == 1

    @pytest.mark.asyncio
    async def test_open_handles_analysis_failure(self):
        service = MiniChatV1Service()
        service._analysis_service.analyze = AsyncMock(return_value={
            "error": "No model available",
            "fallback": "text_only",
        })
        result = await service.open_for_image(b"fake_image")
        assert "message" in result
        assert "No pude" in result["message"]

    @pytest.mark.asyncio
    async def test_ask_about_image(self):
        service = MiniChatV1Service()
        service._image_data = b"fake_image"
        service._analysis_service.analyze = AsyncMock(return_value={
            "description": "There are 3 cats in the image",
            "model_used": "llava:7b",
        })
        result = await service.ask("How many cats?")
        assert result["answer"] == "There are 3 cats in the image"
        assert result["question"] == "How many cats?"

    @pytest.mark.asyncio
    async def test_ask_without_image_returns_error(self):
        service = MiniChatV1Service()
        result = await service.ask("test question")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_messages_stored(self):
        service = MiniChatV1Service()
        service._image_data = b"fake_image"
        service._analysis_service.analyze = AsyncMock(return_value={
            "description": "Response", "model_used": "llava:7b",
        })
        await service.ask("Q1")
        await service.ask("Q2")
        messages = service.get_messages()
        assert len(messages) == 4  # 2 user + 2 assistant

    def test_close_clears_state(self):
        service = MiniChatV1Service()
        service._image_data = b"fake"
        service._messages.append(MagicMock())
        service.close()
        assert service._image_data is None
        assert len(service._messages) == 0

    @pytest.mark.asyncio
    async def test_get_messages_format(self):
        service = MiniChatV1Service()
        service._image_data = b"fake_image"
        service._analysis_service.analyze = AsyncMock(return_value={
            "description": "A dog", "model_used": "llava:7b",
        })
        await service.ask("What is this?")
        messages = service.get_messages()
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert "timestamp" in messages[0]
