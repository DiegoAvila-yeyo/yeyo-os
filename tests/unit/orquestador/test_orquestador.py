"""Tests para YeyoOrquestador — Micro-fase 4.19"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import nodo
from src.orquestador.grafo import YeyoGrafo
from src.orquestador.orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError


@nodo(id="nodo_chat_test")
async def nodo_chat_test(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["respuesta"] = f"Respuesta a: {estado.entrada.get('mensaje', '')}"
    return estado


@nodo(id="nodo_imagen_test")
async def nodo_imagen_test(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["respuesta"] = "imagen_generada.png"
    return estado


def crear_grafo_chat() -> YeyoGrafo:
    return (YeyoGrafo("grafo_chat", "Conversación con el usuario")
            .agregar_nodo(nodo_chat_test)
            .inicio("nodo_chat_test")
            .fin("nodo_chat_test"))


def crear_grafo_imagen() -> YeyoGrafo:
    return (YeyoGrafo("grafo_imagen", "Genera imágenes con IA")
            .agregar_nodo(nodo_imagen_test)
            .inicio("nodo_imagen_test")
            .fin("nodo_imagen_test"))


def mock_ollama_sin_tool_call(contenido="Hola, soy YeyoOS"):
    mock = AsyncMock()
    respuesta = MagicMock()
    respuesta.tool_calls = None
    respuesta.content = contenido
    mock.chat = AsyncMock(return_value=respuesta)
    return mock


def mock_ollama_con_tool_call(grafo_id: str, entrada: str = "test"):
    mock = AsyncMock()
    tool_call_mock = MagicMock()
    tool_call_mock.function.name = grafo_id
    tool_call_mock.function.arguments = {"entrada": entrada}
    respuesta = MagicMock()
    respuesta.tool_calls = [tool_call_mock]
    respuesta.content = ""
    mock.chat = AsyncMock(return_value=respuesta)
    return mock


class TestYeyoOrquestadorRegistro:

    def test_registrar_grafo(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo(crear_grafo_chat())
        assert "grafo_chat" in orq.listar_grafos()

    def test_registrar_grafo_como_tool(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo_como_tool(crear_grafo_chat())
        assert "grafo_chat" in orq.listar_grafos()
        assert "grafo_chat" in orq.listar_tools()

    def test_registrar_grafo_normal_no_en_tools(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo(crear_grafo_chat())
        assert "grafo_chat" not in orq.listar_tools()

    def test_method_chaining_registro(self):
        ollama = mock_ollama_sin_tool_call()
        result = (YeyoOrquestador(ollama)
                  .registrar_grafo_como_tool(crear_grafo_chat())
                  .registrar_grafo_como_tool(crear_grafo_imagen()))
        assert len(result.listar_tools()) == 2


class TestYeyoOrquestadorProcesar:

    @pytest.mark.asyncio
    async def test_procesar_sin_tool_call_retorna_texto(self):
        ollama = mock_ollama_sin_tool_call("Hola desde Ollama")
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo_como_tool(crear_grafo_chat())
        respuesta = await orq.procesar("Hola")
        assert isinstance(respuesta, RespuestaOrquestador)
        assert respuesta.texto == "Hola desde Ollama"
        assert respuesta.grafo_ejecutado is None

    @pytest.mark.asyncio
    async def test_procesar_con_tool_call_ejecuta_grafo(self):
        ollama = mock_ollama_con_tool_call("grafo_chat", "Hola mundo")
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo_como_tool(crear_grafo_chat())
        respuesta = await orq.procesar("Hola mundo")
        assert respuesta.grafo_ejecutado == "grafo_chat"
        assert respuesta.exito is True

    @pytest.mark.asyncio
    async def test_procesar_tool_call_grafo_imagen(self):
        ollama = mock_ollama_con_tool_call("grafo_imagen", "logo cyberpunk")
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo_como_tool(crear_grafo_imagen())
        respuesta = await orq.procesar("genera un logo cyberpunk")
        assert respuesta.grafo_ejecutado == "grafo_imagen"
        assert "imagen_generada" in respuesta.texto

    @pytest.mark.asyncio
    async def test_procesar_tool_call_grafo_no_registrado(self):
        ollama = mock_ollama_con_tool_call("grafo_inexistente")
        orq = YeyoOrquestador(ollama)
        respuesta = await orq.procesar("test")
        assert respuesta.exito is False
        assert "grafo_inexistente" in respuesta.texto

    @pytest.mark.asyncio
    async def test_ollama_error_lanza_excepcion(self):
        ollama = AsyncMock()
        ollama.chat = AsyncMock(side_effect=ConnectionError("Ollama no disponible"))
        orq = YeyoOrquestador(ollama)
        with pytest.raises(OrquestadorError):
            await orq.procesar("Hola")

    @pytest.mark.asyncio
    async def test_procesar_pasa_tools_a_ollama(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo_como_tool(crear_grafo_chat())
        await orq.procesar("test")
        call_kwargs = ollama.chat.call_args.kwargs
        assert "tools" in call_kwargs
        assert len(call_kwargs["tools"]) == 1
        assert call_kwargs["tools"][0]["type"] == "function"

    @pytest.mark.asyncio
    async def test_procesar_sin_tools_no_pasa_tools(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo(crear_grafo_chat())
        await orq.procesar("test")
        call_kwargs = ollama.chat.call_args.kwargs
        assert call_kwargs.get("tools") is None

    @pytest.mark.asyncio
    async def test_ejecutar_grafo_directo(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo(crear_grafo_chat())
        resultado = await orq.ejecutar_grafo_directo("grafo_chat", {"mensaje": "hola"})
        assert resultado.exito is True

    @pytest.mark.asyncio
    async def test_ejecutar_grafo_directo_no_registrado_falla(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        with pytest.raises(OrquestadorError):
            await orq.ejecutar_grafo_directo("grafo_no_existe", {})


class TestToolDefinition:

    def test_tool_definition_tiene_estructura_correcta(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        grafo = crear_grafo_chat()
        orq.registrar_grafo_como_tool(grafo)
        tool = orq._tools["grafo_chat"]
        assert tool["type"] == "function"
        assert tool["function"]["name"] == "grafo_chat"
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]

    def test_tool_usa_descripcion_del_grafo(self):
        ollama = mock_ollama_sin_tool_call()
        orq = YeyoOrquestador(ollama)
        orq.registrar_grafo_como_tool(crear_grafo_chat())
        tool = orq._tools["grafo_chat"]
        assert "Conversación" in tool["function"]["description"]
