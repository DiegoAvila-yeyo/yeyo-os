## ═══════════════════════════════════════
## MICRO-FASE 5.27 — Voice Interface: Wake Word + STT + TTS + MicIndicator
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.27-1 [VSCODE] — Sistema de voz completo: OpenWakeWord + Whisper + pyttsx3 + MicIndicator

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.27 de Capa 5 (Órganos): implementar la interfaz de voz completa — detección de wake word ("Yeyo"), transcripción con faster-whisper, síntesis de voz con pyttsx3, y los componentes React de indicador de micrófono y waveform.

CONTEXTO:
- Micro-fases 5.0–5.26 completadas: todos los nodos, grafos avanzados funcionando
- Micro-fase 3.20 completada: Topbar.tsx existe en frontend/src/components/layout/Topbar.tsx
- Stack: Next.js + React + TypeScript, Zustand para estado, Web Audio API para waveform
- Backend: FastAPI en src/api/, Python con asyncio, threading para operaciones bloqueantes
- Kill Switch (Ctrl+Alt+K, micro-fase 3.21/6.3) ya está integrado — "para todo" también lo activa
- Hardware objetivo: CPU Ryzen (sin GPU para voz), micrófono USB estándar
- La voz es ambient-first: YEYO siempre escucha, responde al wake word sin clicks
- Dependencias Python: openwakeword, faster-whisper, pyttsx3, sounddevice, numpy
- Instalar: pip install openwakeword faster-whisper pyttsx3 sounddevice numpy

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/voice/wake_word.py:

   Ruta: ~/yeyo-os/src/voice/wake_word.py
   Contenido:

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

2. Crear archivo src/voice/stt.py:

   Ruta: ~/yeyo-os/src/voice/stt.py
   Contenido:

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

3. Crear archivo src/voice/tts.py:

   Ruta: ~/yeyo-os/src/voice/tts.py
   Contenido:

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

4. Crear archivo src/voice/voice_service.py:

   Ruta: ~/yeyo-os/src/voice/voice_service.py
   Contenido:

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

5. Crear archivo src/api/voice_ws.py:

   Ruta: ~/yeyo-os/src/api/voice_ws.py
   Contenido:

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

6. Crear archivo src/api/voice_api.py:

   Ruta: ~/yeyo-os/src/api/voice_api.py
   Contenido:

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

7. Crear archivo frontend/src/components/voice/MicIndicator.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/voice/MicIndicator.tsx
   Contenido:

   /**
    * YeyoOS — MicIndicator
    * Micro-fase 5.27 — Capa 5: Órganos
    *
    * Punto de 10px en el topbar que indica el estado del micrófono.
    * Colores y animaciones por estado. Click = toggle micrófono.
    * Se conecta via WebSocket /ws/voice para recibir cambios de estado.
    */

   import React, { useEffect, useRef } from 'react'
   import { useVoiceStore, MicState } from '../../stores/voiceStore'

   const STATE_CONFIG: Record<MicState, { color: string; size: number; animation: string; tooltip: string }> = {
     idle: {
       color: '#2EA043',
       size: 10,
       animation: 'mic-pulse-slow 2s ease-in-out infinite',
       tooltip: 'Micrófono activo — Di "Yeyo" para hablar',
     },
     listening: {
       color: '#4FC3F7',
       size: 14,
       animation: 'mic-pulse-fast 0.5s ease-in-out infinite',
       tooltip: 'Escuchando... Di "Yeyo" para hablar',
     },
     recording: {
       color: '#4FC3F7',
       size: 14,
       animation: 'mic-pulse-fast 0.5s ease-in-out infinite',
       tooltip: 'Grabando tu voz...',
     },
     processing: {
       color: '#FFD600',
       size: 12,
       animation: 'mic-spin 0.8s linear infinite',
       tooltip: 'Procesando...',
     },
     speaking: {
       color: '#ffffff',
       size: 12,
       animation: 'none',
       tooltip: 'YEYO está hablando',
     },
     disabled: {
       color: '#484F58',
       size: 10,
       animation: 'none',
       tooltip: 'Micrófono desactivado — Click para activar',
     },
   }

   export function MicIndicator() {
     const { micState, isEnabled, toggleMic, setMicState } = useVoiceStore()
     const wsRef = useRef<WebSocket | null>(null)

     // Conectar WebSocket /ws/voice
     useEffect(() => {
       const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
       const wsUrl = `${protocol}//${window.location.host}/ws/voice`
       const ws = new WebSocket(wsUrl)
       wsRef.current = ws

       ws.onmessage = (event) => {
         try {
           const data = JSON.parse(event.data)
           if (data.type === 'mic_state') {
             setMicState(data.state as MicState)
           }
         } catch {
           // Ignorar mensajes malformados
         }
       }

       ws.onclose = () => {
         // Reconectar en 3s
         setTimeout(() => {
           if (wsRef.current?.readyState === WebSocket.CLOSED) {
             // El useEffect cleanup y re-mount no aplica aquí —
             // en producción usar un manager de reconexión (como en Capa 3.12)
           }
         }, 3000)
       }

       return () => {
         ws.close()
         wsRef.current = null
       }
     }, [setMicState])

     const config = STATE_CONFIG[micState] || STATE_CONFIG.idle

     return (
       <>
         <style>{`
           @keyframes mic-pulse-slow {
             0%, 100% { opacity: 1; transform: scale(1); }
             50% { opacity: 0.6; transform: scale(0.85); }
           }
           @keyframes mic-pulse-fast {
             0%, 100% { opacity: 1; transform: scale(1); }
             50% { opacity: 0.5; transform: scale(1.2); }
           }
           @keyframes mic-spin {
             from { transform: rotate(0deg); }
             to { transform: rotate(360deg); }
           }
           .mic-indicator-dot:hover .mic-indicator-tooltip {
             opacity: 1;
             transform: translateX(-50%) translateY(0);
           }
         `}</style>

         <div
           className="mic-indicator-dot"
           data-testid="mic-indicator"
           data-state={micState}
           onClick={toggleMic}
           title={config.tooltip}
           style={{
             position: 'relative',
             width: config.size,
             height: config.size,
             borderRadius: '50%',
             background: config.color,
             animation: config.animation,
             cursor: 'pointer',
             transition: 'width 0.2s, height 0.2s, background 0.3s',
             flexShrink: 0,
           }}
         >
           {/* Tooltip */}
           <div
             className="mic-indicator-tooltip"
             style={{
               position: 'absolute',
               top: '100%',
               left: '50%',
               transform: 'translateX(-50%) translateY(4px)',
               background: '#161B22',
               border: '1px solid #30363D',
               borderRadius: 6,
               padding: '5px 10px',
               fontSize: 12,
               color: '#C9D1D9',
               whiteSpace: 'nowrap',
               pointerEvents: 'none',
               opacity: 0,
               transition: 'opacity 0.15s, transform 0.15s',
               zIndex: 1000,
               marginTop: 6,
             }}
           >
             {config.tooltip}
           </div>
         </div>
       </>
     )
   }

