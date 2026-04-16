"""
YeyoOS — Storyboard "Disney Studio" API
Phase 2 — Backend CRUD + AI generation

Endpoints REST:
- POST   /api/v1/storyboard/              — crear storyboard
- GET    /api/v1/storyboard/              — listar storyboards
- GET    /api/v1/storyboard/{id}          — obtener storyboard con frames
- PUT    /api/v1/storyboard/{id}          — actualizar metadata
- DELETE /api/v1/storyboard/{id}          — eliminar storyboard + frames
- POST   /api/v1/storyboard/{id}/frames   — agregar frame
- PUT    /api/v1/storyboard/{id}/frames/{frame_id}    — actualizar frame
- DELETE /api/v1/storyboard/{id}/frames/{frame_id}    — eliminar frame
- PUT    /api/v1/storyboard/{id}/frames/reorder        — reordenar frames
- POST   /api/v1/storyboard/generate      — IA genera storyboard desde prompt
- POST   /api/v1/storyboard/{id}/export   — exportar storyboard como JSON
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("yeyoos.api.storyboard")

router = APIRouter(prefix="/api/v1/storyboard", tags=["storyboard"])


# ========== DB Pool (inyectado desde main.py) ==========

_pool = None
_ia_provider = None


def set_db_pool(pool):
    global _pool
    _pool = pool


def set_ia_provider(provider):
    global _ia_provider
    _ia_provider = provider


async def get_pool():
    if _pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return _pool


async def get_ia():
    if _ia_provider is None:
        raise HTTPException(status_code=503, detail="IA provider not available")
    return _ia_provider


# ========== Request Models ==========

class StoryboardCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")


class StoryboardUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None


class FrameCreate(BaseModel):
    image_url: str = Field(default="")
    description: str = Field(default="")
    movement: str = Field(default="static", max_length=50)
    duration: float = Field(default=4.0, ge=0.1, le=300.0)
    camera: str = Field(default="static", max_length=50)
    emotion: str = Field(default="neutral", max_length=50)
    transition: str = Field(default="cut", max_length=50)
    audio_text: str = Field(default="")
    prompt_extra: str = Field(default="")
    sort_order: int = Field(default=0, ge=0)


class FrameUpdate(BaseModel):
    image_url: Optional[str] = None
    description: Optional[str] = None
    movement: Optional[str] = Field(default=None, max_length=50)
    duration: Optional[float] = Field(default=None, ge=0.1, le=300.0)
    camera: Optional[str] = Field(default=None, max_length=50)
    emotion: Optional[str] = Field(default=None, max_length=50)
    transition: Optional[str] = Field(default=None, max_length=50)
    audio_text: Optional[str] = None
    prompt_extra: Optional[str] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class FrameReorderItem(BaseModel):
    frame_id: str
    sort_order: int


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)


# ========== Response Models ==========

class FrameResponse(BaseModel):
    id: str
    storyboard_id: str
    image_url: str
    description: str
    movement: str
    duration: float
    camera: str
    emotion: str
    transition: str
    audio_text: str
    prompt_extra: str
    sort_order: int
    created_at: Optional[str] = None


class StoryboardResponse(BaseModel):
    id: str
    name: str
    description: str
    frames: List[FrameResponse] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class StoryboardListItem(BaseModel):
    id: str
    name: str
    description: str
    frame_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class GenerateResponse(BaseModel):
    storyboard_id: str
    frames_generated: int


# ========== Helpers ==========

def _row_to_frame(row) -> dict:
    return {
        "id": str(row["id"]),
        "storyboard_id": str(row["storyboard_id"]),
        "image_url": row["image_url"] or "",
        "description": row["description"] or "",
        "movement": row["movement"] or "static",
        "duration": float(row["duration"]),
        "camera": row["camera"] or "static",
        "emotion": row["emotion"] or "neutral",
        "transition": row["transition"] or "cut",
        "audio_text": row["audio_text"] or "",
        "prompt_extra": row["prompt_extra"] or "",
        "sort_order": row["sort_order"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _row_to_storyboard(row, frames: list = None) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "description": row["description"] or "",
        "frames": frames or [],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


# ========== Endpoints ==========

@router.post("/", response_model=StoryboardResponse, status_code=201)
async def create_storyboard(body: StoryboardCreate, pool=Depends(get_pool)):
    """Create a new storyboard."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO storyboards (name, description)
            VALUES ($1, $2)
            RETURNING id, name, description, config, created_at, updated_at
            """,
            body.name,
            body.description,
        )
    return _row_to_storyboard(row)


@router.get("/", response_model=List[StoryboardListItem])
async def list_storyboards(pool=Depends(get_pool)):
    """List all storyboards with frame count."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT s.id, s.name, s.description, s.created_at, s.updated_at,
                   COUNT(f.id) AS frame_count
            FROM storyboards s
            LEFT JOIN storyboard_frames f ON f.storyboard_id = s.id
            GROUP BY s.id
            ORDER BY s.created_at DESC
            """
        )
    return [
        {
            "id": str(r["id"]),
            "name": r["name"],
            "description": r["description"] or "",
            "frame_count": r["frame_count"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]


@router.get("/{storyboard_id}", response_model=StoryboardResponse)
async def get_storyboard(storyboard_id: str, pool=Depends(get_pool)):
    """Get storyboard with all frames ordered by sort_order."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid storyboard ID")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, description, config, created_at, updated_at FROM storyboards WHERE id = $1",
            sb_uuid,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Storyboard not found")

        frames = await conn.fetch(
            """
            SELECT * FROM storyboard_frames
            WHERE storyboard_id = $1
            ORDER BY sort_order ASC, created_at ASC
            """,
            sb_uuid,
        )

    return _row_to_storyboard(row, [_row_to_frame(f) for f in frames])


