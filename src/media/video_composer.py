"""
YeyoOS — Compositor de Video
Compone videos a partir de imágenes usando FFmpeg + moviepy.

Capacidades:
  - Secuencia de imágenes → video MP4
  - Agregar audio (voz, música) a un video
  - Subclips y concatenación
  - Exportación con codec H.264 (compatible con todos los reproductores)
"""

import os
import uuid
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("yeyoos.media.video")

# Directorio temporal para videos generados
_OUTPUT_DIR = Path.home() / ".cache" / "yeyoos" / "videos"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class VideoResult:
    success: bool
    file_path: str = ""
    duration_seconds: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    error: str = ""


class VideoComposerService:
    """
    Compositor de video que combina imágenes y audio con FFmpeg/moviepy.
    Todas las operaciones se ejecutan en un executor para no bloquear el event loop.
    """

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or _OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def images_to_video(
        self,
        image_paths: list[str],
        fps: float = 24.0,
        duration_per_image: float | None = None,
        audio_path: str | None = None,
        transition: str = "none",  # "none" | "fade"
    ) -> VideoResult:
        """
        Convierte una lista de imágenes en un video MP4.
        Si duration_per_image está definido, cada imagen dura ese tiempo en segundos.
        Si audio_path se provee, se sincroniza con el video.
        """
        if not image_paths:
            return VideoResult(success=False, error="No hay imágenes para componer")

        output_path = self.output_dir / f"video_{uuid.uuid4().hex[:8]}.mp4"

        def _compose():
            from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip

            dur = duration_per_image or (1.0 / fps if fps > 0 else 1.0)

            clips = []
            for img_path in image_paths:
                clip = ImageClip(img_path).set_duration(dur)
                if transition == "fade":
                    clip = clip.fadein(0.3).fadeout(0.3)
                clips.append(clip)

            video = concatenate_videoclips(clips, method="compose")

            if audio_path and Path(audio_path).exists():
                audio = AudioFileClip(audio_path)
                # Recorta o repite audio para que coincida con la duración del video
                if audio.duration > video.duration:
                    audio = audio.subclip(0, video.duration)
                video = video.set_audio(audio)

            video.write_videofile(
                str(output_path),
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=str(self.output_dir / "temp_audio.m4a"),
                remove_temp=True,
                logger=None,  # silencia la barra de progreso de moviepy
            )

            return video.duration, video.w, video.h

        try:
            loop = asyncio.get_event_loop()
            duration, w, h = await loop.run_in_executor(None, _compose)
            logger.info(f"Video generado: {output_path} ({duration:.1f}s) ✅")
            return VideoResult(
                success=True,
                file_path=str(output_path),
                duration_seconds=duration,
                width=w,
                height=h,
                fps=fps,
            )
        except Exception as e:
            logger.error(f"Error componiendo video: {e}")
            return VideoResult(success=False, error=str(e))

    async def add_audio_to_video(
        self,
        video_path: str,
        audio_path: str,
    ) -> VideoResult:
        """Agrega o reemplaza el audio de un video existente."""
        output_path = self.output_dir / f"video_audio_{uuid.uuid4().hex[:8]}.mp4"

        def _add_audio():
            from moviepy.editor import VideoFileClip, AudioFileClip
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            if audio.duration > video.duration:
                audio = audio.subclip(0, video.duration)
            video = video.set_audio(audio)
            video.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )
            return video.duration, video.w, video.h

        try:
            loop = asyncio.get_event_loop()
            duration, w, h = await loop.run_in_executor(None, _add_audio)
            return VideoResult(
                success=True,
                file_path=str(output_path),
                duration_seconds=duration,
                width=w,
                height=h,
                fps=0.0,
            )
        except Exception as e:
            logger.error(f"Error agregando audio: {e}")
            return VideoResult(success=False, error=str(e))

    async def concatenate_videos(
        self,
        video_paths: list[str],
    ) -> VideoResult:
        """Concatena múltiples videos en uno solo."""
        if not video_paths:
            return VideoResult(success=False, error="No hay videos para concatenar")

        output_path = self.output_dir / f"video_concat_{uuid.uuid4().hex[:8]}.mp4"

        def _concat():
            from moviepy.editor import VideoFileClip, concatenate_videoclips
            clips = [VideoFileClip(p) for p in video_paths]
            final = concatenate_videoclips(clips)
            final.write_videofile(
                str(output_path),
                codec="libx264",
                audio_codec="aac",
                logger=None,
            )
            return final.duration, final.w, final.h

        try:
            loop = asyncio.get_event_loop()
            duration, w, h = await loop.run_in_executor(None, _concat)
            logger.info(f"Videos concatenados: {output_path} ✅")
            return VideoResult(
                success=True,
                file_path=str(output_path),
                duration_seconds=duration,
                width=w,
                height=h,
                fps=0.0,
            )
        except Exception as e:
            logger.error(f"Error concatenando videos: {e}")
            return VideoResult(success=False, error=str(e))


# Instancia global (singleton)
_video_service: VideoComposerService | None = None


def get_video_service() -> VideoComposerService:
    global _video_service
    if _video_service is None:
        _video_service = VideoComposerService()
    return _video_service
