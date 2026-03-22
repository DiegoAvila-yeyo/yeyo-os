"""Tests para GeneradorGrafos — Micro-fase 5.24"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orquestador.grafo import YeyoGrafo
from src.orquestador.generador import GeneradorGrafos, GeneradorGrafosError


# ─── Mock de Ollama ────────────────────────────────────────────────────────

CODIGO_GRAFO_SIMPLE = '''
async def fn_nodo(estado):
    estado.salida["ok"] = True
    return estado

nodo_test = NodoFuncion(id="nodo_generado", fn=fn_nodo, timeout=30.0)
grafo = (
    YeyoGrafo("grafo_generado_ia", "Grafo generado por IA")
    .agregar_nodo(nodo_test)
    .inicio("nodo_generado")
    .fin("nodo_generado")
)
'''

CODIGO_CON_EVAL = '''
grafo = eval("YeyoGrafo('malicioso', 'malo')")
'''

CODIGO_CON_OS = '''
import os
os.system("rm -rf /")
grafo = YeyoGrafo("hack", "hack")
'''

CODIGO_SIN_GRAFO = '''
x = 42
'''


def mock_ollama_genera_codigo(codigo: str):
    m = AsyncMock()
    resp = MagicMock()
    resp.content = f"```python\n{codigo}\n```"
    m.chat = AsyncMock(return_value=resp)
    return m


def mock_flash_memory():
    m = AsyncMock()
    m.guardar = AsyncMock(return_value="mem-gen-001")
    m.buscar = AsyncMock(return_value=[])
    return m


class TestGeneradorGrafosBasico:

    @pytest.mark.asyncio
    async def test_generar_produce_yeyo_grafo(self):
        ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
        gen = GeneradorGrafos(ollama)
        grafo = await gen.generar("Un grafo simple que guarda ok=True")
        assert isinstance(grafo, YeyoGrafo)

    @pytest.mark.asyncio
    async def test_grafo_generado_tiene_id_correcto(self):
        ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
        gen = GeneradorGrafos(ollama)
        grafo = await gen.generar("Grafo de prueba")
        assert grafo.id == "grafo_generado_ia"

    @pytest.mark.asyncio
    async def test_grafo_generado_es_ejecutable(self):
        ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
        gen = GeneradorGrafos(ollama)
        grafo = await gen.generar("Grafo ejecutable")
        resultado = await grafo.ejecutar({})
        assert resultado.exito is True
        assert resultado.estado_final.salida.get("ok") is True

    @pytest.mark.asyncio
    async def test_descripcion_vacia_falla(self):
        ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
        gen = GeneradorGrafos(ollama)
        with pytest.raises(GeneradorGrafosError):
            await gen.generar("")

    @pytest.mark.asyncio
    async def test_guarda_en_flash_memory(self):
        ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
        flash = mock_flash_memory()
        gen = GeneradorGrafos(ollama, flash_memory=flash)
        await gen.generar("Grafo con memoria")
        flash.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_grafo_agregado_a_historial_interno(self):
        ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
        gen = GeneradorGrafos(ollama)
        await gen.generar("Primero", usuario_id="u1")
        await gen.generar("Segundo", usuario_id="u1")
        assert len(gen.grafos_generados) == 2

    @pytest.mark.asyncio
    async def test_listar_generados_retorna_lista(self):
        ollama = mock_ollama_genera_codigo(CODIGO_GRAFO_SIMPLE)
        gen = GeneradorGrafos(ollama)
        await gen.generar("Grafo x", usuario_id="u1")
        lista = await gen.listar_generados("u1")
        assert isinstance(lista, list)


class TestGeneradorGrafosSeguridad:

    @pytest.mark.asyncio
    async def test_codigo_con_eval_rechazado(self):
        ollama = mock_ollama_genera_codigo(CODIGO_CON_EVAL)
        gen = GeneradorGrafos(ollama)
        with pytest.raises(GeneradorGrafosError):
            await gen.generar("Grafo con eval")

    @pytest.mark.asyncio
    async def test_codigo_con_os_rechazado(self):
        ollama = mock_ollama_genera_codigo(CODIGO_CON_OS)
        gen = GeneradorGrafos(ollama)
        with pytest.raises(GeneradorGrafosError):
            await gen.generar("Grafo con os")

    @pytest.mark.asyncio
    async def test_codigo_sin_grafo_rechazado(self):
        ollama = mock_ollama_genera_codigo(CODIGO_SIN_GRAFO)
        gen = GeneradorGrafos(ollama)
        with pytest.raises(GeneradorGrafosError):
            await gen.generar("Grafo sin variable grafo")


class TestGeneradorGrafosExtraccion:

    def test_extraer_bloque_python(self):
        gen = GeneradorGrafos(AsyncMock())
        texto = "Aquí va el código:\n```python\nx = 1\n```\nFin"
        resultado = gen._extraer_codigo(texto)
        assert resultado == "x = 1"

    def test_extraer_bloque_generico(self):
        gen = GeneradorGrafos(AsyncMock())
        texto = "```\ny = 2\n```"
        resultado = gen._extraer_codigo(texto)
        assert resultado == "y = 2"

    def test_sin_bloques_retorna_todo(self):
        gen = GeneradorGrafos(AsyncMock())
        texto = "z = 3"
        resultado = gen._extraer_codigo(texto)
        assert resultado == "z = 3"


class TestGeneradorGrafosOllama:

    @pytest.mark.asyncio
    async def test_error_en_ollama_lanza_generador_error(self):
        ollama = AsyncMock()
        ollama.chat = AsyncMock(side_effect=ConnectionError("ollama down"))
        gen = GeneradorGrafos(ollama)
        with pytest.raises(GeneradorGrafosError, match="Ollama"):
            await gen.generar("Un grafo que falla")
