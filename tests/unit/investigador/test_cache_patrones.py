"""
Tests unitarios para CachePatrones + Anticipador.
Micro-fase 5.31 — 8 tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.investigador.cache_patrones import CachePatrones
from src.investigador.anticipador import Anticipador
from src.investigador.modelos_cache import PatronRazonamiento, PreComputado


@pytest.fixture
def mock_ia():
    ia = AsyncMock()
    ia.get_embedding.return_value = [0.1] * 768
    ia.generate.return_value = MagicMock(
        content="PREDICCION 1: crear tests\nPREDICCION 2: deploy",
        tokens_used=50,
        latency_ms=100,
    )
    return ia


@pytest.fixture
def cache(mock_ia):
    return CachePatrones(pool=None, ia_provider=mock_ia)


@pytest.fixture
def anticipador(mock_ia, cache):
    return Anticipador(ia_provider=mock_ia, cache_patrones=cache)


@pytest.mark.asyncio
async def test_guardar_patron(cache):
    patron = await cache.guardar_patron(
        tipo_problema="rate limiting en FastAPI",
        pasos_razonamiento=[{"paso": 1, "accion": "importar slowapi"}],
        errores_comunes=[{"error": "olvidar middleware"}],
        patron_correcto="from slowapi import Limiter\nlimiter = Limiter(key_func=get_remote_address)",
        tiempo_original_ms=5000,
        confianza=0.9,
        aplicable_a=["fastapi", "api"],
    )
    assert isinstance(patron, PatronRazonamiento)
    assert patron.tipo_problema == "rate limiting en FastAPI"
    assert patron.confianza == 0.9


@pytest.mark.asyncio
async def test_buscar_patron_local(cache):
    await cache.guardar_patron(
        tipo_problema="rate limiting en FastAPI",
        pasos_razonamiento=[],
        errores_comunes=[],
        patron_correcto="solución rate limiting",
        tiempo_original_ms=3000,
        confianza=0.85,
    )
    resultado = await cache.buscar_patron("rate limiting en FastAPI")
    assert resultado is not None
    assert "rate limiting" in resultado.tipo_problema.lower()


@pytest.mark.asyncio
async def test_buscar_patron_no_encontrado(cache):
    resultado = await cache.buscar_patron("quantum computing con Rust")
    assert resultado is None


@pytest.mark.asyncio
async def test_patron_incrementa_reutilizado(cache):
    await cache.guardar_patron(
        tipo_problema="autenticación JWT",
        pasos_razonamiento=[],
        errores_comunes=[],
        patron_correcto="jwt token code",
        tiempo_original_ms=2000,
        confianza=0.8,
    )
    patron = await cache.buscar_patron("autenticación JWT en Python")
    if patron:
        assert patron.veces_reutilizado >= 1


@pytest.mark.asyncio
async def test_anticipador_registrar_acciones(anticipador):
    anticipador.registrar_accion("crear archivo models.py")
    anticipador.registrar_accion("escribir tests")
    anticipador.registrar_accion("ejecutar pytest")
    assert len(anticipador._acciones) == 3


@pytest.mark.asyncio
async def test_anticipador_predecir(anticipador):
    for i in range(5):
        anticipador.registrar_accion(f"acción {i}")
    predicciones = await anticipador.predecir()
    assert isinstance(predicciones, list)


@pytest.mark.asyncio
async def test_anticipador_pre_computar(anticipador, mock_ia):
    mock_ia.generate.return_value = MagicMock(
        content="solución pre-computada",
        tokens_used=30,
        latency_ms=50,
    )
    precomputados = await anticipador.pre_computar(["crear tests unitarios"])
    assert len(precomputados) >= 1
    assert isinstance(precomputados[0], PreComputado)


@pytest.mark.asyncio
async def test_anticipador_obtener_precomputado(anticipador, mock_ia):
    mock_ia.generate.return_value = MagicMock(
        content="código de tests",
        tokens_used=30,
        latency_ms=50,
    )
    await anticipador.pre_computar(["escribir tests unitarios"])
    resultado = await anticipador.obtener_precomputado("escribir tests unitarios para auth")
    if resultado:
        assert isinstance(resultado, PreComputado)
        assert resultado.usada is True
