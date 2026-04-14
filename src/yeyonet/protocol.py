"""
YeyoNet — Protocolo de mensajes entre nodos.
Todos los mensajes usan un envelope JSON estandarizado.
"""
from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    # Control
    HEARTBEAT = "heartbeat"
    AUTH = "auth"
    AUTH_OK = "auth_ok"
    AUTH_FAIL = "auth_fail"
    ACK = "ack"

    # Jobs
    JOB_ASSIGN = "job_assign"
    JOB_ACCEPT = "job_accept"
    JOB_REJECT = "job_reject"
    JOB_PROGRESS = "job_progress"
    JOB_RESULT = "job_result"
    JOB_CANCEL = "job_cancel"

    # Memory sync
    MEMORY_SYNC = "memory_sync"
    MEMORY_SYNC_ACK = "memory_sync_ack"

    # Commands (cross-device)
    COMMAND = "command"
    COMMAND_RESULT = "command_result"

    # Status
    STATUS_UPDATE = "status_update"
    RESOURCE_REPORT = "resource_report"


class NetMessage(BaseModel):
    """Envelope estándar para todos los mensajes YeyoNet."""
    msg_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    from_node: str = ""
    to_node: str = ""       # vacío = broadcast / para el Central
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    reply_to: Optional[str] = None  # msg_id al que responde (para ACKs)

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "NetMessage":
        return cls.model_validate_json(data)

    def ack(self, payload: dict | None = None) -> "NetMessage":
        """Crea un ACK para este mensaje."""
        return NetMessage(
            type=MessageType.ACK,
            from_node=self.to_node,
            to_node=self.from_node,
            reply_to=self.msg_id,
            payload=payload or {},
        )


# ─── Factory helpers ─────────────────────────────────────────

def make_auth(node_id: str, auth_token: str) -> NetMessage:
    return NetMessage(
        type=MessageType.AUTH,
        from_node=node_id,
        payload={"auth_token": auth_token},
    )


def make_heartbeat(node_id: str) -> NetMessage:
    return NetMessage(
        type=MessageType.HEARTBEAT,
        from_node=node_id,
    )


def make_resource_report(node_id: str, resources: dict) -> NetMessage:
    return NetMessage(
        type=MessageType.RESOURCE_REPORT,
        from_node=node_id,
        payload=resources,
    )


def make_job_assign(from_node: str, to_node: str, job_id: str, job_type: str, payload: dict) -> NetMessage:
    return NetMessage(
        type=MessageType.JOB_ASSIGN,
        from_node=from_node,
        to_node=to_node,
        payload={"job_id": job_id, "job_type": job_type, **payload},
    )


def make_job_progress(node_id: str, job_id: str, progress: int, detail: str = "") -> NetMessage:
    return NetMessage(
        type=MessageType.JOB_PROGRESS,
        from_node=node_id,
        payload={"job_id": job_id, "progress": progress, "detail": detail},
    )


def make_job_result(node_id: str, job_id: str, success: bool, data: dict | None = None, error: str = "") -> NetMessage:
    return NetMessage(
        type=MessageType.JOB_RESULT,
        from_node=node_id,
        payload={"job_id": job_id, "success": success, "data": data or {}, "error": error},
    )
