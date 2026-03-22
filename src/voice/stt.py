"""
YeyoOS — SpeechToText
Micro-fase 5.27 — Capa 5: Órganos

Transcripción de voz usando faster-whisper (modelo "base", CPU).
Captura audio desde micrófono hasta detectar silencio (1.5s sin sonido).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    logger.warning("[stt] faster-whisper no disponible — modo mock")

try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False

SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01   # RMS por debajo de esto = silencio
SILENCE_DURATION = 1.5     # Segundos de silencio para terminar grabación
MAX_RECORD_SECONDS = 30    # Límite absoluto de grabación
CHUNK_SIZE = 1024


class SpeechToText:
    """
    Transcriptor de voz. Carga el modelo Whisper "base" una sola vez.
    Método transcribe(audio_bytes) para audio ya grabado.
    Método record_and_transcribe() para captura completa desde micrófono.
    """

    MODEL_SIZE = "base"

    def __init__(self) -> None:
        self._model: Optional[object] = None
        self._model_lock = threading.Lock()
        self._load_model_lazy()

    def _load_model_lazy(self) -> None:
        """Carga el modelo en un thread para no bloquear el inicio."""
        thread = threading.Thread(target=self._load_model, daemon=True, name="whisper-loader")
        thread.start()

    def _load_model(self) -> None:
        if not _WHISPER_AVAILABLE:
            return
        with self._model_lock:
            try:
                self._model = WhisperModel(self.MODEL_SIZE, device="cpu", compute_type="int8")
                logger.info(f"[stt] modelo Whisper '{self.MODEL_SIZE}' cargado (CPU, int8)")
            except Exception as e:
                logger.error(f"[stt] error cargando Whisper: {e}")

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio PCM 16-bit mono 16kHz a texto.
        Retorna string vacío si falla o modelo no disponible.
        """
        if not _WHISPER_AVAILABLE or self._model is None:
            logger.warning("[stt] transcribe: modelo no disponible")
            return ""

        try:
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _info = self._model.transcribe(
                audio_array,
                language="es",
                beam_size=1,
                vad_filter=True,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            logger.info(f"[stt] transcrito: '{text[:80]}{'...' if len(text) > 80 else ''}'")
            return text
        except Exception as e:
            logger.error(f"[stt] error transcribiendo: {e}")
            return ""

    def record_until_silence(self) -> bytes:
        """
        Graba desde el micrófono hasta detectar 1.5s de silencio
        o alcanzar MAX_RECORD_SECONDS.
        Retorna bytes PCM 16-bit mono 16kHz.
        """
        if not _SD_AVAILABLE:
            logger.warning("[stt] sounddevice no disponible, retornando audio vacío")
            return b""

        frames: list[np.ndarray] = []
        silence_start: Optional[float] = None
        start_time = time.time()

        logger.info("[stt] grabando...")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE,
            ) as stream:
                while True:
                    chunk, _ = stream.read(CHUNK_SIZE)
                    frames.append(chunk.copy())

                    # Detectar silencio por RMS
                    rms = float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0)
                    now = time.time()

                    if rms < SILENCE_THRESHOLD:
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start >= SILENCE_DURATION:
                            logger.info(f"[stt] silencio detectado → fin de grabación ({now - start_time:.1f}s)")
                            break
                    else:
                        silence_start = None

                    if now - start_time >= MAX_RECORD_SECONDS:
                        logger.warning("[stt] límite de grabación alcanzado")
                        break

        except Exception as e:
            logger.error(f"[stt] error grabando: {e}")
            return b""

        if not frames:
            return b""

        audio = np.concatenate(frames, axis=0)
        return audio.tobytes()

    def record_and_transcribe(self) -> str:
        """Graba hasta silencio y transcribe. Método de conveniencia."""
        audio_bytes = self.record_until_silence()
        if not audio_bytes:
            return ""
        return self.transcribe(audio_bytes)
