"""
Tests de integración para OllamaProvider — Micro-fase 1.1
Requieren Ollama corriendo con modelo qwen2.5:3b.
Ejecutar con: pytest tests/integration/ -v -m integration
"""

import pytest
from src.ia.ollama_provider import OllamaProvider
from src.ia.interfaces import IAMessage, IAResponse


pytestmark = pytest.mark.integration


@pytest.fixture
async def provider():
    p = OllamaProvider()
    yield p
    await p.close()


@pytest.mark.asyncio
async def test_ollama_health_check(provider):
    result = await provider.health_check()
    assert result is True, "Ollama no está corriendo"


@pytest.mark.asyncio
async def test_ollama_generate(provider):
    result = await provider.generate("Responde solo con la palabra OK")
    assert isinstance(result, IAResponse)
    assert len(result.content) > 0
    assert result.tokens_used > 0
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_ollama_chat(provider):
    messages = [
        IAMessage(role="system", content="Responde siempre en una sola palabra"),
        IAMessage(role="user", content="Di hola"),
    ]
    result = await provider.chat(messages)
    assert isinstance(result, IAResponse)
    assert len(result.content) > 0


@pytest.mark.asyncio
async def test_ollama_chat_stream(provider):
    messages = [
        IAMessage(role="user", content="Cuenta del 1 al 5"),
    ]
    chunks = []
    async for chunk in provider.chat_stream(messages):
        chunks.append(chunk)
    assert len(chunks) > 0
    full_response = "".join(chunks)
    assert len(full_response) > 0


@pytest.mark.asyncio
async def test_ollama_embedding(provider):
    result = await provider.get_embedding("YeyoOS es un sistema operativo AI-nativo")
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(isinstance(x, float) for x in result)
