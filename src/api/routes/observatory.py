import asyncio
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.api.websocket import manager
from src.observatory.agents.registry import get_agent, list_agents, AGENTS

logger = logging.getLogger("yeyoos.api.observatory")

router = APIRouter(prefix="/api/v1/observatory", tags=["observatory"])

# ========== Dependency Injection ==========

_pool = None
_ia_provider = None
_memory = None


def set_db_pool(pool):
    global _pool
    _pool = pool


def set_ia_provider(provider):
    global _ia_provider
    _ia_provider = provider


def set_memory(mem):
    global _memory
    _memory = mem


async def get_pool():
    if _pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    return _pool


async def get_ia():
    return _ia_provider


async def get_mem():
    return _memory


# ========== Pydantic Models ==========


class TaskCreate(BaseModel):
    agent_name: str
    description: str


class CrewCreate(BaseModel):
    title: str
    description: str = ""
    agents: list[str]


# ========== Background Runners ==========


async def _run_task(task_id: str, agent_name: str, description: str):
    """Execute an agent task in the background."""
    pool = _pool
    ia = _ia_provider
    mem = _memory

    try:
        await manager.broadcast_json(
            {"type": "task_progress", "task_id": task_id, "agent": agent_name, "message": "Working..."}
        )

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE observatory_tasks SET status = 'running' WHERE id = $1",
                UUID(task_id),
            )

        agent = get_agent(agent_name, ia_provider=ia, memory=mem)
        result = await agent.execute(description)

        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE observatory_tasks
                   SET status = $1, result_output = $2, result_files = $3,
                       result_memories = $4, duration_ms = $5, error_message = $6,
                       completed_at = NOW()
                   WHERE id = $7""",
                "completed" if result.success else "error",
                result.output,
                result.files_created,
                result.memories_stored,
                result.duration_ms,
                result.error or "",
                UUID(task_id),
            )

        await manager.broadcast_json(
            {
                "type": "task_completed",
                "task_id": task_id,
                "agent": agent_name,
                "status": "completed" if result.success else "error",
            }
        )

        # Auto-create potential mission if result is actionable
        if result.success:
            await _maybe_create_mission(task_id, result.output, agent_name)

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE observatory_tasks
                       SET status = 'error', error_message = $1, completed_at = NOW()
                       WHERE id = $2""",
                    str(e),
                    UUID(task_id),
                )
        except Exception:
            pass
        await manager.broadcast_json(
            {"type": "task_completed", "task_id": task_id, "agent": agent_name, "status": "error"}
        )


async def _run_crew(crew_id: str, title: str, description: str, agent_names: list[str]):
    """Execute a crew mission — agents run sequentially, each passing context to the next."""
    pool = _pool
    ia = _ia_provider
    mem = _memory

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE observatory_crews SET status = 'running' WHERE id = $1",
                UUID(crew_id),
            )

        results = []
        accumulated_context = f"Mission: {title}\n{description}"

        for idx, agent_name in enumerate(agent_names):
            await manager.broadcast_json(
                {
                    "type": "task_progress",
                    "task_id": crew_id,
                    "agent": agent_name,
                    "message": f"Agent {idx + 1}/{len(agent_names)}: {agent_name} working...",
                }
            )

            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE observatory_crews SET current_agent_index = $1 WHERE id = $2",
                    idx,
                    UUID(crew_id),
                )

            agent = get_agent(agent_name, ia_provider=ia, memory=mem)
            task_prompt = f"{accumulated_context}\n\nTu turno como {agent_name}. Contexto previo disponible."
            result = await agent.execute(task_prompt)

            step = {
                "agent": agent_name,
                "success": result.success,
                "output": result.output,
                "duration_ms": result.duration_ms,
                "error": result.error,
            }
            results.append(step)
            accumulated_context += f"\n\n[{agent_name}]: {result.output[:500]}"

            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE observatory_crews SET results = $1::jsonb WHERE id = $2",
                    json.dumps(results),
                    UUID(crew_id),
                )

            await manager.broadcast_json(
                {
                    "type": "task_completed",
                    "task_id": crew_id,
                    "agent": agent_name,
                    "status": "completed" if result.success else "error",
                }
            )

        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE observatory_crews SET status = 'completed', completed_at = NOW() WHERE id = $1",
                UUID(crew_id),
            )

    except Exception as e:
        logger.error(f"Crew {crew_id} failed: {e}")
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE observatory_crews SET status = 'error', completed_at = NOW() WHERE id = $1",
                    UUID(crew_id),
                )
        except Exception:
            pass


