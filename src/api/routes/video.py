"""
YeyoOS — Video Node API
POST /api/v1/video/process — Chat de IA que controla el editor de video
"""

import json
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("yeyoos.api.video")

router = APIRouter(prefix="/api/v1/video", tags=["video"])


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

    user_prompt = f"{memory_context}\n{editor_ctx}\n\nUsuario: {request.prompt}".strip()

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
