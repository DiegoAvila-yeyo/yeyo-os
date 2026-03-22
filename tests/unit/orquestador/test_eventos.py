"""Tests para GraphEventEmitter y eventos WebSocket — Micro-fase 4.22"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import nodo
from src.orquestador.grafo import YeyoGrafo
from src.orquestador.eventos import GraphEventEmitter, crear_evento_grafo


def mock_connection_manager():
    m = AsyncMock()
    m.broadcast = AsyncMock()
    m.send_to = AsyncMock()
    m.mensajes_enviados = []

    async def capture_broadcast(msg):
        m.mensajes_enviados.append(msg)

    m.broadcast.side_effect = capture_broadcast
    return m


@nodo(id="nodo_test_ws")
async def nodo_test_ws(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["procesado"] = True
    return estado


class TestCrearEventoGrafo:

    def test_crear_evento_estructura_correcta(self):
        evento = crear_evento_grafo(
            grafo_id="mi_grafo",
            nodo_id="nodo_a",
            estado="activo",
            progreso=0.5,
            mensaje="Ejecutando...",
            nodos_totales=3,
        )
        assert evento["type"] == "graph_event"
        assert evento["grafo_id"] == "mi_grafo"
        assert evento["nodo_id"] == "nodo_a"
        assert evento["estado"] == "activo"
        assert evento["progreso"] == 0.5
        assert evento["mensaje"] == "Ejecutando..."
        assert evento["nodos_totales"] == 3
        assert "timestamp" in evento

    def test_progreso_se_clampa_entre_0_y_1(self):
        evento_bajo = crear_evento_grafo("g", "n", "activo", -0.5, "test")
        evento_alto = crear_evento_grafo("g", "n", "activo", 1.5, "test")
        assert evento_bajo["progreso"] == 0.0
        assert evento_alto["progreso"] == 1.0

    def test_timestamp_personalizado(self):
        evento = crear_evento_grafo("g", "n", "activo", 0.5, "test", timestamp="2025-01-01T00:00:00Z")
        assert evento["timestamp"] == "2025-01-01T00:00:00Z"


class TestGraphEventEmitter:

    @pytest.mark.asyncio
    async def test_emite_eventos_via_broadcast(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)
        evento = crear_evento_grafo("grafo_1", "nodo_a", "activo", 0.5, "test")
        await emitter.on_evento(evento)
        manager.broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_mensaje_enviado_es_json_valido(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)
        evento = crear_evento_grafo("grafo_1", "nodo_a", "activo", 0.5, "mensaje test")
        await emitter.on_evento(evento)
        mensaje_json = manager.mensajes_enviados[0]
        parsed = json.loads(mensaje_json)
        assert parsed["type"] == "graph_event"
        assert parsed["grafo_id"] == "grafo_1"

    @pytest.mark.asyncio
    async def test_eventos_guardados_para_testing(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)
        for i in range(3):
            evento = crear_evento_grafo("g", f"nodo_{i}", "activo", i * 0.33, "test")
            await emitter.on_evento(evento)
        assert len(emitter.obtener_eventos()) == 3

    @pytest.mark.asyncio
    async def test_session_id_usa_send_to(self):
        manager = AsyncMock()
        manager.send_to = AsyncMock()
        manager.broadcast = AsyncMock()
        emitter = GraphEventEmitter(manager, session_id="sess-123", broadcast=False)
        evento = crear_evento_grafo("g", "n", "activo", 0.5, "test")
        await emitter.on_evento(evento)
        manager.send_to.assert_called_once()
        manager.broadcast.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_en_websocket_no_interrumpe(self):
        manager = AsyncMock()
        manager.broadcast = AsyncMock(side_effect=ConnectionError("WebSocket cerrado"))
        emitter = GraphEventEmitter(manager)
        evento = crear_evento_grafo("g", "n", "activo", 0.5, "test")
        await emitter.on_evento(evento)

    def test_limpiar_eventos(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)
        emitter.eventos_emitidos.append({"type": "graph_event"})
        emitter.limpiar_eventos()
        assert len(emitter.obtener_eventos()) == 0


class TestIntegracionGrafoWebSocket:

    @pytest.mark.asyncio
    async def test_grafo_emite_eventos_activo_y_completado(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)

        g = (YeyoGrafo("grafo_ws_test")
             .agregar_nodo(nodo_test_ws)
             .inicio("nodo_test_ws")
             .fin("nodo_test_ws"))

        await g.ejecutar({"texto": "test"}, on_evento=emitter.on_evento)

        eventos = emitter.obtener_eventos()
        estados = [e["estado"] for e in eventos]
        assert "activo" in estados
        assert "completado" in estados

    @pytest.mark.asyncio
    async def test_grafo_emite_tipo_correcto_en_todos_eventos(self):
        manager = mock_connection_manager()
        emitter = GraphEventEmitter(manager)

        g = (YeyoGrafo("grafo_tipo_test")
             .agregar_nodo(nodo_test_ws)
             .inicio("nodo_test_ws")
             .fin("nodo_test_ws"))

        await g.ejecutar({}, on_evento=emitter.on_evento)

        for evento in emitter.obtener_eventos():
            assert evento["type"] == "graph_event"
            assert evento["grafo_id"] == "grafo_tipo_test"
            assert "nodo_id" in evento
            assert 0.0 <= evento["progreso"] <= 1.0
