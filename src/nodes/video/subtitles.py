"""
YeyoOS — Video Subtitles (Whisper) + TTS (Piper)
Micro-fase 5.6 — Capa 5: Órganos

Whisper transcribe audio → SRT subtítulos (CPU, no GPU VRAM).
Piper-TTS genera narración desde texto (CPU).
NVENC encoding usa hardware dedicado, no VRAM.
"""

import asyncio
from pathlib import Path
from dataclasses import dataclass, field


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
        self._model_size = model_size
        self._model = None

    async def transcribe(self, audio_path: str, language: str = "es") -> SubtitleResult:
        """Transcribe audio a subtítulos SRT. Ejecuta en CPU."""
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
        """Genera audio desde texto con Piper-TTS. Ejecuta en CPU."""
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