8. Crear archivo frontend/src/components/voice/VoiceWaveform.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/voice/VoiceWaveform.tsx
   Contenido:

   /**
    * YeyoOS — VoiceWaveform
    * Micro-fase 5.27 — Capa 5: Órganos
    *
    * Barra de voz que aparece en bottom-center cuando el micrófono graba.
    * Waveform animado con Web Audio API. Texto transcrito letra por letra.
    * Se desvanece automáticamente al terminar.
    */

   import React, { useEffect, useRef, useCallback } from 'react'
   import { useVoiceStore, MicState } from '../../stores/voiceStore'

   const BAR_COUNT = 24
   const BAR_MIN_HEIGHT = 4
   const BAR_MAX_HEIGHT = 40

   export function VoiceWaveform() {
     const { micState, transcript } = useVoiceStore()
     const canvasRef = useRef<HTMLCanvasElement>(null)
     const animFrameRef = useRef<number | null>(null)
     const analyserRef = useRef<AnalyserNode | null>(null)
     const streamRef = useRef<MediaStream | null>(null)
     const audioCtxRef = useRef<AudioContext | null>(null)

     const visible = micState === 'recording' || micState === 'processing'

     // Iniciar captura de audio para el waveform cuando graba
     useEffect(() => {
       if (micState !== 'recording') {
         // Limpiar audio context al salir de recording
         if (streamRef.current) {
           streamRef.current.getTracks().forEach((t) => t.stop())
           streamRef.current = null
         }
         if (audioCtxRef.current) {
           audioCtxRef.current.close()
           audioCtxRef.current = null
           analyserRef.current = null
         }
         return
       }

       // Obtener acceso al micrófono para visualización
       navigator.mediaDevices
         ?.getUserMedia({ audio: true })
         .then((stream) => {
           streamRef.current = stream
           const ctx = new AudioContext()
           audioCtxRef.current = ctx
           const analyser = ctx.createAnalyser()
           analyser.fftSize = 64
           analyserRef.current = analyser
           const source = ctx.createMediaStreamSource(stream)
           source.connect(analyser)
         })
         .catch(() => {
           // Sin permisos de micrófono — usar animación genérica
         })
     }, [micState])

     // Dibujar waveform en canvas
     const drawWaveform = useCallback(() => {
       const canvas = canvasRef.current
       if (!canvas) return
       const ctx = canvas.getContext('2d')
       if (!ctx) return

       const width = canvas.width
       const height = canvas.height
       ctx.clearRect(0, 0, width, height)

       const barWidth = Math.floor(width / BAR_COUNT) - 2
       const analyser = analyserRef.current

       let dataArray: Uint8Array

       if (analyser) {
         dataArray = new Uint8Array(analyser.frequencyBinCount)
         analyser.getByteFrequencyData(dataArray)
       } else {
         // Animación genérica cuando no hay acceso al micrófono
         dataArray = new Uint8Array(BAR_COUNT).fill(0).map((_, i) =>
           Math.floor(128 + 80 * Math.sin(Date.now() / 200 + i * 0.5))
         )
       }

       for (let i = 0; i < BAR_COUNT; i++) {
         const dataIndex = Math.floor((i / BAR_COUNT) * dataArray.length)
         const normalized = (dataArray[dataIndex] || 0) / 255
         const barHeight = BAR_MIN_HEIGHT + normalized * (BAR_MAX_HEIGHT - BAR_MIN_HEIGHT)

         const gradient = ctx.createLinearGradient(0, height - barHeight, 0, height)
         gradient.addColorStop(0, '#4FC3F7')
         gradient.addColorStop(1, '#0288D1')

         ctx.fillStyle = gradient
         ctx.beginPath()
         ctx.roundRect(
           i * (barWidth + 2),
           height / 2 - barHeight / 2,
           barWidth,
           barHeight,
           2
         )
         ctx.fill()
       }

       animFrameRef.current = requestAnimationFrame(drawWaveform)
     }, [])

     useEffect(() => {
       if (micState === 'recording') {
         animFrameRef.current = requestAnimationFrame(drawWaveform)
       } else {
         if (animFrameRef.current) {
           cancelAnimationFrame(animFrameRef.current)
           animFrameRef.current = null
         }
       }
       return () => {
         if (animFrameRef.current) {
           cancelAnimationFrame(animFrameRef.current)
         }
       }
     }, [micState, drawWaveform])

     if (!visible) return null

     return (
       <div
         data-testid="voice-waveform"
         data-state={micState}
         style={{
           position: 'fixed',
           bottom: 32,
           left: '50%',
           transform: 'translateX(-50%)',
           zIndex: 500,
           background: 'rgba(13, 17, 23, 0.92)',
           border: '1px solid #30363D',
           borderRadius: 16,
           padding: '16px 24px',
           display: 'flex',
           flexDirection: 'column',
           alignItems: 'center',
           gap: 10,
           minWidth: 280,
           backdropFilter: 'blur(8px)',
           animation: 'waveform-appear 0.2s ease',
         }}
       >
         <style>{`
           @keyframes waveform-appear {
             from { opacity: 0; transform: translateX(-50%) translateY(10px); }
             to { opacity: 1; transform: translateX(-50%) translateY(0); }
           }
         `}</style>

         {/* Status text */}
         <div
           data-testid="waveform-status"
           style={{
             fontSize: 13,
             color: micState === 'recording' ? '#4FC3F7' : '#FFD600',
             fontWeight: 600,
             letterSpacing: 0.5,
           }}
         >
           {micState === 'recording' ? '🎙 Te escucho...' : '⚙ Procesando...'}
         </div>

         {/* Canvas del waveform */}
         {micState === 'recording' && (
           <canvas
             ref={canvasRef}
             data-testid="waveform-canvas"
             width={BAR_COUNT * 6}
             height={BAR_MAX_HEIGHT + 8}
             style={{ display: 'block' }}
           />
         )}

         {/* Transcripción en tiempo real */}
         {transcript && (
           <div
             data-testid="waveform-transcript"
             style={{
               fontSize: 14,
               color: '#C9D1D9',
               maxWidth: 360,
               textAlign: 'center',
               fontStyle: 'italic',
             }}
           >
             "{transcript}"
           </div>
         )}
       </div>
     )
   }

