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
