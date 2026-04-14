"""
YeyoNet — Relay Client.
Clase que un satélite usa para conectarse al Central via WebSocket.
Auto-reconnect con backoff exponencial, cola offline.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Awaitable

import websockets
from websockets.exceptions import ConnectionClosed

from .protocol import MessageType, NetMessage, make_auth, make_heartbeat, make_resource_report

logger = logging.getLogger("yeyonet.client")

# Backoff: 1s, 2s, 4s, 8s, 16s, 32s, 60s max
BACKOFF_BASE = 1.0
BACKOFF_MAX = 60.0
HEARTBEAT_INTERVAL = 30.0


class YeyoNetClient:
    """
    Cliente WebSocket que conecta un satélite al Central.
    Maneja autenticación, heartbeat, reconexión automática, cola offline.
    """

    def __init__(
        self,
        central_ws_url: str,
        node_id: str,
        auth_token: str,
        on_message: Callable[[NetMessage], Awaitable[None]] | None = None,
    ):
        self._url = central_ws_url
        self._node_id = node_id
        self._auth_token = auth_token
        self._on_message = on_message
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._connected = False
        self._running = False
        self._offline_queue: list[NetMessage] = []
        self._handlers: dict[MessageType, list[Callable]] = {}
        self._tasks: list[asyncio.Task] = []

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def offline_queue_size(self) -> int:
        return len(self._offline_queue)

    def on(self, msg_type: MessageType, handler: Callable[[NetMessage], Awaitable[None]]) -> None:
        """Registra handler para un tipo de mensaje."""
        self._handlers.setdefault(msg_type, []).append(handler)

    async def start(self) -> None:
        """Inicia la conexión y loops de heartbeat/reconexión."""
        self._running = True
        self._tasks.append(asyncio.create_task(self._connect_loop()))
        logger.info(f"[client] Iniciando conexión a {self._url}")

    async def stop(self) -> None:
        """Detiene el cliente."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._connected = False
        logger.info("[client] Detenido")

    async def send(self, msg: NetMessage) -> bool:
        """Envía un mensaje. Si desconectado, lo encola."""
        msg.from_node = self._node_id
        if self._connected and self._ws:
            try:
                await self._ws.send(msg.to_json())
                return True
            except Exception:
                pass
        # Offline — encolar (excepto heartbeats)
        if msg.type != MessageType.HEARTBEAT:
            self._offline_queue.append(msg)
            logger.debug(f"[client] Mensaje encolado (offline): {msg.type.value}")
        return False

    async def send_resources(self, resources: dict) -> bool:
        """Envía un reporte de recursos."""
        return await self.send(make_resource_report(self._node_id, resources))

    async def _connect_loop(self) -> None:
        """Loop de conexión con backoff exponencial."""
        backoff = BACKOFF_BASE

        while self._running:
            try:
                async with websockets.connect(self._url) as ws:
                    self._ws = ws
                    backoff = BACKOFF_BASE  # reset backoff on success

                    # Authenticate
                    auth_msg = make_auth(self._node_id, self._auth_token)
                    await ws.send(auth_msg.to_json())

                    # Wait for auth response
                    raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    response = NetMessage.from_json(raw)

                    if response.type == MessageType.AUTH_FAIL:
                        logger.error(f"[client] Auth failed: {response.payload.get('error')}")
                        self._running = False
                        return

                    if response.type == MessageType.AUTH_OK:
                        self._connected = True
                        logger.info(f"[client] 🟢 Conectado al Central ({response.payload.get('central_id', '')[:8]}...)")

                        # Flush offline queue
                        await self._flush_offline_queue()

                        # Start heartbeat
                        hb_task = asyncio.create_task(self._heartbeat_loop())

                        try:
                            await self._receive_loop(ws)
                        finally:
                            hb_task.cancel()
                            try:
                                await hb_task
                            except asyncio.CancelledError:
                                pass

            except ConnectionClosed:
                logger.warning("[client] Conexión cerrada por el Central")
            except asyncio.TimeoutError:
                logger.warning("[client] Timeout conectando al Central")
            except OSError as e:
                logger.warning(f"[client] Error de red: {e}")
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"[client] Error inesperado: {e}")

            self._connected = False
            self._ws = None

            if self._running:
                logger.info(f"[client] Reconectando en {backoff:.0f}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_MAX)

    async def _receive_loop(self, ws) -> None:
        """Recibe y despacha mensajes del Central."""
        async for raw in ws:
            try:
                msg = NetMessage.from_json(raw)

                # Dispatch to registered handlers
                handlers = self._handlers.get(msg.type, [])
                for handler in handlers:
                    try:
                        await handler(msg)
                    except Exception as e:
                        logger.error(f"[client] Handler error for {msg.type}: {e}")

                # Generic callback
                if self._on_message:
                    try:
                        await self._on_message(msg)
                    except Exception as e:
                        logger.error(f"[client] on_message error: {e}")

            except Exception as e:
                logger.error(f"[client] Error procesando mensaje: {e}")

    async def _heartbeat_loop(self) -> None:
        """Envía heartbeat periódico al Central."""
        while self._running and self._connected:
            try:
                hb = make_heartbeat(self._node_id)
                if self._ws:
                    await self._ws.send(hb.to_json())
            except Exception:
                break
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def _flush_offline_queue(self) -> None:
        """Envía mensajes acumulados mientras estaba offline."""
        if not self._offline_queue:
            return
        count = len(self._offline_queue)
        logger.info(f"[client] Flushing {count} mensajes offline...")
        while self._offline_queue and self._ws:
            msg = self._offline_queue.pop(0)
            try:
                await self._ws.send(msg.to_json())
            except Exception:
                self._offline_queue.insert(0, msg)
                break
        sent = count - len(self._offline_queue)
        logger.info(f"[client] Flushed {sent}/{count} mensajes")
