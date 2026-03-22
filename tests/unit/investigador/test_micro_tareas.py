"""
Tests unitarios para EjecutorMicroTareas.
Micro-fase 5.29 — 8 tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.investigador.micro_tareas import (
    EjecutorMicroTareas,
    MicroTarea,
    ResultadoCadena,
)
from src.investigador.tarea_db import TareaDB
from src.investigador.modelos import PasoInvestigacion


@pytest.fixture
def mock_ia():
    ia = AsyncMock()
    ia.generate.return_value = MagicMock(
        content="respuesta del modelo",
        tokens_used=50,
        latency_ms=100,
    )
    return ia


@pytest.fixture
def tarea_db():
    return TareaDB(pool=None)


@pytest.fixture
def ejecutor(mock_ia, tarea_db):
    return EjecutorMicroTareas(ia_provider=mock_ia, tarea_db=tarea_db)


@pytest.mark.asyncio
async def test_ejecutar_cadena_simple(ejecutor):
    cadena = [
        MicroTarea(
            prompt="¿Cuál es la capital de Francia?",
            output_key="respuesta",
            max_tokens=200,
        ),
    ]
    resultado = await ejecutor.ejecutar_cadena(cadena)
    assert isinstance(resultado, ResultadoCadena)
    assert resultado.exito is True
    assert resultado.resultado_final == "respuesta del modelo"
    assert len(resultado.pasos) == 1


@pytest.mark.asyncio
async def test_ejecutar_cadena_multiples_pasos(ejecutor):
    cadena = [
        MicroTarea(prompt="Paso 1", output_key="paso1", max_tokens=200),
        MicroTarea(prompt="Paso 2 con {paso1}", input_keys=["paso1"], output_key="paso2", max_tokens=200),
        MicroTarea(prompt="Paso 3 con {paso2}", input_keys=["paso2"], output_key="final", max_tokens=200),
    ]
    resultado = await ejecutor.ejecutar_cadena(cadena)
    assert resultado.exito is True
    assert len(resultado.pasos) == 3
    assert resultado.tokens_total == 150  # 50 * 3


@pytest.mark.asyncio
async def test_datos_iniciales(ejecutor, tarea_db):
    cadena = [
        MicroTarea(
            prompt="Analiza: {tarea}",
            input_keys=["tarea"],
            output_key="analisis",
        ),
    ]
    resultado = await ejecutor.ejecutar_cadena(
        cadena,
        datos_iniciales={"tarea": "implementar rate limiting"},
    )
    assert resultado.exito is True


@pytest.mark.asyncio
async def test_contexto_limpio_entre_pasos(ejecutor, mock_ia):
    """Cada paso llama al modelo independientemente — no acumula contexto."""
    cadena = [
        MicroTarea(prompt="Paso 1", output_key="p1", max_tokens=200),
        MicroTarea(prompt="Paso 2", output_key="p2", max_tokens=200),
    ]
    await ejecutor.ejecutar_cadena(cadena)
    assert mock_ia.generate.call_count == 2
    call1_prompt = mock_ia.generate.call_args_list[0].kwargs.get("prompt", "")
    call2_prompt = mock_ia.generate.call_args_list[1].kwargs.get("prompt", "")
    assert call1_prompt != call2_prompt or mock_ia.generate.call_count == 2


@pytest.mark.asyncio
async def test_error_en_paso_detiene_cadena(mock_ia, tarea_db):
    mock_ia.generate.side_effect = Exception("modelo caído")
    ejecutor = EjecutorMicroTareas(ia_provider=mock_ia, tarea_db=tarea_db)
    cadena = [
        MicroTarea(prompt="Paso 1", output_key="p1"),
        MicroTarea(prompt="Paso 2", output_key="p2"),
    ]
    resultado = await ejecutor.ejecutar_cadena(cadena)
    assert resultado.exito is False
    assert len(resultado.errores) > 0


@pytest.mark.asyncio
async def test_tarea_id_auto_generado(ejecutor):
    cadena = [MicroTarea(prompt="Test", output_key="out")]
    resultado = await ejecutor.ejecutar_cadena(cadena)
    assert resultado.tarea_id.startswith("chain_")


@pytest.mark.asyncio
async def test_tarea_id_personalizado(ejecutor):
    cadena = [MicroTarea(prompt="Test", output_key="out")]
    resultado = await ejecutor.ejecutar_cadena(cadena, tarea_id="mi_tarea_42")
    assert resultado.tarea_id == "mi_tarea_42"


@pytest.mark.asyncio
async def test_duracion_y_tokens_registrados(ejecutor):
    cadena = [
        MicroTarea(prompt="Paso 1", output_key="p1"),
        MicroTarea(prompt="Paso 2", output_key="p2"),
    ]
    resultado = await ejecutor.ejecutar_cadena(cadena)
    assert resultado.tokens_total > 0
    assert resultado.duracion_total_ms >= 0
    for paso in resultado.pasos:
        assert isinstance(paso, PasoInvestigacion)
        assert paso.tokens >= 0
