"""
YeyoOS — Video Generation Lab API
Phase 3 — Backend: project management + clip generation + concatenation

Endpoints REST:
- POST   /api/v1/lab/projects                       — create project from storyboard
- GET    /api/v1/lab/projects                       — list all projects
- GET    /api/v1/lab/projects/{id}                  — get project with clips
- PUT    /api/v1/lab/projects/{id}/config           — update project config
- DELETE /api/v1/lab/projects/{id}                  — delete project
- POST   /api/v1/lab/projects/{id}/generate         — start generation of all clips
- POST   /api/v1/lab/projects/{id}/clips/{idx}/generate — generate single clip
- POST   /api/v1/lab/projects/{id}/concatenate      — concatenate completed clips
- GET    /api/v1/lab/projects/{id}/download          — download final video
- POST   /api/v1/lab/projects/{id}/pause             — pause generation
- POST   /api/v1/lab/projects/{id}/resume            — resume generation
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("yeyoos.api.lab")

router = APIRouter(prefix="/api/v1/lab", tags=["lab"])


# ========== DB Pool & IA Provider (injected from main.py) ==========

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


# ========== Background Generation State ==========

_generation_tasks: dict[str, asyncio.Task] = {}
_generation_paused: dict[str, bool] = {}


# ========== Request Models ==========

class ProjectCreate(BaseModel):
    storyboard_id: str = Field(..., min_length=1)
    name: Optional[str] = Field(default=None, max_length=255)


class ProjectConfig(BaseModel):
    provider: Optional[str] = Field(default=None, max_length=50)
    quality: Optional[str] = Field(default=None, max_length=20)
    fps: Optional[int] = Field(default=None, ge=1, le=120)
    resolution: Optional[str] = Field(default=None, max_length=20)
    transition_default: Optional[str] = Field(default=None, max_length=50)
    duration_default: Optional[float] = Field(default=None, ge=0.5, le=60.0)
    consistency: Optional[str] = Field(default=None, max_length=20)


class GenerateClipRequest(BaseModel):
    frame_index: Optional[int] = None


class ConcatenateResponse(BaseModel):
    success: bool
    output_path: str = ""
    total_duration: float = 0.0


# ========== Response Models ==========

class ClipResponse(BaseModel):
    id: str
    frame_index: int
    status: str
    output_url: str
    duration: float
    provider: str
    error_message: str
    prompt: str = ""
    created_at: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    storyboard_id: Optional[str] = None
    name: str
    status: str
    config: dict = {}
    clips: List[ClipResponse] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProjectListItem(BaseModel):
    id: str
    storyboard_id: Optional[str] = None
    name: str
    status: str
    clip_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ========== Helpers ==========

def _row_to_clip(row) -> dict:
    return {
        "id": str(row["id"]),
        "frame_index": row["frame_index"],
        "status": row["status"] or "idle",
        "output_url": row["output_url"] or "",
        "duration": float(row["duration"]) if row["duration"] else 0.0,
        "provider": row["provider"] or "",
        "error_message": row["error_message"] or "",
        "prompt": row["prompt"] or "",
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


def _row_to_project(row, clips: list = None) -> dict:
    config = row["config"] if row["config"] else {}
    if isinstance(config, str):
        config = json.loads(config)
    return {
        "id": str(row["id"]),
        "storyboard_id": str(row["storyboard_id"]) if row["storyboard_id"] else None,
        "name": row["name"],
        "status": row["status"] or "idle",
        "config": config,
        "clips": clips or [],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def _fetch_project_with_clips(conn, project_uuid) -> dict:
    """Fetch a project row + its clips, return dict ready for response."""
    row = await conn.fetchrow(
        "SELECT * FROM lab_projects WHERE id = $1", project_uuid
    )
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    clips = await conn.fetch(
        "SELECT * FROM lab_clips WHERE project_id = $1 ORDER BY frame_index ASC",
        project_uuid,
    )
    return _row_to_project(row, [_row_to_clip(c) for c in clips])


def _parse_uuid(value: str, label: str = "ID") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label}")


# ========== Background Generation ==========

async def _generate_single_clip(project_id: uuid.UUID, clip_id: uuid.UUID, pool):
    """Generate a single clip (placeholder: simulates with sleep)."""
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE lab_clips SET status = 'generating' WHERE id = $1",
            clip_id,
        )
    try:
        # TODO: Replace with actual video generation API call (FAL/Replicate)
        # Example: result = await fal_client.generate_video(prompt=clip_prompt, ...)
        await asyncio.sleep(2)

        placeholder_url = f"https://placeholder.yeyoos.dev/clips/{clip_id}.mp4"
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE lab_clips
                SET status = 'completed', output_url = $1, duration = 4.0, provider = 'placeholder'
                WHERE id = $2
                """,
                placeholder_url,
                clip_id,
            )
    except asyncio.CancelledError:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE lab_clips SET status = 'idle' WHERE id = $1", clip_id
            )
        raise
    except Exception as e:
        logger.error(f"Clip generation failed ({clip_id}): {e}")
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE lab_clips SET status = 'error', error_message = $1 WHERE id = $2",
                str(e)[:500],
                clip_id,
            )