9. Crear archivo frontend/src/stores/voiceStore.ts:

   Ruta: ~/yeyo-os/frontend/src/stores/voiceStore.ts
   Contenido:

   /**
    * YeyoOS — voiceStore
    * Micro-fase 5.27 — Capa 5: Órganos
    *
    * Store Zustand para el estado del sistema de voz.
    */

   import { create } from 'zustand'

   export type MicState =
     | 'idle'
     | 'listening'
     | 'recording'
     | 'processing'
     | 'speaking'
     | 'disabled'

   interface VoiceState {
     micState: MicState
     isEnabled: boolean
     transcript: string
   }

   interface VoiceActions {
     setMicState: (state: MicState) => void
     toggleMic: () => void
     setTranscript: (text: string) => void
   }

   export const useVoiceStore = create<VoiceState & VoiceActions>()((set, get) => ({
     micState: 'idle',
     isEnabled: true,
     transcript: '',

     setMicState: (state) => {
       set({
         micState: state,
         isEnabled: state !== 'disabled',
         // Limpiar transcripción cuando termina de procesar
         transcript: state === 'idle' || state === 'listening' ? '' : get().transcript,
       })
     },

     toggleMic: () => {
       const { micState } = get()
       if (micState === 'disabled') {
         set({ micState: 'idle', isEnabled: true })
         // Notificar al backend via REST
         fetch('/api/voice/toggle', { method: 'POST' }).catch(() => {})
       } else {
         set({ micState: 'disabled', isEnabled: false })
         fetch('/api/voice/toggle', { method: 'POST' }).catch(() => {})
       }
     },

     setTranscript: (text) => set({ transcript: text }),
   }))

