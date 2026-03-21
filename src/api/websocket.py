"""
YeyoOS — WebSocket Server
Micro-fase 1.7 — Capa 1: Esqueleto

Gestión de conexiones WebSocket para comunicación
en tiempo real con el frontend.
Límite: 50 conexiones simultáneas.
"""

import json
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Gestor de conexiones WebSocket."""

    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self.active_connections: list[WebSocket] = []

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)

    async def connect(self, websocket: WebSocket) -> bool:
        """
        Acepta una nueva conexión WebSocket.
        Retorna False si se alcanzó el límite de conexiones.
        """
        if self.connection_count >= self.max_connections:
            await websocket.close(code=1013, reason="Max connections reached")
            return False
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)

    async def send_json(self, data: dict[str, Any], websocket: WebSocket) -> None:
        await websocket.send_text(json.dumps(data))

    async def broadcast(self, message: str) -> None:
        """Envía mensaje a TODAS las conexiones activas."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_json(self, data: dict[str, Any]) -> None:
        await self.broadcast(json.dumps(data))

    def get_status(self) -> dict:
        return {
            "active_connections": self.connection_count,
            "max_connections": self.max_connections,
        }


# Instancia global del manager
manager = ConnectionManager()
