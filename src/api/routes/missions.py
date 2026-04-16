"""
YeyoOS — Missions Bridge API Routes
Bridge between Observatory (findings) and Workshop (execution pipeline).
"""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("yeyoos.api.missions")

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])

# ========== Dependency Injection ==========

_pool = None


def set_db_pool(pool):
    global _pool
    _pool = pool


async def get_pool():
    if _pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return _pool


# ========== Pydantic Models ==========


class MissionBridgeCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    origin: str = Field(default="user")  # 'observatory' | 'user'
    created_by: str = Field(default="user", max_length=50)
    finding: str = Field(default="")
    analysis: str = Field(default="")
    strategy: str = Field(default="")
    spec: Optional[dict] = None
    observatory_task_id: Optional[str] = None


class MissionBridgeResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    origin: str = "user"
    created_by: str = "user"
    finding: str = ""
    analysis: str = ""
    strategy: str = ""
    status: str = "pending"
    spec: dict = {}
    created_at: Optional[str] = None


class MissionProgressResponse(BaseModel):
    id: str
    title: str
    origin: str
    created_by: str
    finding: str = ""
    analysis: str = ""
    strategy: str = ""
    status: str
    spec: dict = {}
    gates: list = []
    created_at: Optional[str] = None


# ========== Helper ==========


def _dt_str(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


def _safe_json(val):
    """Parse JSON from DB value safely."""
    if val is None:
        return {}
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return {}
    return val


def _row_to_response(row) -> MissionBridgeResponse:
    return MissionBridgeResponse(
        id=str(row["id"]),
        title=row["title"],
        description=row.get("description", "") or "",
        origin=row.get("origin", "user") or "user",
        created_by=row.get("created_by", "user") or "user",
        finding=row.get("finding", "") or "",
        analysis=row.get("analysis", "") or "",
        strategy=row.get("strategy", "") or "",
        status=row.get("status", "pending") or "pending",
        spec=_safe_json(row.get("spec")),
        created_at=_dt_str(row.get("created_at")),
    )


# ========== Endpoints ==========


@router.post("", response_model=MissionBridgeResponse, status_code=201)
async def create_mission(body: MissionBridgeCreate, pool=Depends(get_pool)):
    """Create a mission — from Observatory finding or user."""
    spec_json = json.dumps(body.spec) if body.spec else "{}"
    obs_task_id = UUID(body.observatory_task_id) if body.observatory_task_id else None

    row = await pool.fetchrow(
        """
        INSERT INTO workshop_missions
            (title, description, origin, created_by, finding, analysis, strategy,
             spec, observatory_task_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9)
        RETURNING id, title, description, origin, created_by, finding, analysis,
                  strategy, status, spec, created_at
        """,
        body.title,
        body.description,
        body.origin,
        body.created_by,
        body.finding,
        body.analysis,
        body.strategy,
        spec_json,
        obs_task_id,
    )

    return _row_to_response(row)


@router.get("", response_model=list[MissionBridgeResponse])
async def list_missions(
    status: Optional[str] = Query(None),
    origin: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    pool=Depends(get_pool),
):
    """List all missions, filterable by status and origin."""
    query = """
        SELECT id, title, description, origin, created_by, finding, analysis,
               strategy, status, spec, created_at
        FROM workshop_missions WHERE 1=1
    """
    params: list = []
    idx = 1

    if status:
        query += f" AND status = ${idx}"
        params.append(status)
        idx += 1
    if origin:
        query += f" AND origin = ${idx}"
        params.append(origin)
        idx += 1

    query += f" ORDER BY created_at DESC LIMIT ${idx}"
    params.append(limit)

    rows = await pool.fetch(query, *params)
    return [_row_to_response(r) for r in rows]


@router.get("/{mission_id}", response_model=MissionProgressResponse)
async def get_mission(mission_id: str, pool=Depends(get_pool)):
    """Get mission details including Observatory context + Workshop gates."""
    row = await pool.fetchrow(
        """
        SELECT id, title, description, origin, created_by, finding, analysis,
               strategy, status, spec, created_at
        FROM workshop_missions WHERE id = $1::uuid
        """,
        mission_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Mission not found")

    gates = await pool.fetch(
        """
        SELECT gate_number, gate_name, status, output, duration_ms, attempts
        FROM workshop_gates WHERE mission_id = $1::uuid
        ORDER BY gate_number
        """,
        mission_id,
    )

    return MissionProgressResponse(
        id=str(row["id"]),
        title=row["title"],
        origin=row.get("origin", "user") or "user",
        created_by=row.get("created_by", "user") or "user",
        finding=row.get("finding", "") or "",
        analysis=row.get("analysis", "") or "",
        strategy=row.get("strategy", "") or "",
        status=row.get("status", "pending") or "pending",
        spec=_safe_json(row.get("spec")),
        gates=[
            {
                "gate_number": g["gate_number"],
                "gate_name": g["gate_name"],
                "status": g["status"],
                "output": (g["output"] or "")[:500],
                "duration_ms": g["duration_ms"],
                "attempts": g["attempts"],
            }
            for g in gates
        ],
        created_at=_dt_str(row.get("created_at")),
    )


@router.put("/{mission_id}/approve", response_model=MissionBridgeResponse)
async def approve_mission(
    mission_id: str,
    spec: Optional[dict] = None,
    pool=Depends(get_pool),
):
    """Approve mission and optionally set/update spec. Status → spec_review."""
    if spec is not None:
        row = await pool.fetchrow(
            """
            UPDATE workshop_missions
            SET status = 'spec_review', spec = $2::jsonb, updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING id, title, description, origin, created_by, finding, analysis,
                      strategy, status, spec, created_at
            """,
            mission_id,
            json.dumps(spec),
        )
    else:
        row = await pool.fetchrow(
            """
            UPDATE workshop_missions
            SET status = 'spec_review', updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING id, title, description, origin, created_by, finding, analysis,
                      strategy, status, spec, created_at
            """,
            mission_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Mission not found")

    return _row_to_response(row)


@router.post("/{mission_id}/send-to-workshop")
async def send_to_workshop(mission_id: str, pool=Depends(get_pool)):
    """
    Send mission to Workshop pipeline.
    Updates origin to ensure Workshop knows it came from the bridge,
    then triggers execution via the Workshop pipeline.
    """
    row = await pool.fetchrow(
        "SELECT id, title, spec, status FROM workshop_missions WHERE id = $1::uuid",
        mission_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Mission not found")

    if row["status"] not in ("pending", "spec_review"):
        raise HTTPException(
            status_code=409,
            detail=f"Mission in status '{row['status']}' cannot be sent to workshop",
        )

    # Update status to designing (Workshop will pick it up)
    await pool.execute(
        """
        UPDATE workshop_missions
        SET status = 'spec_review', updated_at = NOW()
        WHERE id = $1::uuid
        """,
        mission_id,
    )

    return {
        "status": "sent_to_workshop",
        "mission_id": mission_id,
        "message": "Mission is ready for Workshop execution. Use POST /api/v1/workshop/missions/{id}/execute to start the pipeline.",
    }


@router.get("/{mission_id}/progress", response_model=MissionProgressResponse)
async def get_mission_progress(mission_id: str, pool=Depends(get_pool)):
    """Get combined progress: Observatory context + Workshop gates."""
    return await get_mission(mission_id, pool)
