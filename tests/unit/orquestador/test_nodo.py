"""Tests para Nodo, NodoFuncion, NodoInline y decorador @nodo — Micro-fase 4.15"""

import asyncio
import pytest
from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import (
    Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
)


# ─── Fixtures ─────────────────────────────────────────────────────────────

def estado_simple() -> EstadoGrafo:
    return EstadoGrafo(entrada={"texto": "hola"})


# ─── Tests: Forma 1 — Decorador @nodo ─────────────────────────────────────

class TestDecoradorNodo:

    @pytest.mark.asyncio
    async def test_decorador_crea_nodo_funcion(self):
        @nodo(id="test_nodo")
        async def mi_fn(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["resultado"] = "ok"
            return estado

        assert isinstance(mi_fn, NodoFuncion)
        assert mi_fn.id == "test_nodo"

    @pytest.mark.asyncio
    async def test_decorador_ejecuta_correctamente(self):
        @nodo(id="suma")
        async def sumar(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["total"] = estado.entrada.get("a", 0) + estado.entrada.get("b", 0)
            return estado

        estado = EstadoGrafo(entrada={"a": 3, "b": 4})
        resultado = await sumar.ejecutar(estado)
        assert resultado.salida["total"] == 7

    def test_decorador_timeout_configurado(self):
        @nodo(id="nodo_lento", timeout=120.0)
        async def fn(estado):
            return estado

        assert fn.timeout == 120.0

    def test_decorador_max_intentos_configurado(self):
        @nodo(id="nodo_retry", max_intentos=3)
        async def fn(estado):
            return estado

        assert fn.max_intentos == 3

    def test_decorador_id_vacio_falla(self):
        with pytest.raises(ValueError):
            @nodo(id="")
            async def fn(estado):
                return estado

    @pytest.mark.asyncio
    async def test_decorador_timeout_se_respeta(self):
        @nodo(id="nodo_muy_lento", timeout=0.05)
        async def fn_lenta(estado: EstadoGrafo) -> EstadoGrafo:
            await asyncio.sleep(0.2)
            return estado

        estado = estado_simple()
        with pytest.raises(NodoTimeoutError):
            await fn_lenta.ejecutar_con_timeout(estado)

    @pytest.mark.asyncio
    async def test_nodo_rapido_no_timeout(self):
        @nodo(id="nodo_rapido", timeout=2.0)
        async def fn_rapida(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["ok"] = True
            return estado

        estado = estado_simple()
        resultado = await fn_rapida.ejecutar_con_timeout(estado)
        assert resultado.salida["ok"] is True


# ─── Tests: Forma 2 — Herencia de Nodo ─────────────────────────────────────

class TestNodoClase:

    @pytest.mark.asyncio
    async def test_nodo_por_herencia_ejecuta(self):
        class MiNodo(Nodo):
            id = "nodo_herencia"
            timeout = 10.0
            max_intentos = 2

            async def ejecutar(self, estado: EstadoGrafo) -> EstadoGrafo:
                estado.salida["tipo"] = "herencia"
                return estado

        nodo_inst = MiNodo()
        estado = estado_simple()
        resultado = await nodo_inst.ejecutar(estado)
        assert resultado.salida["tipo"] == "herencia"

    def test_nodo_herencia_atributos_clase(self):
        class NodoConfig(Nodo):
            id = "nodo_config"
            timeout = 45.0
            max_intentos = 5

            async def ejecutar(self, estado):
                return estado

        n = NodoConfig()
        assert n.id == "nodo_config"
        assert n.timeout == 45.0
        assert n.max_intentos == 5

    def test_nodo_sin_id_falla(self):
        class NodoSinId(Nodo):
            async def ejecutar(self, estado):
                return estado

        with pytest.raises(ValueError):
            NodoSinId()

    def test_nodo_timeout_invalido_falla(self):
        with pytest.raises(ValueError):
            NodoFuncion(id="test", fn=lambda e: e, timeout=-1.0)

    def test_nodo_max_intentos_cero_falla(self):
        with pytest.raises(ValueError):
            NodoFuncion(id="test", fn=lambda e: e, max_intentos=0)

    @pytest.mark.asyncio
    async def test_nodo_sin_override_falla(self):
        class NodoBase(Nodo):
            id = "nodo_base"
            # No sobreescribe ejecutar()

        n = NodoBase()
        estado = estado_simple()
        with pytest.raises(NotImplementedError):
            await n.ejecutar(estado)


# ─── Tests: Forma 3 — Inline ───────────────────────────────────────────────

class TestNodoInline:

    @pytest.mark.asyncio
    async def test_nodo_inline_con_lambda(self):
        nodo_passthrough = NodoInline(
            id="passthrough",
            fn=lambda estado: estado
        )
        estado = estado_simple()
        resultado = await nodo_passthrough.ejecutar(estado)
        assert resultado is estado  # mismo objeto

    @pytest.mark.asyncio
    async def test_nodo_inline_con_async_fn(self):
        async def fn_async(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["procesado"] = True
            return estado

        nodo_inst = NodoInline(id="async_inline", fn=fn_async)
        estado = estado_simple()
        resultado = await nodo_inst.ejecutar(estado)
        assert resultado.salida["procesado"] is True

    def test_nodo_inline_configuracion(self):
        n = NodoInline(id="test", fn=lambda e: e, timeout=15.0, max_intentos=2)
        assert n.id == "test"
        assert n.timeout == 15.0
        assert n.max_intentos == 2

    @pytest.mark.asyncio
    async def test_nodo_inline_modifica_estado(self):
        def fn_modificadora(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["clave"] = "valor"
            estado.contexto["flag"] = True
            return estado

        n = NodoInline(id="modificador", fn=fn_modificadora)
        estado = estado_simple()
        resultado = await n.ejecutar(estado)
        assert resultado.salida["clave"] == "valor"
        assert resultado.contexto["flag"] is True


# ─── Tests: NodoError y NodoTimeoutError ───────────────────────────────────

class TestNodoErrors:

    def test_nodo_error_tiene_nodo_id(self):
        error = NodoError("mi_nodo", "algo falló")
        assert error.nodo_id == "mi_nodo"
        assert "mi_nodo" in str(error)

    def test_nodo_timeout_error_es_nodo_error(self):
        error = NodoTimeoutError("nodo_lento", "timeout")
        assert isinstance(error, NodoError)

    def test_nodo_error_con_causa(self):
        causa = ValueError("causa original")
        error = NodoError("nodo", "fallo", causa=causa)
        assert error.causa is causa


# ─── Tests: repr y metadata ────────────────────────────────────────────────

class TestNodoRepr:

    def test_repr_nodo_funcion(self):
        @nodo(id="mi_nodo", timeout=10.0)
        async def fn(e):
            return e
        assert "mi_nodo" in repr(fn)

    def test_nodo_inline_repr(self):
        n = NodoInline(id="inline_test", fn=lambda e: e)
        assert "inline_test" in repr(n)
