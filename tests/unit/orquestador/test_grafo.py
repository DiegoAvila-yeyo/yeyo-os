"""Tests para YeyoGrafo y ResultadoGrafo — Micro-fase 4.17"""

import asyncio
import pytest
from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import nodo, NodoInline, NodoError
from src.orquestador.edge import edge, FIN_GRAFO
from src.orquestador.grafo import YeyoGrafo, ResultadoGrafo, GrafoError


@nodo(id="nodo_a", timeout=5.0)
async def nodo_a(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["a"] = "ejecutado"
    return estado


@nodo(id="nodo_b", timeout=5.0)
async def nodo_b(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["b"] = "ejecutado"
    return estado


@nodo(id="nodo_c", timeout=5.0)
async def nodo_c(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["c"] = "ejecutado"
    return estado


@nodo(id="nodo_falla")
async def nodo_falla(estado: EstadoGrafo) -> EstadoGrafo:
    raise ValueError("Error simulado en nodo_falla")


@nodo(id="nodo_lento", timeout=0.1)
async def nodo_lento(estado: EstadoGrafo) -> EstadoGrafo:
    await asyncio.sleep(1.0)
    return estado


class TestYeyoGrafoConfiguracion:

    def test_grafo_con_id_valido(self):
        g = YeyoGrafo("mi_grafo", "Descripción")
        assert g.id == "mi_grafo"
        assert g.descripcion == "Descripción"

    def test_grafo_sin_id_falla(self):
        with pytest.raises(GrafoError):
            YeyoGrafo("")

    def test_agregar_nodo_devuelve_grafo(self):
        g = YeyoGrafo("test")
        result = g.agregar_nodo(nodo_a)
        assert result is g  # method chaining

    def test_agregar_nodo_duplicado_falla(self):
        g = YeyoGrafo("test").agregar_nodo(nodo_a)
        with pytest.raises(GrafoError, match="Ya existe"):
            g.agregar_nodo(nodo_a)

    @pytest.mark.asyncio
    async def test_inicio_sin_inicio_falla(self):
        g = YeyoGrafo("test").agregar_nodo(nodo_a)
        with pytest.raises(GrafoError, match="inicio"):
            await g.ejecutar({})

    def test_repr_informativo(self):
        g = YeyoGrafo("mi_grafo").agregar_nodo(nodo_a).inicio("nodo_a")
        assert "mi_grafo" in repr(g)


class TestYeyoGrafoEjecucionSimple:

    @pytest.mark.asyncio
    async def test_grafo_un_nodo(self):
        g = (YeyoGrafo("test_uno")
             .agregar_nodo(nodo_a)
             .inicio("nodo_a")
             .fin("nodo_a"))
        resultado = await g.ejecutar({"texto": "hola"})
        assert resultado.exito is True
        assert "nodo_a" in resultado.nodos_ejecutados
        assert resultado.estado_final.salida["a"] == "ejecutado"

    @pytest.mark.asyncio
    async def test_grafo_tres_nodos_en_secuencia(self):
        g = (YeyoGrafo("test_secuencia")
             .agregar_nodo(nodo_a)
             .agregar_nodo(nodo_b)
             .agregar_nodo(nodo_c)
             .inicio("nodo_a")
             .edge("nodo_a", "nodo_b")
             .edge("nodo_b", "nodo_c")
             .fin("nodo_c"))
        resultado = await g.ejecutar({"texto": "hola"})
        assert resultado.exito is True
        assert resultado.nodos_ejecutados == ["nodo_a", "nodo_b", "nodo_c"]
        assert resultado.estado_final.salida["a"] == "ejecutado"
        assert resultado.estado_final.salida["b"] == "ejecutado"
        assert resultado.estado_final.salida["c"] == "ejecutado"

    @pytest.mark.asyncio
    async def test_resultado_tiene_duracion(self):
        g = YeyoGrafo("test").agregar_nodo(nodo_a).inicio("nodo_a").fin("nodo_a")
        resultado = await g.ejecutar({})
        assert resultado.duracion_total_ms >= 0

    @pytest.mark.asyncio
    async def test_acepta_estado_grafo_como_entrada(self):
        g = YeyoGrafo("test").agregar_nodo(nodo_a).inicio("nodo_a").fin("nodo_a")
        estado_previo = EstadoGrafo(entrada={"previo": True})
        estado_previo.contexto["dato_previo"] = "valor"
        resultado = await g.ejecutar(estado_previo)
        assert resultado.estado_final.contexto["dato_previo"] == "valor"


class TestYeyoGrafoCondicional:

    @pytest.mark.asyncio
    async def test_edge_condicional_elige_ruta_correcta(self):
        @nodo(id="ruta_alta")
        async def ruta_alta(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["ruta"] = "alta"
            return estado

        @nodo(id="ruta_baja")
        async def ruta_baja(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["ruta"] = "baja"
            return estado

        @nodo(id="evaluador")
        async def evaluador(estado: EstadoGrafo) -> EstadoGrafo:
            estado.contexto["score"] = estado.entrada.get("score", 0)
            return estado

        g = (YeyoGrafo("test_cond")
             .agregar_nodo(evaluador)
             .agregar_nodo(ruta_alta)
             .agregar_nodo(ruta_baja)
             .inicio("evaluador")
             .edge_condicional("evaluador", lambda e: "ruta_alta" if e.contexto["score"] >= 0.8 else "ruta_baja")
             .fin("ruta_alta"))

        resultado_alto = await g.ejecutar({"score": 0.9})
        assert resultado_alto.estado_final.salida["ruta"] == "alta"

        resultado_bajo = await g.ejecutar({"score": 0.3})
        assert resultado_bajo.estado_final.salida["ruta"] == "baja"


class TestYeyoGrafoErrores:

    @pytest.mark.asyncio
    async def test_nodo_que_falla_retorna_exito_false(self):
        g = (YeyoGrafo("test_falla")
             .agregar_nodo(nodo_falla)
             .inicio("nodo_falla")
             .fin("nodo_falla"))
        resultado = await g.ejecutar({})
        assert resultado.exito is False
        assert len(resultado.errores) > 0

    @pytest.mark.asyncio
    async def test_max_intentos_se_respeta(self):
        contador = {"n": 0}

        @nodo(id="nodo_retry_test", max_intentos=3)
        async def nodo_retry(estado: EstadoGrafo) -> EstadoGrafo:
            contador["n"] += 1
            raise ValueError("Falla siempre")

        g = (YeyoGrafo("test_retry")
             .agregar_nodo(nodo_retry)
             .inicio("nodo_retry_test")
             .fin("nodo_retry_test"))
        resultado = await g.ejecutar({})
        assert resultado.exito is False
        assert contador["n"] == 3  # 3 intentos

    @pytest.mark.asyncio
    async def test_nodo_timeout_se_respeta(self):
        g = (YeyoGrafo("test_timeout")
             .agregar_nodo(nodo_lento)
             .inicio("nodo_lento")
             .fin("nodo_lento"))
        resultado = await g.ejecutar({})
        assert resultado.exito is False
        assert "timeout" in resultado.errores[0]["mensaje"].lower()

    @pytest.mark.asyncio
    async def test_timeout_total_grafo(self):
        @nodo(id="nodo_muy_lento", timeout=10.0)
        async def nodo_muy_lento(estado: EstadoGrafo) -> EstadoGrafo:
            await asyncio.sleep(5.0)
            return estado

        g = (YeyoGrafo("test_timeout_total", timeout_total=0.1)
             .agregar_nodo(nodo_muy_lento)
             .inicio("nodo_muy_lento")
             .fin("nodo_muy_lento"))
        resultado = await g.ejecutar({})
        assert resultado.exito is False


class TestYeyoGrafoSubgrafo:

    @pytest.mark.asyncio
    async def test_subgrafo_como_nodo(self):
        sub = (YeyoGrafo("sub_grafo")
               .agregar_nodo(nodo_a)
               .agregar_nodo(nodo_b)
               .inicio("nodo_a")
               .edge("nodo_a", "nodo_b")
               .fin("nodo_b"))

        @nodo(id="antes")
        async def nodo_antes(estado: EstadoGrafo) -> EstadoGrafo:
            estado.contexto["antes"] = True
            return estado

        principal = (YeyoGrafo("grafo_principal")
                     .agregar_nodo(nodo_antes)
                     .agregar_nodo(sub.como_nodo())
                     .inicio("antes")
                     .edge("antes", "sub_grafo")
                     .fin("sub_grafo"))

        resultado = await principal.ejecutar({"texto": "test"})
        assert resultado.exito is True
        assert resultado.estado_final.salida.get("a") == "ejecutado"
        assert resultado.estado_final.salida.get("b") == "ejecutado"


class TestYeyoGrafoCallbackEvento:

    @pytest.mark.asyncio
    async def test_callback_recibe_eventos(self):
        eventos_recibidos = []

        async def mi_callback(evento: dict) -> None:
            eventos_recibidos.append(evento)

        g = (YeyoGrafo("test_eventos")
             .agregar_nodo(nodo_a)
             .agregar_nodo(nodo_b)
             .inicio("nodo_a")
             .edge("nodo_a", "nodo_b")
             .fin("nodo_b"))

        await g.ejecutar({}, on_evento=mi_callback)

        assert len(eventos_recibidos) >= 4
        estados = [e["estado"] for e in eventos_recibidos]
        assert "activo" in estados
        assert "completado" in estados

    @pytest.mark.asyncio
    async def test_evento_tiene_estructura_correcta(self):
        eventos = []

        async def callback(evento):
            eventos.append(evento)

        g = YeyoGrafo("test").agregar_nodo(nodo_a).inicio("nodo_a").fin("nodo_a")
        await g.ejecutar({}, on_evento=callback)

        evento = eventos[0]
        assert evento["type"] == "graph_event"
        assert evento["grafo_id"] == "test"
        assert "nodo_id" in evento
        assert "estado" in evento
        assert "progreso" in evento
        assert "timestamp" in evento
        assert 0.0 <= evento["progreso"] <= 1.0
