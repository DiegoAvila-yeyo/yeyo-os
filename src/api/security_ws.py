"""
YeyoOS — Security WebSocket Endpoint
Micro-fase 3.21 — Capa 3: Cuerpo

WebSocket /ws/security:
- Emite eventos {type: "permission_request", ...} al frontend.
- Recibe decisiones {type: "permission_response", request_id, allowed, remember}.
- Múltiples clientes soportados (broadcast a todos los conectados).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.security.permission_service import permission_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["security"])

# Conjunto de conexiones activas
_connections: Set[WebSocket] = set()


async def _broadcast(payload: dict) -> None:
    """Envía un evento a todos los clientes WebSocket conectados."""
    if not _connections:
        logger.warning("[security_ws] broadcast: no clients connected")
        return
    message = json.dumps(payload)
    dead: Set[WebSocket] = set()
    for ws in _connections.copy():
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _connections.discard(ws)


# Registrar el callback de broadcast en el servicio de permisos
permission_service.set_ws_callback(_broadcast)


@router.websocket("/ws/security")
async def security_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.add(websocket)
    logger.info(f"[security_ws] client connected. total={len(_connections)}")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"[security_ws] invalid JSON: {raw[:200]}")
                continue

            msg_type = data.get("type")

            if msg_type == "permission_response":
                request_id = data.get("request_id", "")
                allowed = bool(data.get("allowed", False))
                remember = bool(data.get("remember", False))
                resolved = permission_service.resolve(request_id, allowed, remember)
                if not resolved:
                    logger.warning(f"[security_ws] unknown request_id={request_id}")

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            else:
                logger.debug(f"[security_ws] unhandled type={msg_type}")

    except WebSocketDisconnect:
        logger.info("[security_ws] client disconnected")
    finally:
        _connections.discard(websocket)
