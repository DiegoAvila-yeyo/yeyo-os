"""
YeyoOS — Voice REST API
Micro-fase 5.27 — Capa 5: Órganos

Endpoints REST para controlar el servicio de voz.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.voice.voice_service import voice_service, MicState
from src.voice.tts import TextToSpeech

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/voice", tags=["voice"])

_tts = TextToSpeech()


class SpeakRequest(BaseModel):
    text: str
    rate: Optional[int] = None
    volume: Optional[float] = None


class VoiceConfigRequest(BaseModel):
    wake_words: Optional[List[str]] = None
    rate: Optional[int] = None
    volume: Optional[float] = None
    voice_enabled: Optional[bool] = None


class VoiceStatusResponse(BaseModel):
    running: bool
    state: str
    voice_enabled: bool


@router.post("/speak")
async def speak(request: SpeakRequest) -> dict:
    """Hace TTS de un texto dado."""
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Texto vacío")
    if request.rate or request.volume:
        _tts.configure(rate=request.rate, volume=request.volume)
    await _tts.speak(request.text)
    return {"ok": True, "text": request.text[:100]}


@router.get("/status", response_model=VoiceStatusResponse)
async def get_status() -> VoiceStatusResponse:
    """Retorna el estado actual del servicio de voz."""
    return VoiceStatusResponse(
        running=voice_service.is_running,
        state=voice_service.state.value,
        voice_enabled=_tts.voice_enabled,
    )


@router.post("/toggle")
async def toggle_mic() -> dict:
    """Activa o desactiva el micrófono."""
    await voice_service.toggle_mic()
    return {"ok": True, "state": voice_service.state.value}


@router.post("/config")
async def configure_voice(request: VoiceConfigRequest) -> dict:
    """Configura wake words, voz y velocidad."""
    if request.voice_enabled is not None:
        _tts.voice_enabled = request.voice_enabled
    if request.rate or request.volume:
        _tts.configure(rate=request.rate, volume=request.volume)
    if request.wake_words:
        logger.info(f"[voice_api] wake_words actualizados: {request.wake_words}")
        # Reiniciar detector con nuevas wake words
        was_running = voice_service.is_running
        if was_running:
            await voice_service.stop()
        voice_service._detector._wake_words = request.wake_words
        if was_running:
            await voice_service.start()
    return {"ok": True}