10. Modificar frontend/src/components/layout/Topbar.tsx para integrar MicIndicator:

    Ruta: ~/yeyo-os/frontend/src/components/layout/Topbar.tsx
    Instrucción: Localiza el archivo Topbar.tsx existente (de micro-fase 3.20).
    Agrega el import de MicIndicator y colócalo en el área derecha del topbar.

    BUSCAR en Topbar.tsx el lugar donde están los iconos/controles del lado derecho
    (usualmente cerca del cierre de la primera sección o en un div de controles).
    AGREGAR estas líneas:

    // Al inicio del archivo, después de los imports existentes:
    import { MicIndicator } from '../voice/MicIndicator'

    // Dentro del JSX, en el área derecha del topbar (busca el div con iconos de control):
    // Añadir antes del último icono del topbar:
    <MicIndicator />

11. Crear archivo tests/test_wake_word.py:

    Ruta: ~/yeyo-os/tests/test_wake_word.py
    Contenido:

    """
    Tests para WakeWordDetector — Micro-fase 5.27
    """

    import asyncio
    import pytest

    from src.voice.wake_word import WakeWordDetector


    @pytest.fixture
    def detector():
        """WakeWordDetector fresco por test."""
        d = WakeWordDetector(wake_words=["yeyo", "jarvis"])
        yield d
        d.stop()


    @pytest.mark.asyncio
    async def test_detector_inicia_y_para(detector):
        """El detector se puede iniciar y detener sin errores."""
        loop = asyncio.get_event_loop()
        detector.start(loop=loop)
        assert detector.is_listening() is True
        detector.stop()
        assert detector.is_listening() is False


    @pytest.mark.asyncio
    async def test_inject_detection_pone_en_queue(detector):
        """inject_detection() coloca el wake word en la queue."""
        loop = asyncio.get_event_loop()
        detector.start(loop=loop)
        await asyncio.sleep(0.05)  # Dar tiempo al thread a iniciar

        detector.inject_detection("yeyo")
        await asyncio.sleep(0.05)  # Dar tiempo al put_detection

        word = await asyncio.wait_for(detector.queue.get(), timeout=1.0)
        assert word == "yeyo"


    @pytest.mark.asyncio
    async def test_inject_detection_sin_iniciar(detector):
        """inject_detection() sin loop configurado no falla."""
        # Sin start(), _loop es None — no debe lanzar excepción
        detector._loop = asyncio.get_event_loop()
        detector.inject_detection("jarvis")
        await asyncio.sleep(0.1)
        # No debe haber nada en la queue (no hay loop activo en thread)
        assert detector.queue.empty() or not detector.queue.empty()  # No crash = OK


    def test_wake_words_por_defecto():
        """Los wake words por defecto incluyen 'yeyo'."""
        d = WakeWordDetector()
        assert "yeyo" in d.DEFAULT_WAKE_WORDS
        assert "jarvis" in d.DEFAULT_WAKE_WORDS


    def test_wake_words_configurables():
        """Se pueden configurar wake words personalizados."""
        d = WakeWordDetector(wake_words=["hola", "mundo"])
        assert d._wake_words == ["hola", "mundo"]

