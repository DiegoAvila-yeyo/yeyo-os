## ═══════════════════════════════════════
## MICRO-FASE 4.22 — WebSocket Graph Events (Backend)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.22-1 [VSCODE] — Emitir eventos de grafo en tiempo real via WebSocket

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.22 de Capa 4 (Sistema Nervioso): agregar soporte para emitir eventos de grafo en tiempo real via WebSocket cuando YeyoGrafo ejecuta nodos.

CONTEXTO:
- Micro-fases 4.14-4.21 completadas: orquestador completo con grafos estáticos
- WebSocket existente en src/api/websocket.py (del Capa 1.7 o 3.12)
- YeyoGrafo ya tiene callback on_evento (micro-fase 4.17) pero no lo conecta con WebSocket
- Crear GraphEventEmitter que implementa el callback para emitir eventos via WebSocket
- El frontend (micro-fase 3.16) espera eventos: {type: "graph_event", grafo_id, nodo_id, estado, progreso, mensaje, timestamp}
- ConnectionManager existente en src/api/websocket.py para broadcast a todos los clientes conectados

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/orquestador/eventos.py:

   Ruta: ~/yeyo-os/src/orquestador/eventos.py
   Contenido:

   """
   YeyoOS — GraphEventEmitter
   Micro-fase 4.22 — Capa 4: Sistema Nervioso

   Conecta los callbacks de evento de YeyoGrafo con WebSocket.
   Emite eventos en tiempo real al frontend cuando los nodos cambian de estado.
   """

   import json
   from datetime import datetime, timezone
   from typing import Optional, Callable, Awaitable, Any


   # Tipo del evento que se emite
   GraphEvent = dict


   class GraphEventEmitter:
       """
       Emite eventos de ejecución de grafos via WebSocket.

       Se pasa como callback on_evento a YeyoGrafo.ejecutar():
           emitter = GraphEventEmitter(connection_manager, "session_id")
           await grafo.ejecutar(entrada, on_evento=emitter.on_evento)
       """

       def __init__(
           self,
           connection_manager: Any,
           session_id: Optional[str] = None,
           broadcast: bool = True,
       ):
           """
           Args:
               connection_manager: instancia de ConnectionManager del WebSocket
               session_id: si se pasa, solo emite al cliente con esta sesión
               broadcast: si True, emite a todos los clientes conectados
           """
           self._manager = connection_manager
           self.session_id = session_id
           self.broadcast = broadcast
           self.eventos_emitidos: list[GraphEvent] = []  # para testing

       async def on_evento(self, evento: GraphEvent) -> None:
           """
           Callback que YeyoGrafo llama después de cada cambio de estado de nodo.
           Emite el evento via WebSocket.
           """
           # Agregar timestamp si no lo tiene
           if "timestamp" not in evento:
               evento["timestamp"] = datetime.now(timezone.utc).isoformat()

           # Guardar para testing/auditoría
           self.eventos_emitidos.append(evento)

           # Serializar a JSON
           mensaje_json = json.dumps(evento, ensure_ascii=False)

           try:
               if self.broadcast or self.session_id is None:
                   await self._manager.broadcast(mensaje_json)
               else:
                   await self._manager.send_to(self.session_id, mensaje_json)
           except Exception:
               # Los errores de WebSocket no deben interrumpir la ejecución del grafo
               pass

       def obtener_eventos(self) -> list[GraphEvent]:
           """Retorna todos los eventos emitidos (útil para testing)."""
           return list(self.eventos_emitidos)

       def limpiar_eventos(self) -> None:
           """Limpia el historial de eventos."""
           self.eventos_emitidos.clear()


   def crear_evento_grafo(
       grafo_id: str,
       nodo_id: str,
       estado: str,
       progreso: float,
       mensaje: str,
       nodos_totales: int = 0,
       timestamp: Optional[str] = None,
   ) -> GraphEvent:
       """
       Crea un evento de grafo con la estructura esperada por el frontend.

       Estructura: {type, grafo_id, nodo_id, estado, progreso, mensaje, timestamp, nodos_totales}
       """
       return {
           "type": "graph_event",
           "grafo_id": grafo_id,
           "nodo_id": nodo_id,
           "estado": estado,
           "progreso": round(min(1.0, max(0.0, progreso)), 3),
           "mensaje": mensaje,
           "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
           "nodos_totales": nodos_totales,
       }

2. Actualizar src/orquestador/__init__.py:

   Ruta: ~/yeyo-os/src/orquestador/__init__.py
   Contenido:
   """
   YeyoOS — YeyoOrquestador
   Motor de orquestación nativo de YeyoOS.
   Micro-fases 4.14-4.23 — Capa 4: Sistema Nervioso
   """
   from .estado import EstadoGrafo, EstadoGrafoError
   from .nodo import Nodo, NodoFuncion, NodoInline, NodoError, NodoTimeoutError, nodo
   from .edge import Edge, EdgeDirecto, EdgeCondicional, EdgeError, FIN_GRAFO, edge
   from .grafo import YeyoGrafo, ResultadoGrafo, GrafoError, GrafoTimeoutError
   from .paralelo import NodoParalelo
   from .orquestador import YeyoOrquestador, RespuestaOrquestador, OrquestadorError
   from .catalogo import CatalogoNodos, CatalogoError
   from .eventos import GraphEventEmitter, crear_evento_grafo

