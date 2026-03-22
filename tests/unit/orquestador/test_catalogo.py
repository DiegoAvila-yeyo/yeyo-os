"""Tests para CatalogoNodos — Micro-fase 4.20"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orquestador.estado import EstadoGrafo
from src.orquestador.catalogo import CatalogoNodos, CatalogoError


def mock_ollama():
    m = AsyncMock()
    respuesta = MagicMock()
    respuesta.content = "Respuesta de prueba"
    m.chat = AsyncMock(return_value=respuesta)
    m.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
    return m


def mock_flash_memory():
    m = AsyncMock()
    m.guardar = AsyncMock(return_value="mem-test-123")
    m.buscar = AsyncMock(return_value=[
        {"id": "mem-1", "contenido": "resultado test", "score": 0.9}
    ])
    return m


class TestCatalogoNodosBase:

    def test_catalogo_tiene_5_nodos_base(self):
        catalogo = CatalogoNodos()
        assert len(catalogo.listar()) == 5

    def test_nodos_base_correctos(self):
        catalogo = CatalogoNodos()
        nodos = catalogo.listar()
        assert "nodo_chat" in nodos
        assert "nodo_embeddings" in nodos
        assert "nodo_guardar_memoria" in nodos
        assert "nodo_buscar_memoria" in nodos
        assert "nodo_log" in nodos

    def test_obtener_nodo_existente(self):
        catalogo = CatalogoNodos()
        nodo = catalogo.obtener("nodo_chat")
        assert nodo.id == "nodo_chat"

    def test_obtener_nodo_inexistente_falla(self):
        catalogo = CatalogoNodos()
        with pytest.raises(CatalogoError, match="no encontrado"):
            catalogo.obtener("nodo_inexistente")

    def test_existe_nodo(self):
        catalogo = CatalogoNodos()
        assert catalogo.existe("nodo_chat") is True
        assert catalogo.existe("nodo_magico") is False

    def test_describir_retorna_dict(self):
        catalogo = CatalogoNodos()
        descripciones = catalogo.describir()
        assert isinstance(descripciones, dict)
        assert len(descripciones) == 5

    def test_registrar_nodo_adicional(self):
        from src.orquestador.nodo import NodoInline
        catalogo = CatalogoNodos()
        nodo_extra = NodoInline(id="nodo_extra", fn=lambda e: e)
        catalogo.registrar(nodo_extra)
        assert catalogo.existe("nodo_extra")
        assert len(catalogo.listar()) == 6


class TestNodoChat:

    @pytest.mark.asyncio
    async def test_nodo_chat_sin_ollama_usa_mock(self):
        catalogo = CatalogoNodos(ollama_provider=None)
        nodo = catalogo.obtener("nodo_chat")
        estado = EstadoGrafo(entrada={"mensaje": "Hola"})
        resultado = await nodo.ejecutar(estado)
        assert "respuesta" in resultado.salida
        assert "Hola" in resultado.salida["respuesta"]

    @pytest.mark.asyncio
    async def test_nodo_chat_con_ollama_mock(self):
        ollama = mock_ollama()
        catalogo = CatalogoNodos(ollama_provider=ollama)
        nodo = catalogo.obtener("nodo_chat")
        estado = EstadoGrafo(entrada={"mensaje": "Hola"})
        resultado = await nodo.ejecutar(estado)
        assert resultado.salida["respuesta"] == "Respuesta de prueba"
        ollama.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_nodo_chat_pasa_sistema_y_historial(self):
        ollama = mock_ollama()
        catalogo = CatalogoNodos(ollama_provider=ollama)
        nodo = catalogo.obtener("nodo_chat")
        estado = EstadoGrafo(entrada={
            "mensaje": "Hola",
            "sistema": "Eres un asistente de YeyoOS",
            "historial": [{"role": "user", "content": "Mensaje anterior"}]
        })
        await nodo.ejecutar(estado)
        messages_usados = ollama.chat.call_args.kwargs.get("messages", [])
        assert messages_usados[0]["role"] == "system"
        assert "YeyoOS" in messages_usados[0]["content"]


class TestNodoEmbeddings:

    @pytest.mark.asyncio
    async def test_nodo_embeddings_sin_ollama_usa_mock(self):
        catalogo = CatalogoNodos(ollama_provider=None)
        nodo = catalogo.obtener("nodo_embeddings")
        estado = EstadoGrafo(entrada={"texto": "hola mundo"})
        resultado = await nodo.ejecutar(estado)
        assert "embedding" in resultado.salida
        assert isinstance(resultado.salida["embedding"], list)
        assert "embedding_dim" in resultado.salida

    @pytest.mark.asyncio
    async def test_nodo_embeddings_con_ollama(self):
        ollama = mock_ollama()
        catalogo = CatalogoNodos(ollama_provider=ollama)
        nodo = catalogo.obtener("nodo_embeddings")
        estado = EstadoGrafo(entrada={"texto": "texto de prueba"})
        resultado = await nodo.ejecutar(estado)
        assert resultado.salida["embedding_dim"] == 5
        assert resultado.salida["embedding"] == [0.1, 0.2, 0.3, 0.4, 0.5]


class TestNodoGuardarMemoria:

    @pytest.mark.asyncio
    async def test_nodo_guardar_sin_flash_memory_usa_mock(self):
        catalogo = CatalogoNodos(flash_memory=None)
        nodo = catalogo.obtener("nodo_guardar_memoria")
        estado = EstadoGrafo(entrada={"dato": "algo importante", "tipo": "nota"})
        resultado = await nodo.ejecutar(estado)
        assert "memoria_id" in resultado.salida
        assert len(resultado.memoria_ids) == 1

    @pytest.mark.asyncio
    async def test_nodo_guardar_con_flash_memory(self):
        flash = mock_flash_memory()
        catalogo = CatalogoNodos(flash_memory=flash)
        nodo = catalogo.obtener("nodo_guardar_memoria")
        estado = EstadoGrafo(entrada={"dato": "dato importante", "importancia": 0.9})
        resultado = await nodo.ejecutar(estado)
        assert resultado.salida["memoria_id"] == "mem-test-123"
        assert "mem-test-123" in resultado.memoria_ids
        flash.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_nodo_guardar_registra_en_estado(self):
        catalogo = CatalogoNodos(flash_memory=None)
        nodo = catalogo.obtener("nodo_guardar_memoria")
        estado = EstadoGrafo(entrada={"dato": "test"})
        resultado = await nodo.ejecutar(estado)
        assert len(resultado.memoria_ids) == 1


class TestNodoBuscarMemoria:

    @pytest.mark.asyncio
    async def test_nodo_buscar_sin_flash_memory_usa_mock(self):
        catalogo = CatalogoNodos(flash_memory=None)
        nodo = catalogo.obtener("nodo_buscar_memoria")
        estado = EstadoGrafo(entrada={"query": "buscar algo"})
        resultado = await nodo.ejecutar(estado)
        assert "resultados" in resultado.salida
        assert "total_encontrados" in resultado.salida
        assert resultado.salida["total_encontrados"] >= 0

    @pytest.mark.asyncio
    async def test_nodo_buscar_con_flash_memory(self):
        flash = mock_flash_memory()
        catalogo = CatalogoNodos(flash_memory=flash)
        nodo = catalogo.obtener("nodo_buscar_memoria")
        estado = EstadoGrafo(entrada={"query": "algo importante", "limite": 3})
        resultado = await nodo.ejecutar(estado)
        assert resultado.salida["total_encontrados"] == 1
        flash.buscar.assert_called_once()


class TestNodoLog:

    @pytest.mark.asyncio
    async def test_nodo_log_registra_correctamente(self):
        catalogo = CatalogoNodos()
        nodo = catalogo.obtener("nodo_log")
        estado = EstadoGrafo(entrada={"mensaje_log": "Prueba de log", "nivel": "info"})
        resultado = await nodo.ejecutar(estado)
        assert resultado.salida["log_registrado"] is True

    @pytest.mark.asyncio
    async def test_nodo_log_con_mensaje_vacio(self):
        catalogo = CatalogoNodos()
        nodo = catalogo.obtener("nodo_log")
        estado = EstadoGrafo(entrada={})
        resultado = await nodo.ejecutar(estado)
        assert resultado.salida["log_registrado"] is True
