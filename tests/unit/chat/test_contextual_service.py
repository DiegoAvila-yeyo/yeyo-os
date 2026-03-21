"""
Tests para ContextualChatService — Micro-fase 2.6
Tests unitarios con mocks de IAProvider, FlashMemory y EmbeddingService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.chat.contextual_service import (
    ContextualChatService,
    count_tokens,
    truncate_to_tokens,
    BUDGET_SYSTEM,
    BUDGET_MEMORIES,
    BUDGET_HISTORY,
    BUDGET_INPUT,
    BUDGET_RESPONSE,
    BUDGET_TOTAL,
)
from src.ia.interfaces import IAProvider, IAResponse
from src.memory.models import Memory


@pytest.fixture
def mock_ia():
    ia = AsyncMock(spec=IAProvider)
    ia.chat.return_value = IAResponse(
        content="Respuesta contextual",
        model="qwen2.5:3b",
        tokens_used=20,
        latency_ms=200.0,
    )
    return ia


@pytest.fixture
def mock_memory():
    fm = AsyncMock()
    fm.search_semantic.return_value = [
        Memory(id="mem-1", content="El usuario prefiere Python", type="preference", checksum="a" * 64),
        Memory(id="mem-2", content="El usuario se llama Diego", type="fact", checksum="b" * 64),
    ]
    return fm


@pytest.fixture
def mock_embeddings():
    emb = MagicMock()
    emb.generate.return_value = [0.1] * 384
    return emb


@pytest.fixture
def contextual_service(mock_ia, mock_memory, mock_embeddings):
    return ContextualChatService(ia=mock_ia, memory=mock_memory, embeddings=mock_embeddings)


class TestTokenBudgetConstants:
    def test_total_budget_is_4000(self):
        assert BUDGET_TOTAL == 4000

    def test_budget_components_sum_to_total(self):
        assert BUDGET_SYSTEM + BUDGET_MEMORIES + BUDGET_HISTORY + BUDGET_INPUT + BUDGET_RESPONSE == BUDGET_TOTAL

    def test_system_budget(self):
        assert BUDGET_SYSTEM == 300

    def test_memories_budget(self):
        assert BUDGET_MEMORIES == 1000

    def test_history_budget(self):
        assert BUDGET_HISTORY == 1500

    def test_input_budget(self):
        assert BUDGET_INPUT == 500

    def test_response_budget(self):
        assert BUDGET_RESPONSE == 700


class TestTokenCounting:
    def test_count_tokens_approximation(self):
        text = "Hola mundo test"
        tokens = count_tokens(text)
        assert tokens > 0

    def test_count_tokens_empty(self):
        assert count_tokens("") == 0

    def test_count_tokens_none(self):
        assert count_tokens(None) == 0

    def test_truncate_short_text(self):
        text = "Hola"
        assert truncate_to_tokens(text, 100) == text

    def test_truncate_long_text(self):
        text = "a " * 2000  # ~1000 tokens
        result = truncate_to_tokens(text, 10)
        assert count_tokens(result) <= 15


class TestBuildContext:
    @pytest.mark.asyncio
    async def test_build_context_returns_dict(self, contextual_service):
        ctx = await contextual_service.build_context("Hola")
        assert isinstance(ctx, dict)

    @pytest.mark.asyncio
    async def test_build_context_has_all_keys(self, contextual_service):
        ctx = await contextual_service.build_context("Hola")
        for key in ["system_prompt", "relevant_memories", "conversation_history", "user_input", "token_usage"]:
            assert key in ctx

    @pytest.mark.asyncio
    async def test_build_context_includes_memories(self, contextual_service):
        ctx = await contextual_service.build_context("¿Qué lenguaje prefiero?")
        assert len(ctx["relevant_memories"]) > 0
        assert "Python" in ctx["system_prompt"]

    @pytest.mark.asyncio
    async def test_build_context_token_usage(self, contextual_service):
        ctx = await contextual_service.build_context("Test")
        usage = ctx["token_usage"]
        for key in ["system", "memories", "history", "input", "reserved_response"]:
            assert key in usage
        assert usage["reserved_response"] == BUDGET_RESPONSE

    @pytest.mark.asyncio
    async def test_build_context_respects_total_budget(self, contextual_service):
        ctx = await contextual_service.build_context("Test con presupuesto")
        assert ctx["token_usage"]["total"] <= BUDGET_TOTAL

    @pytest.mark.asyncio
    async def test_build_context_empty_history(self, contextual_service):
        ctx = await contextual_service.build_context("Test", conversation_history=[])
        assert ctx["conversation_history"] == []

    @pytest.mark.asyncio
    async def test_build_context_with_history(self, contextual_service):
        history = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola!"},
        ]
        ctx = await contextual_service.build_context("Otra cosa", history)
        assert len(ctx["conversation_history"]) == 2

    @pytest.mark.asyncio
    async def test_build_context_truncates_long_history(self, contextual_service):
        history = [{"role": "user", "content": "x" * 3000} for _ in range(10)]
        ctx = await contextual_service.build_context("Test", history)
        total_history_tokens = sum(count_tokens(m["content"]) for m in ctx["conversation_history"])
        assert total_history_tokens <= BUDGET_HISTORY

    @pytest.mark.asyncio
    async def test_build_context_no_memories_found(self, mock_ia, mock_embeddings):
        mock_mem = AsyncMock()
        mock_mem.search_semantic.return_value = []
        service = ContextualChatService(ia=mock_ia, memory=mock_mem, embeddings=mock_embeddings)
        ctx = await service.build_context("Algo sin memorias")
        assert ctx["relevant_memories"] == []


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_returns_string(self, contextual_service):
        result = await contextual_service.send_message("Hola")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_send_message_empty_input(self, contextual_service):
        result = await contextual_service.send_message("")
        assert "No recibí" in result

    @pytest.mark.asyncio
    async def test_send_message_calls_ia(self, contextual_service, mock_ia):
        await contextual_service.send_message("Test")
        mock_ia.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_conversation_id(self, contextual_service):
        result = await contextual_service.send_message("Test", conversation_id="conv-123")
        assert isinstance(result, str)


class TestSendMessageStream:
    @pytest.mark.asyncio
    async def test_stream_empty_input(self, contextual_service):
        chunks = []
        async for chunk in contextual_service.send_message_stream(""):
            chunks.append(chunk)
        assert "No recibí" in chunks[0]

    @pytest.mark.asyncio
    async def test_stream_generates_chunks(self, mock_ia, mock_memory, mock_embeddings):
        async def fake_stream(*args, **kwargs):
            for chunk in ["Hola", " ", "Diego"]:
                yield chunk

        mock_ia.chat_stream = fake_stream
        service = ContextualChatService(ia=mock_ia, memory=mock_memory, embeddings=mock_embeddings)
        chunks = []
        async for chunk in service.send_message_stream("Test"):
            chunks.append(chunk)
        assert len(chunks) == 3
