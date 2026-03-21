"""Tests para IAProvider Interface — Micro-fase 1.0"""

import pytest
from pydantic import ValidationError
from src.ia.interfaces import IAProvider, IAMessage, IAResponse


class TestIAMessage:
    """Tests para el modelo IAMessage."""

    def test_valid_user_message(self):
        msg = IAMessage(role="user", content="Hola YeyoOS")
        assert msg.role == "user"
        assert msg.content == "Hola YeyoOS"

    def test_valid_system_message(self):
        msg = IAMessage(role="system", content="Eres un asistente")
        assert msg.role == "system"

    def test_valid_assistant_message(self):
        msg = IAMessage(role="assistant", content="Hola!")
        assert msg.role == "assistant"

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            IAMessage(role="admin", content="test")

    def test_empty_content_rejected(self):
        with pytest.raises(ValidationError):
            IAMessage(role="user", content="")

    def test_missing_role_rejected(self):
        with pytest.raises(ValidationError):
            IAMessage(content="test")

    def test_missing_content_rejected(self):
        with pytest.raises(ValidationError):
            IAMessage(role="user")


class TestIAResponse:
    """Tests para el modelo IAResponse."""

    def test_valid_response(self):
        resp = IAResponse(
            content="Hola",
            model="qwen2.5:3b",
            tokens_used=42,
            latency_ms=150.5,
        )
        assert resp.content == "Hola"
        assert resp.model == "qwen2.5:3b"
        assert resp.tokens_used == 42
        assert resp.latency_ms == 150.5

    def test_has_all_required_fields(self):
        fields = IAResponse.model_fields
        assert "content" in fields
        assert "model" in fields
        assert "tokens_used" in fields
        assert "latency_ms" in fields

    def test_negative_tokens_rejected(self):
        with pytest.raises(ValidationError):
            IAResponse(
                content="test",
                model="test",
                tokens_used=-1,
                latency_ms=10.0,
            )

    def test_negative_latency_rejected(self):
        with pytest.raises(ValidationError):
            IAResponse(
                content="test",
                model="test",
                tokens_used=10,
                latency_ms=-1.0,
            )

    def test_missing_field_rejected(self):
        with pytest.raises(ValidationError):
            IAResponse(content="test", model="test")


class TestIAProvider:
    """Tests para la interfaz abstracta IAProvider."""

    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            IAProvider()

    def test_all_methods_are_abstract(self):
        abstract_methods = IAProvider.__abstractmethods__
        expected = {
            "generate",
            "chat",
            "chat_stream",
            "get_embedding",
            "health_check",
            "get_model_name",
            "get_max_tokens",
        }
        assert abstract_methods == expected

    def test_has_seven_abstract_methods(self):
        assert len(IAProvider.__abstractmethods__) == 7

    def test_incomplete_implementation_fails(self):
        class Incomplete(IAProvider):
            async def generate(self, prompt, system="", temperature=0.7):
                pass

        with pytest.raises(TypeError):
            Incomplete()
