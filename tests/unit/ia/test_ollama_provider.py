"""
Tests unitarios para OllamaProvider — Micro-fase 1.1
Usan mocks para no depender de Ollama corriendo.
"""

import pytest
import httpx
import respx
from src.ia.ollama_provider import OllamaProvider
from src.ia.interfaces import IAProvider, IAMessage, IAResponse


@pytest.fixture
def provider():
    return OllamaProvider(
        host="http://localhost:11434",
        model="qwen2.5:3b",
    )


class TestOllamaProviderBasic:
    """Tests básicos sin red."""

    def test_is_ia_provider(self, provider):
        assert isinstance(provider, IAProvider)

    def test_default_host(self):
        p = OllamaProvider()
        assert "localhost" in p.host
        assert "11434" in p.host

    def test_default_model(self):
        p = OllamaProvider()
        assert p.model == "qwen2.5:3b"

    def test_custom_host_and_model(self):
        p = OllamaProvider(host="http://custom:9999", model="llama3:8b")
        assert p.host == "http://custom:9999"
        assert p.model == "llama3:8b"

    def test_get_model_name(self, provider):
        assert provider.get_model_name() == "qwen2.5:3b"

    def test_get_max_tokens(self, provider):
        assert provider.get_max_tokens() == 4000


class TestOllamaProviderMocked:
    """Tests con HTTP mockeado."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_success(self, provider):
        respx.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json={"models": []})
        )
        result = await provider.health_check()
        assert result is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_failure(self, provider):
        respx.get("http://localhost:11434/api/tags").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        result = await provider.health_check()
        assert result is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_health_check_timeout(self, provider):
        respx.get("http://localhost:11434/api/tags").mock(
            side_effect=httpx.TimeoutException("Timeout")
        )
        result = await provider.health_check()
        assert result is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_returns_ia_response(self, provider):
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={
                "response": "Hola, soy YeyoOS",
                "model": "qwen2.5:3b",
                "eval_count": 10,
                "prompt_eval_count": 5,
            })
        )
        result = await provider.generate("Saluda")
        assert isinstance(result, IAResponse)
        assert result.content == "Hola, soy YeyoOS"
        assert result.model == "qwen2.5:3b"
        assert result.tokens_used == 15
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_with_system_prompt(self, provider):
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(200, json={
                "response": "OK",
                "eval_count": 1,
                "prompt_eval_count": 5,
            })
        )
        result = await provider.generate(
            prompt="Di OK",
            system="Eres un asistente conciso",
        )
        assert result.content == "OK"

    @pytest.mark.asyncio
    @respx.mock
    async def test_chat_returns_ia_response(self, provider):
        respx.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(200, json={
                "message": {"role": "assistant", "content": "¡Hola!"},
                "model": "qwen2.5:3b",
                "eval_count": 5,
                "prompt_eval_count": 10,
            })
        )
        messages = [
            IAMessage(role="system", content="Eres YeyoOS"),
            IAMessage(role="user", content="Hola"),
        ]
        result = await provider.chat(messages)
        assert isinstance(result, IAResponse)
        assert result.content == "¡Hola!"
        assert result.tokens_used == 15

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_embedding_returns_vector(self, provider):
        fake_embedding = [0.1] * 768
        respx.post("http://localhost:11434/api/embed").mock(
            return_value=httpx.Response(200, json={
                "embeddings": [fake_embedding]
            })
        )
        result = await provider.get_embedding("test text")
        assert isinstance(result, list)
        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    @respx.mock
    async def test_generate_http_error_raises(self, provider):
        respx.post("http://localhost:11434/api/generate").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await provider.generate("test")

    @pytest.mark.asyncio
    async def test_close_client(self, provider):
        await provider.close()
        # No debe lanzar excepción