async def _generate_all_clips(project_id: str, pool):
    """Background task: generates clips one by one."""
    proj_uuid = uuid.UUID(project_id)
    try:
        async with pool.acquire() as conn:
            clips = await conn.fetch(
                """
                SELECT id, frame_index FROM lab_clips
                WHERE project_id = $1 AND status IN ('idle', 'error')
                ORDER BY frame_index ASC
                """,
                proj_uuid,
            )

        for clip_row in clips:
            # Check if paused
            if _generation_paused.get(project_id, False):
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE lab_projects SET status = 'paused', updated_at = NOW() WHERE id = $1",
                        proj_uuid,
                    )
                logger.info(f"Generation paused for project {project_id}")
                return

            await _generate_single_clip(proj_uuid, clip_row["id"], pool)

        # All clips done — update project status
        async with pool.acquire() as conn:
            error_count = await conn.fetchval(
                "SELECT COUNT(*) FROM lab_clips WHERE project_id = $1 AND status = 'error'",
                proj_uuid,
            )
            final_status = "error" if error_count > 0 else "completed"
            await conn.execute(
                "UPDATE lab_projects SET status = $1, updated_at = NOW() WHERE id = $2",
                final_status,
                proj_uuid,
            )
        logger.info(f"Generation finished for project {project_id}: {final_status}")

    except asyncio.CancelledError:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE lab_projects SET status = 'paused', updated_at = NOW() WHERE id = $1",
                proj_uuid,
            )
        logger.info(f"Generation cancelled for project {project_id}")
    except Exception as e:
        logger.error(f"Generation error for project {project_id}: {e}")
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE lab_projects SET status = 'error', updated_at = NOW() WHERE id = $1",
                proj_uuid,
            )
    finally:
        _generation_tasks.pop(project_id, None)
        _generation_paused.pop(project_id, None)


# ========== Endpoints ==========

