"""
YeyoOS — Video Node API
POST /api/v1/video/process — Chat de IA que controla el editor de video
POST /api/v1/video/ingest  — Ingesta de videos de referencia (pose estimation)
"""

import asyncio
import json
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

logger = logging.getLogger("yeyoos.api.video")

router = APIRouter(prefix="/api/v1/video", tags=["video"])

_node_memory_service = None


def set_video_memory_service(ms):
    global _node_memory_service
    _node_memory_service = ms


# ========== Dependency stubs (inyectados desde main.py) ==========

async def get_ia_provider():
    return None

async def get_flash_memory():
    return None


# ========== Models ==========

class EditorState(BaseModel):
    currentTime: float = 0
    duration: float = 0
    playing: bool = False
    clips: list = []


class VideoProcessRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=1000)
    node_id: str = Field(default="default")
    editor_state: Optional[EditorState] = None


class VideoCommand(BaseModel):
    action: str  # split | delete | seek | play | pause | addClip
    time: Optional[float] = None
    clip_id: Optional[str] = None
    src: Optional[str] = None
    start_time: Optional[float] = None
    duration: Optional[float] = None


class VideoProcessResponse(BaseModel):
    respuesta: str
    commands: List[dict] = []


# ========== Endpoint ==========

@router.post("/process", response_model=VideoProcessResponse)
async def process_video(
    request: VideoProcessRequest,
    ia=Depends(get_ia_provider),
    memory=Depends(get_flash_memory),
):
    """
    IA de edición de video. Recibe prompt + estado del editor,
    responde con texto y lista de comandos para ejecutar sobre el editor.
    """
    if ia is None:
        raise HTTPException(status_code=503, detail="IA no disponible")

    # Contexto de memoria del nodo
    namespace = f"video:{request.node_id}:usuario"
    memory_context = ""
    if memory:
        try:
            async with memory.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT content FROM flash_memories
                    WHERE namespace = $1
                    ORDER BY accessed_at DESC
                    LIMIT 5
                    """,
                    namespace,
                )
            if rows:
                memory_context = "Contexto previo:\n" + "\n".join(
                    f"- {r['content']}" for r in rows
                )
        except Exception as e:
            logger.warning(f"No se pudo recuperar memoria: {e}")

    # Estado del editor como contexto
    editor_ctx = ""
    if request.editor_state:
        s = request.editor_state
        editor_ctx = (
            f"Estado del editor: tiempo={s.currentTime:.1f}s, "
            f"duración={s.duration:.1f}s, "
            f"clips={len(s.clips)}, "
            f"reproduciendo={s.playing}"
        )

    # Contexto de acciones humanas de referencia
    action_ctx = ""
    if _node_memory_service:
        try:
            action_ctx = await _node_memory_service.get_action_context(request.prompt, limit=3)
            if action_ctx:
                action_ctx = f"\nAcciones de referencia disponibles:\n{action_ctx}"
            video_ctx = await _node_memory_service.get_video_context(request.prompt, limit=3)
            if video_ctx:
                memory_context += f"\nConocimiento de video:\n{video_ctx}"
        except Exception as e:
            logger.warning(f"Error cargando contexto de acciones: {e}")

    system_prompt = """Eres un asistente de edición de video integrado en YeyoOS.
Puedes controlar directamente el editor de video mediante comandos JSON.

Cuando el usuario te pida hacer algo en el video, responde con:
1. Una explicación natural en español (campo "respuesta")
2. Una lista de comandos (campo "commands") para ejecutar

Comandos disponibles:
- {"action": "split", "time": 6.0}  — cortar DESPUÉS del segundo 5 (siempre usa N+1)
- {"action": "seek", "time": 3.0}   — mover el cursor al segundo 3
- {"action": "play"}                 — reproducir
- {"action": "pause"}                — pausar
- {"action": "delete", "clip_id": "abc123"} — eliminar un clip

