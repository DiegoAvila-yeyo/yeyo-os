"""Tests para Orquestador Interface — Micro-fase 1.3"""

import pytest
from src.core.interfaces import (
    OrquestadorProvider,
    TokenBudget,
    OrquestadorContext,
)


class TestTokenBudget:
    def test_default_values(self):
        budget = TokenBudget()
        assert budget.system == 300
        assert budget.memories == 1000
        assert budget.history == 1500
        assert budget.input == 500
        assert budget.response == 700

    def test_total_is_4000(self):
        budget = TokenBudget()
        assert budget.total == 4000

    def test_custom_values(self):
        budget = TokenBudget(system=200, memories=800, history=1000, input=400, response=600)
        assert budget.total == 3000

    def test_total_is_computed_property(self):
        budget = TokenBudget()
        assert isinstance(TokenBudget.total.fget(budget), int)


class TestOrquestadorContext:
    def test_default_context(self):
        ctx = OrquestadorContext()
        assert ctx.system_prompt == ""
        assert ctx.relevant_memories == []
        assert ctx.conversation_history == []
        assert ctx.user_input == ""
        assert ctx.token_budget.total == 4000

    def test_context_with_data(self):
        ctx = OrquestadorContext(
            system_prompt="Eres YeyoOS",
            relevant_memories=["memoria1", "memoria2"],
            user_input="Hola",
        )
        assert ctx.system_prompt == "Eres YeyoOS"
        assert len(ctx.relevant_memories) == 2
        assert ctx.user_input == "Hola"


class TestOrquestadorProvider:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            OrquestadorProvider()

    def test_all_methods_are_abstract(self):
        expected = {
            "process_message",
            "process_message_stream",
            "get_context_for_prompt",
            "health_check",
        }
        assert OrquestadorProvider.__abstractmethods__ == expected

    def test_has_four_abstract_methods(self):
        assert len(OrquestadorProvider.__abstractmethods__) == 4

    def test_health_check_returns_dict_not_bool(self):
        """health_check retorna dict porque verifica múltiples subsistemas."""
        import inspect
        sig = inspect.signature(OrquestadorProvider.health_check)
        annotations = sig.return_annotation
        assert annotations is dict

    def test_incomplete_implementation_fails(self):
        class Incomplete(OrquestadorProvider):
            async def process_message(self, user_input, context=None):
                pass

        with pytest.raises(TypeError):
            Incomplete()