@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, pool=Depends(get_pool)):
    """Create a new lab project from a storyboard."""
    sb_uuid = _parse_uuid(body.storyboard_id, "storyboard ID")

    async with pool.acquire() as conn:
        # Verify storyboard exists and fetch its frames
        sb_row = await conn.fetchrow(
            "SELECT id, name FROM storyboards WHERE id = $1", sb_uuid
        )
        if not sb_row:
            raise HTTPException(status_code=404, detail="Storyboard not found")

        frames = await conn.fetch(
            """
            SELECT id, description, sort_order, duration, prompt_extra
            FROM storyboard_frames
            WHERE storyboard_id = $1
            ORDER BY sort_order ASC, created_at ASC
            """,
            sb_uuid,
        )

        project_name = body.name or f"Lab: {sb_row['name']}"

        async with conn.transaction():
            proj_row = await conn.fetchrow(
                """
                INSERT INTO lab_projects (storyboard_id, name)
                VALUES ($1, $2)
                RETURNING *
                """,
                sb_uuid,
                project_name,
            )
            proj_id = proj_row["id"]

            # Create one clip per storyboard frame
            for idx, frame in enumerate(frames):
                prompt = frame["prompt_extra"] or frame["description"] or ""
                await conn.execute(
                    """
                    INSERT INTO lab_clips (project_id, frame_index, prompt)
                    VALUES ($1, $2, $3)
                    """,
                    proj_id,
                    idx,
                    prompt,
                )

        return await _fetch_project_with_clips(conn, proj_id)


