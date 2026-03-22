"""Tests para Edge, EdgeDirecto, EdgeCondicional y decorador @edge — Micro-fase 4.16"""

import pytest
from src.orquestador.estado import EstadoGrafo
from src.orquestador.edge import (
    Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
)


def estado_con_score(score: float) -> EstadoGrafo:
    e = EstadoGrafo(entrada={"prompt": "test"})
    e.contexto["score"] = score
    return e


class TestFIN_GRAFO:
    def test_fin_grafo_es_string(self):
        assert isinstance(FIN_GRAFO, str)

    def test_fin_grafo_valor(self):
        assert FIN_GRAFO == "__fin__"


class TestEdgeDirecto:

    @pytest.mark.asyncio
    async def test_evalua_siempre_al_mismo_destino(self):
        e = EdgeDirecto(desde="nodo_a", hasta="nodo_b")
        estado = EstadoGrafo(entrada={})
        assert await e.evaluar(estado) == "nodo_b"

    @pytest.mark.asyncio
    async def test_evalua_siempre_igual_independiente_del_estado(self):
        e = EdgeDirecto(desde="a", hasta="b")
        for _ in range(5):
            estado = EstadoGrafo(entrada={"x": _})
            assert await e.evaluar(estado) == "b"

    @pytest.mark.asyncio
    async def test_puede_apuntar_a_fin_grafo(self):
        e = EdgeDirecto(desde="ultimo", hasta=FIN_GRAFO)
        estado = EstadoGrafo(entrada={})
        assert await e.evaluar(estado) == FIN_GRAFO

    def test_desde_vacio_falla(self):
        with pytest.raises(EdgeError):
            EdgeDirecto(desde="", hasta="nodo_b")

    def test_hasta_vacio_falla(self):
        with pytest.raises(EdgeError):
            EdgeDirecto(desde="nodo_a", hasta="")

    def test_atributos_correctos(self):
        e = EdgeDirecto(desde="origen", hasta="destino")
        assert e.desde == "origen"
        assert e.hasta == "destino"

    def test_repr_informativo(self):
        e = EdgeDirecto(desde="a", hasta="b")
        assert "a" in repr(e)
        assert "b" in repr(e)


class TestEdgeCondicional:

    @pytest.mark.asyncio
    async def test_evalua_con_funcion_sync(self):
        def fn(estado: EstadoGrafo) -> str:
            return "alto" if estado.contexto.get("score", 0) >= 0.8 else "bajo"

        e = EdgeCondicional(desde="evaluar", fn=fn)
        assert await e.evaluar(estado_con_score(0.9)) == "alto"
        assert await e.evaluar(estado_con_score(0.5)) == "bajo"

    @pytest.mark.asyncio
    async def test_evalua_con_funcion_async(self):
        async def fn(estado: EstadoGrafo) -> str:
            return "alto" if estado.contexto.get("score", 0) >= 0.8 else "bajo"

        e = EdgeCondicional(desde="evaluar", fn=fn)
        assert await e.evaluar(estado_con_score(0.9)) == "alto"
        assert await e.evaluar(estado_con_score(0.3)) == "bajo"

    @pytest.mark.asyncio
    async def test_puede_retornar_fin_grafo(self):
        e = EdgeCondicional(
            desde="chequear",
            fn=lambda estado: FIN_GRAFO if estado.contexto.get("terminar") else "continuar"
        )
        estado = EstadoGrafo(entrada={})
        estado.contexto["terminar"] = True
        assert await e.evaluar(estado) == FIN_GRAFO

    @pytest.mark.asyncio
    async def test_multiples_destinos_posibles(self):
        def fn(estado: EstadoGrafo) -> str:
            score = estado.contexto.get("score", 0)
            if score >= 0.8:
                return "upscale"
            elif score >= 0.5:
                return "refinar"
            else:
                return "regenerar"

        e = EdgeCondicional(desde="evaluar", fn=fn)
        assert await e.evaluar(estado_con_score(0.9)) == "upscale"
        assert await e.evaluar(estado_con_score(0.6)) == "refinar"
        assert await e.evaluar(estado_con_score(0.2)) == "regenerar"

    @pytest.mark.asyncio
    async def test_retornar_no_string_falla(self):
        e = EdgeCondicional(desde="test", fn=lambda e: 42)
        estado = EstadoGrafo(entrada={})
        with pytest.raises(EdgeError, match="string"):
            await e.evaluar(estado)

    @pytest.mark.asyncio
    async def test_retornar_string_vacio_falla(self):
        e = EdgeCondicional(desde="test", fn=lambda e: "")
        estado = EstadoGrafo(entrada={})
        with pytest.raises(EdgeError):
            await e.evaluar(estado)

    def test_fn_none_falla(self):
        with pytest.raises(EdgeError):
            EdgeCondicional(desde="test", fn=None)

    def test_desde_vacio_falla(self):
        with pytest.raises(EdgeError):
            EdgeCondicional(desde="", fn=lambda e: "x")

    def test_repr_informativo(self):
        e = EdgeCondicional(desde="evaluar", fn=lambda e: "x", nombre="mi_fn")
        assert "evaluar" in repr(e)
        assert "mi_fn" in repr(e)


class TestDecoradorEdge:

    @pytest.mark.asyncio
    async def test_decorador_crea_edge_condicional(self):
        @edge(desde="evaluar")
        def siguiente(estado: EstadoGrafo) -> str:
            return "ok"

        assert isinstance(siguiente, EdgeCondicional)
        assert siguiente.desde == "evaluar"

    @pytest.mark.asyncio
    async def test_decorador_sync_evalua_correctamente(self):
        @edge(desde="evaluar")
        def siguiente(estado: EstadoGrafo) -> str:
            return "alto" if estado.contexto.get("score", 0) >= 0.8 else "bajo"

        assert await siguiente.evaluar(estado_con_score(0.9)) == "alto"
        assert await siguiente.evaluar(estado_con_score(0.3)) == "bajo"

    @pytest.mark.asyncio
    async def test_decorador_async_evalua_correctamente(self):
        @edge(desde="evaluar")
        async def siguiente(estado: EstadoGrafo) -> str:
            return "resultado_async"

        estado = EstadoGrafo(entrada={})
        assert await siguiente.evaluar(estado) == "resultado_async"

    def test_decorador_desde_vacio_falla(self):
        with pytest.raises(EdgeError):
            @edge(desde="")
            def fn(e):
                return "x"

    def test_decorador_preserva_nombre_funcion(self):
        @edge(desde="nodo_a")
        def mi_logica_de_routing(estado: EstadoGrafo) -> str:
            return "destino"

        assert mi_logica_de_routing.nombre == "mi_logica_de_routing"
