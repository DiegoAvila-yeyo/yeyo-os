"""
YeyoOS — Workshop API Routes
16 Anti-Slop Gates pipeline for code generation and validation.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from src.api.websocket import manager
from src.workshop.pipeline import WorkshopPipeline, MissionSpec, GATE_DEFINITIONS

logger = logging.getLogger("yeyoos.api.workshop")

router = APIRouter(prefix="/api/v1/workshop", tags=["workshop"])


# ========== Dependency Injection (set from main.py) ==========

_pool = None
_ia_provider = None
_ws_manager = manager


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


# ========== Active Pipelines Registry ==========

_pipelines: dict[str, WorkshopPipeline] = {}
_pipeline_tasks: dict[str, asyncio.Task] = {}


# ========== Request Models ==========


class SpecModel(BaseModel):
    inputs: list[dict] = Field(default_factory=list)
    outputs: list[dict] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    error_handling: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)


class MissionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    spec: SpecModel = Field(default_factory=SpecModel)


# ========== Response Models ==========


class GateResponse(BaseModel):
    gate_number: int
    gate_name: str
    status: str
    output: str = ""
    duration_ms: int = 0
    attempts: int = 0


class MissionResponse(BaseModel):
    id: str
    title: str
    description: str = ""
    status: str
    origin: str = "user"
    spec: dict = {}
    gates: list[GateResponse] = []
    code_files: list[dict] = []
    test_results: dict = {}
    security_report: dict = {}
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MissionListItem(BaseModel):
    id: str
    title: str
    status: str
    origin: str = "user"
    gate_count: int = 0
    created_at: Optional[str] = None


# ========== Helper ==========


def _dt_str(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


# ========== Endpoints ==========


@router.post("/missions", response_model=MissionResponse, status_code=201)
async def create_mission(body: MissionCreate, pool=Depends(get_pool)):
    """Create a new workshop mission with spec."""
    spec_json = json.dumps(body.spec.model_dump())

    row = await pool.fetchrow(
        """
        INSERT INTO workshop_missions (title, description, spec)
        VALUES ($1, $2, $3::jsonb)
        RETURNING id, title, description, status, origin, spec, code_files,
                  test_results, security_report, created_at, updated_at
        """,
        body.title, body.description, spec_json,
    )

    return MissionResponse(
        id=str(row["id"]),
        title=row["title"],
        description=row["description"],
        status=row["status"],
        origin=row["origin"],
        spec=json.loads(row["spec"]) if isinstance(row["spec"], str) else row["spec"],
        code_files=json.loads(row["code_files"]) if isinstance(row["code_files"], str) else row["code_files"],
        test_results=json.loads(row["test_results"]) if isinstance(row["test_results"], str) else row["test_results"],
        security_report=json.loads(row["security_report"]) if isinstance(row["security_report"], str) else row["security_report"],
        created_at=_dt_str(row["created_at"]),
        updated_at=_dt_str(row["updated_at"]),
    )


@router.get("/missions", response_model=list[MissionListItem])
async def list_missions(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    pool=Depends(get_pool),
):
    """List all workshop missions."""
    if status:
        rows = await pool.fetch(
            """
            SELECT m.id, m.title, m.status, m.origin, m.created_at,
                   (SELECT COUNT(*) FROM workshop_gates g WHERE g.mission_id = m.id) as gate_count
            FROM workshop_missions m
            WHERE m.status = $1
            ORDER BY m.created_at DESC
            LIMIT $2 OFFSET $3
            """,
            status, limit, offset,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT m.id, m.title, m.status, m.origin, m.created_at,
                   (SELECT COUNT(*) FROM workshop_gates g WHERE g.mission_id = m.id) as gate_count
            FROM workshop_missions m
            ORDER BY m.created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )

    return [
        MissionListItem(
            id=str(r["id"]),
            title=r["title"],
            status=r["status"],
            origin=r["origin"],
            gate_count=r["gate_count"],
            created_at=_dt_str(r["created_at"]),
        )
        for r in rows
    ]


@router.get("/missions/{mission_id}", response_model=MissionResponse)
async def get_mission(mission_id: str, pool=Depends(get_pool)):
    """Get mission details with all gate results."""
    row = await pool.fetchrow(
        """
        SELECT id, title, description, status, origin, spec, code_files,
               test_results, security_report, created_at, updated_at
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

    return MissionResponse(
        id=str(row["id"]),
        title=row["title"],
        description=row["description"],
        status=row["status"],
        origin=row["origin"],
        spec=json.loads(row["spec"]) if isinstance(row["spec"], str) else row["spec"],
        gates=[
            GateResponse(
                gate_number=g["gate_number"],
                gate_name=g["gate_name"],
                status=g["status"],
                output=g["output"] or "",
                duration_ms=g["duration_ms"],
                attempts=g["attempts"],
            )
            for g in gates
        ],
        code_files=json.loads(row["code_files"]) if isinstance(row["code_files"], str) else row["code_files"],
        test_results=json.loads(row["test_results"]) if isinstance(row["test_results"], str) else row["test_results"],
        security_report=json.loads(row["security_report"]) if isinstance(row["security_report"], str) else row["security_report"],
        created_at=_dt_str(row["created_at"]),
        updated_at=_dt_str(row["updated_at"]),
    )