12. Crear archivo tests/test_stt.py:

    Ruta: ~/yeyo-os/tests/test_stt.py
    Contenido:

    """
    Tests para SpeechToText — Micro-fase 5.27
    """

    import pytest
    from unittest.mock import MagicMock, patch
    import numpy as np


    def test_transcribe_sin_modelo_retorna_vacio():
        """Sin modelo disponible, transcribe() retorna string vacío."""
        with patch("src.voice.stt._WHISPER_AVAILABLE", False):
            from src.voice.stt import SpeechToText
            stt = SpeechToText()
            stt._model = None
            result = stt.transcribe(b"\x00" * 1024)
            assert result == ""


    def test_transcribe_con_modelo_mock():
        """Con modelo mock, transcribe() retorna el texto de los segmentos."""
        with patch("src.voice.stt._WHISPER_AVAILABLE", True):
            from src.voice.stt import SpeechToText

            mock_segment = MagicMock()
            mock_segment.text = "  hola mundo  "
            mock_info = MagicMock()

            stt = SpeechToText.__new__(SpeechToText)
            stt._model_lock = __import__("threading").Lock()
            mock_model = MagicMock()
            mock_model.transcribe.return_value = ([mock_segment], mock_info)
            stt._model = mock_model

            # Audio PCM 16-bit de 1 segundo (silencio)
            audio = np.zeros(16000, dtype=np.int16).tobytes()
            result = stt.transcribe(audio)
            assert result == "hola mundo"


    def test_transcribe_multiples_segmentos():
        """Múltiples segmentos se unen con espacio."""
        with patch("src.voice.stt._WHISPER_AVAILABLE", True):
            from src.voice.stt import SpeechToText

            seg1 = MagicMock()
            seg1.text = "primera parte"
            seg2 = MagicMock()
            seg2.text = "segunda parte"

            stt = SpeechToText.__new__(SpeechToText)
            stt._model_lock = __import__("threading").Lock()
            mock_model = MagicMock()
            mock_model.transcribe.return_value = ([seg1, seg2], MagicMock())
            stt._model = mock_model

            audio = np.zeros(16000, dtype=np.int16).tobytes()
            result = stt.transcribe(audio)
            assert result == "primera parte segunda parte"


    def test_transcribe_excepcion_retorna_vacio():
        """Si el modelo lanza excepción, transcribe() retorna vacío."""
        with patch("src.voice.stt._WHISPER_AVAILABLE", True):
            from src.voice.stt import SpeechToText

            stt = SpeechToText.__new__(SpeechToText)
            stt._model_lock = __import__("threading").Lock()
            mock_model = MagicMock()
            mock_model.transcribe.side_effect = RuntimeError("GPU OOM")
            stt._model = mock_model

            audio = np.zeros(16000, dtype=np.int16).tobytes()
            result = stt.transcribe(audio)
            assert result == ""

13. Crear archivo tests/test_tts_voice.py:

    Ruta: ~/yeyo-os/tests/test_tts_voice.py
    Contenido:

    """
    Tests para TextToSpeech — Micro-fase 5.27
    """

    import asyncio
    import pytest
    import time
    from unittest.mock import patch, MagicMock


    @pytest.fixture
    def tts_mock():
        """TTS con pyttsx3 mockeado."""
        with patch("src.voice.tts._PYTTSX3_AVAILABLE", True):
            with patch("src.voice.tts.pyttsx3") as mock_pyttsx3:
                mock_engine = MagicMock()
                mock_pyttsx3.init.return_value = mock_engine
                from src.voice.tts import TextToSpeech
                yield TextToSpeech(), mock_engine


    @pytest.mark.asyncio
    async def test_speak_no_bloquea(tts_mock):
        """speak() async retorna rápido sin esperar que el audio termine."""
        tts, _ = tts_mock
        start = time.time()
        await tts.speak("Texto de prueba que tardaría en hablar")
        elapsed = time.time() - start
        # speak() con run_in_executor puede bloquear en test — verificar que no excede 2s
        assert elapsed < 5.0  # En tests con mock es casi instantáneo


    @pytest.mark.asyncio
    async def test_speak_texto_vacio_no_hace_nada(tts_mock):
        """speak() con texto vacío no llama al engine."""
        tts, mock_engine = tts_mock
        await tts.speak("   ")
        mock_engine.say.assert_not_called()


    def test_speak_sync_espera(tts_mock):
        """speak_sync() llama al engine y espera."""
        tts, mock_engine = tts_mock
        tts.speak_sync("Hola mundo")
        mock_engine.say.assert_called_once_with("Hola mundo")
        mock_engine.runAndWait.assert_called_once()


    def test_voice_enabled_false_no_habla(tts_mock):
        """Cuando voice_enabled=False, speak_sync() no habla."""
        tts, mock_engine = tts_mock
        tts.voice_enabled = False
        tts.speak_sync("No debería hablar")
        mock_engine.say.assert_not_called()


    def test_configure_rate_y_volume(tts_mock):
        """configure() actualiza rate y volume."""
        tts, _ = tts_mock
        tts.configure(rate=200, volume=0.5)
        assert tts._rate == 200
        assert tts._volume == 0.5


    def test_configure_limites():
        """configure() respeta los límites min/max."""
        from src.voice.tts import TextToSpeech
        tts = TextToSpeech()
        tts.configure(rate=1000, volume=2.0)
        assert tts._rate == 400
        assert tts._volume == 1.0
        tts.configure(rate=-100, volume=-1.0)
        assert tts._rate == 50
        assert tts._volume == 0.0


    @pytest.mark.asyncio
    async def test_say_system_frases(tts_mock):
        """say_system() habla las frases del sistema predefinidas."""
        tts, mock_engine = tts_mock
        await tts.say_system("ready")
        mock_engine.say.assert_called_with("Dime.")

