"""
YeyoOS — Workflow Orchestrator Service
Singleton service providing CRUD + execution for workflows.
Integrates engine, triggers, and robot pool.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any

from src.workflows.models import (
    Workflow, WorkflowNode, WorkflowEdge, WorkflowExecution,
    NodeType, WorkflowStatus, ExecutionStatus, TriggerType,
    NODE_TYPE_INFO, NODE_TYPE_CATEGORIES,
)
from src.workflows.engine import WorkflowEngine
from src.workflows.triggers import TriggerManager
from src.workflows.robots import RobotPool

logger = logging.getLogger("yeyoos.workflows.service")


class WorkflowService:
    """Singleton service that ties together the workflow engine, trigger
    manager, and robot pool.  Provides the main API surface for
    workflow CRUD and execution used by the FastAPI routes.
    """

    _instance: Optional["WorkflowService"] = None

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "WorkflowService":
        """Create or return the singleton WorkflowService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """Initialise the service with engine, triggers, robot pool,
        and an in-memory workflow store (replaced by DB when pool is set).
        """
        self.engine = WorkflowEngine()
        self.triggers = TriggerManager()
        self.robots = RobotPool(pool_size=5)
        self.workflows: dict[str, Workflow] = {}
        self._db_pool = None  # asyncpg pool, set via set_db_pool()
        self._register_handlers()

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def _register_handlers(self) -> None:
        """Import and register all node-type handlers from the handlers
        sub-package.  Each import is wrapped in try/except so missing
        optional dependencies don't crash startup.
        """
        handler_map: list[tuple[NodeType, str, str]] = [
            # (NodeType, module path, function name)
            (NodeType.IMAGE_GEN,    "src.workflows.handlers.image_gen",  "handle_image_gen"),
            (NodeType.VIDEO_GEN,    "src.workflows.handlers.video_gen",  "handle_video_gen"),
            (NodeType.SLIDESHOW,    "src.workflows.handlers.slideshow",  "handle_slideshow"),
            (NodeType.CHAT,         "src.workflows.handlers.chat",       "handle_chat"),
            (NodeType.FILTER,       "src.workflows.handlers.filter",     "handle_filter"),
            (NodeType.CODE,         "src.workflows.handlers.code",       "handle_code"),
            (NodeType.MEMORY_READ,  "src.workflows.handlers.memory",     "handle_memory_read"),
            (NodeType.MEMORY_WRITE, "src.workflows.handlers.memory",     "handle_memory_write"),
            (NodeType.FILE_READ,    "src.workflows.handlers.file_io",    "handle_file_read"),
            (NodeType.FILE_WRITE,   "src.workflows.handlers.file_io",    "handle_file_write"),
            (NodeType.HTTP_REQUEST, "src.workflows.handlers.http",       "handle_http_request"),
            # CONDITION, LOOP, and DELAY are handled internally by the engine.
        ]

        import importlib

        for node_type, module_path, func_name in handler_map:
            try:
                mod = importlib.import_module(module_path)
                handler = getattr(mod, func_name)
                self.engine.register_handler(node_type, handler)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Could not register handler for %s (%s.%s): %s",
                    node_type.value, module_path, func_name, exc,
                )

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    async def set_db_pool(self, pool: Any) -> None:
        """Set the asyncpg connection pool and load persisted workflows."""
        self._db_pool = pool
        await self._load_workflows_from_db()

    async def _load_workflows_from_db(self) -> None:
        """Load all workflow rows from the ``workflows`` table and
        populate the in-memory dict.
        """
        if self._db_pool is None:
            return
        try:
            async with self._db_pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM workflows")
            for row in rows:
                wf = Workflow(
                    id=row["id"],
                    name=row["name"],
                    description=row.get("description", ""),
                    status=WorkflowStatus(row["status"]),
                    nodes=[
                        WorkflowNode.from_dict(n)
                        for n in json.loads(row.get("nodes", "[]"))
                    ],
                    edges=[
                        WorkflowEdge.from_dict(e)
                        for e in json.loads(row.get("edges", "[]"))
                    ],
                    trigger_type=TriggerType(row.get("trigger_type", "manual")),
                    trigger_config=json.loads(row.get("trigger_config", "{}")),
                    variables=json.loads(row.get("variables", "{}")),
                    created_at=row.get("created_at", datetime.now(timezone.utc)),
                    updated_at=row.get("updated_at", datetime.now(timezone.utc)),
                )
                self.workflows[wf.id] = wf
            logger.info("Loaded %d workflows from DB", len(rows))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load workflows from DB: %s", exc)

    async def _save_workflow_to_db(self, workflow: Workflow) -> None:
        """Upsert a single workflow row in the ``workflows`` table."""
        if self._db_pool is None:
            return
        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO workflows
                        (id, name, description, status, nodes, edges,
                         trigger_type, trigger_config, variables,
                         created_at, updated_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    ON CONFLICT (id) DO UPDATE SET
                        name           = EXCLUDED.name,
                        description    = EXCLUDED.description,
                        status         = EXCLUDED.status,
                        nodes          = EXCLUDED.nodes,
                        edges          = EXCLUDED.edges,
                        trigger_type   = EXCLUDED.trigger_type,
                        trigger_config = EXCLUDED.trigger_config,
                        variables      = EXCLUDED.variables,
                        updated_at     = EXCLUDED.updated_at
                    """,
                    workflow.id,
                    workflow.name,
                    workflow.description,
                    workflow.status.value,
                    json.dumps([n.to_dict() for n in workflow.nodes]),
                    json.dumps([e.to_dict() for e in workflow.edges]),
                    workflow.trigger_type.value,
                    json.dumps(workflow.trigger_config),
                    json.dumps(workflow.variables),
                    workflow.created_at,
                    workflow.updated_at,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to save workflow %s to DB: %s", workflow.id, exc)

    async def _save_execution_to_db(self, execution: WorkflowExecution) -> None:
        """Insert an execution record into the ``workflow_executions`` table."""
        if self._db_pool is None:
            return
        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO workflow_executions
                        (id, workflow_id, workflow_name, status,
                         node_results, variables, robot_id,
                         trigger_type, started_at, completed_at, error)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    ON CONFLICT (id) DO UPDATE SET
                        status       = EXCLUDED.status,
                        node_results = EXCLUDED.node_results,
                        variables    = EXCLUDED.variables,
                        completed_at = EXCLUDED.completed_at,
                        error        = EXCLUDED.error
                    """,
                    execution.id,
                    execution.workflow_id,
                    execution.workflow_name,
                    execution.status.value,
                    json.dumps([nr.to_dict() for nr in execution.node_results]),
                    json.dumps(execution.variables),
                    execution.robot_id,
                    execution.trigger_type.value,
                    execution.started_at,
                    execution.completed_at,
                    execution.error,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to save execution %s to DB: %s", execution.id, exc,
            )

    async def _delete_workflow_from_db(self, workflow_id: str) -> None:
        """Delete a workflow row from the DB by id."""
        if self._db_pool is None:
            return
        try:
            async with self._db_pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM workflows WHERE id = $1", workflow_id,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to delete workflow %s from DB: %s", workflow_id, exc,
            )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_workflow(self, data: dict) -> Workflow:
        """Create a new workflow from a dict of fields and persist it.

        Accepted keys mirror ``Workflow`` fields: *name*, *description*,
        *nodes*, *edges*, *trigger_type*, *trigger_config*, *variables*.
        """
        nodes = [
            WorkflowNode.from_dict(n) if isinstance(n, dict) else n
            for n in data.get("nodes", [])
        ]
        edges = [
            WorkflowEdge.from_dict(e) if isinstance(e, dict) else e
            for e in data.get("edges", [])
        ]

        workflow = Workflow(
            name=data.get("name", "New Workflow"),
            description=data.get("description", ""),
            status=WorkflowStatus(data["status"]) if "status" in data else WorkflowStatus.DRAFT,
            nodes=nodes,
            edges=edges,
            trigger_type=TriggerType(data["trigger_type"]) if "trigger_type" in data else TriggerType.MANUAL,
            trigger_config=data.get("trigger_config", {}),
            variables=data.get("variables", {}),
        )

        self.workflows[workflow.id] = workflow
        await self._save_workflow_to_db(workflow)
        logger.info("Created workflow %s (%s)", workflow.id, workflow.name)
        return workflow

    async def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Return a workflow by id, or ``None`` if not found."""
        return self.workflows.get(workflow_id)

    async def list_workflows(self) -> list[Workflow]:
        """Return every workflow currently stored."""
        return list(self.workflows.values())

    async def update_workflow(
        self, workflow_id: str, data: dict,
    ) -> Optional[Workflow]:
        """Update mutable fields of an existing workflow and persist.

        Returns the updated ``Workflow`` or ``None`` if not found.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            return None

        if "name" in data:
            workflow.name = data["name"]
        if "description" in data:
            workflow.description = data["description"]
        if "status" in data:
            workflow.status = WorkflowStatus(data["status"])
        if "nodes" in data:
            workflow.nodes = [
                WorkflowNode.from_dict(n) if isinstance(n, dict) else n
                for n in data["nodes"]
            ]
        if "edges" in data:
            workflow.edges = [
                WorkflowEdge.from_dict(e) if isinstance(e, dict) else e
                for e in data["edges"]
            ]
        if "trigger_type" in data:
            workflow.trigger_type = TriggerType(data["trigger_type"])
        if "trigger_config" in data:
            workflow.trigger_config = data["trigger_config"]
        if "variables" in data:
            workflow.variables = data["variables"]

        workflow.updated_at = datetime.now(timezone.utc)
        await self._save_workflow_to_db(workflow)
        logger.info("Updated workflow %s", workflow_id)
        return workflow

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow definition.

        .. note::

            This only removes the workflow definition — it **never**
            deletes memories created during past executions.

        Returns ``True`` if the workflow was found and removed.
        """
        if workflow_id not in self.workflows:
            return False

        # Stop any active triggers for this workflow.
        await self.triggers.stop_cron(workflow_id)
        del self.workflows[workflow_id]
        await self._delete_workflow_from_db(workflow_id)
        logger.info("Deleted workflow %s", workflow_id)
        return True

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def execute_workflow(
        self,
        workflow_id: str,
        variables: Optional[dict] = None,
    ) -> Optional[WorkflowExecution]:
        """Kick off a workflow execution in the background.

        1. Looks up the workflow.
        2. Acquires a robot from the pool.
        3. Fires the engine in an ``asyncio.create_task`` so the caller
           gets the ``WorkflowExecution`` (in PENDING state) immediately.
        4. On completion the robot is released and the execution saved to DB.

        Returns ``None`` if the workflow doesn't exist.
        """
        workflow = self.workflows.get(workflow_id)
        if workflow is None:
            logger.warning("execute_workflow: unknown id %s", workflow_id)
            return None

        robot = self.robots.acquire(execution_id="pending")

        # Build a lightweight execution stub to return immediately.
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            status=ExecutionStatus.PENDING,
            variables=variables or {},
            robot_id=robot.id if robot else None,
            trigger_type=workflow.trigger_type,
            total_nodes=len(workflow.nodes),
        )

        async def _run() -> None:
            try:
                result = await self.engine.execute(workflow, variables)
                # Propagate fields produced by the engine back into our stub.
                execution.status = result.status
                execution.node_results = result.node_results
                execution.variables = result.variables
                execution.completed_at = result.completed_at
                execution.error = result.error
                execution.current_node_index = result.current_node_index
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Workflow %s execution failed: %s", workflow_id, exc,
                )
                execution.status = ExecutionStatus.FAILED
                execution.error = str(exc)
                execution.completed_at = datetime.now(timezone.utc)
            finally:
                if robot:
                    self.robots.release(robot.id)
                await self._save_execution_to_db(execution)

        asyncio.create_task(_run())  # noqa: RUF006
        logger.info(
            "Launched execution %s for workflow %s (robot=%s)",
            execution.id, workflow_id, robot.id if robot else "none",
        )
        return execution

    async def get_execution(
        self, exec_id: str,
    ) -> Optional[WorkflowExecution]:
        """Look up an execution by id (delegates to the engine)."""
        return self.engine.get_execution(exec_id)

    async def get_workflow_executions(
        self, workflow_id: str,
    ) -> list[WorkflowExecution]:
        """Return all executions for a given workflow."""
        return self.engine.get_executions_for_workflow(workflow_id)

    # ------------------------------------------------------------------
    # Node-type metadata
    # ------------------------------------------------------------------

    def get_node_types(self) -> dict:
        """Return the full node-type catalogue for the frontend.

        Includes ``info`` (per-type metadata) and ``categories``
        (logical groupings).
        """
        return {
            "info": NODE_TYPE_INFO,
            "categories": NODE_TYPE_CATEGORIES,
        }


# ------------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------------


def get_workflow_service() -> WorkflowService:
    """FastAPI dependency for WorkflowService."""
    return WorkflowService.get_instance()
