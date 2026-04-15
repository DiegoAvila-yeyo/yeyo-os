"""
YeyoOS — Video Node API
POST /api/v1/video/process — Chat de IA que controla el editor de video
POST /api/v1/video/ingest  — Ingesta de videos de referencia (pose estimation)
"""

import json
import logging
import tempfile
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
