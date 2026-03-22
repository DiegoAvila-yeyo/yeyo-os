"""
Tests unitarios para PipelineInvestigador.
Micro-fase 5.28 — 10 tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.investigador.modelos import (
    InvestigacionCompleta,
    PasoInvestigacion,
    ResultadoBusqueda,
)
from src.investigador.pipeline import PipelineInvestigador, CONFIANZA_MINIMA_INTERNA
from src.investigador.evaluador import EvaluadorCandidatos, EvaluacionCandidato
from src.investigador.buscador_externo import BuscadorExterno
from src.investigador.ensamblador import Ensamblador
from src.investigador.verificador import Verificador


@pytest.fixture
def mock_ia():
    ia = AsyncMock()
    ia.generate.return_value = MagicMock(content="codigo adaptado", tokens_used=100, latency_ms=50)
    ia.get_embedding.return_value = [0.1] * 768
    return ia


@pytest.fixture
def mock_flash():
    flash = AsyncMock()
    flash.recall.return_value = []
    flash.search_semantic.return_value = []
    flash.store.return_value = MagicMock(id="mem_123")
    return flash


@pytest.fixture
def mock_cache():
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set.return_value = None
    return cache


@pytest.fixture
def mock_buscador():
    buscador = AsyncMock(spec=BuscadorExterno)
    buscador.buscar_github.return_value = [
        ResultadoBusqueda(
            fuente="github",
            url="https://github.com/test/repo",
            codigo="def hello(): return 'world'",
            score=0.8,
            metadata={"estrellas": 500, "lenguaje": "Python"},
        ),
    ]
    buscador.buscar_stackoverflow.return_value = []
    return buscador


@pytest.fixture
def pipeline(mock_ia, mock_flash, mock_cache, mock_buscador):
    return PipelineInvestigador(
        ia_provider=mock_ia,
        flash_memory=mock_flash,
        memory_cache=mock_cache,
        buscador_externo=mock_buscador,
    )


@pytest.mark.asyncio
async def test_investigar_retorna_investigacion_completa(pipeline):
    resultado = await pipeline.investigar("cómo hacer rate limiting")
    assert isinstance(resultado, InvestigacionCompleta)
    assert resultado.tarea_id.startswith("inv_")
    assert resultado.tiempo_total_ms >= 0


@pytest.mark.asyncio
async def test_investigar_busca_interno_primero(pipeline, mock_flash):
    from src.memory.models import Memory
    mem = MagicMock()
    mem.id = "mem_1"
    mem.content = "solución encontrada"
    mem.type = "skill"
    mem.tier = "HOT"
    mock_flash.search_semantic.return_value = [mem]
    resultado = await pipeline.investigar("algo conocido")
    assert len(resultado.pasos) >= 1
    assert resultado.pasos[0].tipo == "busqueda_interna"


@pytest.mark.asyncio
async def test_investigar_busca_externo_si_interno_no_tiene(pipeline, mock_buscador):
    resultado = await pipeline.investigar("algo nuevo")
    mock_buscador.buscar_github.assert_called_once()


@pytest.mark.asyncio
async def test_investigar_evalua_candidatos(pipeline):
    resultado = await pipeline.investigar("test query")
    tipos_pasos = [p.tipo for p in resultado.pasos]
    assert "evaluacion" in tipos_pasos


@pytest.mark.asyncio
async def test_investigar_ensambla_mejor_candidato(pipeline):
    resultado = await pipeline.investigar("test ensamblaje")
    tipos_pasos = [p.tipo for p in resultado.pasos]
    assert "ensamblaje" in tipos_pasos


@pytest.mark.asyncio
async def test_investigar_verifica_resultado(pipeline):
    resultado = await pipeline.investigar("test verificación")
    tipos_pasos = [p.tipo for p in resultado.pasos]
    assert "verificacion" in tipos_pasos


@pytest.mark.asyncio
async def test_investigar_almacena_si_confianza_suficiente(pipeline, mock_flash):
    resultado = await pipeline.investigar("test almacenamiento")
    if resultado.confianza >= 0.6:
        mock_flash.store.assert_called()


@pytest.mark.asyncio
async def test_investigar_sin_resultados(pipeline, mock_buscador):
    mock_buscador.buscar_github.return_value = []
    mock_buscador.buscar_stackoverflow.return_value = []
    resultado = await pipeline.investigar("algo imposible de encontrar")
    assert resultado.confianza <= 0.1


@pytest.mark.asyncio
async def test_investigar_con_cache_patrones(mock_ia, mock_flash):
    cache_patrones = AsyncMock()
    patron_mock = MagicMock()
    patron_mock.patron_correcto = "solución cacheada"
    patron_mock.confianza = 0.95
    cache_patrones.buscar_patron.return_value = patron_mock

    pipeline = PipelineInvestigador(
        ia_provider=mock_ia,
        flash_memory=mock_flash,
        cache_patrones=cache_patrones,
    )
    resultado = await pipeline.investigar("problema conocido")
    assert resultado.exito is True
    assert resultado.confianza >= 0.9


@pytest.mark.asyncio
async def test_investigar_registra_todos_los_pasos(pipeline):
    resultado = await pipeline.investigar("test pasos completos")
    assert len(resultado.pasos) >= 2
    for paso in resultado.pasos:
        assert isinstance(paso, PasoInvestigacion)
        assert paso.numero > 0
        assert paso.tipo != ""