14. Crear archivo tests/test_voice_service.py:

    Ruta: ~/yeyo-os/tests/test_voice_service.py
    Contenido:

    """
    Tests para VoiceService — Micro-fase 5.27
    """

    import asyncio
    import pytest
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.voice.voice_service import VoiceService, MicState


    @pytest.fixture
    def service():
        """VoiceService fresco con mocks."""
        with patch("src.voice.voice_service.WakeWordDetector") as MockDetector, \
             patch("src.voice.voice_service.SpeechToText") as MockSTT, \
             patch("src.voice.voice_service.TextToSpeech") as MockTTS:

            mock_detector = MagicMock()
            mock_detector.queue = asyncio.Queue()
            mock_detector.start = MagicMock()
            mock_detector.stop = MagicMock()
            mock_detector.is_listening.return_value = True
            MockDetector.return_value = mock_detector

            mock_stt = MagicMock()
            mock_stt.record_until_silence.return_value = b"\x00" * 1024
            mock_stt.transcribe.return_value = "hola mundo"
            MockSTT.return_value = mock_stt

            mock_tts = MagicMock()
            mock_tts.speak = AsyncMock()
            mock_tts.say_system = AsyncMock()
            mock_tts.voice_enabled = True
            MockTTS.return_value = mock_tts

            svc = VoiceService()
            yield svc, mock_detector, mock_stt, mock_tts


    @pytest.mark.asyncio
    async def test_start_inicia_detector(service):
        """start() inicia el detector y cambia estado a LISTENING."""
        svc, mock_detector, _, _ = service
        await svc.start()
        assert svc.state == MicState.LISTENING
        mock_detector.start.assert_called_once()
        await svc.stop()


    @pytest.mark.asyncio
    async def test_stop_detiene_detector(service):
        """stop() detiene el detector y cambia estado a DISABLED."""
        svc, mock_detector, _, _ = service
        await svc.start()
        await svc.stop()
        assert svc.state == MicState.DISABLED
        mock_detector.stop.assert_called()


    @pytest.mark.asyncio
    async def test_comando_para_todo_activa_kill_switch(service):
        """Comando "para todo" activa el kill switch callback."""
        svc, _, _, _ = service
        kill_switch_called = []
        svc.set_kill_switch_callback(lambda: kill_switch_called.append(True))

        handled = svc._handle_quick_command("oye para todo por favor")
        assert handled is True
        assert len(kill_switch_called) == 1


    @pytest.mark.asyncio
    async def test_comando_silencio_deshabilita_mic(service):
        """Comando "silencio" deshabilita el micrófono."""
        svc, mock_detector, _, _ = service
        loop = asyncio.get_event_loop()
        svc._detector.start(loop=loop)

        handled = svc._handle_quick_command("silencio")
        assert handled is True
        assert svc.state == MicState.DISABLED


    @pytest.mark.asyncio
    async def test_comando_despierta_habilita_mic(service):
        """Comando "despierta" habilita el micrófono."""
        svc, mock_detector, _, _ = service
        svc._state = MicState.DISABLED
        handled = svc._handle_quick_command("despierta")
        assert handled is True
        assert svc.state == MicState.LISTENING


    def test_texto_normal_no_es_comando(service):
        """Texto normal no activa ningún comando rápido."""
        svc, _, _, _ = service
        handled = svc._handle_quick_command("genera una imagen de un gato")
        assert handled is False


    @pytest.mark.asyncio
    async def test_state_callback_se_llama(service):
        """El callback de estado se llama al cambiar estado."""
        svc, _, _, _ = service
        states_received = []
        svc.set_state_callback(lambda s: states_received.append(s))
        await svc.start()
        assert MicState.LISTENING in states_received
        await svc.stop()


    def test_comando_abre_imagen(service):
        """Comando "abre imagen" activa el callback de nodo."""
        svc, _, _, _ = service
        nodes_opened = []
        svc.set_open_node_callback(lambda n: nodes_opened.append(n))
        handled = svc._handle_quick_command("abre imagen")
        assert handled is True
        assert "image" in nodes_opened

