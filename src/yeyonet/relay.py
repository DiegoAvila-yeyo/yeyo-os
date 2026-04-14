"""
YeyoNet — Relay Server.
WebSocket server que el Central ejecuta para coordinar satélites.
Maneja autenticación, heartbeat, routing de mensajes.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Awaitable

from fastapi import WebSocket, WebSocketDisconnect

from .protocol import MessageType, NetMessage
from .satellite_manager import SatelliteManager
from .models import NodeResources

logger = logging.getLogger("yeyonet.relay")

# Heartbeat: si un nodo no envía en 90s, se considera desconectado
HEARTBEAT_TIMEOUT = 90.0


class ConnectedNode:
    """Representa un nodo conectado al relay."""

    def __init__(self, node_id: str, ws: WebSocket):
        self.node_id = node_id
        self.ws = ws
        self.last_seen = time.time()
        self.authenticated = False

    @property
    def is_alive(self) -> bool:
        return (time.time() - self.last_seen) < HEARTBEAT_TIMEOUT

    def touch(self) -> None:
        self.last_seen = time.time()


class YeyoNetRelay:
    """
    WebSocket relay server del Central.
    Acepta conexiones de satélites, autentica, enruta mensajes.
    """

    def __init__(self, satellite_manager: SatelliteManager, central_node_id: str):
        self._sat_mgr = satellite_manager
        self._central_id = central_node_id
        self._nodes: dict[str, ConnectedNode] = {}  # node_id → ConnectedNode
        self._handlers: dict[MessageType, list[Callable]] = {}
        self._cleanup_task: asyncio.Task | None = None

    @property
    def connected_count(self) -> int:
        return len(self._nodes)

    def get_connected_ids(self) -> list[str]:
        return list(self._nodes.keys())

    def on_message(self, msg_type: MessageType, handler: Callable[[NetMessage, str], Awaitable[None]]) -> None:
        """Registra un handler para un tipo de mensaje."""
        self._handlers.setdefault(msg_type, []).append(handler)

    async def start(self) -> None:
        """Inicia tarea de limpieza periódica."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"[relay] Iniciado (central={self._central_id[:8]}...)")

    async def stop(self) -> None:
        """Detiene el relay."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        # Cerrar todas las conexiones
        for node in list(self._nodes.values()):
            try:
                await node.ws.close()
            except Exception:
                pass
        self._nodes.clear()
        logger.info("[relay] Detenido")

    async def handle_connection(self, ws: WebSocket) -> None:
        """Maneja una conexión WebSocket entrante de un satélite."""
        await ws.accept()
        temp_node = ConnectedNode(node_id="pending", ws=ws)

        try:
            # Esperar mensaje de autenticación (timeout 10s)
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=10.0)
            except asyncio.TimeoutError:
                await self._send(ws, NetMessage(
                    type=MessageType.AUTH_FAIL,
                    from_node=self._central_id,
                    payload={"error": "Auth timeout"},
                ))
                await ws.close()
                return

            msg = NetMessage.from_json(raw)
            if msg.type != MessageType.AUTH:
                await self._send(ws, NetMessage(
                    type=MessageType.AUTH_FAIL,
                    from_node=self._central_id,
                    payload={"error": "First message must be AUTH"},
                ))
                await ws.close()
                return

            # Validar token
            token = msg.payload.get("auth_token", "")
            node = await self._sat_mgr.authenticate(token)
            if not node:
                await self._send(ws, NetMessage(
                    type=MessageType.AUTH_FAIL,
                    from_node=self._central_id,
                    payload={"error": "Invalid token"},
                ))
                await ws.close()
                return

            # Autenticado
            temp_node.node_id = node.id
            temp_node.authenticated = True
            self._nodes[node.id] = temp_node

            await self._sat_mgr.update_heartbeat(node.id)

            await self._send(ws, NetMessage(
                type=MessageType.AUTH_OK,
                from_node=self._central_id,
                to_node=node.id,
                payload={"central_id": self._central_id, "permissions": [p.value if hasattr(p, 'value') else p for p in node.permissions]},
            ))

            logger.info(f"[relay] 🟢 {node.name} ({node.id[:8]}...) conectado")

            # Loop de mensajes
            await self._message_loop(temp_node)

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"[relay] Error en conexión: {e}")
        finally:
            if temp_node.node_id in self._nodes:
                del self._nodes[temp_node.node_id]
                if temp_node.authenticated:
                    logger.info(f"[relay] ⭘ Nodo {temp_node.node_id[:8]}... desconectado")

    async def _message_loop(self, node: ConnectedNode) -> None:
        """Procesa mensajes de un nodo autenticado."""
        while True:
            raw = await node.ws.receive_text()
            node.touch()

            try:
                msg = NetMessage.from_json(raw)
                msg.from_node = node.node_id  # enforce sender identity

                # Heartbeat — responder inmediatamente
                if msg.type == MessageType.HEARTBEAT:
                    await self._sat_mgr.update_heartbeat(node.node_id)
                    await self._send(node.ws, msg.ack())
                    continue

                # Resource report
                if msg.type == MessageType.RESOURCE_REPORT:
                    try:
                        resources = NodeResources(**msg.payload)
                        await self._sat_mgr.update_heartbeat(node.node_id, resources)
                    except Exception:
                        await self._sat_mgr.update_heartbeat(node.node_id)
                    await self._send(node.ws, msg.ack())
                    continue

                # Route to specific node
                if msg.to_node and msg.to_node != self._central_id:
                    target = self._nodes.get(msg.to_node)
                    if target and target.authenticated:
                        await self._send(target.ws, msg)
                    else:
                        await self._send(node.ws, NetMessage(
                            type=MessageType.ACK,
                            from_node=self._central_id,
                            to_node=node.node_id,
                            reply_to=msg.msg_id,
                            payload={"error": "Target node not connected"},
                        ))
                    continue

                # Dispatch to handlers
                handlers = self._handlers.get(msg.type, [])
                for handler in handlers:
                    try:
                        await handler(msg, node.node_id)
                    except Exception as e:
                        logger.error(f"[relay] Handler error for {msg.type}: {e}")

            except Exception as e:
                logger.error(f"[relay] Error procesando mensaje: {e}")

    async def send_to_node(self, node_id: str, msg: NetMessage) -> bool:
        """Envía un mensaje a un nodo específico. Retorna True si se envió."""
        node = self._nodes.get(node_id)
        if not node or not node.authenticated:
            return False
        try:
            await self._send(node.ws, msg)
            return True
        except Exception:
            return False

    async def broadcast(self, msg: NetMessage, exclude: str | None = None) -> int:
        """Envía un mensaje a todos los nodos conectados. Retorna cuántos recibieron."""
        sent = 0
        for nid, node in list(self._nodes.items()):
            if nid == exclude or not node.authenticated:
                continue
            try:
                await self._send(node.ws, msg)
                sent += 1
            except Exception:
                pass
        return sent

    async def _send(self, ws: WebSocket, msg: NetMessage) -> None:
        await ws.send_text(msg.to_json())

    async def _cleanup_loop(self) -> None:
        """Periódicamente revisa nodos desconectados."""
        while True:
            await asyncio.sleep(60)
            try:
                dead = [nid for nid, n in self._nodes.items() if not n.is_alive]
                for nid in dead:
                    node = self._nodes.pop(nid, None)
                    if node:
                        try:
                            await node.ws.close()
                        except Exception:
                            pass
                        logger.info(f"[relay] ⭘ Nodo {nid[:8]}... timeout (cleanup)")

                # Refresh DB statuses
                await self._sat_mgr.refresh_statuses()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"[relay] Cleanup error: {e}")
