"""
YeyoOS — VoiceService
Micro-fase 5.27 — Capa 5: Órganos

Orquesta WakeWordDetector + SpeechToText + TextToSpeech.
Loop: wake word → graba → transcribe → WebSocket → espera respuesta → TTS.
Comandos rápidos: "para todo", "abre imagen", "silencio", "despierta".
"""

from __future__ import annotations

import asyncio
import logging
import re
from enum import Enum
from typing import Callable, Optional

from src.voice.wake_word import WakeWordDetector
from src.voice.stt import SpeechToText
from src.voice.tts import TextToSpeech

logger = logging.getLogger(__name__)


class MicState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    RECORDING = "recording"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    DISABLED = "disabled"


# Comandos rápidos: (regex, acción_nombre)
QUICK_COMMANDS = [
    (re.compile(r"\bpara\s+todo\b", re.I), "kill_switch"),
    (re.compile(r"\babre?\s+imagen\b", re.I), "open_node_image"),
    (re.compile(r"\bsilencio\b", re.I), "disable_mic"),
    (re.compile(r"\bdespierta\b", re.I), "enable_mic"),
]


class VoiceService:
    """
    Servicio de voz principal de YeyoOS.
    Se integra con el sistema de chat via WebSocket.
    """

    def __init__(self) -> None:
        self._detector = WakeWordDetector()
        self._stt = SpeechToText()
        self._tts = TextToSpeech()
        self._state = MicState.IDLE
        self._running = False
        self._state_callback: Optional[Callable[[MicState], None]] = None
        self._chat_send_callback: Optional[Callable[[str], asyncio.Future]] = None
        self._kill_switch_callback: Optional[Callable[[], None]] = None
        self._open_node_callback: Optional[Callable[[str], None]] = None

    @property
    def state(self) -> MicState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._running

    def set_state_callback(self, cb: Callable[[MicState], None]) -> None:
        """Callback que se llama cuando cambia el estado del micrófono."""
        self._state_callback = cb

    def set_chat_callback(self, cb: Callable[[str], asyncio.Future]) -> None:
        """Callback que envía el texto transcrito al chat activo."""
        self._chat_send_callback = cb

    def set_kill_switch_callback(self, cb: Callable[[], None]) -> None:
        self._kill_switch_callback = cb

    def set_open_node_callback(self, cb: Callable[[str], None]) -> None:
        self._open_node_callback = cb

    def _set_state(self, state: MicState) -> None:
        self._state = state
        logger.info(f"[voice] estado: {state.value}")
        if self._state_callback:
            self._state_callback(state)

    async def start(self) -> None:
        """Inicia el loop de voz."""
        if self._running:
            return
        self._running = True
        loop = asyncio.get_event_loop()
        self._detector.start(loop=loop)
        self._set_state(MicState.LISTENING)
        logger.info("[voice] VoiceService iniciado")
        asyncio.create_task(self._main_loop())

    async def stop(self) -> None:
        """Detiene el servicio de voz."""
        self._running = False
        self._detector.stop()
        self._set_state(MicState.DISABLED)
        logger.info("[voice] VoiceService detenido")

    async def toggle_mic(self) -> None:
        """Activa/desactiva el micrófono."""
        if self._state == MicState.DISABLED:
            await self.start()
        else:
            await self.stop()

    def disable_mic(self) -> None:
        self._detector.stop()
        self._set_state(MicState.DISABLED)

    def enable_mic(self) -> None:
        loop = asyncio.get_event_loop()
        self._detector.start(loop=loop)
        self._set_state(MicState.LISTENING)

    def _handle_quick_command(self, text: str) -> bool:
        """
        Verifica si el texto es un comando rápido y lo ejecuta.
        Retorna True si fue manejado, False si se debe enviar al chat.
        """
        for pattern, action in QUICK_COMMANDS:
            if pattern.search(text):
                logger.info(f"[voice] comando rápido: {action}")
                if action == "kill_switch" and self._kill_switch_callback:
                    self._kill_switch_callback()
                elif action == "disable_mic":
                    self.disable_mic()
                elif action == "enable_mic":
                    self.enable_mic()
                elif action == "open_node_image" and self._open_node_callback:
                    self._open_node_callback("image")
                return True
        return False

    async def _main_loop(self) -> None:
        """Loop principal: espera wake word → graba → transcribe → responde."""
        logger.info("[voice] loop principal activo")
        while self._running:
            try:
                # Esperar wake word
                self._set_state(MicState.LISTENING)
                word = await asyncio.wait_for(
                    self._detector.queue.get(), timeout=1.0
                )
                if not self._running:
                    break

                logger.info(f"[voice] wake word: '{word}'")
                await self._tts.say_system("ready")  # "Dime."
                self._set_state(MicState.RECORDING)

                # Grabar en executor para no bloquear
                loop = asyncio.get_event_loop()
                audio_bytes = await loop.run_in_executor(
                    None, self._stt.record_until_silence
                )

                if not audio_bytes:
                    self._set_state(MicState.LISTENING)
                    continue

                # Transcribir
                self._set_state(MicState.PROCESSING)
                text = await loop.run_in_executor(None, self._stt.transcribe, audio_bytes)

                if not text.strip():
                    self._set_state(MicState.LISTENING)
                    continue

                logger.info(f"[voice] transcrito: '{text}'")

                # Comandos rápidos (sin IA)
                if self._handle_quick_command(text):
                    continue

                # Enviar al chat si hay callback
                if self._chat_send_callback:
                    try:
                        response = await asyncio.wait_for(
                            self._chat_send_callback(text), timeout=30.0
                        )
                        if response:
                            self._set_state(MicState.SPEAKING)
                            await self._tts.speak(str(response))
                    except asyncio.TimeoutError:
                        logger.warning("[voice] timeout esperando respuesta del chat")
                    except Exception as e:
                        logger.error(f"[voice] error enviando al chat: {e}")
                else:
                    logger.warning("[voice] no hay chat callback — transcripción perdida")

            except asyncio.TimeoutError:
                # Normal: nadie habló en 1s, continuar
                continue
            except Exception as e:
                logger.error(f"[voice] error en loop: {e}")
                await asyncio.sleep(0.5)

        logger.info("[voice] loop principal terminado")


# Singleton global
voice_service = VoiceService()
