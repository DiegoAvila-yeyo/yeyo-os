"""Tests para NodoParalelo — Micro-fase 4.18"""

import asyncio
import time
import pytest
from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import nodo, NodoError
from src.orquestador.paralelo import NodoParalelo


@nodo(id="gen_a", timeout=5.0)
async def gen_a(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["a"] = "valor_a"
    return estado


@nodo(id="gen_b", timeout=5.0)
async def gen_b(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["b"] = "valor_b"
    return estado


@nodo(id="gen_c", timeout=5.0)
async def gen_c(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["c"] = "valor_c"
    return estado


@nodo(id="gen_lento", timeout=5.0)
async def gen_lento(estado: EstadoGrafo) -> EstadoGrafo:
    await asyncio.sleep(0.1)
    estado.salida["lento"] = "hecho"
    return estado


@nodo(id="gen_falla")
async def gen_falla(estado: EstadoGrafo) -> EstadoGrafo:
    raise ValueError("Fallo simulado en gen_falla")


def combinar_simple(resultados):
    combinado = {}
    for r in resultados:
        combinado.update(r.salida)
    return combinado


class TestNodoParaleloConfiguracion:

    def test_creacion_basica(self):
        n = NodoParalelo(
            id="test_paralelo",
            nodos=[gen_a, gen_b],
            combinar=combinar_simple,
        )
        assert n.id == "test_paralelo"
        assert n.modo_error == "fail_fast"

    def test_sin_nodos_falla(self):
        with pytest.raises(ValueError):
            NodoParalelo(id="vacio", nodos=[], combinar=combinar_simple)

    def test_modo_error_invalido_falla(self):
        with pytest.raises(ValueError):
            NodoParalelo(id="test", nodos=[gen_a], combinar=combinar_simple, modo_error="otro_modo")

    def test_modo_continue_on_error_valido(self):
        n = NodoParalelo(
            id="test",
            nodos=[gen_a],
            combinar=combinar_simple,
            modo_error="continue_on_error"
        )
        assert n.modo_error == "continue_on_error"


class TestNodoParaleloEjecucion:

    @pytest.mark.asyncio
    async def test_ejecuta_nodos_en_paralelo(self):
        n = NodoParalelo(
            id="gen_abc",
            nodos=[gen_a, gen_b, gen_c],
            combinar=combinar_simple,
        )
        estado = EstadoGrafo(entrada={})
        resultado = await n.ejecutar(estado)
        assert resultado.salida["a"] == "valor_a"
        assert resultado.salida["b"] == "valor_b"
        assert resultado.salida["c"] == "valor_c"

    @pytest.mark.asyncio
    async def test_tiempo_total_es_del_nodo_mas_lento_no_la_suma(self):
        """Con 3 nodos de 0.1s cada uno, el tiempo total debe ser ~0.1s (no 0.3s)."""
        @nodo(id="p1", timeout=5.0)
        async def p1(e):
            await asyncio.sleep(0.1)
            e.salida["p1"] = True
            return e

        @nodo(id="p2", timeout=5.0)
        async def p2(e):
            await asyncio.sleep(0.1)
            e.salida["p2"] = True
            return e

        n = NodoParalelo(id="paralelo_time", nodos=[p1, p2], combinar=combinar_simple)
        estado = EstadoGrafo(entrada={})
        t_inicio = time.monotonic()
        resultado = await n.ejecutar(estado)
        t_fin = time.monotonic()
        duracion = t_fin - t_inicio
        assert duracion < 0.18, f"Tiempo {duracion:.3f}s debería ser < 0.18s (paralelo)"
        assert resultado.salida.get("p1") is True
        assert resultado.salida.get("p2") is True

    @pytest.mark.asyncio
    async def test_combinar_fusiona_resultados(self):
        def combinar_personalizado(resultados):
            return {
                "total": sum(r.salida.get("valor", 0) for r in resultados),
                "count": len(resultados),
            }

        @nodo(id="num1")
        async def num1(e):
            e.salida["valor"] = 10
            return e

        @nodo(id="num2")
        async def num2(e):
            e.salida["valor"] = 20
            return e

        n = NodoParalelo(id="suma_paralelo", nodos=[num1, num2], combinar=combinar_personalizado)
        estado = EstadoGrafo(entrada={})
        resultado = await n.ejecutar(estado)
        assert resultado.salida["total"] == 30
        assert resultado.salida["count"] == 2

    @pytest.mark.asyncio
    async def test_cada_nodo_recibe_copia_independiente(self):
        """Los nodos no deben compartir el mismo EstadoGrafo."""
        estados_recibidos = []

        @nodo(id="captura1")
        async def captura1(e):
            estados_recibidos.append(id(e))
            return e

        @nodo(id="captura2")
        async def captura2(e):
            estados_recibidos.append(id(e))
            return e

        n = NodoParalelo(id="test_copia", nodos=[captura1, captura2], combinar=combinar_simple)
        estado = EstadoGrafo(entrada={})
        await n.ejecutar(estado)
        assert estados_recibidos[0] != estados_recibidos[1]


class TestNodoParaleloFailFast:

    @pytest.mark.asyncio
    async def test_fail_fast_falla_si_un_nodo_falla(self):
        n = NodoParalelo(
            id="paralelo_falla",
            nodos=[gen_a, gen_falla],
            combinar=combinar_simple,
            modo_error="fail_fast",
        )
        estado = EstadoGrafo(entrada={})
        with pytest.raises(NodoError):
            await n.ejecutar(estado)

    @pytest.mark.asyncio
    async def test_fail_fast_con_todos_exitosos_funciona(self):
        n = NodoParalelo(
            id="paralelo_ok",
            nodos=[gen_a, gen_b],
            combinar=combinar_simple,
            modo_error="fail_fast",
        )
        estado = EstadoGrafo(entrada={})
        resultado = await n.ejecutar(estado)
        assert resultado.salida.get("a") == "valor_a"
        assert resultado.salida.get("b") == "valor_b"


class TestNodoParaleloContinueOnError:

    @pytest.mark.asyncio
    async def test_continue_on_error_continua_si_uno_falla(self):
        n = NodoParalelo(
            id="paralelo_continue",
            nodos=[gen_a, gen_falla, gen_b],
            combinar=combinar_simple,
            modo_error="continue_on_error",
        )
        estado = EstadoGrafo(entrada={})
        resultado = await n.ejecutar(estado)
        assert resultado.salida.get("a") == "valor_a"
        assert resultado.salida.get("b") == "valor_b"

    @pytest.mark.asyncio
    async def test_continue_on_error_registra_errores(self):
        n = NodoParalelo(
            id="paralelo_err",
            nodos=[gen_a, gen_falla],
            combinar=combinar_simple,
            modo_error="continue_on_error",
        )
        estado = EstadoGrafo(entrada={})
        resultado = await n.ejecutar(estado)
        assert "errores_paralelo" in resultado.contexto
        assert len(resultado.contexto["errores_paralelo"]) == 1
        assert resultado.contexto["errores_paralelo"][0]["nodo_id"] == "gen_falla"

    @pytest.mark.asyncio
    async def test_continue_on_error_todos_fallan_lanza_error(self):
        @nodo(id="falla2")
        async def falla2(e):
            raise ValueError("falla2")

        n = NodoParalelo(
            id="todos_fallan",
            nodos=[gen_falla, falla2],
            combinar=combinar_simple,
            modo_error="continue_on_error",
        )
        estado = EstadoGrafo(entrada={})
        with pytest.raises(NodoError, match="Todos los nodos paralelos fallaron"):
            await n.ejecutar(estado)
