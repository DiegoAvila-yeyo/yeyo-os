"""Tests para NodoCache — Micro-fase 5.23"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import nodo, NodoInline
from src.orquestador.cache import NodoCache, TIPO_CACHE


# ─── Nodo de prueba ────────────────────────────────────────────────────────

contador_ejecuciones = {"n": 0}


@nodo(id="nodo_costoso")
async def nodo_costoso(estado: EstadoGrafo) -> EstadoGrafo:
    contador_ejecuciones["n"] += 1
    estado.salida["resultado_costoso"] = f"resultado_{contador_ejecuciones['n']}"
    return estado


def reset_contador():
    contador_ejecuciones["n"] = 0


# ─── Mock de FlashMemory ───────────────────────────────────────────────────

def mock_flash_memory_vacio():
    m = AsyncMock()
    m.guardar = AsyncMock(return_value="mem-cache-001")
    m.buscar = AsyncMock(return_value=[])
    return m


def mock_flash_memory_con_cache(salida_cacheada: dict, hash_entrada: str, nodo_id: str):
    m = AsyncMock()
    cache_data = {
        "nodo_id": nodo_id,
        "hash_entrada": hash_entrada,
        "salida": salida_cacheada,
        "guardado_en": datetime.now(timezone.utc).isoformat(),
        "tipo": TIPO_CACHE,
    }
    m.guardar = AsyncMock(return_value="mem-cache-001")
    m.buscar = AsyncMock(return_value=[{
        "id": "mem-cache-001",
        "contenido": json.dumps(cache_data),
        "score": 0.99
    }])
    return m


def mock_flash_memory_con_cache_expirado(salida_cacheada: dict, hash_entrada: str, nodo_id: str):
    m = AsyncMock()
    tiempo_expirado = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    cache_data = {
        "nodo_id": nodo_id,
        "hash_entrada": hash_entrada,
        "salida": salida_cacheada,
        "guardado_en": tiempo_expirado,
        "tipo": TIPO_CACHE,
    }
    m.guardar = AsyncMock(return_value="mem-cache-001")
    m.buscar = AsyncMock(return_value=[{
        "id": "mem-cache-001",
        "contenido": json.dumps(cache_data),
        "score": 0.99
    }])
    return m


class TestNodoCacheHash:

    def test_mismo_input_mismo_hash(self):
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        entrada = {"texto": "hola", "usuario": "u1"}
        h1 = nc._hash_entrada(entrada)
        h2 = nc._hash_entrada(entrada)
        assert h1 == h2

    def test_diferente_input_diferente_hash(self):
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        h1 = nc._hash_entrada({"texto": "hola"})
        h2 = nc._hash_entrada({"texto": "adios"})
        assert h1 != h2

    def test_orden_no_importa_mismo_hash(self):
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        h1 = nc._hash_entrada({"b": 2, "a": 1})
        h2 = nc._hash_entrada({"a": 1, "b": 2})
        assert h1 == h2

    def test_hash_tiene_16_caracteres(self):
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        h = nc._hash_entrada({"x": "y"})
        assert len(h) == 16

    def test_campos_entrada_filtra_campos(self):
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash, campos_entrada=["texto"])
        h1 = nc._hash_entrada({"texto": "hola", "timestamp": "2025-01-01"})
        h2 = nc._hash_entrada({"texto": "hola", "timestamp": "2025-12-31"})
        assert h1 == h2


class TestNodoCacheMiss:

    @pytest.mark.asyncio
    async def test_cache_miss_ejecuta_nodo(self):
        reset_contador()
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        estado = EstadoGrafo(entrada={"texto": "nuevo"})
        await nc.ejecutar(estado)
        assert contador_ejecuciones["n"] == 1
        assert nc.cache_misses == 1

    @pytest.mark.asyncio
    async def test_cache_miss_guarda_resultado(self):
        reset_contador()
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        estado = EstadoGrafo(entrada={"texto": "guardar"})
        await nc.ejecutar(estado)
        flash.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_miss_marca_contexto(self):
        reset_contador()
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        estado = EstadoGrafo(entrada={"texto": "miss"})
        resultado = await nc.ejecutar(estado)
        assert resultado.contexto.get("cache_hit") is False

    @pytest.mark.asyncio
    async def test_cache_miss_tiene_resultado_del_nodo(self):
        reset_contador()
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        estado = EstadoGrafo(entrada={"texto": "ejecutar"})
        resultado = await nc.ejecutar(estado)
        assert "resultado_costoso" in resultado.salida


class TestNodoCacheHit:

    @pytest.mark.asyncio
    async def test_cache_hit_no_ejecuta_nodo(self):
        reset_contador()
        estado = EstadoGrafo(entrada={"texto": "cacheado"})
        nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
        hash_entrada = nc_temp._hash_entrada(estado.entrada)

        salida_cacheada = {"resultado_costoso": "resultado_del_cache"}
        flash = mock_flash_memory_con_cache(salida_cacheada, hash_entrada, "nodo_costoso")
        nc = NodoCache(nodo_costoso, flash)
        resultado = await nc.ejecutar(estado)

        assert contador_ejecuciones["n"] == 0
        assert nc.cache_hits == 1
        assert resultado.salida["resultado_costoso"] == "resultado_del_cache"

    @pytest.mark.asyncio
    async def test_cache_hit_marca_contexto(self):
        estado = EstadoGrafo(entrada={"texto": "hit"})
        nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
        hash_entrada = nc_temp._hash_entrada(estado.entrada)

        flash = mock_flash_memory_con_cache({"r": "ok"}, hash_entrada, "nodo_costoso")
        nc = NodoCache(nodo_costoso, flash)
        resultado = await nc.ejecutar(estado)
        assert resultado.contexto.get("cache_hit") is True

    @pytest.mark.asyncio
    async def test_cache_hit_no_guarda_en_flash_memory(self):
        estado = EstadoGrafo(entrada={"texto": "hit_no_guardar"})
        nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
        hash_entrada = nc_temp._hash_entrada(estado.entrada)

        flash = mock_flash_memory_con_cache({"r": "ok"}, hash_entrada, "nodo_costoso")
        nc = NodoCache(nodo_costoso, flash)
        await nc.ejecutar(estado)
        flash.guardar.assert_not_called()


class TestNodoCacheExpirado:

    @pytest.mark.asyncio
    async def test_cache_expirado_ejecuta_nodo(self):
        reset_contador()
        estado = EstadoGrafo(entrada={"texto": "expirado"})
        nc_temp = NodoCache(nodo_costoso, mock_flash_memory_vacio())
        hash_entrada = nc_temp._hash_entrada(estado.entrada)

        flash = mock_flash_memory_con_cache_expirado(
            {"r": "viejo"}, hash_entrada, "nodo_costoso"
        )
        nc = NodoCache(nodo_costoso, flash)
        resultado = await nc.ejecutar(estado)
        assert contador_ejecuciones["n"] == 1
        assert nc.cache_misses == 1


class TestNodoCacheTasaHit:

    def test_tasa_hit_sin_ejecuciones(self):
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        assert nc.tasa_hit == 0.0

    def test_tasa_hit_con_datos(self):
        flash = mock_flash_memory_vacio()
        nc = NodoCache(nodo_costoso, flash)
        nc.cache_hits = 3
        nc.cache_misses = 1
        assert nc.tasa_hit == 0.75


class TestNodoCacheErrorFlash:

    @pytest.mark.asyncio
    async def test_error_en_buscar_no_interrumpe(self):
        reset_contador()
        flash = AsyncMock()
        flash.buscar = AsyncMock(side_effect=ConnectionError("down"))
        flash.guardar = AsyncMock(return_value="mem-001")
        nc = NodoCache(nodo_costoso, flash)
        estado = EstadoGrafo(entrada={"texto": "error_buscar"})
        resultado = await nc.ejecutar(estado)
        assert contador_ejecuciones["n"] == 1
        assert "resultado_costoso" in resultado.salida

    @pytest.mark.asyncio
    async def test_error_en_guardar_no_interrumpe(self):
        reset_contador()
        flash = AsyncMock()
        flash.buscar = AsyncMock(return_value=[])
        flash.guardar = AsyncMock(side_effect=ConnectionError("down"))
        nc = NodoCache(nodo_costoso, flash)
        estado = EstadoGrafo(entrada={"texto": "error_guardar"})
        resultado = await nc.ejecutar(estado)
        assert contador_ejecuciones["n"] == 1