# ========== Mission Bridge Helper ==========

_ACTION_WORDS = [
    "implementar", "crear", "refactorizar", "optimizar", "corregir", "arreglar",
    "mejorar", "actualizar", "migrar", "reemplazar", "agregar", "eliminar",
    "implement", "create", "refactor", "optimize", "fix", "improve", "update",
    "migrate", "replace", "add", "remove", "should", "must", "recommend",
]


async def _maybe_create_mission(task_id: str, result_output: str, agent_name: str) -> str | None:
    """
    Check if a task result contains actionable findings.
    If so, auto-create a potential mission in the bridge.
    Returns mission id or None.
    """
    if not result_output or len(result_output) < 200:
        return None

    output_lower = result_output.lower()
    action_score = sum(1 for word in _ACTION_WORDS if word in output_lower)
    if action_score < 2:
        return None

    try:
        pool = _pool
        if pool is None:
            return None

        # Extract a short title from the first meaningful line
        lines = [l.strip() for l in result_output.split("\n") if l.strip() and not l.strip().startswith("#")]
        title = lines[0][:120] if lines else f"Hallazgo de {agent_name}"
        title = f"[{agent_name}] {title}"

        row = await pool.fetchrow(
            """
            INSERT INTO workshop_missions
                (title, description, origin, created_by, finding, observatory_task_id)
            VALUES ($1, $2, 'observatory', $3, $4, $5)
            RETURNING id
            """,
            title[:255],
            f"Auto-detected actionable finding from {agent_name} task.",
            agent_name,
            result_output[:2000],
            UUID(task_id),
        )
        mission_id = str(row["id"])
        logger.info(f"Auto-created mission {mission_id} from task {task_id} ({agent_name})")

        await manager.broadcast_json(
            {
                "type": "mission_created",
                "mission_id": mission_id,
                "task_id": task_id,
                "agent": agent_name,
                "origin": "observatory",
            }
        )
        return mission_id
    except Exception as e:
        logger.warning(f"Failed to auto-create mission from task {task_id}: {e}")
        return None


# ========== Endpoints ==========


@router.get("/agents")
async def get_agents():
    """List all observatory agents with their info and quick tasks."""
    return {"agents": list_agents()}