@router.put("/{storyboard_id}", response_model=StoryboardResponse)
async def update_storyboard(storyboard_id: str, body: StoryboardUpdate, pool=Depends(get_pool)):
    """Update storyboard metadata."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid storyboard ID")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = []
    params = []
    idx = 1
    for key, val in updates.items():
        set_clauses.append(f"{key} = ${idx}")
        params.append(val)
        idx += 1

    set_clauses.append(f"updated_at = NOW()")
    params.append(sb_uuid)

    query = f"""
        UPDATE storyboards SET {', '.join(set_clauses)}
        WHERE id = ${idx}
        RETURNING id, name, description, config, created_at, updated_at
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Storyboard not found")

        frames = await conn.fetch(
            "SELECT * FROM storyboard_frames WHERE storyboard_id = $1 ORDER BY sort_order ASC",
            sb_uuid,
        )

    return _row_to_storyboard(row, [_row_to_frame(f) for f in frames])


@router.delete("/{storyboard_id}", status_code=204)
async def delete_storyboard(storyboard_id: str, pool=Depends(get_pool)):
    """Delete storyboard and cascade frames."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid storyboard ID")

    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM storyboards WHERE id = $1", sb_uuid)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Storyboard not found")


# ========== Frame Endpoints ==========

@router.post("/{storyboard_id}/frames", response_model=FrameResponse, status_code=201)
async def add_frame(storyboard_id: str, body: FrameCreate, pool=Depends(get_pool)):
    """Add a frame to a storyboard."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid storyboard ID")

    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM storyboards WHERE id = $1", sb_uuid)
        if not exists:
            raise HTTPException(status_code=404, detail="Storyboard not found")

        row = await conn.fetchrow(
            """
            INSERT INTO storyboard_frames
                (storyboard_id, image_url, description, movement, duration,
                 camera, emotion, transition, audio_text, prompt_extra, sort_order)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
            """,
            sb_uuid,
            body.image_url,
            body.description,
            body.movement,
            body.duration,
            body.camera,
            body.emotion,
            body.transition,
            body.audio_text,
            body.prompt_extra,
            body.sort_order,
        )

    return _row_to_frame(row)


@router.put("/{storyboard_id}/frames/{frame_id}", response_model=FrameResponse)
async def update_frame(storyboard_id: str, frame_id: str, body: FrameUpdate, pool=Depends(get_pool)):
    """Update a specific frame."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
        f_uuid = uuid.UUID(frame_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clauses = []
    params = []
    idx = 1
    for key, val in updates.items():
        set_clauses.append(f"{key} = ${idx}")
        params.append(val)
        idx += 1

    params.append(f_uuid)
    params.append(sb_uuid)

    query = f"""
        UPDATE storyboard_frames SET {', '.join(set_clauses)}
        WHERE id = ${idx} AND storyboard_id = ${idx + 1}
        RETURNING *
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Frame not found")

    return _row_to_frame(row)


@router.delete("/{storyboard_id}/frames/{frame_id}", status_code=204)
async def delete_frame(storyboard_id: str, frame_id: str, pool=Depends(get_pool)):
    """Delete a specific frame."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
        f_uuid = uuid.UUID(frame_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM storyboard_frames WHERE id = $1 AND storyboard_id = $2",
            f_uuid,
            sb_uuid,
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Frame not found")


@router.put("/{storyboard_id}/frames/reorder")
async def reorder_frames(
    storyboard_id: str,
    items: List[FrameReorderItem],
    pool=Depends(get_pool),
):
    """Reorder frames within a storyboard."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid storyboard ID")

    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT 1 FROM storyboards WHERE id = $1", sb_uuid)
        if not exists:
            raise HTTPException(status_code=404, detail="Storyboard not found")

        async with conn.transaction():
            for item in items:
                try:
                    f_uuid = uuid.UUID(item.frame_id)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid frame ID: {item.frame_id}")

                await conn.execute(
                    """
                    UPDATE storyboard_frames
                    SET sort_order = $1
                    WHERE id = $2 AND storyboard_id = $3
                    """,
                    item.sort_order,
                    f_uuid,
                    sb_uuid,
                )

        # Update storyboard timestamp
        await conn.execute("UPDATE storyboards SET updated_at = NOW() WHERE id = $1", sb_uuid)

    return {"status": "ok", "reordered": len(items)}


