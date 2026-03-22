"""
YeyoOS — TextToSpeech
Micro-fase 5.27 — Capa 5: Órganos

Síntesis de voz con pyttsx3.
speak() es async y no bloquea. speak_sync() espera a que termine.
Frases del sistema predefinidas para respuestas rápidas.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False
    logger.warning("[tts] pyttsx3 no disponible — modo silencioso")

# Frases del sistema
SYSTEM_PHRASES = {
    "ready": "Dime.",
    "understood": "Entendido.",
    "paused": "Sistema pausado.",
    "listening": "Lista.",
    "error": "Hubo un error.",
    "processing": "Un momento.",
    "goodbye": "Hasta luego.",
    "hello": "Hola.",
}


class TextToSpeech:
    """
    Motor TTS basado en pyttsx3.
    Las operaciones de audio son síncronas por naturaleza de pyttsx3,
    pero se ejecutan en threads para no bloquear el event loop.
    """

    def __init__(self, rate: int = 165, volume: float = 0.9) -> None:
        self._rate = rate
        self._volume = volume
        self._enabled = True
        self._speak_lock = threading.Lock()

    @property
    def voice_enabled(self) -> bool:
        return self._enabled

    @voice_enabled.setter
    def voice_enabled(self, value: bool) -> None:
        self._enabled = value
        logger.info(f"[tts] voz {'habilitada' if value else 'deshabilitada'}")

    def _run_engine(self, text: str) -> None:
        """Ejecuta pyttsx3 de forma síncrona. Llamar desde thread."""
        if not _PYTTSX3_AVAILABLE:
            logger.debug(f"[tts] (mock) hablaría: '{text}'")
            return
        with self._speak_lock:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", self._rate)
                engine.setProperty("volume", self._volume)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                logger.error(f"[tts] error: {e}")

    async def speak(self, text: str) -> None:
        """
        Habla el texto de forma no bloqueante.
        Lanza un thread daemon y retorna inmediatamente.
        """
        if not self._enabled:
            return
        if not text.strip():
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._run_engine, text)

    def speak_sync(self, text: str) -> None:
        """Habla el texto de forma síncrona (bloquea hasta terminar)."""
        if not self._enabled:
            return
        if not text.strip():
            return
        self._run_engine(text)

    async def say_system(self, phrase_key: str) -> None:
        """Habla una frase del sistema predefinida."""
        text = SYSTEM_PHRASES.get(phrase_key, phrase_key)
        await self.speak(text)

    def configure(self, rate: Optional[int] = None, volume: Optional[float] = None) -> None:
        if rate is not None:
            self._rate = max(50, min(400, rate))
        if volume is not None:
            self._volume = max(0.0, min(1.0, volume))