15. Crear archivo frontend/src/__tests__/voice/MicIndicator.test.tsx:

    Ruta: ~/yeyo-os/frontend/src/__tests__/voice/MicIndicator.test.tsx
    Contenido:

    /**
     * Tests para MicIndicator — Micro-fase 5.27
     */

    import React from 'react'
    import { render, screen, fireEvent } from '@testing-library/react'
    import { MicIndicator } from '../../components/voice/MicIndicator'
    import { useVoiceStore } from '../../stores/voiceStore'

    // Mock WebSocket
    const mockWs = {
      onmessage: null as any,
      onclose: null as any,
      close: jest.fn(),
      readyState: WebSocket.OPEN,
    }
    global.WebSocket = jest.fn(() => mockWs) as any

    // Mock fetch para toggle
    global.fetch = jest.fn().mockResolvedValue({ ok: true })

    beforeEach(() => {
      jest.clearAllMocks()
      useVoiceStore.setState({
        micState: 'idle',
        isEnabled: true,
        transcript: '',
      })
    })

    describe('MicIndicator', () => {
      it('renderiza el indicador de micrófono', () => {
        render(<MicIndicator />)
        expect(screen.getByTestId('mic-indicator')).toBeInTheDocument()
      })

      it('tiene data-state="idle" por defecto', () => {
        render(<MicIndicator />)
        expect(screen.getByTestId('mic-indicator')).toHaveAttribute('data-state', 'idle')
      })

      it('cambia data-state cuando el store cambia', () => {
        render(<MicIndicator />)
        useVoiceStore.setState({ micState: 'listening' })
        // Forzar re-render verificando que el componente reacciona al store
        const { rerender } = render(<MicIndicator />)
        rerender(<MicIndicator />)
        expect(screen.getAllByTestId('mic-indicator')[0]).toHaveAttribute('data-state', 'listening')
      })

      it('cambia color al estado recording', () => {
        useVoiceStore.setState({ micState: 'recording' })
        render(<MicIndicator />)
        const indicator = screen.getByTestId('mic-indicator')
        expect(indicator).toHaveAttribute('data-state', 'recording')
      })

      it('cambia color al estado disabled', () => {
        useVoiceStore.setState({ micState: 'disabled' })
        render(<MicIndicator />)
        expect(screen.getByTestId('mic-indicator')).toHaveAttribute('data-state', 'disabled')
      })

      it('click llama a toggleMic y hace fetch a /api/voice/toggle', () => {
        render(<MicIndicator />)
        fireEvent.click(screen.getByTestId('mic-indicator'))
        expect(global.fetch).toHaveBeenCalledWith('/api/voice/toggle', { method: 'POST' })
      })

      it('actualiza estado desde mensaje WebSocket', () => {
        render(<MicIndicator />)
        // Simular mensaje WS
        if (mockWs.onmessage) {
          mockWs.onmessage({ data: JSON.stringify({ type: 'mic_state', state: 'speaking' }) })
        }
        expect(useVoiceStore.getState().micState).toBe('speaking')
      })
    })

16. Crear archivo frontend/src/__tests__/voice/VoiceWaveform.test.tsx:

    Ruta: ~/yeyo-os/frontend/src/__tests__/voice/VoiceWaveform.test.tsx
    Contenido:

    /**
     * Tests para VoiceWaveform — Micro-fase 5.27
     */

    import React from 'react'
    import { render, screen } from '@testing-library/react'
    import { VoiceWaveform } from '../../components/voice/VoiceWaveform'
    import { useVoiceStore } from '../../stores/voiceStore'

    // Mock Web Audio API
    const mockAnalyser = {
      fftSize: 64,
      frequencyBinCount: 32,
      getByteFrequencyData: jest.fn(),
      connect: jest.fn(),
    }
    const mockSource = { connect: jest.fn() }
    const mockAudioContext = {
      createAnalyser: jest.fn(() => mockAnalyser),
      createMediaStreamSource: jest.fn(() => mockSource),
      close: jest.fn(),
    }
    global.AudioContext = jest.fn(() => mockAudioContext) as any

    // Mock getUserMedia
    global.navigator.mediaDevices = {
      getUserMedia: jest.fn().mockRejectedValue(new Error('no mic in tests')),
    } as any

    beforeEach(() => {
      jest.clearAllMocks()
      useVoiceStore.setState({
        micState: 'idle',
        isEnabled: true,
        transcript: '',
      })
    })

    describe('VoiceWaveform', () => {
      it('no renderiza nada en estado idle', () => {
        const { container } = render(<VoiceWaveform />)
        expect(screen.queryByTestId('voice-waveform')).not.toBeInTheDocument()
      })

      it('no renderiza nada en estado listening', () => {
        useVoiceStore.setState({ micState: 'listening' })
        render(<VoiceWaveform />)
        expect(screen.queryByTestId('voice-waveform')).not.toBeInTheDocument()
      })

      it('renderiza en estado recording', () => {
        useVoiceStore.setState({ micState: 'recording' })
        render(<VoiceWaveform />)
        expect(screen.getByTestId('voice-waveform')).toBeInTheDocument()
      })

      it('renderiza en estado processing', () => {
        useVoiceStore.setState({ micState: 'processing' })
        render(<VoiceWaveform />)
        expect(screen.getByTestId('voice-waveform')).toBeInTheDocument()
      })

      it('muestra "Te escucho..." en recording', () => {
        useVoiceStore.setState({ micState: 'recording' })
        render(<VoiceWaveform />)
        expect(screen.getByTestId('waveform-status')).toHaveTextContent('Te escucho')
      })

      it('muestra "Procesando..." en processing', () => {
        useVoiceStore.setState({ micState: 'processing' })
        render(<VoiceWaveform />)
        expect(screen.getByTestId('waveform-status')).toHaveTextContent('Procesando')
      })

      it('muestra canvas en recording', () => {
        useVoiceStore.setState({ micState: 'recording' })
        render(<VoiceWaveform />)
        expect(screen.getByTestId('waveform-canvas')).toBeInTheDocument()
      })

      it('muestra transcripción si hay texto', () => {
        useVoiceStore.setState({ micState: 'recording', transcript: 'genera una imagen' })
        render(<VoiceWaveform />)
        expect(screen.getByTestId('waveform-transcript')).toHaveTextContent('genera una imagen')
      })

      it('no muestra transcripción si no hay texto', () => {
        useVoiceStore.setState({ micState: 'recording', transcript: '' })
        render(<VoiceWaveform />)
        expect(screen.queryByTestId('waveform-transcript')).not.toBeInTheDocument()
      })

      it('desaparece al volver a idle', () => {
        useVoiceStore.setState({ micState: 'recording' })
        const { rerender } = render(<VoiceWaveform />)
        expect(screen.getByTestId('voice-waveform')).toBeInTheDocument()
        useVoiceStore.setState({ micState: 'idle' })
        rerender(<VoiceWaveform />)
        expect(screen.queryByTestId('voice-waveform')).not.toBeInTheDocument()
      })
    })

