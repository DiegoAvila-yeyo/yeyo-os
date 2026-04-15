"""
YeyoNet — JobOrchestrator.
Corazón de la render farm: recibe solicitudes, asigna a nodos, trackea estado.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime

import asyncpg

from .models import JobStatus, JobType, NodeResources, YeyoNetJob
from .protocol import MessageType, NetMessage, make_job_assign

logger = logging.getLogger("yeyonet.orchestrator")

# Capacidades requeridas por tipo de job
JOB_REQUIREMENTS: dict[str, dict] = {
    "image_generate": {"needs_gpu": True, "min_ram_gb": 4.0},
    "video_render": {"needs_gpu": False, "min_ram_gb": 2.0},
    "text_inference": {"needs_gpu": False, "min_ram_gb": 4.0, "needs_ollama": True},
    "training_step": {"needs_gpu": True, "min_ram_gb": 8.0},
    "memory_sync": {"needs_gpu": False, "min_ram_gb": 0.5},
    "custom": {"needs_gpu": False, "min_ram_gb": 1.0},
}


class JobOrchestrator:
    """
    Gestiona la cola de trabajos distribuidos.
    Asigna jobs a nodos según capacidad y carga.
    """

    def __init__(self, pool: asyncpg.Pool, relay=None):
        self._pool = pool
        self._relay = relay
        self._running = False
        self._dispatch_task: asyncio.Task | None = None

    def set_relay(self, relay) -> None:
        self._relay = relay

    async def start(self) -> None:
        self._running = True
        self._dispatch_task = asyncio.create_task(self._dispatch_loop())
        logger.info("[orchestrator] Iniciado")

    async def stop(self) -> None:
        self._running = False
        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

    # ─── CRUD de jobs ────────────────────────────────────────

    async def create_job(
        self,
        job_type: JobType,
        payload: dict,
        requested_by: str | None = None,
        priority: int = 5,
        timeout_seconds: int = 600,
    ) -> YeyoNetJob:
        """Crea un nuevo job y lo encola."""
        job_id = str(uuid.uuid4())

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO yeyonet_jobs (id, type, status, requested_by, payload, priority, timeout_seconds)
                VALUES ($1, $2, 'queued', $3, $4::jsonb, $5, $6)
                """,
                uuid.UUID(job_id),
                job_type.value,
                uuid.UUID(requested_by) if requested_by else None,
                json.dumps(payload),
                priority,
                timeout_seconds,
            )

        job = YeyoNetJob(
            id=job_id,
            type=job_type,
            payload=payload,
            requested_by=requested_by,
            priority=priority,
            timeout_seconds=timeout_seconds,
        )
        logger.info(f"[orchestrator] Job creado: {job_id[:8]}... tipo={job_type.value} prioridad={priority}")
        return job

    async def get_job(self, job_id: str) -> dict | None:
        """Obtiene un job completo."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM yeyonet_jobs WHERE id = $1",
                uuid.UUID(job_id),
            )
        return _row_to_dict(row) if row else None

    async def list_jobs(
        self,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Lista jobs con filtros opcionales."""
        query = "SELECT * FROM yeyonet_jobs WHERE 1=1"
        params = []
        idx = 1

        if status:
            query += f" AND status = ${idx}"
            params.append(status)
            idx += 1
        if job_type:
            query += f" AND type = ${idx}"
            params.append(job_type)
            idx += 1

        query += f" ORDER BY priority DESC, created_at ASC LIMIT ${idx}"
        params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [_row_to_dict(r) for r in rows]

    async def cancel_job(self, job_id: str) -> bool:
        """Cancela un job si aún no completó."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE yeyonet_jobs SET status = 'cancelled'
                WHERE id = $1 AND status IN ('queued', 'assigned')
                """,
                uuid.UUID(job_id),
            )
            cancelled = result.split()[-1] != "0"

        if cancelled:
            # Notify assigned node
            job = await self.get_job(job_id)
            if job and job.get("assigned_to") and self._relay:
                await self._relay.send_to_node(
                    job["assigned_to"],
                    NetMessage(type=MessageType.JOB_CANCEL, payload={"job_id": job_id}),
                )
            logger.info(f"[orchestrator] Job cancelado: {job_id[:8]}...")
        return cancelled

    # ─── Progreso y resultados ───────────────────────────────

    async def update_progress(self, job_id: str, progress: int, detail: str = "") -> None:
        """Actualiza progreso de un job (llamado por worker via relay)."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE yeyonet_jobs SET progress = $1, progress_detail = $2 WHERE id = $3",
                min(progress, 100),
                detail,
                uuid.UUID(job_id),
            )

    async def complete_job(self, job_id: str, result: dict) -> None:
        """Marca un job como completado con su resultado."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE yeyonet_jobs
                SET status = 'completed', result = $1::jsonb, progress = 100, completed_at = NOW()
                WHERE id = $2
                """,
                json.dumps(result),
                uuid.UUID(job_id),
            )
        logger.info(f"[orchestrator] Job completado: {job_id[:8]}...")

    async def fail_job(self, job_id: str, error: str) -> None:
        """Marca un job como fallido. Reintenta si hay intentos restantes."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT attempt, max_attempts FROM yeyonet_jobs WHERE id = $1",
                uuid.UUID(job_id),
            )
            if row and row["attempt"] < row["max_attempts"]:
                # Retry — re-queue
                await conn.execute(
                    """
                    UPDATE yeyonet_jobs
                    SET status = 'queued', assigned_to = NULL, attempt = attempt + 1,
                        progress = 0, progress_detail = $1
                    WHERE id = $2
                    """,
                    f"Retry after: {error[:100]}",
                    uuid.UUID(job_id),
                )
                logger.info(f"[orchestrator] Job {job_id[:8]}... re-encolado (intento {row['attempt']+1}/{row['max_attempts']})")
            else:
                # No more retries
                await conn.execute(
                    """
                    UPDATE yeyonet_jobs
                    SET status = 'failed', result = $1::jsonb, completed_at = NOW()
                    WHERE id = $2
                    """,
                    json.dumps({"error": error}),
                    uuid.UUID(job_id),
                )
                logger.info(f"[orchestrator] Job fallido: {job_id[:8]}... — {error[:80]}")

    # ─── Job distribution for multi-node work ────────────────

    async def create_distributed_job(
        self,
        job_type: JobType,
        items: list[dict],
        requested_by: str | None = None,
        priority: int = 5,
    ) -> dict:
        """
        Crea un job distribuido con múltiples sub-items.
        Usado para: N variaciones de imagen, chunks de video, etc.
        Retorna el job padre y los sub-results creados.
        """
        parent_job = await self.create_job(
            job_type=job_type,
            payload={"distributed": True, "total_items": len(items), "items": items},
            requested_by=requested_by,
            priority=priority,
        )

        # Create sub-result entries for each item
        async with self._pool.acquire() as conn:
            for i, item in enumerate(items):
                await conn.execute(
                    """
                    INSERT INTO yeyonet_job_results (job_id, chunk_index, chunk_total, status, data)
                    VALUES ($1, $2, $3, 'pending', $4::jsonb)
                    """,
                    uuid.UUID(parent_job.id),
                    i,
                    len(items),
                    json.dumps(item),
                )

        logger.info(f"[orchestrator] Job distribuido creado: {parent_job.id[:8]}... ({len(items)} items)")
        return {"job_id": parent_job.id, "total_items": len(items)}

    async def get_job_results(self, job_id: str) -> list[dict]:
        """Obtiene sub-resultados de un job distribuido."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM yeyonet_job_results
                WHERE job_id = $1 ORDER BY chunk_index
                """,
                uuid.UUID(job_id),
            )
        return [
            {
                "id": str(r["id"]),
                "chunk_index": r["chunk_index"],
                "chunk_total": r["chunk_total"],
                "status": r["status"],
                "data": r["data"],
                "error": r["error"],
                "duration_ms": r["duration_ms"],
                "node_id": str(r["node_id"]) if r["node_id"] else None,
            }
            for r in rows
        ]

    # ─── Dispatch loop — assigns queued jobs to available nodes ──

    async def _dispatch_loop(self) -> None:
        """Periódicamente intenta asignar jobs en cola a nodos disponibles."""
        while self._running:
            try:
                await self._try_dispatch()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"[orchestrator] Dispatch error: {e}")
            await asyncio.sleep(5)  # Check every 5 seconds

    async def _try_dispatch(self) -> None:
        """Intenta asignar el siguiente job en cola."""
        if not self._relay:
            return

        async with self._pool.acquire() as conn:
            # Get highest priority queued job
            job_row = await conn.fetchrow(
                """
                SELECT * FROM yeyonet_jobs
                WHERE status = 'queued'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """
            )
            if not job_row:
                return

            job_id = str(job_row["id"])
            job_type = job_row["type"]

            # Find best node for this job
            node_id = await self._find_best_node(job_type, conn)
            if not node_id:
                return  # No capable node available

            # Assign job
            await conn.execute(
                "UPDATE yeyonet_jobs SET status = 'assigned', assigned_to = $1, started_at = NOW() WHERE id = $2",
                uuid.UUID(node_id),
                uuid.UUID(job_id),
            )

        # Send job to node via relay
        payload = job_row["payload"] if isinstance(job_row["payload"], dict) else json.loads(job_row["payload"])
        msg = make_job_assign(
            from_node="central",
            to_node=node_id,
            job_id=job_id,
            job_type=job_type,
            payload=payload,
        )
        sent = await self._relay.send_to_node(node_id, msg)
        if sent:
            logger.info(f"[orchestrator] Job {job_id[:8]}... asignado a {node_id[:8]}...")
        else:
            # Node disconnected — re-queue
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "UPDATE yeyonet_jobs SET status = 'queued', assigned_to = NULL WHERE id = $1",
                    uuid.UUID(job_id),
                )

    async def _find_best_node(self, job_type: str, conn) -> str | None:
        """Encuentra el mejor nodo disponible para un tipo de job."""
        reqs = JOB_REQUIREMENTS.get(job_type, {})
        connected_ids = self._relay.get_connected_ids() if self._relay else []

        if not connected_ids:
            return None

        # Get online nodes with their resources
        rows = await conn.fetch(
            """
            SELECT id, resources, mode FROM yeyonet_nodes
            WHERE id = ANY($1::uuid[]) AND status = 'online'
            """,
            [uuid.UUID(nid) for nid in connected_ids],
        )

        best_node = None
        best_score = -1

        for row in rows:
            node_id = str(row["id"])
            res = row["resources"]
            if isinstance(res, str):
                res = json.loads(res)
            if not res:
                res = {}

            # Check requirements
            if reqs.get("needs_gpu") and not res.get("gpu_name"):
                continue
            if res.get("ram_free_gb", 0) < reqs.get("min_ram_gb", 0):
                continue
            if reqs.get("needs_ollama") and not res.get("ollama_models"):
                continue

            # Score: prefer least loaded, most capable
            score = 100.0
            score -= res.get("cpu_percent", 50)  # Lower CPU usage = better
            score += res.get("ram_free_gb", 0) * 5  # More RAM = better
            if res.get("gpu_name"):
                score += 30  # GPU bonus
            score -= res.get("active_jobs", 0) * 20  # Fewer active jobs = better

            if score > best_score:
                best_score = score
                best_node = node_id

        return best_node

    # ─── Handle messages from relay ──────────────────────────

    async def handle_job_progress(self, msg: NetMessage, node_id: str) -> None:
        """Handler para JOB_PROGRESS desde un worker."""
        job_id = msg.payload.get("job_id", "")
        progress = msg.payload.get("progress", 0)
        detail = msg.payload.get("detail", "")
        await self.update_progress(job_id, progress, detail)

    async def handle_job_result(self, msg: NetMessage, node_id: str) -> None:
        """Handler para JOB_RESULT desde un worker."""
        job_id = msg.payload.get("job_id", "")
        success = msg.payload.get("success", False)
        data = msg.payload.get("data", {})
        error = msg.payload.get("error", "")

        if success:
            await self.complete_job(job_id, data)
        else:
            await self.fail_job(job_id, error)

    async def get_queue_stats(self) -> dict:
        """Estadísticas de la cola de jobs."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT status, COUNT(*) as count FROM yeyonet_jobs GROUP BY status"
            )
        stats = {r["status"]: r["count"] for r in rows}
        return {
            "queued": stats.get("queued", 0),
            "assigned": stats.get("assigned", 0),
            "running": stats.get("running", 0),
            "completed": stats.get("completed", 0),
            "failed": stats.get("failed", 0),
            "cancelled": stats.get("cancelled", 0),
        }


def _row_to_dict(row: asyncpg.Record) -> dict:
    """Convierte row de DB a dict serializable."""
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
    return d
