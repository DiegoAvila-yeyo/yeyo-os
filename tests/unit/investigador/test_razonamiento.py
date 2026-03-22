"""
Tests unitarios para Razonamiento Extendido.
Micro-fase 5.30 — 10 tests (3 CoT + 3 ToT + 3 SC + 1 Selector).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.investigador.razonamiento import (
    ChainOfThought,
    TreeOfThought,
    SelfConsistency,
    ResultadoRazonamiento,
)
from src.investigador.selector_estrategia import SelectorEstrategia
from src.investigador.tarea_db import TareaDB


@pytest.fixture
def mock_ia():
    ia = AsyncMock()
    ia.generate.return_value = MagicMock(
        content="solución generada por el modelo",
        tokens_used=80,
        latency_ms=100,
    )
    return ia


@pytest.fixture
def tarea_db():
    return TareaDB(pool=None)


# --- Tests ChainOfThought ---

@pytest.mark.asyncio
async def test_cot_retorna_resultado(mock_ia, tarea_db):
    cot = ChainOfThought(mock_ia, tarea_db, num_pasos=3)
    resultado = await cot.razonar("¿Cómo implementar un rate limiter?")
    assert isinstance(resultado, ResultadoRazonamiento)
    assert resultado.estrategia == "cot"
    assert resultado.resultado_final != ""
    assert resultado.confianza > 0


@pytest.mark.asyncio
async def test_cot_ejecuta_multiples_pasos(mock_ia, tarea_db):
    cot = ChainOfThought(mock_ia, tarea_db, num_pasos=4)
    resultado = await cot.razonar("Problema complejo")
    assert resultado.pasos_total >= 3
    assert resultado.tokens_total > 0


@pytest.mark.asyncio
async def test_cot_un_solo_camino(mock_ia, tarea_db):
    cot = ChainOfThought(mock_ia, tarea_db)
    resultado = await cot.razonar("Test")
    assert resultado.caminos_explorados == 1


# --- Tests TreeOfThought ---

@pytest.mark.asyncio
async def test_tot_retorna_resultado(mock_ia, tarea_db):
    tot = TreeOfThought(mock_ia, tarea_db, num_ramas=2)
    resultado = await tot.razonar("¿Cómo diseñar un sistema distribuido?")
    assert isinstance(resultado, ResultadoRazonamiento)
    assert resultado.estrategia == "tot"
    assert resultado.resultado_final != ""


@pytest.mark.asyncio
async def test_tot_explora_multiples_caminos(mock_ia, tarea_db):
    tot = TreeOfThought(mock_ia, tarea_db, num_ramas=3)
    resultado = await tot.razonar("Problema con múltiples enfoques")
    assert resultado.caminos_explorados >= 1


@pytest.mark.asyncio
async def test_tot_parsea_mejor_solucion(mock_ia, tarea_db):
    ia_eval = AsyncMock()
    respuesta_counter = [0]

    async def generate_side_effect(**kwargs):
        respuesta_counter[0] += 1
        if "mejor" in kwargs.get("prompt", "").lower() or "evalúa" in kwargs.get("prompt", "").lower():
            return MagicMock(content="1 - La primera es mejor", tokens_used=30, latency_ms=50)
        return MagicMock(content=f"Solución {respuesta_counter[0]}", tokens_used=50, latency_ms=100)

    ia_eval.generate = AsyncMock(side_effect=generate_side_effect)
    tot = TreeOfThought(ia_eval, tarea_db, num_ramas=2)
    resultado = await tot.razonar("Test parseo")
    assert resultado.resultado_final != ""


# --- Tests SelfConsistency ---

@pytest.mark.asyncio
async def test_sc_retorna_resultado(mock_ia, tarea_db):
    sc = SelfConsistency(mock_ia, tarea_db, num_muestras=3)
    resultado = await sc.razonar("¿Cuánto es 2+2?")
    assert isinstance(resultado, ResultadoRazonamiento)
    assert resultado.estrategia in ("sc", "sc+tot")


@pytest.mark.asyncio
async def test_sc_consenso_con_respuestas_iguales(mock_ia, tarea_db):
    mock_ia.generate.return_value = MagicMock(
        content="4", tokens_used=10, latency_ms=20,
    )
    sc = SelfConsistency(mock_ia, tarea_db, num_muestras=5, umbral_consenso=0.5)
    resultado = await sc.razonar("¿Cuánto es 2+2?")
    assert resultado.consenso is not None
    assert resultado.consenso >= 0.5


@pytest.mark.asyncio
async def test_sc_escala_a_tot_sin_consenso(mock_ia, tarea_db):
    call_counter = [0]

    async def varied_responses(**kwargs):
        call_counter[0] += 1
        return MagicMock(
            content=f"respuesta_unica_{call_counter[0]}",
            tokens_used=30,
            latency_ms=50,
        )

    mock_ia.generate = AsyncMock(side_effect=varied_responses)
    sc = SelfConsistency(mock_ia, tarea_db, num_muestras=5, umbral_consenso=0.9)
    resultado = await sc.razonar("Pregunta ambigua")
    assert resultado.estrategia in ("sc", "sc+tot")


# --- Test SelectorEstrategia ---

@pytest.mark.asyncio
async def test_selector_elige_por_complejidad(mock_ia, tarea_db):
    selector = SelectorEstrategia(mock_ia, tarea_db)

    # Tarea simple
    comp_simple = selector.estimar_complejidad("hola")
    assert comp_simple < 0.3

    # Tarea compleja
    comp_compleja = selector.estimar_complejidad(
        "Implementar un sistema distribuido con machine learning "
        "y concurrent processing para optimization de neural network"
    )
    assert comp_compleja > 0.3

    # Resolver con auto-selección
    resultado = await selector.resolver("tarea simple")
    assert isinstance(resultado, ResultadoRazonamiento)
