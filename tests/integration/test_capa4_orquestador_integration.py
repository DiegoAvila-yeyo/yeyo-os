"""
Tests de integración del YeyoOrquestador — Micro-fase 4.23
Prueba el flujo completo de punta a punta con mocks para Ollama y FlashMemory.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import nodo, NodoInline
from src.orquestador.edge import edge, FIN_GRAFO
from src.orquestador.grafo import YeyoGrafo
from src.orquestador.paralelo import NodoParalelo
from src.orquestador.orquestador import YeyoOrquestador
from src.orquestador.catalogo import CatalogoNodos
from src.orquestador.eventos import GraphEventEmitter, crear_evento_grafo
from src.orquestador.grafos import crear_grafo_chat_contextual, crear_grafo_busqueda_semantica


def mock_ollama(respuesta="Respuesta OK"):
    m = AsyncMock()
    resp = MagicMock()
    resp.content = respuesta
    resp.tool_calls = None
    m.chat = AsyncMock(return_value=resp)
    m.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4])
    return m


def mock_flash_memory():
    m = AsyncMock()
    m.guardar = AsyncMock(return_value="mem-integ-001")
    m.buscar = AsyncMock(return_value=[
        {"id": "m1", "contenido": "dato relevante", "score": 0.9}
    ])
    return m


def mock_connection_manager():
    m = AsyncMock()
    m.broadcast = AsyncMock()
    m.mensajes_ws = []
    async def capturar(msg):
        m.mensajes_ws.append(msg)
    m.broadcast.side_effect = capturar
    return m


class TestIntegracionEstadoGrafo:

    @pytest.mark.asyncio
    async def test_estado_fluye_entre_3_nodos(self):
        @nodo(id="paso1")
        async def paso1(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["paso1"] = "ejecutado"
            e.contexto["contador"] = 1
            return e

        @nodo(id="paso2")
        async def paso2(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["paso2"] = "ejecutado"
            e.contexto["contador"] += 1
            return e

        @nodo(id="paso3")
        async def paso3(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["contador_final"] = e.contexto["contador"]
            return e

        g = (YeyoGrafo("flujo_estado")
             .agregar_nodo(paso1)
             .agregar_nodo(paso2)
             .agregar_nodo(paso3)
             .inicio("paso1")
             .edge("paso1", "paso2")
             .edge("paso2", "paso3")
             .fin("paso3"))

        resultado = await g.ejecutar({"entrada": "test"})

        assert resultado.exito is True
        assert resultado.nodos_ejecutados == ["paso1", "paso2", "paso3"]
        assert resultado.estado_final.salida["paso1"] == "ejecutado"
        assert resultado.estado_final.salida["paso2"] == "ejecutado"
        assert resultado.estado_final.salida["contador_final"] == 2
        assert resultado.estado_final.contexto["contador"] == 2

    @pytest.mark.asyncio
    async def test_estado_grafo_serializa_y_deserializa(self):
        @nodo(id="serializador")
        async def serializador(e: EstadoGrafo) -> EstadoGrafo:
            json_str = e.a_json()
            e_reconstruido = EstadoGrafo.desde_json(json_str)
            assert e_reconstruido.entrada == e.entrada
            e.salida["serializado"] = True
            return e

        g = (YeyoGrafo("test_serial")
             .agregar_nodo(serializador)
             .inicio("serializador")
             .fin("serializador"))

        resultado = await g.ejecutar({"dato": "importante"})
        assert resultado.exito is True
        assert resultado.estado_final.salida["serializado"] is True


class TestIntegracionEdgeCondicional:

    @pytest.mark.asyncio
    async def test_flujo_condicional_elige_ruta_correcta(self):
        @nodo(id="clasificar")
        async def clasificar(e: EstadoGrafo) -> EstadoGrafo:
            texto = e.entrada.get("texto", "")
            e.contexto["categoria"] = "pregunta" if "?" in texto else "afirmacion"
            return e

        @nodo(id="responder_pregunta")
        async def responder_pregunta(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["tipo"] = "pregunta"
            e.salida["respuesta"] = "Respondiendo pregunta"
            return e

        @nodo(id="responder_afirmacion")
        async def responder_afirmacion(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["tipo"] = "afirmacion"
            e.salida["respuesta"] = "Entendido"
            return e

        g = (YeyoGrafo("test_condicional")
             .agregar_nodo(clasificar)
             .agregar_nodo(responder_pregunta)
             .agregar_nodo(responder_afirmacion)
             .inicio("clasificar")
             .edge_condicional(
                 "clasificar",
                 lambda e: "responder_pregunta"
                 if e.contexto.get("categoria") == "pregunta"
                 else "responder_afirmacion"
             ))

        resultado_pregunta = await g.ejecutar({"texto": "¿Cómo estás?"})
        assert resultado_pregunta.estado_final.salida["tipo"] == "pregunta"

        resultado_afirmacion = await g.ejecutar({"texto": "Me gusta Python"})
        assert resultado_afirmacion.estado_final.salida["tipo"] == "afirmacion"


class TestIntegracionNodoParalelo:

    @pytest.mark.asyncio
    async def test_nodo_paralelo_en_grafo(self):
        @nodo(id="gen_1")
        async def gen_1(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["v1"] = 100
            return e

        @nodo(id="gen_2")
        async def gen_2(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["v2"] = 200
            return e

        @nodo(id="gen_3")
        async def gen_3(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["v3"] = 300
            return e

        paralelo = NodoParalelo(
            id="generar_paralelo",
            nodos=[gen_1, gen_2, gen_3],
            combinar=lambda rs: {"total": sum(r.salida.get("v1", 0) + r.salida.get("v2", 0) + r.salida.get("v3", 0) for r in rs)},
        )

        @nodo(id="finalizar")
        async def finalizar(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["resultado_final"] = e.salida.get("total", 0)
            return e

        g = (YeyoGrafo("test_paralelo_grafo")
             .agregar_nodo(paralelo)
             .agregar_nodo(finalizar)
             .inicio("generar_paralelo")
             .edge("generar_paralelo", "finalizar")
             .fin("finalizar"))

        resultado = await g.ejecutar({})
        assert resultado.exito is True
        assert resultado.estado_final.salida["resultado_final"] == 600


class TestIntegracionSubgrafo:

    @pytest.mark.asyncio
    async def test_subgrafo_se_ejecuta_correctamente(self):
        @nodo(id="sub_nodo_1")
        async def sub_nodo_1(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["sub1"] = "ok"
            return e

        @nodo(id="sub_nodo_2")
        async def sub_nodo_2(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["sub2"] = "ok"
            return e

        sub_grafo = (YeyoGrafo("proceso_interno")
                     .agregar_nodo(sub_nodo_1)
                     .agregar_nodo(sub_nodo_2)
                     .inicio("sub_nodo_1")
                     .edge("sub_nodo_1", "sub_nodo_2")
                     .fin("sub_nodo_2"))

        @nodo(id="antes_del_sub")
        async def antes(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["antes"] = True
            return e

        @nodo(id="despues_del_sub")
        async def despues(e: EstadoGrafo) -> EstadoGrafo:
            e.salida["despues"] = True
            return e

        grafo_principal = (YeyoGrafo("flujo_con_subgrafo")
                            .agregar_nodo(antes)
                            .agregar_nodo(sub_grafo.como_nodo())
                            .agregar_nodo(despues)
                            .inicio("antes_del_sub")
                            .edge("antes_del_sub", "proceso_interno")
                            .edge("proceso_interno", "despues_del_sub")
                            .fin("despues_del_sub"))

        resultado = await grafo_principal.ejecutar({"input": "test"})
        assert resultado.exito is True
        assert resultado.estado_final.salida["antes"] is True
        assert resultado.estado_final.salida["sub1"] == "ok"
        assert resultado.estado_final.salida["sub2"] == "ok"
        assert resultado.estado_final.salida["despues"] is True


class TestIntegracionWebSocketEvents:

    @pytest.mark.asyncio
    async def test_eventos_websocket_emitidos_en_orden(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)

        @nodo(id="ws_nodo_a")
        async def ws_nodo_a(e: EstadoGrafo) -> EstadoGrafo:
            return e

        @nodo(id="ws_nodo_b")
        async def ws_nodo_b(e: EstadoGrafo) -> EstadoGrafo:
            return e

        g = (YeyoGrafo("grafo_ws_orden")
             .agregar_nodo(ws_nodo_a)
             .agregar_nodo(ws_nodo_b)
             .inicio("ws_nodo_a")
             .edge("ws_nodo_a", "ws_nodo_b")
             .fin("ws_nodo_b"))

        await g.ejecutar({}, on_evento=emitter.on_evento)

        eventos = emitter.obtener_eventos()
        assert len(eventos) >= 4

        assert eventos[0]["nodo_id"] == "ws_nodo_a"
        assert eventos[0]["estado"] == "activo"

        assert eventos[1]["nodo_id"] == "ws_nodo_a"
        assert eventos[1]["estado"] == "completado"


class TestIntegracionYeyoOrquestador:

    @pytest.mark.asyncio
    async def test_orquestador_ejecuta_grafo_via_tool_calling(self):
        ollama = mock_ollama()
        tool_call_mock = MagicMock()
        tool_call_mock.function.name = "grafo_chat_contextual"
        tool_call_mock.function.arguments = {"entrada": "Hola mundo"}
        resp_con_tool = MagicMock()
        resp_con_tool.tool_calls = [tool_call_mock]
        resp_con_tool.content = ""
        ollama.chat = AsyncMock(return_value=resp_con_tool)

        flash = mock_flash_memory()
        grafo_chat = crear_grafo_chat_contextual(
            ollama_provider=ollama, flash_memory=flash
        )

        orquestador = (YeyoOrquestador(ollama)
                       .registrar_grafo_como_tool(grafo_chat))

        respuesta = await orquestador.procesar("Hola, ¿cómo estás?")

        assert respuesta.grafo_ejecutado == "grafo_chat_contextual"
        assert respuesta.exito is True

    @pytest.mark.asyncio
    async def test_orquestador_responde_sin_tool_call(self):
        ollama = mock_ollama("Respuesta directa sin grafo")
        grafo_chat = crear_grafo_chat_contextual(ollama_provider=ollama)

        orquestador = (YeyoOrquestador(ollama)
                       .registrar_grafo_como_tool(grafo_chat))

        respuesta = await orquestador.procesar("Solo una pregunta sencilla")
        assert respuesta.texto == "Respuesta directa sin grafo"
        assert respuesta.grafo_ejecutado is None


class TestIntegracionGrafosEstaticos:

    @pytest.mark.asyncio
    async def test_grafo_chat_contextual_flujo_completo(self):
        ollama = mock_ollama("Respuesta del asistente")
        flash = mock_flash_memory()
        grafo = crear_grafo_chat_contextual(ollama_provider=ollama, flash_memory=flash)

        resultado = await grafo.ejecutar({
            "mensaje": "¿Qué es YeyoOS?",
            "historial": [],
            "usuario_id": "test_user"
        })

        assert resultado.exito is True
        assert resultado.estado_final.salida.get("respuesta") == "Respuesta del asistente"
        assert resultado.estado_final.salida.get("memorias_guardadas", 0) >= 0
        assert len(resultado.nodos_ejecutados) == 5

    @pytest.mark.asyncio
    async def test_grafo_busqueda_semantica_flujo_completo(self):
        ollama = mock_ollama("Los resultados muestran que...")
        flash = mock_flash_memory()
        grafo = crear_grafo_busqueda_semantica(ollama_provider=ollama, flash_memory=flash)

        resultado = await grafo.ejecutar({
            "query": "información sobre Python",
            "limite": 3
        })

        assert resultado.exito is True
        assert "respuesta" in resultado.estado_final.salida
        ollama.embeddings.assert_called_once_with("información sobre Python")


class TestIntegracionGrafoMultiNodo:

    @pytest.mark.asyncio
    async def test_grafo_multi_nodo_pipeline(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)

        @nodo(id="script_node")
        async def script_node(estado: EstadoGrafo) -> EstadoGrafo:
            estado.salida["guion"] = "Guión generado"
            return estado

        async def _gen_imagen(estado: EstadoGrafo) -> EstadoGrafo:
            imagenes = estado.salida.get("imagenes", [])
            imagenes.append("imagen_mock.png")
            estado.salida["imagenes"] = imagenes
            return estado

        imagen_0 = NodoInline(id="imagen_0", fn=_gen_imagen)
        imagen_1 = NodoInline(id="imagen_1", fn=_gen_imagen)
        imagen_2 = NodoInline(id="imagen_2", fn=_gen_imagen)

        def _combinar_imagenes(resultados):
            imagenes = []
            for r in resultados:
                imagenes.extend(r.salida.get("imagenes", []))
            return {"imagenes": imagenes}

        image_node = NodoParalelo(
            id="image_node",
            nodos=[imagen_0, imagen_1, imagen_2],
            combinar=_combinar_imagenes,
        )

        @nodo(id="video_node")
        async def video_node(estado: EstadoGrafo) -> EstadoGrafo:
            imagenes = estado.salida.get("imagenes", [])
            estado.salida["video_path"] = f"video_{len(imagenes)}.mp4"
            return estado

        grafo = (
            YeyoGrafo("grafo_multi_nodo_test")
            .agregar_nodo(script_node)
            .agregar_nodo(image_node)
            .agregar_nodo(video_node)
            .inicio("script_node")
            .edge("script_node", "image_node")
            .edge("image_node", "video_node")
            .fin("video_node")
        )

        resultado = await grafo.ejecutar({}, on_evento=emitter.on_evento)

        assert resultado.exito is True

        eventos = emitter.obtener_eventos()
        nodo_ids_en_eventos = {e["nodo_id"] for e in eventos if "nodo_id" in e}
        assert "script_node" in nodo_ids_en_eventos
        assert "image_node" in nodo_ids_en_eventos
        assert "video_node" in nodo_ids_en_eventos

        assert "imagenes" in resultado.estado_final.salida
        assert len(resultado.estado_final.salida["imagenes"]) >= 1

        assert "video_path" in resultado.estado_final.salida

        historial_ids = resultado.nodos_ejecutados
        assert "script_node" in historial_ids
        assert "image_node" in historial_ids
        assert "video_node" in historial_ids
        assert historial_ids.index("script_node") < historial_ids.index("image_node")
        assert historial_ids.index("image_node") < historial_ids.index("video_node")
