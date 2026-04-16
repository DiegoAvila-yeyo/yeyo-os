"""
YeyoOS — Workflow Orchestrator API Routes
CRUD + execution + WebSocket for workflow management.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel, Field

from src.workflows.service import WorkflowService, get_workflow_service
from src.workflows.models import NODE_TYPE_INFO, NODE_TYPE_CATEGORIES

logger = logging.getLogger("yeyoos.api.workflows")

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class WorkflowCreate(BaseModel):
    """Schema for creating a new workflow."""

    name: str
    description: str = ""
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    trigger_type: str = "manual"
    trigger_config: dict = Field(default_factory=dict)
    variables: dict = Field(default_factory=dict)


class WorkflowUpdate(BaseModel):
    """Schema for partially updating an existing workflow."""

    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[list[dict]] = None
    edges: Optional[list[dict]] = None
    trigger_type: Optional[str] = None
    trigger_config: Optional[dict] = None
    variables: Optional[dict] = None
    status: Optional[str] = None


class WorkflowExecuteRequest(BaseModel):
    """Schema for triggering a workflow execution."""

    variables: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------

@router.post("/", status_code=201)
async def create_workflow(
    payload: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Create a new workflow definition."""
    workflow = await service.create_workflow(
        name=payload.name,
        description=payload.description,
        nodes=payload.nodes,
        edges=payload.edges,
        trigger_type=payload.trigger_type,
        trigger_config=payload.trigger_config,
        variables=payload.variables,
    )
    return workflow.to_dict()


@router.get("/")
async def list_workflows(
    service: WorkflowService = Depends(get_workflow_service),
):
    """Return every workflow definition."""
    workflows = await service.list_workflows()
    return [w.to_dict() for w in workflows]


@router.get("/node-types")
async def get_node_types():
    """Return the catalogue of available node types and their categories."""

    def _serialize(obj):
        """Convert enum keys/values to plain strings for JSON transport."""
        if isinstance(obj, dict):
            return {str(k): _serialize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_serialize(i) for i in obj]
        if hasattr(obj, "value"):
            return obj.value
        return obj

    return {
        "types": _serialize(NODE_TYPE_INFO),
        "categories": _serialize(NODE_TYPE_CATEGORIES),
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Retrieve a single workflow by ID."""
    workflow = await service.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow.to_dict()


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Update an existing workflow definition."""
    updates = payload.model_dump(exclude_none=True)
    workflow = await service.update_workflow(workflow_id, updates)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow.to_dict()


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Delete a workflow and its execution history."""
    deleted = await service.delete_workflow(workflow_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"detail": "Workflow deleted"}


# ---------------------------------------------------------------------------
# Execution Endpoints
# ---------------------------------------------------------------------------

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    payload: WorkflowExecuteRequest,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Start a new execution for the given workflow."""
    workflow = await service.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    execution = await service.execute_workflow(workflow_id, variables=payload.variables)
    return execution.to_dict()


@router.get("/{workflow_id}/executions")
async def list_executions(
    workflow_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """List all executions belonging to a workflow."""
    executions = await service.list_executions(workflow_id)
    return [e.to_dict() for e in executions]


@router.get("/executions/{exec_id}")
async def get_execution(
    exec_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Retrieve a single execution by ID."""
    execution = await service.get_execution(exec_id)
    if execution is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution.to_dict()


# ---------------------------------------------------------------------------
# WebSocket — live execution updates
# ---------------------------------------------------------------------------

@router.websocket("/ws/{exec_id}")
async def execution_ws(
    websocket: WebSocket,
    exec_id: str,
    service: WorkflowService = Depends(get_workflow_service),
):
    """Stream real-time execution progress to the client."""
    await websocket.accept()
    engine = service.engine
    engine.ws_connections.setdefault(exec_id, []).append(websocket)
    logger.info("WebSocket connected for execution %s", exec_id)

    try:
        while True:
            # Keep the connection alive; handle ping/pong or client messages.
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for execution %s", exec_id)
    finally:
        connections = engine.ws_connections.get(exec_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            engine.ws_connections.pop(exec_id, None)
