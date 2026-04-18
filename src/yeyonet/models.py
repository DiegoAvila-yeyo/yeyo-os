"""
YeyoNet — Modelos de datos para la red distribuida.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Enums ───────────────────────────────────────────────────

class NodeRole(str, Enum):
    CENTRAL = "central"
    SATELLITE = "satellite"


class SatelliteMode(str, Enum):
    COMPLETO = "completo"    # GPU + todos los modelos
    LIGERO = "ligero"        # Chat local, delega GPU
    MINIMO = "minimo"        # Solo UI, todo delegado


class NodeStatus(str, Enum):
    ONLINE = "online"
    IDLE = "idle"
    OFFLINE = "offline"


class Permission(str, Enum):
    CHAT = "chat"
    GRAFOS = "grafos"
    MEMORIA = "memoria"
    CONTROL = "control"


class JobType(str, Enum):
    IMAGE_GENERATE = "image_generate"
    VIDEO_RENDER = "video_render"
    TEXT_INFERENCE = "text_inference"
    TRAINING_STEP = "training_step"
    MEMORY_SYNC = "memory_sync"
    CUSTOM = "custom"
    PIPELINE_STEP = "pipeline_step"


class JobStatus(str, Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStepStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ─── Resource info reportada por cada nodo ───────────────────

class NodeResources(BaseModel):
    cpu_percent: float = 0.0
    ram_free_gb: float = 0.0
    gpu_name: Optional[str] = None
    gpu_vram_mb: int = 0
    gpu_usage_percent: float = 0.0
    ollama_models: list[str] = Field(default_factory=list)
    active_jobs: int = 0


# ─── Nodo de la red ──────────────────────────────────────────

class YeyoNetNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    role: NodeRole = NodeRole.SATELLITE
    mode: SatelliteMode = SatelliteMode.COMPLETO
    status: NodeStatus = NodeStatus.OFFLINE
    auth_token: str = ""
    permissions: list[Permission] = Field(default_factory=lambda: [Permission.CHAT])
    visibility_level: int = Field(default=1, ge=1, le=4)
    resources: NodeResources = Field(default_factory=NodeResources)
    ollama_host: Optional[str] = None
    ip_address: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── Invitación ──────────────────────────────────────────────

class YeyoNetInvitation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    satellite_name: str
    permissions: list[Permission] = Field(default_factory=lambda: [Permission.CHAT])
    visibility_level: int = Field(default=1, ge=1, le=4)
    used: bool = False
    used_by_node_id: Optional[str] = None
    used_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_expired(self) -> bool:
        from datetime import timezone
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return now > expires

    @property
    def is_available(self) -> bool:
        return not self.used and not self.is_expired


# ─── Job ─────────────────────────────────────────────────────

class YeyoNetJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: JobType
    status: JobStatus = JobStatus.QUEUED
    requested_by: Optional[str] = None
    assigned_to: Optional[str] = None
    payload: dict = Field(default_factory=dict)
    result: Optional[dict] = None
    progress: int = Field(default=0, ge=0, le=100)
    progress_detail: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=10)
    attempt: int = 1
    max_attempts: int = 3
    timeout_seconds: int = 600
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─── API Request/Response models ─────────────────────────────

class InviteRequest(BaseModel):
    satellite_name: str = Field(..., min_length=1, max_length=100)
    permissions: list[Permission] = Field(default_factory=lambda: [Permission.CHAT])
    visibility_level: int = Field(default=1, ge=1, le=4)
    expires_in_days: int = Field(default=7, ge=1, le=9999)


class RegisterRequest(BaseModel):
    code: str = Field(..., min_length=19, max_length=19)
    node_name: Optional[str] = None
    mode: SatelliteMode = SatelliteMode.COMPLETO
    ollama_host: Optional[str] = None


class RegisterResponse(BaseModel):
    node_id: str
    auth_token: str
    central_ws_url: str
    permissions: list[Permission]
    visibility_level: int


class SatelliteUpdate(BaseModel):
    name: Optional[str] = None
    permissions: Optional[list[Permission]] = None
    visibility_level: Optional[int] = Field(default=None, ge=1, le=4)


class JobCreateRequest(BaseModel):
    type: JobType
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    timeout_seconds: int = Field(default=600, ge=30, le=7200)


class PipelineRunCreateRequest(BaseModel):
    flow_id: str = Field(default="image_prompt_ring_v1", min_length=1, max_length=100)
    input: dict = Field(default_factory=dict)
    ring_node_ids: list[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
