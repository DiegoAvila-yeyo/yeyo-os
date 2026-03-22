"""
YeyoOS — WakeWordDetector
Micro-fase 5.27 — Capa 5: Órganos

Detecta wake words usando OpenWakeWord.
Corre en un thread daemon separado para no bloquear el event loop.
Wake words configurables: ["yeyo", "yeyis", "yeyito", "yeyon", "jarvis"]
Al detectar → pone evento en asyncio.Queue para el VoiceService.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Intentar importar openwakeword (puede no estar en CI)
try:
    from openwakeword.model import Model as OWWModel
    _OWW_AVAILABLE = True
except ImportError:
    _OWW_AVAILABLE = False
    logger.warning("[wake_word] openwakeword no disponible — usando modo mock")

# Intentar importar sounddevice
try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False
    logger.warning("[wake_word] sounddevice no disponible")

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 1280  # 80ms a 16kHz (requerido por OpenWakeWord)
DETECTION_THRESHOLD = 0.5


class WakeWordDetector:
    """
    Escucha continuamente el micrófono en un thread daemon.
    Al detectar un wake word, pone su nombre en self._queue.
    """

    DEFAULT_WAKE_WORDS: List[str] = ["yeyo", "yeyis", "yeyito", "yeyon", "jarvis"]

    def __init__(
        self,
        wake_words: Optional[List[str]] = None,
        event_loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._wake_words = wake_words or self.DEFAULT_WAKE_WORDS
        self._loop = event_loop
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._listening = False
        self._model: Optional[object] = None

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Inicia el thread de escucha."""
        if self._listening:
            logger.warning("[wake_word] ya está escuchando")
            return

        self._loop = loop or self._loop or asyncio.get_event_loop()
        self._stop_event.clear()
        self._listening = True

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="wake-word-detector",
        )
        self._thread.start()
        logger.info(f"[wake_word] iniciado. wake_words={self._wake_words}")

    def stop(self) -> None:
        """Detiene el thread de escucha."""
        self._stop_event.set()
        self._listening = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("[wake_word] detenido")

    def is_listening(self) -> bool:
        return self._listening and (self._thread is not None and self._thread.is_alive())

    @property
    def queue(self) -> asyncio.Queue[str]:
        """Queue donde se depositan los wake words detectados."""
        return self._queue

    def _load_model(self) -> Optional[object]:
        """Carga el modelo OpenWakeWord (lazy)."""
        if not _OWW_AVAILABLE:
            return None
        try:
            model = OWWModel(wakeword_models=self._wake_words, inference_framework="onnx")
            logger.info("[wake_word] modelo OWW cargado")
            return model
        except Exception as e:
            logger.error(f"[wake_word] error cargando modelo: {e}")
            return None

    def _put_detection(self, word: str) -> None:
        """Hilo-seguro: pone la detección en la queue asyncio."""
        if self._loop and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._queue.put(word), self._loop
            )

    def _run(self) -> None:
        """Loop principal del thread de escucha."""
        self._model = self._load_model()

        if not _SD_AVAILABLE or not _OWW_AVAILABLE or self._model is None:
            logger.warning("[wake_word] modo simulado activo (sin hardware/modelo)")
            # En modo simulado, espera señal externa via inject_detection()
            while not self._stop_event.is_set():
                time.sleep(0.1)
            return

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SAMPLES,
            ) as stream:
                logger.info("[wake_word] escuchando micrófono...")
                while not self._stop_event.is_set():
                    audio_chunk, _ = stream.read(CHUNK_SAMPLES)
                    audio_float = audio_chunk.flatten().astype(np.float32) / 32768.0

                    predictions = self._model.predict(audio_float)

                    for word in self._wake_words:
                        score = predictions.get(word, 0.0)
                        if score >= DETECTION_THRESHOLD:
                            logger.info(f"[wake_word] detectado: '{word}' (score={score:.3f})")
                            self._put_detection(word)
                            # Pequeña pausa para evitar detecciones duplicadas
                            time.sleep(1.5)
                            break
        except Exception as e:
            logger.error(f"[wake_word] error en stream: {e}")
        finally:
            self._listening = False

    def inject_detection(self, word: str = "yeyo") -> None:
        """
        Inyecta una detección manualmente. Útil para tests y modo simulado.
        """
        self._put_detection(word)
