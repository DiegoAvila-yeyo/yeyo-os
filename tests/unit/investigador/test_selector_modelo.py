"""
Tests unitarios para SelectorModelo.
Micro-fase 5.32 — 8 tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.investigador.selector_modelo import SelectorModelo
from src.investigador.modelos_selector import (
    ModeloConfig,
    MODELO_LOCAL_SMALL,
    MODELO_LOCAL_CODER,
    MODELO_YEYONET_DEFAULT,
    MODELO_API_FALLBACK,
)


@pytest.fixture
def selector():
    return SelectorModelo(
        ollama_host="http://localhost:11434",
        yeyonet_endpoint=None,
        api_key=None,
    )


def test_estimar_complejidad_simple(selector):
    comp = selector.estimar_complejidad("hola mundo")
    assert comp < 0.3


def test_estimar_complejidad_media(selector):
    comp = selector.estimar_complejidad(
        "crear una API REST con database y authentication para middleware"
    )
    assert comp >= 0.15


def test_estimar_complejidad_alta(selector):
    comp = selector.estimar_complejidad(
        "implementar un sistema distributed con machine learning "
        "concurrent processing y neural network optimization "
        "con security encryption para microservices"
    )
    assert comp >= 0.5


@pytest.mark.asyncio
async def test_elegir_modelo_simple(selector):
    with patch.object(selector, '_esta_disponible', return_value=True):
        modelo = await selector.elegir("hola")
        assert isinstance(modelo, ModeloConfig)
        assert modelo.tipo == "local"


@pytest.mark.asyncio
async def test_elegir_modelo_con_override(selector):
    modelo_mock = ModeloConfig(nombre="test:model", tipo="local", disponible=True)
    selector._modelos_cache = [modelo_mock]
    with patch.object(selector, '_esta_disponible', return_value=True):
        modelo = await selector.elegir("cualquier tarea", modelo_override="test:model")
        assert modelo.nombre == "test:model"


@pytest.mark.asyncio
async def test_fallback_si_no_disponible(selector):
    """Si el modelo preferido no está, baja al siguiente."""
    call_count = [0]

    async def disponible_selectivo(modelo):
        call_count[0] += 1
        return modelo.nombre == "qwen2.5:3b"

    with patch.object(selector, '_esta_disponible', side_effect=disponible_selectivo):
        modelo = await selector.elegir("tarea compleja con machine learning distributed")
        assert modelo.nombre == "qwen2.5:3b"


def test_registrar_tiempo(selector):
    selector.registrar_tiempo("api_rest", 5000)
    selector.registrar_tiempo("api_rest", 6000)
    assert len(selector._historial_tiempos["api_rest"]) == 2


@pytest.mark.asyncio
async def test_invalidar_cache(selector):
    selector._modelos_cache = [MODELO_LOCAL_SMALL]
    await selector.invalidar_cache()
    assert selector._modelos_cache is None


@pytest.mark.asyncio
async def test_modelos_disponibles_default(selector):
    """Retorna al menos un modelo disponible (local Ollama o default)."""
    modelos = await selector.modelos_disponibles()
    assert len(modelos) >= 1
    # Todos los modelos detectados deben tener nombre y tipo
    for m in modelos:
        assert m.nombre != ""
        assert m.tipo in ("local", "yeyonet", "api")
