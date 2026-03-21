"""
Tests para TokenBudget — Micro-fase 2.8
Tests unitarios puro — no requiere servicios externos.
"""

import pytest
from src.chat.token_budget import TokenBudget
from src.ia.interfaces import IAMessage
from src.memory.models import Memory


class TestTokenBudgetConstants:
    def test_total_is_4000(self):
        assert TokenBudget.TOTAL == 4000

    def test_components_sum_to_total(self):
        assert (TokenBudget.SYSTEM + TokenBudget.MEMORIES + TokenBudget.HISTORY
                + TokenBudget.INPUT + TokenBudget.RESPONSE) == TokenBudget.TOTAL

    def test_system_is_300(self):
        assert TokenBudget.SYSTEM == 300

    def test_memories_is_1000(self):
        assert TokenBudget.MEMORIES == 1000

    def test_history_is_1500(self):
        assert TokenBudget.HISTORY == 1500

    def test_input_is_500(self):
        assert TokenBudget.INPUT == 500

    def test_response_is_700(self):
        assert TokenBudget.RESPONSE == 700

    def test_chars_per_token_is_4(self):
        assert TokenBudget.CHARS_PER_TOKEN == 4


class TestCountTokens:
    def test_empty_string(self):
        assert TokenBudget.count_tokens("") == 0

    def test_none_returns_zero(self):
        assert TokenBudget.count_tokens(None) == 0

    def test_short_text_minimum_one(self):
        assert TokenBudget.count_tokens("Hi") >= 1

    def test_approximation(self):
        assert TokenBudget.count_tokens("a" * 40) == 10

    def test_longer_text(self):
        assert TokenBudget.count_tokens("a" * 400) == 100

    def test_realistic_text(self):
        tokens = TokenBudget.count_tokens("Hola, me llamo Diego y programo en Python")
        assert 5 <= tokens <= 20


class TestTruncateToBudget:
    def test_short_text_not_truncated(self):
        text = "Hola mundo"
        assert TokenBudget.truncate_to_budget(text, 100) == text

    def test_long_text_truncated(self):
        text = "palabra " * 500
        result = TokenBudget.truncate_to_budget(text, 10)
        assert len(result) < len(text)
        assert result.endswith("...")

    def test_empty_string(self):
        assert TokenBudget.truncate_to_budget("", 100) == ""

    def test_truncation_ends_with_ellipsis(self):
        text = "uno dos tres cuatro cinco seis siete ocho nueve diez " * 20
        result = TokenBudget.truncate_to_budget(text, 5)
        assert result.endswith("...")


class TestFitMemories:
    def test_empty_list(self):
        assert TokenBudget.fit_memories([]) == []

    def test_memories_within_budget(self):
        memories = [
            Memory(content="Corto", type="fact", checksum="a" * 64),
            Memory(content="También corto", type="preference", checksum="b" * 64),
        ]
        assert len(TokenBudget.fit_memories(memories, max_tokens=1000)) == 2

    def test_memories_exceed_budget(self):
        memories = [
            Memory(content="x" * 2000, type="fact", checksum="a" * 64),
            Memory(content="x" * 2000, type="fact", checksum="b" * 64),
            Memory(content="x" * 2000, type="fact", checksum="c" * 64),
        ]
        result = TokenBudget.fit_memories(memories, max_tokens=1000)
        assert len(result) < 3

    def test_priority_order_preserved(self):
        memories = [
            Memory(content="Primera (prioritaria)", type="fact", checksum="a" * 64),
            Memory(content="Segunda", type="preference", checksum="b" * 64),
        ]
        result = TokenBudget.fit_memories(memories, max_tokens=1000)
        assert result[0].content == "Primera (prioritaria)"


class TestFitHistory:
    def test_empty_list(self):
        assert TokenBudget.fit_history([]) == []

    def test_history_within_budget(self):
        messages = [
            IAMessage(role="user", content="Hola"),
            IAMessage(role="assistant", content="Hola!"),
        ]
        assert len(TokenBudget.fit_history(messages, max_tokens=1500)) == 2

    def test_history_truncates_oldest_first(self):
        messages = [
            IAMessage(role="user", content="Mensaje antiguo " * 100),
            IAMessage(role="assistant", content="Respuesta antigua " * 100),
            IAMessage(role="user", content="Reciente"),
            IAMessage(role="assistant", content="Última respuesta"),
        ]
        result = TokenBudget.fit_history(messages, max_tokens=20)
        assert result[-1].content == "Última respuesta"

    def test_history_all_fit(self):
        messages = [
            IAMessage(role="user", content="Uno"),
            IAMessage(role="assistant", content="Dos"),
        ]
        assert len(TokenBudget.fit_history(messages, max_tokens=1500)) == 2


class TestCalculateUsage:
    def test_returns_all_fields(self):
        usage = TokenBudget.calculate_usage("System", "Memories", [], "Input")
        for key in ["system", "memories", "history", "input", "response_reserved",
                    "total", "remaining", "within_budget"]:
            assert key in usage

    def test_within_budget(self):
        usage = TokenBudget.calculate_usage("Hola", "Memoria", [], "Test")
        assert usage["within_budget"] is True

    def test_response_reserved(self):
        usage = TokenBudget.calculate_usage("", "", [], "")
        assert usage["response_reserved"] == 700


class TestValidateBudget:
    def test_valid_budget(self):
        assert TokenBudget.validate_budget(200, 800, 1000, 300) is True

    def test_system_over_budget(self):
        assert TokenBudget.validate_budget(400, 0, 0, 0) is False

    def test_exactly_at_budget(self):
        assert TokenBudget.validate_budget(300, 1000, 1500, 500) is True
