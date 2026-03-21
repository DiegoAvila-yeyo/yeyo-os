"""
Tests para SystemPromptBuilder — Micro-fase 2.13
Tests unitarios.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.chat.system_prompt import (
    SystemPromptBuilder,
    BASE_PROMPT,
    MAX_PROMPT_TOKENS,
)
from src.chat.token_budget import TokenBudget
from src.memory.models import Memory


class TestBasePrompt:
    """Tests del prompt base."""

    def test_base_prompt_exists(self):
        assert BASE_PROMPT is not None
        assert len(BASE_PROMPT) > 0

    def test_base_prompt_contains_yeyoos(self):
        assert "YeyoOS" in BASE_PROMPT

    def test_base_prompt_in_spanish(self):
        assert "español" in BASE_PROMPT

    def test_base_prompt_fits_budget(self):
        tokens = TokenBudget.count_tokens(BASE_PROMPT)
        assert tokens <= MAX_PROMPT_TOKENS

    def test_max_tokens_is_300(self):
        assert MAX_PROMPT_TOKENS == 300

    def test_get_base_prompt_static(self):
        assert SystemPromptBuilder.get_base_prompt() == BASE_PROMPT

    def test_get_max_tokens_static(self):
        assert SystemPromptBuilder.get_max_tokens() == 300


class TestBuildPrompt:
    """Tests de construcción dinámica."""

    @pytest.mark.asyncio
    async def test_build_without_memory(self):
        builder = SystemPromptBuilder(flash_memory=None)
        prompt = await builder.build()
        assert BASE_PROMPT in prompt

    @pytest.mark.asyncio
    async def test_build_fits_in_300_tokens(self):
        builder = SystemPromptBuilder(flash_memory=None)
        prompt = await builder.build()
        assert TokenBudget.count_tokens(prompt) <= 300

    @pytest.mark.asyncio
    async def test_build_with_preferences(self):
        mock_memory = AsyncMock()
        mock_memory.recall_by_type.return_value = [
            Memory(
                content="Prefiere Python",
                type="preference",
                checksum="a" * 64,
            ),
            Memory(
                content="Le gusta el modo oscuro",
                type="preference",
                checksum="b" * 64,
            ),
        ]
        builder = SystemPromptBuilder(flash_memory=mock_memory)
        prompt = await builder.build()
        assert "Prefiere Python" in prompt
        assert "modo oscuro" in prompt

    @pytest.mark.asyncio
    async def test_build_never_exceeds_budget(self):
        mock_memory = AsyncMock()
        # Muchas preferencias largas
        mock_memory.recall_by_type.return_value = [
            Memory(
                content="x" * 500,
                type="preference",
                checksum=f"{i}" * 64,
            )
            for i in range(10)
        ]
        builder = SystemPromptBuilder(flash_memory=mock_memory)
        prompt = await builder.build()
        assert TokenBudget.count_tokens(prompt) <= 300

    @pytest.mark.asyncio
    async def test_build_with_context(self):
        builder = SystemPromptBuilder(flash_memory=None)
        prompt = await builder.build(context={
            "mode": "programación",
            "language": "español",
        })
        assert "programación" in prompt

    @pytest.mark.asyncio
    async def test_build_with_empty_context(self):
        builder = SystemPromptBuilder(flash_memory=None)
        prompt = await builder.build(context={})
        assert BASE_PROMPT in prompt

    @pytest.mark.asyncio
    async def test_build_memory_error_handled(self):
        """Error en Flash Memory no crashea el builder."""
        mock_memory = AsyncMock()
        mock_memory.recall_by_type.side_effect = Exception("DB error")
        builder = SystemPromptBuilder(flash_memory=mock_memory)
        prompt = await builder.build()
        assert BASE_PROMPT in prompt  # Fallback al base

    @pytest.mark.asyncio
    async def test_build_includes_preferences_section(self):
        mock_memory = AsyncMock()
        mock_memory.recall_by_type.return_value = [
            Memory(
                content="Le gusta café",
                type="preference",
                checksum="a" * 64,
            ),
        ]
        builder = SystemPromptBuilder(flash_memory=mock_memory)
        prompt = await builder.build()
        assert "[Preferencias del usuario]" in prompt