@router.post("/task")
async def create_task(body: TaskCreate, pool=Depends(get_pool)):
    """Assign a task to an agent. Runs asynchronously in background."""
    if body.agent_name not in AGENTS:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {body.agent_name}")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO observatory_tasks (agent_name, description, status)
               VALUES ($1, $2, 'pending')
               RETURNING id, status, created_at""",
            body.agent_name,
            body.description,
        )

    task_id = str(row["id"])
    asyncio.create_task(_run_task(task_id, body.agent_name, body.description))

    return {
        "id": task_id,
        "agent_name": body.agent_name,
        "description": body.description,
        "status": "pending",
        "created_at": row["created_at"].isoformat(),
    }


@router.get("/tasks")
async def list_tasks(
    agent_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    pool=Depends(get_pool),
):
    """List tasks, optionally filtered by agent_name and/or status."""
    query = "SELECT * FROM observatory_tasks WHERE 1=1"
    params = []
    idx = 1

    if agent_name:
        query += f" AND agent_name = ${idx}"
        params.append(agent_name)
        idx += 1
    if status:
        query += f" AND status = ${idx}"
        params.append(status)
        idx += 1

    query += f" ORDER BY created_at DESC LIMIT ${idx}"
    params.append(limit)

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return {
        "tasks": [
            {
                "id": str(r["id"]),
                "agent_name": r["agent_name"],
                "description": r["description"],
                "status": r["status"],
                "result_output": r["result_output"],
                "result_files": r["result_files"],
                "result_memories": r["result_memories"],
                "duration_ms": r["duration_ms"],
                "error_message": r["error_message"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            }
            for r in rows
        ]
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, pool=Depends(get_pool)):
    """Get a specific task result."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM observatory_tasks WHERE id = $1", UUID(task_id)
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": str(row["id"]),
        "agent_name": row["agent_name"],
        "description": row["description"],
        "status": row["status"],
        "result_output": row["result_output"],
        "result_files": row["result_files"],
        "result_memories": row["result_memories"],
        "duration_ms": row["duration_ms"],
        "error_message": row["error_message"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, pool=Depends(get_pool)):
    """Cancel or delete a task."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM observatory_tasks WHERE id = $1", UUID(task_id)
        )

    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Task not found")

    return {"deleted": True, "id": task_id}


@router.post("/crew")
async def create_crew(body: CrewCreate, pool=Depends(get_pool)):
    """Create a multi-agent crew mission. Agents run sequentially."""
    for name in body.agents:
        if name not in AGENTS:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {name}")

    if len(body.agents) < 1:
        raise HTTPException(status_code=400, detail="At least one agent required")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO observatory_crews (title, description, agent_sequence, status)
               VALUES ($1, $2, $3, 'pending')
               RETURNING id, status, created_at""",
            body.title,
            body.description,
            body.agents,
        )

    crew_id = str(row["id"])
    asyncio.create_task(_run_crew(crew_id, body.title, body.description, body.agents))

    return {
        "id": crew_id,
        "title": body.title,
        "agents": body.agents,
        "status": "pending",
        "created_at": row["created_at"].isoformat(),
    }


@router.get("/crew/{crew_id}")
async def get_crew(crew_id: str, pool=Depends(get_pool)):
    """Get crew mission status and results."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM observatory_crews WHERE id = $1", UUID(crew_id)
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Crew mission not found")

    return {
        "id": str(row["id"]),
        "title": row["title"],
        "description": row["description"],
        "agent_sequence": row["agent_sequence"],
        "status": row["status"],
        "current_agent_index": row["current_agent_index"],
        "results": json.loads(row["results"]) if isinstance(row["results"], str) else row["results"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
    }


@router.post("/tasks/{task_id}/to-mission")
async def task_to_mission(task_id: str, pool=Depends(get_pool)):
    """Manually convert a completed task result into a mission."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM observatory_tasks WHERE id = $1",
            UUID(task_id),
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if row["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task must be completed to create a mission")
    if not row["result_output"]:
        raise HTTPException(status_code=400, detail="Task has no result output")

    title = f"[{row['agent_name']}] {row['description'][:120]}"

    async with pool.acquire() as conn:
        mission_row = await conn.fetchrow(
            """
            INSERT INTO workshop_missions
                (title, description, origin, created_by, finding, observatory_task_id)
            VALUES ($1, $2, 'observatory', $3, $4, $5)
            RETURNING id, title, status, created_at
            """,
            title[:255],
            row["description"],
            row["agent_name"],
            row["result_output"][:2000],
            UUID(task_id),
        )

    return {
        "mission_id": str(mission_row["id"]),
        "title": mission_row["title"],
        "status": mission_row["status"],
        "origin": "observatory",
        "created_by": row["agent_name"],
        "created_at": mission_row["created_at"].isoformat() if mission_row["created_at"] else None,
    }