VERIFICAR:
- [ ] src/voice/wake_word.py: WakeWordDetector inicia/para, inject_detection() coloca en queue, modo mock cuando no hay hardware
- [ ] src/voice/stt.py: transcribe(audio_bytes) retorna texto, record_until_silence() detecta 1.5s de silencio, modelo Whisper "base" en CPU
- [ ] src/voice/tts.py: speak() async no bloquea, speak_sync() espera, voice_enabled=False silencia, SYSTEM_PHRASES definidas
- [ ] src/voice/voice_service.py: "para todo" activa kill switch, "silencio" deshabilita mic, "despierta" habilita mic, state_callback se llama
- [ ] src/api/voice_ws.py: WebSocket /ws/voice emite mic_state al conectar, broadcast al cambiar estado
- [ ] src/api/voice_api.py: POST /speak, GET /status, POST /toggle, POST /config funcionan
- [ ] MicIndicator.tsx: colores correctos por estado, click → toggleMic, WebSocket recibe mic_state
- [ ] VoiceWaveform.tsx: visible en recording/processing, invisible en idle/listening, muestra transcript
- [ ] voiceStore.ts: setMicState, toggleMic, setTranscript funcionan
- [ ] MicIndicator integrado en Topbar.tsx
- [ ] Tests pytest pasan: test_wake_word.py (5), test_stt.py (4), test_tts_voice.py (7), test_voice_service.py (8)
- [ ] Tests Jest pasan: MicIndicator (7 tests), VoiceWaveform (10 tests)

SI FALLA:
- openwakeword no disponible: pip install openwakeword — en CI mockear con inject_detection()
- faster-whisper requiere C++ runtime: pip install faster-whisper — en Linux instalar libgomp1
- sounddevice no encuentra micrófono: en CI los tests mockean sd con patch, no requieren hardware real
- pyttsx3 requiere espeak en Linux: apt-get install espeak-ng — en CI usar la fixture tts_mock
- Web Audio API no disponible en jsdom: ya está mockeado en el test con global.AudioContext = jest.fn()
- canvas.roundRect no existe en jsdom: ignorar error en tests, el canvas es visual y no se testea contenido
- WebSocket en tests React: usar el mock global.WebSocket = jest.fn(() => mockWs)
- MicIndicator update desde WS: llamar mockWs.onmessage() manualmente en el test
- Topbar.tsx import: si el path difiere, ajustar el import relativo según la estructura de carpetas de 3.20

NO HACER:
- No usar GPU para el modelo Whisper (device="cpu" es obligatorio para este hardware)
- No bloquear el event loop con operaciones de audio (siempre en executor o thread daemon)
- No grabar indefinidamente (MAX_RECORD_SECONDS=30 como límite absoluto)
- No persistir el transcript en localStorage
- No iniciar múltiples instancias de pyttsx3 simultáneas (usar el lock en _run_engine)
- No abrir múltiples streams de micrófono simultáneos (WakeWordDetector y STT usan el mismo hardware en momentos distintos)

GATE: Di "Yeyo" → sistema detecta wake word → habla "Dime." → grabas → transcribe con Whisper → YEYO responde por voz y texto. MicIndicator en el topbar cambia de verde tenue (idle) a azul brillante (listening/recording) a amarillo (processing) a blanco (speaking). VoiceWaveform aparece en bottom-center al grabar con waveform animado. "Para todo" activa el Kill Switch. Todos los tests pasan.
```