3. Crear archivo tests/unit/orquestador/test_eventos.py:

   Ruta: ~/yeyo-os/tests/unit/orquestador/test_eventos.py
   Contenido:

   """Tests para GraphEventEmitter y eventos WebSocket — Micro-fase 4.22"""

   import json
   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.orquestador.estado import EstadoGrafo
   from src.orquestador.nodo import nodo
   from src.orquestador.grafo import YeyoGrafo
   from src.orquestador.eventos import GraphEventEmitter, crear_evento_grafo


   # ─── Mock de ConnectionManager ─────────────────────────────────────────────

   def mock_connection_manager():
       m = AsyncMock()
       m.broadcast = AsyncMock()
       m.send_to = AsyncMock()
       m.mensajes_enviados = []

       async def capture_broadcast(msg):
           m.mensajes_enviados.append(msg)

       m.broadcast.side_effect = capture_broadcast
       return m


   # ─── Nodos de prueba ──────────────────────────────────────────────────────

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
           manager.send_to.assert_called_once_with("sess-123", pytest.any(str))
           manager.broadcast.assert_not_called()

       @pytest.mark.asyncio
       async def test_error_en_websocket_no_interrumpe(self):
           manager = AsyncMock()
           manager.broadcast = AsyncMock(side_effect=ConnectionError("WebSocket cerrado"))
           emitter = GraphEventEmitter(manager)
           evento = crear_evento_grafo("g", "n", "activo", 0.5, "test")
           # No debe lanzar excepción
           await emitter.on_evento(evento)

       def test_limpiar_eventos(self):
           manager = mock_connection_manager()
           emitter = GraphEventEmitter(manager)
           emitter.eventos_emitidos.append({"type": "graph_event"})
           emitter.limpiar_eventos()
           assert len(emitter.obtener_eventos()) == 0


   class TestIntegracionGrafoWebSocket:
       """Tests de integración: YeyoGrafo + GraphEventEmitter."""

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

       @pytest.mark.asyncio
       async def test_grafo_emite_evento_error_cuando_nodo_falla(self):
           @nodo(id="nodo_que_falla_ws")
           async def nodo_falla_ws(estado: EstadoGrafo) -> EstadoGrafo:
               raise ValueError("Error simulado")

           manager = mock_connection_manager()
           emitter = GraphEventEmitter(manager)

           g = (YeyoGrafo("grafo_error_ws")
                .agregar_nodo(nodo_falla_ws)
                .inicio("nodo_que_falla_ws")
                .fin("nodo_que_falla_ws"))

           await g.ejecutar({}, on_evento=emitter.on_evento)

           estados = [e["estado"] for e in emitter.obtener_eventos()]
           assert "error" in estados

       @pytest.mark.asyncio
       async def test_broadcast_llamado_por_cada_evento(self):
           manager = mock_connection_manager()
           emitter = GraphEventEmitter(manager)

           @nodo(id="nodo_a_ws")
           async def nodo_a_ws(e):
               return e

           @nodo(id="nodo_b_ws")
           async def nodo_b_ws(e):
               return e

           g = (YeyoGrafo("grafo_multi_ws")
                .agregar_nodo(nodo_a_ws)
                .agregar_nodo(nodo_b_ws)
                .inicio("nodo_a_ws")
                .edge("nodo_a_ws", "nodo_b_ws")
                .fin("nodo_b_ws"))

           await g.ejecutar({}, on_evento=emitter.on_evento)

           # 2 nodos × 2 eventos (activo + completado) = 4 eventos mínimo
           assert manager.broadcast.call_count >= 4

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/orquestador/test_eventos.py -v

VERIFICAR:
- [ ] src/orquestador/eventos.py existe con GraphEventEmitter y crear_evento_grafo
- [ ] crear_evento_grafo() produce dict con estructura correcta (type, grafo_id, nodo_id, estado, progreso, mensaje, timestamp)
- [ ] GraphEventEmitter.on_evento() emite via manager.broadcast()
- [ ] Mensaje emitido es JSON válido con estructura correcta
- [ ] Error en WebSocket no interrumpe la ejecución del grafo
- [ ] Con session_id → usa send_to() en lugar de broadcast()
- [ ] Integración con YeyoGrafo: cada nodo emite "activo" y "completado"
- [ ] TODOS los tests pasan

SI FALLA:
- ConnectionManager no existe en src/api/websocket.py: GraphEventEmitter es agnóstico al manager, cualquier objeto con broadcast() funciona
- json.dumps falla: verificar que los valores del evento son JSON-serializables (no datetime objects)
- broadcast vs send_to: el mock debe tener ambos métodos

NO HACER:
- No modificar src/api/websocket.py directamente — GraphEventEmitter es independiente
- No crear endpoints REST para eventos — solo WebSocket
- No implementar rooms/channels de WebSocket (eso sería futuro)

GATE: Cada cambio de estado de nodo en YeyoGrafo emite un evento WebSocket con la estructura {type, grafo_id, nodo_id, estado, progreso, mensaje, timestamp}, los errores de WebSocket no interrumpen la ejecución, todos los tests pasan.
```