@router.get("/projects", response_model=List[ProjectListItem])
async def list_projects(pool=Depends(get_pool)):
    """List all lab projects."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT p.id, p.storyboard_id, p.name, p.status,
                   p.created_at, p.updated_at,
                   COUNT(c.id) AS clip_count
            FROM lab_projects p
            LEFT JOIN lab_clips c ON c.project_id = p.id
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """
        )
    return [
        {
            "id": str(r["id"]),
            "storyboard_id": str(r["storyboard_id"]) if r["storyboard_id"] else None,
            "name": r["name"],
            "status": r["status"] or "idle",
            "clip_count": r["clip_count"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    ]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, pool=Depends(get_pool)):
    """Get a project with all its clips."""
    proj_uuid = _parse_uuid(project_id, "project ID")
    async with pool.acquire() as conn:
        return await _fetch_project_with_clips(conn, proj_uuid)


@router.put("/projects/{project_id}/config", response_model=ProjectResponse)
async def update_config(project_id: str, body: ProjectConfig, pool=Depends(get_pool)):
    """Update project configuration (merge with existing)."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No config fields to update")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT config FROM lab_projects WHERE id = $1", proj_uuid
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        current_config = row["config"] if row["config"] else {}
        if isinstance(current_config, str):
            current_config = json.loads(current_config)

        current_config.update(updates)

        await conn.execute(
            """
            UPDATE lab_projects SET config = $1::jsonb, updated_at = NOW()
            WHERE id = $2
            """,
            json.dumps(current_config),
            proj_uuid,
        )
        return await _fetch_project_with_clips(conn, proj_uuid)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str, pool=Depends(get_pool)):
    """Delete a project and all its clips (cascade)."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    # Cancel any running generation
    task = _generation_tasks.pop(project_id, None)
    if task and not task.done():
        task.cancel()
    _generation_paused.pop(project_id, None)

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM lab_projects WHERE id = $1", proj_uuid
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Project not found")


@router.post("/projects/{project_id}/generate", response_model=dict)
async def start_generation(project_id: str, pool=Depends(get_pool)):
    """Start background generation of all idle/errored clips."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    if project_id in _generation_tasks and not _generation_tasks[project_id].done():
        raise HTTPException(status_code=409, detail="Generation already in progress")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, status FROM lab_projects WHERE id = $1", proj_uuid
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        await conn.execute(
            "UPDATE lab_projects SET status = 'generating', updated_at = NOW() WHERE id = $1",
            proj_uuid,
        )

    _generation_paused[project_id] = False
    task = asyncio.create_task(_generate_all_clips(project_id, pool))
    _generation_tasks[project_id] = task

    return {"status": "generating", "project_id": project_id}


@router.post("/projects/{project_id}/clips/{frame_idx}/generate", response_model=ClipResponse)
async def generate_single(project_id: str, frame_idx: int, pool=Depends(get_pool)):
    """Generate (or re-generate) a single clip by frame index."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    async with pool.acquire() as conn:
        clip = await conn.fetchrow(
            "SELECT * FROM lab_clips WHERE project_id = $1 AND frame_index = $2",
            proj_uuid,
            frame_idx,
        )
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")

        # Reset clip before regenerating
        await conn.execute(
            "UPDATE lab_clips SET status = 'idle', error_message = '' WHERE id = $1",
            clip["id"],
        )

    await _generate_single_clip(proj_uuid, clip["id"], pool)

    async with pool.acquire() as conn:
        updated = await conn.fetchrow(
            "SELECT * FROM lab_clips WHERE id = $1", clip["id"]
        )
    return _row_to_clip(updated)


@router.post("/projects/{project_id}/concatenate", response_model=ConcatenateResponse)
async def concatenate_clips(project_id: str, pool=Depends(get_pool)):
    """Concatenate all completed clips into a final video."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM lab_projects WHERE id = $1", proj_uuid
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        clips = await conn.fetch(
            """
            SELECT output_url, duration FROM lab_clips
            WHERE project_id = $1 AND status = 'completed'
            ORDER BY frame_index ASC
            """,
            proj_uuid,
        )

    if not clips:
        raise HTTPException(status_code=400, detail="No completed clips to concatenate")

    video_paths = [c["output_url"] for c in clips if c["output_url"]]

    if not video_paths:
        raise HTTPException(status_code=400, detail="No clip files available")

    try:
        from src.media.video_composer import get_video_service
        composer = get_video_service()
        result = await composer.concatenate_videos(video_paths)

        if not result.success:
            raise HTTPException(status_code=500, detail=f"Concatenation failed: {result.error}")

        return ConcatenateResponse(
            success=True,
            output_path=result.file_path,
            total_duration=result.duration_seconds,
        )
    except ImportError:
        raise HTTPException(status_code=501, detail="Video composer not available")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Concatenation error: {e}")
        raise HTTPException(status_code=500, detail=f"Concatenation failed: {str(e)}")


@router.get("/projects/{project_id}/download")
async def download_video(project_id: str, pool=Depends(get_pool)):
    """Download the final concatenated video for a project."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM lab_projects WHERE id = $1", proj_uuid
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

    # Look for the most recent concatenated video in the output directory
    from src.media.video_composer import _OUTPUT_DIR
    output_dir = _OUTPUT_DIR

    # Find matching concat files
    concat_files = sorted(
        output_dir.glob("video_concat_*.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not concat_files:
        raise HTTPException(
            status_code=404,
            detail="No concatenated video found. Run /concatenate first.",
        )

    video_path = concat_files[0]
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    return FileResponse(
        path=str(video_path),
        media_type="video/mp4",
        filename=f"lab_{project_id[:8]}.mp4",
    )


@router.post("/projects/{project_id}/pause", response_model=dict)
async def pause_generation(project_id: str, pool=Depends(get_pool)):
    """Pause an in-progress generation."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status FROM lab_projects WHERE id = $1", proj_uuid
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

    if project_id not in _generation_tasks or _generation_tasks[project_id].done():
        raise HTTPException(status_code=409, detail="No active generation to pause")

    _generation_paused[project_id] = True
    return {"status": "pausing", "project_id": project_id}


@router.post("/projects/{project_id}/resume", response_model=dict)
async def resume_generation(project_id: str, pool=Depends(get_pool)):
    """Resume a paused generation."""
    proj_uuid = _parse_uuid(project_id, "project ID")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status FROM lab_projects WHERE id = $1", proj_uuid
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        if row["status"] != "paused":
            raise HTTPException(status_code=409, detail="Project is not paused")

    if project_id in _generation_tasks and not _generation_tasks[project_id].done():
        raise HTTPException(status_code=409, detail="Generation already running")

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE lab_projects SET status = 'generating', updated_at = NOW() WHERE id = $1",
            proj_uuid,
        )

    _generation_paused[project_id] = False
    task = asyncio.create_task(_generate_all_clips(project_id, pool))
    _generation_tasks[project_id] = task

    return {"status": "generating", "project_id": project_id}