@router.post("/missions/{mission_id}/execute")
async def execute_mission(mission_id: str, pool=Depends(get_pool)):
    """Start the 16-gate pipeline as a background task."""
    row = await pool.fetchrow(
        "SELECT id, title, spec, status FROM workshop_missions WHERE id = $1::uuid",
        mission_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Mission not found")

    if mission_id in _pipelines and not _pipelines[mission_id]._cancelled:
        raise HTTPException(status_code=409, detail="Pipeline already running")

    spec_data = json.loads(row["spec"]) if isinstance(row["spec"], str) else row["spec"]
    spec = MissionSpec(
        inputs=spec_data.get("inputs", []),
        outputs=spec_data.get("outputs", []),
        edge_cases=spec_data.get("edge_cases", []),
        error_handling=spec_data.get("error_handling", []),
        constraints=spec_data.get("constraints", []),
        acceptance_criteria=spec_data.get("acceptance_criteria", []),
    )

    # Update mission status
    await pool.execute(
        "UPDATE workshop_missions SET status = 'spec_review', updated_at = NOW() WHERE id = $1::uuid",
        mission_id,
    )

    pipeline = WorkshopPipeline(ia_provider=_ia_provider, pool=_pool, ws_manager=_ws_manager)
    _pipelines[mission_id] = pipeline

    async def _run():
        try:
            await pipeline.execute(mission_id, spec, title=row["title"])
        except Exception as e:
            logger.error(f"Pipeline failed for mission {mission_id}: {e}")
            try:
                await pool.execute(
                    "UPDATE workshop_missions SET status = 'error', updated_at = NOW() WHERE id = $1::uuid",
                    mission_id,
                )
            except Exception:
                pass
        finally:
            _pipelines.pop(mission_id, None)
            _pipeline_tasks.pop(mission_id, None)

    task = asyncio.create_task(_run())
    _pipeline_tasks[mission_id] = task

    return {"status": "running", "mission_id": mission_id, "total_gates": len(GATE_DEFINITIONS)}


@router.post("/missions/{mission_id}/gates/{gate_number}/approve")
async def approve_gate(mission_id: str, gate_number: int, pool=Depends(get_pool)):
    """Approve a gate that's waiting for human approval (gate 15)."""
    if gate_number != 15:
        raise HTTPException(status_code=400, detail="Only gate 15 (Human Checkpoint) requires approval")

    # Update the gate status
    result = await pool.execute(
        """
        UPDATE workshop_gates SET status = 'passed'
        WHERE mission_id = $1::uuid AND gate_number = $2 AND status = 'waiting_approval'
        """,
        mission_id, gate_number,
    )

    pipeline = _pipelines.get(mission_id)
    if mission_id not in _pipelines:
        # Pipeline completed with waiting_approval and was popped from _pipelines.
        # Create a continuation pipeline from DB state.
        spec_row = await pool.fetchrow(
            "SELECT spec, title, code_files FROM workshop_missions WHERE id = $1::uuid",
            mission_id,
        )
        if spec_row:
            spec_data = json.loads(spec_row["spec"]) if isinstance(spec_row["spec"], str) else spec_row["spec"]
            # Get generated code from gate 2 output (more reliable than code_files)
            code_from_gate = await pool.fetchval(
                """SELECT output FROM workshop_gates 
                   WHERE mission_id = $1::uuid AND gate_number = 2 AND status = 'passed'
                   ORDER BY created_at DESC LIMIT 1""",
                mission_id,
            )
            generated_code = code_from_gate or ""

            mini = WorkshopPipeline(ia_provider=_ia_provider, pool=_pool, ws_manager=_ws_manager)
            mini._generated_code = generated_code
            spec = MissionSpec(**spec_data)

            async def _continue_from_db():
                try:
                    from src.workshop.pipeline import GateResult
                    import time as _time
                    start = _time.time()
                    await mini._update_gate_status(mission_id, 16, "Contract Testing", "running")
                    await mini._broadcast(mission_id, 16, "Contract Testing", "running")
                    result = await mini._gate_contract(mini._generated_code, spec)
                    result.duration_ms = int((_time.time() - start) * 1000)
                    await mini._save_gate_result(mission_id, result)
                    await mini._broadcast(mission_id, 16, "Contract Testing", result.status, result.output[:500])
                    final_status = "completed" if result.status in ("passed", "skipped") else "error"
                    await mini._update_mission_status(mission_id, final_status, mini._generated_code)
                except Exception as e:
                    logger.error(f"Gate 16 continuation (from DB) failed: {e}")
                    await mini._update_mission_status(mission_id, "error", mini._generated_code)

            asyncio.create_task(_continue_from_db())
    elif pipeline and pipeline.current_gate == 15:
        # Resume pipeline from gate 16 (contract testing)
        spec_row = await pool.fetchrow(
            "SELECT spec, title FROM workshop_missions WHERE id = $1::uuid",
            mission_id,
        )
        if spec_row:
            spec_data = json.loads(spec_row["spec"]) if isinstance(spec_row["spec"], str) else spec_row["spec"]
            # The existing pipeline is paused at gate 15; we need to continue
            # Create a new mini-pipeline for remaining gates
            mini = WorkshopPipeline(ia_provider=_ia_provider, pool=_pool, ws_manager=_ws_manager)
            mini._generated_code = pipeline.generated_code
            mini._architecture = pipeline._architecture
            mini._test_code = pipeline._test_code

            spec = MissionSpec(**spec_data)

            async def _continue():
                try:
                    # Run only gate 16
                    from src.workshop.pipeline import GateResult
                    import time as _time
                    start = _time.time()
                    await mini._update_gate_status(mission_id, 16, "Contract Testing", "running")
                    await mini._broadcast(mission_id, 16, "Contract Testing", "running")
                    result = await mini._gate_contract(mini._generated_code, spec)
                    result.duration_ms = int((_time.time() - start) * 1000)
                    await mini._save_gate_result(mission_id, result)
                    await mini._broadcast(mission_id, 16, "Contract Testing", result.status, result.output[:500])

                    final_status = "completed" if result.status == "passed" else "error"
                    await mini._update_mission_status(mission_id, final_status, mini._generated_code)
                except Exception as e:
                    logger.error(f"Gate 16 continuation failed: {e}")

            asyncio.create_task(_continue())

    return {"status": "approved", "mission_id": mission_id, "gate_number": gate_number}


@router.get("/missions/{mission_id}/sandbox")
async def get_sandbox(mission_id: str, pool=Depends(get_pool)):
    """Get current sandbox state — generated code + latest gate output."""
    row = await pool.fetchrow(
        "SELECT code_files, status FROM workshop_missions WHERE id = $1::uuid",
        mission_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Mission not found")

    code_files = json.loads(row["code_files"]) if isinstance(row["code_files"], str) else row["code_files"]

    latest_gate = await pool.fetchrow(
        """
        SELECT gate_number, gate_name, status, output
        FROM workshop_gates WHERE mission_id = $1::uuid
        ORDER BY gate_number DESC LIMIT 1
        """,
        mission_id,
    )

    pipeline = _pipelines.get(mission_id)
    current_gate = pipeline.current_gate if pipeline else -1

    return {
        "mission_id": mission_id,
        "status": row["status"],
        "code_files": code_files,
        "current_gate": current_gate,
        "latest_gate": {
            "gate_number": latest_gate["gate_number"],
            "gate_name": latest_gate["gate_name"],
            "status": latest_gate["status"],
            "output": latest_gate["output"][:2000] if latest_gate["output"] else "",
        } if latest_gate else None,
    }


@router.post("/missions/{mission_id}/pause")
async def pause_mission(mission_id: str):
    """Pause a running pipeline."""
    pipeline = _pipelines.get(mission_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline for this mission")

    pipeline.pause()
    return {"status": "paused", "mission_id": mission_id, "current_gate": pipeline.current_gate}


@router.post("/missions/{mission_id}/resume")
async def resume_mission(mission_id: str):
    """Resume a paused pipeline."""
    pipeline = _pipelines.get(mission_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="No active pipeline for this mission")

    pipeline.resume()
    return {"status": "resumed", "mission_id": mission_id, "current_gate": pipeline.current_gate}


@router.post("/missions/{mission_id}/cancel")
async def cancel_mission(mission_id: str, pool=Depends(get_pool)):
    """Cancel a running pipeline."""
    pipeline = _pipelines.get(mission_id)
    if pipeline:
        pipeline.cancel()

    task = _pipeline_tasks.get(mission_id)
    if task and not task.done():
        task.cancel()

    await pool.execute(
        "UPDATE workshop_missions SET status = 'error', updated_at = NOW() WHERE id = $1::uuid",
        mission_id,
    )

    _pipelines.pop(mission_id, None)
    _pipeline_tasks.pop(mission_id, None)

    return {"status": "cancelled", "mission_id": mission_id}


@router.get("/gates")
async def list_gate_definitions():
    """List all 17 gate definitions."""
    return [
        {"gate_number": num, "gate_name": name, "description": desc}
        for num, name, desc in GATE_DEFINITIONS
    ]