REGLA IMPORTANTE para split: si el usuario dice "corta en el segundo N", usa time: N+1.
Ejemplo: "corta en el segundo 5" → {"action": "split", "time": 6.0}
Esto asegura que el segundo N queda incluido en el primer clip.

Responde SIEMPRE en este formato JSON exacto:
{"respuesta": "texto aquí", "commands": [...]}

Si no hay nada que hacer en el editor, usa commands: []"""

    user_prompt = f"{memory_context}\n{action_ctx}\n{editor_ctx}\n\nUsuario: {request.prompt}".strip()

    try:
        response = await ia.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.4,
        )

        # Parsear respuesta JSON
        content = response.content.strip()
        # Limpiar markdown si viene con ```json
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)
        respuesta = parsed.get("respuesta", content)
        commands = parsed.get("commands", [])

    except (json.JSONDecodeError, KeyError):
        # Si no pudo parsear JSON, devolver texto plano sin comandos
        respuesta = response.content.strip()
        commands = []

    # Guardar en memoria del nodo
    if memory:
        try:
            await memory.store(
                content=f"Usuario: {request.prompt}\nAsistente: {respuesta}",
                type="conversacion",
                source="video_node",
                namespace=namespace,
            )
        except Exception as e:
            logger.warning(f"No se pudo guardar memoria: {e}")

    return VideoProcessResponse(respuesta=respuesta, commands=commands)


# ─── Video Ingest — Pose Estimation Pipeline ─────────────────────────────────

@router.post("/ingest")
async def ingest_video(
    file: UploadFile = File(...),
    label: str = Form(""),
):
    """
    Ingesta un video de referencia: extrae frames, corre MediaPipe Pose,
    segmenta acciones y guarda memorias en video:acciones_humanas.
    """
    if not file.filename or not file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
        raise HTTPException(status_code=400, detail="Formato de video no soportado. Usa mp4, mov, avi, mkv o webm.")

    if _node_memory_service is None:
        raise HTTPException(status_code=503, detail="Memory service no inicializado")

    # Save uploaded file to temp
    with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from src.nodes.video.ingest import VideoIngestPipeline
        pipeline = VideoIngestPipeline(memory_service=_node_memory_service)
        result = await pipeline.ingest(tmp_path, label_hint=label)

        return {
            "status": "ok",
            "filename": file.filename,
            "duration_sec": round(result.duration_sec, 2),
            "fps": round(result.fps, 1),
            "total_frames": result.total_frames,
            "poses_extracted": result.poses_extracted,
            "segments": [
                {
                    "action": s.action_label,
                    "start_sec": round(s.start_sec, 2),
                    "end_sec": round(s.end_sec, 2),
                    "confidence": round(s.avg_confidence, 3),
                    "frame_count": s.frame_count,
                }
                for s in result.segments
            ],
            "memories_stored": result.memories_stored,
        }
    except Exception as e:
        logger.error(f"Error en ingesta de video: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.get("/actions")
async def get_actions(
    query: str = "",
    limit: int = 10,
):
    """Busca acciones humanas en la memoria por similitud semántica."""
    if _node_memory_service is None:
        raise HTTPException(status_code=503, detail="Memory service no inicializado")

    if not query:
        return {"actions": [], "count": 0}

    context = await _node_memory_service.get_action_context(query, limit=limit)
    actions = [line.lstrip("- ") for line in context.split("\n") if line.strip()] if context else []

    return {"actions": actions, "count": len(actions), "query": query}


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1 — CapCut Pro Backend: Video Editor Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

_VIDEO_OUTPUT_DIR = Path.home() / ".cache" / "yeyoos" / "videos"
_VIDEO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Filter & Transition Definitions ─────────────────────────────────────────

FILTER_MAP = {
    "sepia": {
        "ffmpeg": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
        "description": "Warm sepia tone effect",
    },
    "bw": {
        "ffmpeg": "hue=s=0",
        "description": "Black and white (desaturated)",
    },
    "vintage": {
        "ffmpeg": "curves=vintage",
        "description": "Vintage film color grading",
    },
    "cinematic": {
        "ffmpeg": "eq=contrast=1.3:brightness=-0.05:saturation=0.8,curves=m='0/0 0.5/0.4 1/1'",
        "description": "Cinematic look with enhanced contrast and color curves",
    },
}

TRANSITION_MAP = {
    "fade": {
        "xfade_name": "fadeblack",
        "description": "Classic fade through black transition",
    },
    "dissolve": {
        "xfade_name": "fade",
        "description": "Cross-dissolve between clips",
    },
    "wipe": {
        "xfade_name": "wipeleft",
        "description": "Wipe left transition",
    },
    "zoom": {
        "xfade_name": "zoomin",
        "description": "Zoom in transition",
    },
    "slide": {
        "xfade_name": "slideleft",
        "description": "Slide left transition",
    },
}

RESOLUTION_MAP = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160),
}


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class SubtitleEntryResponse(BaseModel):
    index: int
    start_time: str
    end_time: str
    text: str


class SubtitleGenerateResponse(BaseModel):
    entries: List[SubtitleEntryResponse]
    srt_content: str
    language: str
    duration_seconds: float


class FilterApplyRequest(BaseModel):
    input_path: str
    filter_name: str
    output_path: Optional[str] = None


class FilterApplyResponse(BaseModel):
    success: bool
    output_path: str
    filter_applied: str


class TransitionApplyRequest(BaseModel):
    clip_a_path: str
    clip_b_path: str
    transition_type: str
    duration: float = 1.0
    output_path: Optional[str] = None


class TransitionApplyResponse(BaseModel):
    success: bool
    output_path: str
    transition_applied: str


class ClipSpec(BaseModel):
    path: str
    start: float = 0.0
    end: float = -1.0
    track: str = "main"
    filters: List[str] = Field(default_factory=list)


class TransitionSpec(BaseModel):
    between: List[int]
    type: str
    duration: float = 1.0


class ExportRequest(BaseModel):
    clips: List[ClipSpec]
    subtitles_srt: Optional[str] = None
    transitions: List[TransitionSpec] = Field(default_factory=list)
    output_format: str = "mp4"
    resolution: str = "1080p"
    fps: int = 30


class ExportResponse(BaseModel):
    success: bool
    output_path: str
    duration_seconds: float
    resolution: str


class FilterInfo(BaseModel):
    name: str
    description: str
    ffmpeg_filter: str


class TransitionInfo(BaseModel):
    name: str
    description: str


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_video_duration(path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot read video file: {stderr.decode().strip()}",
        )
    try:
        return float(stdout.decode().strip())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot determine duration for: {path}",
        )


async def _run_ffmpeg(command: str, timeout: int = 300) -> str:
    """Validate and execute an FFmpeg command. Returns stderr output."""
    from src.nodes.video.ffmpeg_validator import FFmpegValidator

    validator = FFmpegValidator()
    result = validator.validate(command)
    if not result.is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"FFmpeg command rejected: {result.reason}",
        )

    proc = await asyncio.create_subprocess_shell(
        result.sanitized_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(
            status_code=504,
            detail=f"FFmpeg operation timed out after {timeout}s",
        )

    if proc.returncode != 0:
        err_lines = stderr.decode().strip().split("\n") if stderr else ["Unknown FFmpeg error"]
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg failed: {err_lines[-1]}",
        )
    return stderr.decode() if stderr else ""


# ─── Video Editor Endpoints ──────────────────────────────────────────────────

@router.post("/subtitles/generate", response_model=SubtitleGenerateResponse)
async def generate_subtitles(
    file: UploadFile = File(...),
    language: str = Form("es"),
):
    """Generate SRT subtitles from a video/audio file using Whisper."""
    allowed_exts = (
        ".mp4", ".mov", ".avi", ".mkv", ".webm",
        ".wav", ".mp3", ".flac", ".ogg", ".m4a",
    )
    if not file.filename or not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Use: {', '.join(allowed_exts)}",
        )

    with tempfile.NamedTemporaryFile(
        suffix=Path(file.filename).suffix, delete=False,
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from src.nodes.video.subtitles import WhisperSubtitleService

        whisper_svc = WhisperSubtitleService()
        result = await whisper_svc.transcribe(tmp_path, language=language)

        return SubtitleGenerateResponse(
            entries=[
                SubtitleEntryResponse(
                    index=e.index,
                    start_time=e.start_time,
                    end_time=e.end_time,
                    text=e.text,
                )
                for e in result.entries
            ],
            srt_content=result.srt_content,
            language=result.language,
            duration_seconds=result.duration_seconds,
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Whisper not installed. Run: pip install openai-whisper",
        )
    except Exception as e:
        logger.error(f"Subtitle generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/filter/apply", response_model=FilterApplyResponse)
async def apply_filter(request: FilterApplyRequest):
    """Apply a visual filter to a video file using FFmpeg."""
    if request.filter_name not in FILTER_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown filter '{request.filter_name}'. Available: {list(FILTER_MAP.keys())}",
        )

    input_path = Path(request.input_path)
    if not input_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Input file not found: {request.input_path}",
        )

    output_path = request.output_path or str(
        _VIDEO_OUTPUT_DIR / f"filtered_{request.filter_name}_{uuid.uuid4().hex[:8]}.mp4"
    )

    vf = FILTER_MAP[request.filter_name]["ffmpeg"]
    command = (
        f'ffmpeg -i "{request.input_path}" '
        f'-vf "{vf}" '
        f'-c:a copy "{output_path}"'
    )

    await _run_ffmpeg(command)

    return FilterApplyResponse(
        success=True,
        output_path=output_path,
        filter_applied=request.filter_name,
    )


@router.post("/transition/apply", response_model=TransitionApplyResponse)
async def apply_transition(request: TransitionApplyRequest):
    """Apply a transition between two video clips using FFmpeg xfade."""
    if request.transition_type not in TRANSITION_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown transition '{request.transition_type}'. Available: {list(TRANSITION_MAP.keys())}",
        )

    for label, path_str in [
        ("clip_a", request.clip_a_path),
        ("clip_b", request.clip_b_path),
    ]:
        if not Path(path_str).exists():
            raise HTTPException(
                status_code=404,
                detail=f"{label} not found: {path_str}",
            )

    output_path = request.output_path or str(
        _VIDEO_OUTPUT_DIR
        / f"transition_{request.transition_type}_{uuid.uuid4().hex[:8]}.mp4"
    )

    clip_a_dur = await _get_video_duration(request.clip_a_path)
    trans_dur = min(request.duration, clip_a_dur * 0.9)
    offset = max(0, clip_a_dur - trans_dur)

    xfade_name = TRANSITION_MAP[request.transition_type]["xfade_name"]
    filter_complex = (
        f"[0:v][1:v]xfade=transition={xfade_name}"
        f":duration={trans_dur}:offset={offset}"
    )

    command = (
        f'ffmpeg -i "{request.clip_a_path}" -i "{request.clip_b_path}" '
        f'-filter_complex "{filter_complex}" '
        f'-c:a copy "{output_path}"'
    )

    await _run_ffmpeg(command)

    return TransitionApplyResponse(
        success=True,
        output_path=output_path,
        transition_applied=request.transition_type,
    )


@router.post("/export", response_model=ExportResponse)
async def export_video(request: ExportRequest):
    """Export a multi-clip project with filters, transitions, and subtitles."""
    if not request.clips:
        raise HTTPException(status_code=400, detail="No clips provided")

    for i, clip in enumerate(request.clips):
        if not Path(clip.path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"Clip {i} not found: {clip.path}",
            )

    if request.resolution not in RESOLUTION_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown resolution '{request.resolution}'. Available: {list(RESOLUTION_MAP.keys())}",
        )

    res_w, res_h = RESOLUTION_MAP[request.resolution]
    output_path = str(
        _VIDEO_OUTPUT_DIR / f"export_{uuid.uuid4().hex[:8]}.{request.output_format}"
    )

    temp_files: List[str] = []

    try:
        if len(request.clips) == 1 and not request.transitions:
            await _export_single_clip(
                request.clips[0], request, output_path, res_w, res_h,
            )
        else:
            await _export_multi_clip(
                request, output_path, res_w, res_h, temp_files,
            )

        # Burn subtitles if provided
        if request.subtitles_srt:
            output_path = await _burn_subtitles(
                output_path, request.subtitles_srt, temp_files,
            )

        duration = await _get_video_duration(output_path)

        return ExportResponse(
            success=True,
            output_path=output_path,
            duration_seconds=round(duration, 2),
            resolution=request.resolution,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        for f in temp_files:
            Path(f).unlink(missing_ok=True)


@router.get("/filters")
async def list_filters():
    """List all available video filters with descriptions."""
    return [
        FilterInfo(
            name=name,
            description=info["description"],
            ffmpeg_filter=info["ffmpeg"],
        )
        for name, info in FILTER_MAP.items()
    ]


@router.get("/transitions")
async def list_transitions():
    """List all available video transitions with descriptions."""
    return [
        TransitionInfo(name=name, description=info["description"])
        for name, info in TRANSITION_MAP.items()
    ]


# ─── Export Helpers ───────────────────────────────────────────────────────────

async def _export_single_clip(
    clip: ClipSpec,
    request: ExportRequest,
    output_path: str,
    res_w: int,
    res_h: int,
) -> None:
    """Export a single clip with optional trim and filters."""
    vf_parts = [
        f"scale={res_w}:{res_h}:force_original_aspect_ratio=decrease,"
        f"pad={res_w}:{res_h}:(ow-iw)/2:(oh-ih)/2",
    ]
    for f_name in clip.filters:
        if f_name in FILTER_MAP:
            vf_parts.append(FILTER_MAP[f_name]["ffmpeg"])
    vf = ",".join(vf_parts)

    trim_flags = ""
    if clip.start > 0:
        trim_flags += f" -ss {clip.start}"
    if clip.end > 0:
        trim_flags += f" -to {clip.end}"

    command = (
        f'ffmpeg{trim_flags} -i "{clip.path}" '
        f'-vf "{vf}" '
        f"-c:v libx264 -crf 23 -preset medium -pix_fmt yuv420p "
        f'-r {request.fps} -c:a copy "{output_path}"'
    )
    await _run_ffmpeg(command, timeout=600)


async def _export_multi_clip(
    request: ExportRequest,
    output_path: str,
    res_w: int,
    res_h: int,
    temp_files: List[str],
) -> None:
    """Export multiple clips with optional transitions."""
    # Step 1: Normalize each clip (trim + filter + scale)
    processed_clips: List[str] = []
    for i, clip in enumerate(request.clips):
        clip_out = str(
            _VIDEO_OUTPUT_DIR / f"_clip_{i}_{uuid.uuid4().hex[:8]}.mp4"
        )
        temp_files.append(clip_out)

        vf_parts = [
            f"scale={res_w}:{res_h}:force_original_aspect_ratio=decrease,"
            f"pad={res_w}:{res_h}:(ow-iw)/2:(oh-ih)/2",
        ]
        for f_name in clip.filters:
            if f_name in FILTER_MAP:
                vf_parts.append(FILTER_MAP[f_name]["ffmpeg"])
        vf = ",".join(vf_parts)

        trim_flags = ""
        if clip.start > 0:
            trim_flags += f" -ss {clip.start}"
        if clip.end > 0:
            trim_flags += f" -to {clip.end}"

        command = (
            f'ffmpeg{trim_flags} -i "{clip.path}" '
            f'-vf "{vf}" '
            f"-c:v libx264 -crf 23 -preset medium -pix_fmt yuv420p "
            f'-r {request.fps} -an "{clip_out}"'
        )
        await _run_ffmpeg(command, timeout=600)
        processed_clips.append(clip_out)

    # Build transition lookup: (idx_a, idx_b) → TransitionSpec
    trans_lookup = {}
    for t in request.transitions:
        if len(t.between) == 2:
            trans_lookup[(t.between[0], t.between[1])] = t

    # Step 2: Chain clips with transitions or concat
    if not request.transitions:
        await _concat_clips(processed_clips, output_path, temp_files)
    else:
        current = processed_clips[0]
        for i in range(1, len(processed_clips)):
            trans = trans_lookup.get((i - 1, i))
            step_out = str(
                _VIDEO_OUTPUT_DIR / f"_chain_{i}_{uuid.uuid4().hex[:8]}.mp4"
            )
            temp_files.append(step_out)

            if trans and trans.type in TRANSITION_MAP:
                cur_dur = await _get_video_duration(current)
                trans_dur = min(trans.duration, cur_dur * 0.9)
                offset = max(0, cur_dur - trans_dur)
                xfade_name = TRANSITION_MAP[trans.type]["xfade_name"]
                filter_complex = (
                    f"[0:v][1:v]xfade=transition={xfade_name}"
                    f":duration={trans_dur}:offset={offset}"
                )
                command = (
                    f'ffmpeg -i "{current}" -i "{processed_clips[i]}" '
                    f'-filter_complex "{filter_complex}" '
                    f'-pix_fmt yuv420p "{step_out}"'
                )
            else:
                # No transition — simple concat via concat demuxer
                concat_file = str(
                    _VIDEO_OUTPUT_DIR / f"_cat_{uuid.uuid4().hex[:8]}.txt"
                )
                temp_files.append(concat_file)
                with open(concat_file, "w") as f:
                    f.write(f"file '{current}'\n")
                    f.write(f"file '{processed_clips[i]}'\n")
                command = (
                    f'ffmpeg -f concat -safe 0 -i "{concat_file}" '
                    f'-c copy "{step_out}"'
                )

            await _run_ffmpeg(command, timeout=600)
            current = step_out

        import shutil
        shutil.copy2(current, output_path)


async def _concat_clips(
    clip_paths: List[str],
    output_path: str,
    temp_files: List[str],
) -> None:
    """Concatenate clips using FFmpeg concat demuxer."""
    concat_file = str(
        _VIDEO_OUTPUT_DIR / f"_concat_{uuid.uuid4().hex[:8]}.txt"
    )
    temp_files.append(concat_file)

    with open(concat_file, "w") as f:
        for path in clip_paths:
            f.write(f"file '{path}'\n")

    command = (
        f'ffmpeg -f concat -safe 0 -i "{concat_file}" '
        f'-c copy "{output_path}"'
    )
    await _run_ffmpeg(command, timeout=600)


async def _burn_subtitles(
    video_path: str,
    srt_content: str,
    temp_files: List[str],
) -> str:
    """Burn SRT subtitles into a video file."""
    srt_file = str(
        _VIDEO_OUTPUT_DIR / f"_subs_{uuid.uuid4().hex[:8]}.srt"
    )
    temp_files.append(srt_file)
    Path(srt_file).write_text(srt_content, encoding="utf-8")

    output_with_subs = str(
        _VIDEO_OUTPUT_DIR / f"_subbed_{uuid.uuid4().hex[:8]}.mp4"
    )
    # Original will be cleaned up; mark it
    temp_files.append(video_path)

    # Escape path for FFmpeg subtitles filter (colons and backslashes)
    escaped_srt = srt_file.replace("\\", "\\\\\\\\").replace(":", "\\\\:")

    command = (
        f'ffmpeg -i "{video_path}" '
        f"-vf \"subtitles='{escaped_srt}'\" "
        f'-c:a copy "{output_with_subs}"'
    )
    await _run_ffmpeg(command, timeout=600)
    return output_with_subs
