"""
YeyoOS — TTS API Endpoint
Micro-fase 3.18 — Capa 3: Cuerpo

Endpoint POST /api/tts que usa pyttsx3 para hablar texto.
pyttsx3 es síncrono y no-bloqueante para el frontend ya que
se ejecuta en un thread separado.
"""

import threading
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str
    rate: int = 150       # palabras por minuto
    volume: float = 0.9   # 0.0-1.0


class TTSResponse(BaseModel):
    ok: bool
    mensaje: str


def _hablar_en_thread(text: str, rate: int, volume: float) -> None:
    """Ejecuta pyttsx3 en un thread separado para no bloquear FastAPI."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.setProperty("volume", volume)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        logger.error(f"TTS error: {e}")


@router.post("/", response_model=TTSResponse)
async def hablar(request: TTSRequest) -> TTSResponse:
    """
    Habla el texto usando pyttsx3 en un thread separado.
    Retorna inmediatamente sin esperar a que termine el audio.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")

    t = threading.Thread(
        target=_hablar_en_thread,
        args=(request.text, request.rate, request.volume),
        daemon=True,
    )
    t.start()

    logger.info(f"TTS iniciado: '{request.text[:50]}...' " if len(request.text) > 50 else f"TTS iniciado: '{request.text}'")
    return TTSResponse(ok=True, mensaje="TTS iniciado")
