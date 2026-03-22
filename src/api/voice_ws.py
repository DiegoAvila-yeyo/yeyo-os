"""
YeyoOS — Voice WebSocket Endpoint
Micro-fase 5.27 — Capa 5: Órganos

WebSocket /ws/voice:
- Emite estado del micrófono: {type:"mic_state", state:...}
- Recibe audio chunks del frontend (futuro)
- Conecta VoiceService con el frontend en tiempo real
"""

from __future__ import annotations

import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.voice.voice_service import voice_service, MicState

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice"])

_connections: Set[WebSocket] = set()


async def _broadcast_state(state: MicState) -> None:
    """Emite el estado del micrófono a todos los clientes."""
    message = json.dumps({"type": "mic_state", "state": state.value})
    dead: Set[WebSocket] = set()
    for ws in _connections.copy():
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _connections.discard(ws)


# Registrar callback de estado en VoiceService
def _on_state_change(state: MicState) -> None:
    import asyncio
    loop = asyncio.get_event_loop()
    if not loop.is_closed():
        asyncio.run_coroutine_threadsafe(_broadcast_state(state), loop)


voice_service.set_state_callback(_on_state_change)


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    _connections.add(websocket)
    logger.info(f"[voice_ws] cliente conectado. total={len(_connections)}")

    # Enviar estado inicial
    await websocket.send_text(
        json.dumps({"type": "mic_state", "state": voice_service.state.value})
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg_type == "audio_chunk":
                # Futuro: recibir audio del frontend para transcripción
                pass
            else:
                logger.debug(f"[voice_ws] tipo desconocido: {msg_type}")

    except WebSocketDisconnect:
        logger.info("[voice_ws] cliente desconectado")
    finally:
        _connections.discard(websocket)
