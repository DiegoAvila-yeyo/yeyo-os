"""
YeyoNet — Orquestador para pipelines circulares multi-step.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

import asyncpg

from .models import JobType
from .pipeline_steps import (
    PipelineStepExecutor,
    get_pipeline_flow_definition,
    get_pipeline_step_requirements,
    list_pipeline_flows,
)
from .ring_scheduler import NoEligibleRingNodeError, RingScheduler

logger = logging.getLogger("yeyonet.pipeline")


class PipelineOrchestrator:
    """Coordina runs multi-step entre el nodo local y nodos satélite."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        job_orchestrator,
        local_node_id: str,
        scheduler: RingScheduler | None = None,
        step_executor: PipelineStepExecutor | None = None,
    ):
        self._pool = pool
        self._job_orchestrator = job_orchestrator
        self._local_node_id = local_node_id
        self._scheduler = scheduler or RingScheduler()
        self._step_executor = step_executor or PipelineStepExecutor()

    def list_flows(self) -> list[dict]:
        return list_pipeline_flows()

    async def create_run(
        self,
        flow_id: str,
        input_payload: dict,
        requested_by: str,
        ring_node_ids: list[str] | None = None,
        priority: int = 5,
    ) -> dict:
        step_specs = get_pipeline_flow_definition(flow_id)
        ring = await self._resolve_ring_nodes(ring_node_ids)
        capabilities = await self._get_ring_capabilities(ring)

        try:
            assignments = self._scheduler.assign_steps(ring, step_specs, capabilities)
        except NoEligibleRingNodeError as exc:
            raise ValueError(str(exc)) from exc

        run_id = str(uuid.uuid4())

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO yeyonet_pipeline_runs (
                    id, flow_id, status, requested_by, ring_node_ids, next_ring_index, input_payload
                )
                VALUES ($1, $2, 'running', $3, $4::jsonb, $5, $6::jsonb)
                """,
                uuid.UUID(run_id),
                flow_id,
                uuid.UUID(requested_by),
                json.dumps(ring),
                assignments[0].ring_index if assignments else 0,
                json.dumps(input_payload),
            )

            for step_index, (step_spec, assignment) in enumerate(zip(step_specs, assignments, strict=False)):
                await conn.execute(
                    """
                    INSERT INTO yeyonet_pipeline_steps (
                        id, run_id, step_index, step_type, status, assigned_to, assigned_ring_index
                    )
                    VALUES ($1, $2, $3, $4, 'pending', $5, $6)
                    """,
                    uuid.uuid4(),
                    uuid.UUID(run_id),
                    step_index,
                    step_spec["step_type"],
                    uuid.UUID(assignment.node_id),
                    assignment.ring_index,
                )

        await self._dispatch_next_step(run_id, priority=priority, requested_by=requested_by)
        return await self.get_run(run_id)

    async def get_run(self, run_id: str) -> dict | None:
        async with self._pool.acquire() as conn:
            run_row = await conn.fetchrow(
                "SELECT * FROM yeyonet_pipeline_runs WHERE id = $1",
                uuid.UUID(run_id),
            )
            if not run_row:
                return None

            step_rows = await conn.fetch(
                """
                SELECT * FROM yeyonet_pipeline_steps
                WHERE run_id = $1
                ORDER BY step_index
                """,
                uuid.UUID(run_id),
            )
            artifact_rows = await conn.fetch(
                """
                SELECT * FROM yeyonet_artifacts
                WHERE run_id = $1
                ORDER BY created_at, id
                """,
                uuid.UUID(run_id),
            )

        run_data = _row_to_dict(run_row)
        run_data["run_id"] = run_data["id"]
        run_data["steps"] = [_row_to_dict(row) for row in step_rows]
        run_data["artifacts"] = [_row_to_dict(row) for row in artifact_rows]
        return run_data

    async def handle_job_result(
        self,
        job: dict | None,
        success: bool,
        data: dict,
        error: str,
        node_id: str,
    ) -> None:
        if not job or job.get("type") != JobType.PIPELINE_STEP.value:
            return

        payload = job.get("payload") or {}
        run_id = payload.get("run_id")
        step_id = payload.get("step_id")
        if not run_id or not step_id:
            logger.warning("[pipeline] Ignoring pipeline_step job without run_id/step_id")
            return

        if success:
            output_payload = data.get("output", data)
            await self._complete_step(
                run_id=run_id,
                step_id=step_id,
                output_payload=output_payload,
                completed_by=node_id,
            )
            await self._dispatch_next_step(
                run_id,
                priority=int(job.get("priority", 5) or 5),
                requested_by=job.get("requested_by") or self._local_node_id,
            )
            return

        await self._fail_run(run_id, step_id, error or "Remote pipeline step failed")

    async def _dispatch_next_step(self, run_id: str, priority: int, requested_by: str) -> None:
        async with self._pool.acquire() as conn:
            run_row = await conn.fetchrow(
                "SELECT * FROM yeyonet_pipeline_runs WHERE id = $1",
                uuid.UUID(run_id),
            )
            if not run_row or run_row["status"] in {"completed", "failed", "cancelled"}:
                return

            step_rows = await conn.fetch(
                """
                SELECT * FROM yeyonet_pipeline_steps
                WHERE run_id = $1
                ORDER BY step_index
                """,
                uuid.UUID(run_id),
            )

        steps = [_row_to_dict(row) for row in step_rows]
        pending_step = next((step for step in steps if step["status"] == "pending"), None)
        if not pending_step:
            last_completed = next((step for step in reversed(steps) if step["status"] == "completed"), None)
            final_output = last_completed.get("output_payload") if last_completed else {}
            await self._mark_run_completed(run_id, final_output)
            return

        previous_output = {}
        if pending_step["step_index"] > 0:
            previous_step = steps[pending_step["step_index"] - 1]
            if previous_step["status"] != "completed":
                return
            previous_output = previous_step.get("output_payload") or {}

        step_input = self._build_step_input(
            step_type=pending_step["step_type"],
            run_input=_json_value(run_row["input_payload"], {}),
            previous_output=_json_value(previous_output, {}),
            run_id=run_id,
        )

        await self._update_step_input(
            step_id=pending_step["id"],
            run_id=run_id,
            step_index=pending_step["step_index"],
            ring_index=pending_step["assigned_ring_index"],
            input_payload=step_input,
        )

        if pending_step["assigned_to"] == self._local_node_id:
            await self._run_local_step(run_id, pending_step, step_input, priority, requested_by)
            return

        remote_job = await self._job_orchestrator.create_job(
            job_type=JobType.PIPELINE_STEP,
            payload={
                "run_id": run_id,
                "step_id": pending_step["id"],
                "step_type": pending_step["step_type"],
                "input": step_input,
                "target_node_id": pending_step["assigned_to"],
                "requirements": get_pipeline_step_requirements(pending_step["step_type"]),
            },
            requested_by=requested_by,
            priority=priority,
            timeout_seconds=1800,
        )

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE yeyonet_pipeline_steps
                SET status = 'assigned', job_id = $1, started_at = NOW()
                WHERE id = $2
                """,
                uuid.UUID(remote_job.id),
                uuid.UUID(pending_step["id"]),
            )

    async def _run_local_step(
        self,
        run_id: str,
        step: dict,
        step_input: dict,
        priority: int,
        requested_by: str,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE yeyonet_pipeline_steps
                SET status = 'running', started_at = NOW()
                WHERE id = $1
                """,
                uuid.UUID(step["id"]),
            )

        async def _report_progress(progress: int, detail: str) -> None:
            logger.info(
                "[pipeline] run=%s step=%s progress=%s detail=%s",
                run_id[:8],
                step["step_type"],
                progress,
                detail,
            )

        try:
            output_payload = await self._step_executor.execute(
                step_type=step["step_type"],
                input_payload=step_input,
                report_progress=_report_progress,
            )
        except Exception as exc:
            await self._fail_run(run_id, step["id"], str(exc))
            return

        await self._complete_step(
            run_id=run_id,
            step_id=step["id"],
            output_payload=output_payload,
            completed_by=self._local_node_id,
        )
        await self._dispatch_next_step(run_id, priority=priority, requested_by=requested_by)

    async def _complete_step(
        self,
        run_id: str,
        step_id: str,
        output_payload: dict,
        completed_by: str,
    ) -> None:
        ring = await self._resolve_ring_nodes(None, run_id=run_id)
        artifact_id = str(uuid.uuid4())

        async with self._pool.acquire() as conn:
            step_row = await conn.fetchrow(
                """
                SELECT step_type, assigned_ring_index FROM yeyonet_pipeline_steps
                WHERE id = $1
                """,
                uuid.UUID(step_id),
            )
            if not step_row:
                return

            await conn.execute(
                """
                INSERT INTO yeyonet_artifacts (id, run_id, step_id, kind, data, metadata)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
                """,
                uuid.UUID(artifact_id),
                uuid.UUID(run_id),
                uuid.UUID(step_id),
                step_row["step_type"],
                json.dumps(output_payload),
                json.dumps({"completed_by": completed_by}),
            )

            await conn.execute(
                """
                UPDATE yeyonet_pipeline_steps
                SET status = 'completed',
                    output_payload = $1::jsonb,
                    output_artifact_id = $2,
                    completed_at = NOW()
                WHERE id = $3
                """,
                json.dumps(output_payload),
                uuid.UUID(artifact_id),
                uuid.UUID(step_id),
            )

            await conn.execute(
                """
                UPDATE yeyonet_pipeline_runs
                SET next_ring_index = $1
                WHERE id = $2
                """,
                (step_row["assigned_ring_index"] + 1) % len(ring),
                uuid.UUID(run_id),
            )

    async def _mark_run_completed(self, run_id: str, output_payload: dict) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE yeyonet_pipeline_runs
                SET status = 'completed',
                    output_payload = $1::jsonb,
                    completed_at = NOW()
                WHERE id = $2
                """,
                json.dumps(output_payload),
                uuid.UUID(run_id),
            )

    async def _fail_run(self, run_id: str, step_id: str, error: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE yeyonet_pipeline_steps
                SET status = 'failed', error = $1, completed_at = NOW()
                WHERE id = $2
                """,
                error,
                uuid.UUID(step_id),
            )
            await conn.execute(
                """
                UPDATE yeyonet_pipeline_runs
                SET status = 'failed', error = $1, completed_at = NOW()
                WHERE id = $2
                """,
                error,
                uuid.UUID(run_id),
            )

    async def _update_step_input(
        self,
        step_id: str,
        run_id: str,
        step_index: int,
        ring_index: int,
        input_payload: dict,
    ) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE yeyonet_pipeline_steps
                SET input_payload = $1::jsonb
                WHERE id = $2
                """,
                json.dumps(input_payload),
                uuid.UUID(step_id),
            )
            await conn.execute(
                """
                UPDATE yeyonet_pipeline_runs
                SET current_step_index = $1, next_ring_index = $2
                WHERE id = $3
                """,
                step_index,
                ring_index,
                uuid.UUID(run_id),
            )

    async def _resolve_ring_nodes(self, ring_node_ids: list[str] | None, run_id: str | None = None) -> list[str]:
        if ring_node_ids:
            ring = list(ring_node_ids)
        elif run_id:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT ring_node_ids FROM yeyonet_pipeline_runs WHERE id = $1",
                    uuid.UUID(run_id),
                )
            ring = list(_json_value(row["ring_node_ids"], [])) if row else []
        else:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id FROM yeyonet_nodes
                    WHERE role = 'satellite' AND status = 'online'
                    ORDER BY created_at ASC
                    """
                )
            ring = [self._local_node_id, *[str(row["id"]) for row in rows]]

        if self._local_node_id not in ring:
            ring.insert(0, self._local_node_id)

        deduped: list[str] = []
        seen: set[str] = set()
        for node_id in ring:
            if node_id in seen:
                continue
            seen.add(node_id)
            deduped.append(node_id)

        if len(deduped) < 2:
            raise ValueError("At least two nodes are required for the ring pilot")

        return deduped

    async def _get_ring_capabilities(self, ring_node_ids: list[str]) -> dict[str, dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, resources FROM yeyonet_nodes
                WHERE id = ANY($1::uuid[])
                """,
                [uuid.UUID(node_id) for node_id in ring_node_ids],
            )

        capabilities: dict[str, dict] = {self._local_node_id: {}}
        for row in rows:
            resources = row["resources"] or {}
            if isinstance(resources, str):
                resources = json.loads(resources)
            capabilities[str(row["id"])] = resources
        return capabilities

    def _build_step_input(
        self,
        step_type: str,
        run_input: dict,
        previous_output: dict,
        run_id: str,
    ) -> dict:
        if step_type == "prepare_prompt":
            return dict(run_input)
        if step_type == "generate_image":
            return dict(previous_output)
        if step_type == "store_result":
            return {**previous_output, "run_id": run_id}
        if step_type == "publish_result":
            return {**previous_output, "run_id": run_id}
        raise ValueError(f"Unsupported pipeline step: {step_type}")


def _row_to_dict(row: asyncpg.Record | dict) -> dict:
    if row is None:
        return {}

    data = dict(row)
    for key, value in data.items():
        if isinstance(value, uuid.UUID):
            data[key] = str(value)
        elif isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, str) and value[:1] in {"{", "["}:
            try:
                data[key] = json.loads(value)
            except ValueError:
                pass
    return data


def _json_value(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return default
    return value