# ========== AI Generate ==========

STORYBOARD_SYSTEM_PROMPT = """You are a storyboard director. Given a story description, create a sequence of visual frames for an animated storyboard.

For each frame, provide a JSON object with these fields:
- description: visual description of the scene (1-2 sentences)
- movement: character movement type (static, walk, run, gesture, dance, jump, sit, turn)
- duration: frame duration in seconds (2.0 to 8.0)
- camera: camera angle (static, pan_left, pan_right, zoom_in, zoom_out, tilt_up, tilt_down, tracking)
- emotion: dominant emotion (neutral, happy, sad, angry, surprised, scared, excited, thoughtful)
- transition: transition to next frame (cut, fade, dissolve, wipe, slide)
- audio_text: narration or dialogue for this frame (can be empty)

Respond ONLY with a JSON array of frame objects. No extra text. Example:
[
  {"description": "A young girl stands at the edge of a forest", "movement": "static", "duration": 4.0, "camera": "zoom_in", "emotion": "thoughtful", "transition": "fade", "audio_text": "Once upon a time..."},
  {"description": "She takes her first step into the woods", "movement": "walk", "duration": 3.0, "camera": "tracking", "emotion": "excited", "transition": "cut", "audio_text": ""}
]

Create between 4 and 12 frames. Make the story visual and cinematic."""


@router.post("/generate", response_model=GenerateResponse)
async def generate_storyboard(body: GenerateRequest, pool=Depends(get_pool)):
    """AI generates a storyboard from a text prompt using Ollama."""
    if _ia_provider is None:
        raise HTTPException(status_code=503, detail="IA provider not available")

    try:
        response = await _ia_provider.generate(
            prompt=body.prompt,
            system=STORYBOARD_SYSTEM_PROMPT,
            temperature=0.7,
        )
    except Exception as e:
        logger.error(f"Ollama generation failed: {e}")
        raise HTTPException(status_code=502, detail="AI generation failed")

    # Parse response
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        frames_data = json.loads(content)
        if not isinstance(frames_data, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse AI response: {e}\nContent: {content[:500]}")
        raise HTTPException(status_code=502, detail="AI returned invalid format")

    # Create storyboard + frames in DB
    async with pool.acquire() as conn:
        async with conn.transaction():
            sb_row = await conn.fetchrow(
                """
                INSERT INTO storyboards (name, description)
                VALUES ($1, $2)
                RETURNING id
                """,
                f"AI: {body.prompt[:100]}",
                body.prompt,
            )
            sb_id = sb_row["id"]

            for idx, frame in enumerate(frames_data):
                await conn.execute(
                    """
                    INSERT INTO storyboard_frames
                        (storyboard_id, description, movement, duration,
                         camera, emotion, transition, audio_text, sort_order)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    sb_id,
                    frame.get("description", ""),
                    frame.get("movement", "static"),
                    float(frame.get("duration", 4.0)),
                    frame.get("camera", "static"),
                    frame.get("emotion", "neutral"),
                    frame.get("transition", "cut"),
                    frame.get("audio_text", ""),
                    idx,
                )

    return GenerateResponse(
        storyboard_id=str(sb_id),
        frames_generated=len(frames_data),
    )


# ========== Export ==========

@router.post("/{storyboard_id}/export")
async def export_storyboard(storyboard_id: str, pool=Depends(get_pool)):
    """Export storyboard as complete JSON (for Lab node)."""
    try:
        sb_uuid = uuid.UUID(storyboard_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid storyboard ID")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, description, config, created_at, updated_at FROM storyboards WHERE id = $1",
            sb_uuid,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Storyboard not found")

        frames = await conn.fetch(
            """
            SELECT * FROM storyboard_frames
            WHERE storyboard_id = $1
            ORDER BY sort_order ASC, created_at ASC
            """,
            sb_uuid,
        )

    config = row["config"] if row["config"] else {}

    return {
        "storyboard": {
            "id": str(row["id"]),
            "name": row["name"],
            "description": row["description"] or "",
            "config": config,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        },
        "frames": [_row_to_frame(f) for f in frames],
        "total_frames": len(frames),
        "total_duration": sum(float(f["duration"]) for f in frames),
    }
