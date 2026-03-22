"""Tests de integración mock para grafos estáticos — Micro-fase 4.21"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orquestador.grafos import (
    crear_grafo_chat_contextual,
    crear_grafo_busqueda_semantica,
)


def mock_ollama(respuesta_texto="Respuesta de prueba"):
    m = AsyncMock()
    resp = MagicMock()
    resp.content = respuesta_texto
    m.chat = AsyncMock(return_value=resp)
    m.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return m


def mock_flash_memory(resultados=None):
    m = AsyncMock()
    m.guardar = AsyncMock(return_value="mem-test-001")
    m.buscar = AsyncMock(return_value=resultados or [
        {"id": "m1", "contenido": "información relevante", "score": 0.9}
    ])
    return m


class TestGrafoChatContextual:

    def test_crear_grafo_chat_contextual(self):
        grafo = crear_grafo_chat_contextual()
        assert grafo.id == "grafo_chat_contextual"
        assert grafo._nodo_inicio == "mejorar_prompt"

    def test_grafo_tiene_descripcion(self):
        grafo = crear_grafo_chat_contextual()
        assert grafo.descripcion != ""

    @pytest.mark.asyncio
    async def test_ejecuta_con_mocks_sin_providers(self):
        grafo = crear_grafo_chat_contextual()
        resultado = await grafo.ejecutar({"mensaje": "Hola, ¿cómo estás?"})
        assert resultado.exito is True
        assert "respuesta" in resultado.estado_final.salida

    @pytest.mark.asyncio
    async def test_ejecuta_con_ollama_mock(self):
        ollama = mock_ollama("Estoy bien, gracias por preguntar")
        flash = mock_flash_memory()
        grafo = crear_grafo_chat_contextual(ollama_provider=ollama, flash_memory=flash)
        resultado = await grafo.ejecutar({"mensaje": "¿Cómo estás?", "usuario_id": "u1"})
        assert resultado.exito is True
        assert resultado.estado_final.salida["respuesta"] == "Estoy bien, gracias por preguntar"

    @pytest.mark.asyncio
    async def test_guarda_memoria_de_la_conversacion(self):
        ollama = mock_ollama()
        flash = mock_flash_memory()
        grafo = crear_grafo_chat_contextual(ollama_provider=ollama, flash_memory=flash)
        resultado = await grafo.ejecutar({"mensaje": "recuerda que me gustan los gatos"})
        assert resultado.exito is True
        flash.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_historial_en_contexto_funciona(self):
        ollama = mock_ollama()
        grafo = crear_grafo_chat_contextual(ollama_provider=ollama)
        historial = [
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¡Hola!"},
        ]
        resultado = await grafo.ejecutar({"mensaje": "¿Recuerdas lo anterior?", "historial": historial})
        assert resultado.exito is True


class TestGrafoBusquedaSemantica:

    def test_crear_grafo_busqueda_semantica(self):
        grafo = crear_grafo_busqueda_semantica()
        assert grafo.id == "grafo_busqueda_semantica"
        assert grafo._nodo_inicio == "preparar_busqueda"

    def test_grafo_tiene_descripcion(self):
        grafo = crear_grafo_busqueda_semantica()
        assert grafo.descripcion != ""

    @pytest.mark.asyncio
    async def test_ejecuta_con_mocks_sin_providers(self):
        grafo = crear_grafo_busqueda_semantica()
        resultado = await grafo.ejecutar({"query": "información sobre gatos"})
        assert resultado.exito is True

    @pytest.mark.asyncio
    async def test_ejecuta_con_resultados_de_flash_memory(self):
        ollama = mock_ollama("Los gatos son animales independientes")
        flash = mock_flash_memory([
            {"id": "m1", "contenido": "Los gatos son mascotas populares", "score": 0.95},
            {"id": "m2", "contenido": "Los gatos duermen mucho", "score": 0.85},
        ])
        grafo = crear_grafo_busqueda_semantica(ollama_provider=ollama, flash_memory=flash)
        resultado = await grafo.ejecutar({"query": "gatos"})
        assert resultado.exito is True
        assert "respuesta" in resultado.estado_final.salida

    @pytest.mark.asyncio
    async def test_genera_embeddings_de_la_query(self):
        ollama = mock_ollama()
        flash = mock_flash_memory()
        grafo = crear_grafo_busqueda_semantica(ollama_provider=ollama, flash_memory=flash)
        await grafo.ejecutar({"query": "buscar algo importante"})
        ollama.embeddings.assert_called_once_with("buscar algo importante")

    @pytest.mark.asyncio
    async def test_resultados_bajos_filtrados(self):
        ollama = mock_ollama("No encontré información relevante")
        flash = mock_flash_memory([
            {"id": "m1", "contenido": "resultado poco relevante", "score": 0.2}
        ])
        grafo = crear_grafo_busqueda_semantica(ollama_provider=ollama, flash_memory=flash)
        resultado = await grafo.ejecutar({"query": "busqueda sin resultados"})
        assert resultado.exito is True
        assert resultado.estado_final.salida.get("total_encontrados", 0) == 0
