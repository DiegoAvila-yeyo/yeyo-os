## ═══════════════════════════════════════
## MICRO-FASE 5.6 — Video Node (Subtitles + TTS)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.6-1 [VSCODE] — Subtítulos con Whisper y narración con TTS

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.6 de Capa 5 (Órganos): añadir generación de subtítulos con Whisper y narración TTS al Video Node.

CONTEXTO:
- Micro-fase 5.5 completada: VideoNode con FFmpeg + validación de seguridad
- Whisper: transcribe audio a subtítulos SRT (corre en CPU, NO en GPU VRAM)
- TTS: text-to-speech con piper-tts (CPU)
- NVENC: encoding por hardware usa circuito dedicado, NO VRAM
- Estos servicios NO compiten con Ollama por VRAM
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/video/subtitles.py:

   Ruta: ~/yeyo-os/src/nodes/video/subtitles.py
   Contenido:

   """
   YeyoOS — Video Subtitles (Whisper) + TTS (Piper)
   Micro-fase 5.6 — Capa 5: Órganos

   Whisper transcribe audio → SRT subtítulos (CPU, no GPU VRAM).
   Piper-TTS genera narración desde texto (CPU).
   NVENC encoding usa hardware dedicado, no VRAM.
   """

   import asyncio
   import tempfile
   from pathlib import Path
   from typing import Optional
   from dataclasses import dataclass, field
   from datetime import datetime, timezone


   @dataclass
   class SubtitleEntry:
       """Entrada de subtítulo SRT."""
       index: int
       start_time: str  # HH:MM:SS,mmm
       end_time: str
       text: str


   @dataclass
   class SubtitleResult:
       """Resultado de generación de subtítulos."""
       entries: list[SubtitleEntry]
       srt_content: str
       language: str
       duration_seconds: float


   class WhisperSubtitleService:
       """
       Genera subtítulos SRT desde audio usando Whisper.
       IMPORTANTE: Corre en CPU, NO usa GPU VRAM.
       """

       def __init__(self, model_size: str = "base"):
           """
           model_size: tiny, base, small, medium, large
           Para 16GB RAM, 'base' es recomendado.
           """
           self._model_size = model_size
           self._model = None

       async def transcribe(self, audio_path: str, language: str = "es") -> SubtitleResult:
           """
           Transcribe audio a subtítulos SRT.
           Ejecuta en CPU — no compite con Ollama por VRAM.
           """
           if self._model is None:
               self._model = await self._load_model()

           result = await asyncio.to_thread(
               self._run_whisper, audio_path, language
           )

           entries = self._parse_segments(result["segments"])
           srt_content = self._generate_srt(entries)

           return SubtitleResult(
               entries=entries,
               srt_content=srt_content,
               language=language,
               duration_seconds=result.get("duration", 0.0),
           )

       async def _load_model(self):
           """Carga modelo Whisper (CPU only)."""
           import whisper
           return whisper.load_model(self._model_size, device="cpu")

       def _run_whisper(self, audio_path: str, language: str) -> dict:
           """Ejecuta Whisper en thread separado (CPU)."""
           result = self._model.transcribe(
               audio_path,
               language=language,
               task="transcribe",
           )
           return result

       def _parse_segments(self, segments: list[dict]) -> list[SubtitleEntry]:
           """Convierte segmentos de Whisper a SubtitleEntry."""
           entries = []
           for i, seg in enumerate(segments, start=1):
               entries.append(SubtitleEntry(
                   index=i,
                   start_time=self._format_time(seg["start"]),
                   end_time=self._format_time(seg["end"]),
                   text=seg["text"].strip(),
               ))
           return entries

       def _format_time(self, seconds: float) -> str:
           """Convierte segundos a formato SRT (HH:MM:SS,mmm)."""
           h = int(seconds // 3600)
           m = int((seconds % 3600) // 60)
           s = int(seconds % 60)
           ms = int((seconds % 1) * 1000)
           return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

       def _generate_srt(self, entries: list[SubtitleEntry]) -> str:
           """Genera contenido SRT desde entries."""
           lines = []
           for entry in entries:
               lines.append(str(entry.index))
               lines.append(f"{entry.start_time} --> {entry.end_time}")
               lines.append(entry.text)
               lines.append("")
           return "\n".join(lines)

       async def save_srt(self, result: SubtitleResult, output_path: str) -> str:
           """Guarda subtítulos en archivo SRT."""
           path = Path(output_path)
           path.write_text(result.srt_content, encoding="utf-8")
           return str(path)


   class PiperTTSService:
       """
       Text-to-Speech con Piper-TTS.
       IMPORTANTE: Corre en CPU, NO usa GPU VRAM.
       """

       def __init__(self, voice: str = "es_ES-mls_9972-low"):
           self._voice = voice

       async def generate_audio(
           self, text: str, output_path: str, speed: float = 1.0
       ) -> dict:
           """
           Genera audio desde texto con Piper-TTS.
           Ejecuta en CPU — no compite con Ollama por VRAM.
           """
           try:
               process = await asyncio.create_subprocess_exec(
                   "piper",
                   "--model", self._voice,
                   "--output_file", output_path,
                   stdin=asyncio.subprocess.PIPE,
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )

               stdout, stderr = await asyncio.wait_for(
                   process.communicate(input=text.encode("utf-8")),
                   timeout=120,
               )

               if process.returncode == 0:
                   return {
                       "output_path": output_path,
                       "text_length": len(text),
                       "voice": self._voice,
                   }
               else:
                   return {"error": f"Piper TTS error: {stderr.decode()}"}

           except FileNotFoundError:
               return {"error": "Piper TTS no instalado. Instalar: pip install piper-tts"}
           except asyncio.TimeoutError:
               return {"error": "TTS timeout: generación excedió 2 minutos"}

       async def list_voices(self) -> list[str]:
           """Lista voces disponibles."""
           try:
               process = await asyncio.create_subprocess_exec(
                   "piper", "--list-voices",
                   stdout=asyncio.subprocess.PIPE,
                   stderr=asyncio.subprocess.PIPE,
               )
               stdout, _ = await process.communicate()
               return stdout.decode().strip().split("\n")
           except Exception:
               return [self._voice]

2. Crear archivo tests/unit/nodes/video/test_subtitles.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/video/test_subtitles.py
   Contenido:

   """Tests para Subtitles + TTS — Micro-fase 5.6"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.video.subtitles import (
       WhisperSubtitleService, PiperTTSService,
       SubtitleEntry, SubtitleResult,
   )


   class TestWhisperSubtitles:

       def test_format_time(self):
           service = WhisperSubtitleService()
           assert service._format_time(0.0) == "00:00:00,000"
           assert service._format_time(61.5) == "00:01:01,500"
           assert service._format_time(3661.123) == "01:01:01,123"

       def test_generate_srt(self):
           service = WhisperSubtitleService()
           entries = [
               SubtitleEntry(1, "00:00:00,000", "00:00:02,000", "Hola mundo"),
               SubtitleEntry(2, "00:00:02,000", "00:00:04,000", "Soy YeyoOS"),
           ]
           srt = service._generate_srt(entries)
           assert "1\n00:00:00,000 --> 00:00:02,000\nHola mundo" in srt
           assert "2\n00:00:02,000 --> 00:00:04,000\nSoy YeyoOS" in srt

       def test_parse_segments(self):
           service = WhisperSubtitleService()
           segments = [
               {"start": 0.0, "end": 2.0, "text": " Hola "},
               {"start": 2.0, "end": 4.0, "text": " Mundo "},
           ]
           entries = service._parse_segments(segments)
           assert len(entries) == 2
           assert entries[0].text == "Hola"
           assert entries[1].text == "Mundo"

       def test_model_runs_on_cpu(self):
           """Whisper DEBE correr en CPU, NO en GPU VRAM."""
           service = WhisperSubtitleService(model_size="base")
           # Verificar que el diseño especifica CPU
           assert service._model_size == "base"


   class TestPiperTTS:

       @pytest.mark.asyncio
       async def test_tts_error_when_not_installed(self):
           service = PiperTTSService()
           result = await service.generate_audio("test", "/tmp/test.wav")
           # Si piper no está instalado, debe retornar error gracefully
           assert "error" in result or "output_path" in result

       def test_default_voice_is_spanish(self):
           service = PiperTTSService()
           assert "es" in service._voice.lower()

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/video/test_subtitles.py -v

VERIFICAR:
- [ ] Whisper genera SRT con formato correcto
- [ ] Whisper corre en CPU (NO GPU VRAM)
- [ ] Piper TTS genera audio desde texto (CPU)
- [ ] Formato SRT correcto: index, timestamps, texto
- [ ] _format_time convierte segundos a HH:MM:SS,mmm
- [ ] NVENC mencionado como hardware dedicado (no VRAM)
- [ ] TODOS los tests pasan

SI FALLA:
- whisper no instalado: tests unitarios no lo necesitan (mockeable)
- piper no instalado: test gracefully handles FileNotFoundError
- Import error: verificar __init__.py

NO HACER:
- No instalar whisper/piper realmente (tests unitarios usan mocks o funciones puras)
- No usar GPU VRAM para Whisper ni TTS
- No implementar NVENC encoding completo

GATE: Whisper genera SRT en CPU, Piper TTS genera audio en CPU, formato SRT correcto, ninguno usa GPU VRAM, todos los tests pasan.
```
