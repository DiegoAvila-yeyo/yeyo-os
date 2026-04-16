"""
YeyoOS — Workflow Orchestrator Models
Internal workflow system for chaining YeyoOS nodes (image_gen, video, chat, etc.)
Different from the Automation node (which handles external WhatsApp/email).
"""

import uuid
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass, field


class NodeType(str, Enum):
    """Types of nodes available in the workflow designer."""
    IMAGE_GEN = "image_gen"
    VIDEO_GEN = "video_gen"
    SLIDESHOW = "slideshow"
    CHAT = "chat"
    FILTER = "filter"
    CODE = "code"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    HTTP_REQUEST = "http_request"
    CONDITION = "condition"
    LOOP = "loop"
    DELAY = "delay"


class WorkflowStatus(str, Enum):
    """Status of a workflow definition."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class TriggerType(str, Enum):
    """How a workflow can be triggered."""
    MANUAL = "manual"
    CRON = "cron"
    EVENT = "event"


NODE_TYPE_CATEGORIES = {
    "IA & Media": [NodeType.IMAGE_GEN, NodeType.VIDEO_GEN, NodeType.SLIDESHOW, NodeType.CHAT, NodeType.FILTER],
    "Code & Files": [NodeType.CODE, NodeType.FILE_READ, NodeType.FILE_WRITE],
    "Memory": [NodeType.MEMORY_READ, NodeType.MEMORY_WRITE],
    "Logic": [NodeType.CONDITION, NodeType.LOOP, NodeType.DELAY],
    "External": [NodeType.HTTP_REQUEST],
}

NODE_TYPE_INFO = {
    NodeType.IMAGE_GEN: {"label": "🖼️ Image Generation", "description": "Generate images with AI", "color": "#8B5CF6"},
    NodeType.VIDEO_GEN: {"label": "🎬 Video Generation", "description": "Generate videos with AI", "color": "#6366F1"},
    NodeType.SLIDESHOW: {"label": "📽️ Slideshow", "description": "Create slideshow from images", "color": "#818CF8"},
    NodeType.CHAT: {"label": "💬 Chat AI", "description": "Get AI text response", "color": "#06B6D4"},
    NodeType.FILTER: {"label": "🔍 AI Filter", "description": "Score/filter content with AI", "color": "#14B8A6"},
    NodeType.CODE: {"label": "🐍 Code", "description": "Run Python code in sandbox", "color": "#F59E0B"},
    NodeType.MEMORY_READ: {"label": "🧠 Memory Read", "description": "Read from Flash Memory", "color": "#EC4899"},
    NodeType.MEMORY_WRITE: {"label": "📝 Memory Write", "description": "Write to Flash Memory", "color": "#F472B6"},
    NodeType.FILE_READ: {"label": "📂 File Read", "description": "Read file contents", "color": "#10B981"},
    NodeType.FILE_WRITE: {"label": "💾 File Write", "description": "Write to a file", "color": "#34D399"},
    NodeType.HTTP_REQUEST: {"label": "🌐 HTTP Request", "description": "Make HTTP request", "color": "#F97316"},
    NodeType.CONDITION: {"label": "🔀 Condition", "description": "Branch based on condition", "color": "#EF4444"},
    NodeType.LOOP: {"label": "🔄 Loop", "description": "Repeat nodes N times", "color": "#F87171"},
    NodeType.DELAY: {"label": "⏱️ Delay", "description": "Wait for specified time", "color": "#6B7280"},
}


@dataclass
class WorkflowNode:
    """A single node in a workflow definition."""
    id: str = field(default_factory=lambda: f"wn-{uuid.uuid4().hex[:8]}")
    node_type: NodeType = NodeType.CHAT
    label: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0
    next_node_ids: list[str] = field(default_factory=list)
    # For condition nodes: true_branch and false_branch node IDs
    true_branch: Optional[str] = None
    false_branch: Optional[str] = None
    # For loop nodes: body node IDs and iteration count
    loop_body: list[str] = field(default_factory=list)
    loop_count: int = 1

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "label": self.label or NODE_TYPE_INFO.get(self.node_type, {}).get("label", self.node_type.value),
            "config": self.config,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "next_node_ids": self.next_node_ids,
            "true_branch": self.true_branch,
            "false_branch": self.false_branch,
            "loop_body": self.loop_body,
            "loop_count": self.loop_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowNode":
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", f"wn-{uuid.uuid4().hex[:8]}"),
            node_type=NodeType(data["node_type"]),
            label=data.get("label", ""),
            config=data.get("config", {}),
            position_x=data.get("position_x", 0.0),
            position_y=data.get("position_y", 0.0),
            next_node_ids=data.get("next_node_ids", []),
            true_branch=data.get("true_branch"),
            false_branch=data.get("false_branch"),
            loop_body=data.get("loop_body", []),
            loop_count=data.get("loop_count", 1),
        )


@dataclass
class WorkflowEdge:
    """Connection between two workflow nodes."""
    id: str = field(default_factory=lambda: f"we-{uuid.uuid4().hex[:8]}")
    source_id: str = ""
    target_id: str = ""
    label: str = ""
    edge_type: str = "default"  # "default", "true", "false"

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dictionary."""
        return {
            "target_id": self.target_id,
            "label": self.label,
            "edge_type": self.edge_type,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowEdge":
        """Deserialize from a dictionary."""
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            label=data.get("label", ""),
            edge_type=data.get("edge_type", "default"),
        )


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str = field(default_factory=lambda: f"wf-{uuid.uuid4().hex[:8]}")
    name: str = "New Workflow"
    description: str = ""
    status: WorkflowStatus = WorkflowStatus.DRAFT
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_config: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_entry_node(self) -> Optional[WorkflowNode]:
        """Find the first node (no incoming edges)."""
        target_ids = {e.target_id for e in self.edges}
        for node in self.nodes:
            if node.id not in target_ids:
                return node
        return self.nodes[0] if self.nodes else None

    def get_node_by_id(self, node_id: str) -> Optional[WorkflowNode]:
        """Find a node by its ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_next_nodes(self, node_id: str) -> list[WorkflowNode]:
        """Get all nodes connected after the given node."""
        next_ids = []
        for edge in self.edges:
            if edge.source_id == node_id:
                next_ids.append(edge.target_id)
        node = self.get_node_by_id(node_id)
        if node:
            next_ids.extend(node.next_node_ids)
        return [n for n in (self.get_node_by_id(nid) for nid in next_ids) if n is not None]

    def to_dict(self) -> dict:
        """Serialize the full workflow to a JSON-friendly dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "trigger_type": self.trigger_type.value,
            "trigger_config": self.trigger_config,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Workflow":
        """Deserialize from a dictionary (e.g. JSON from DB or API)."""
        return cls(
            name=data.get("name", "New Workflow"),
            description=data.get("description", ""),
            status=WorkflowStatus(data.get("status", "draft")),
            nodes=[WorkflowNode.from_dict(n) for n in data.get("nodes", [])],
            edges=[WorkflowEdge.from_dict(e) for e in data.get("edges", [])],
            trigger_type=TriggerType(data.get("trigger_type", "manual")),
            trigger_config=data.get("trigger_config", {}),
            variables=data.get("variables", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(timezone.utc),
        )


@dataclass
class NodeExecutionResult:
    """Result of executing a single workflow node."""
    node_id: str
    node_type: NodeType
    status: ExecutionStatus = ExecutionStatus.COMPLETED
    output: Any = None
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    retry_count: int = 0

    def to_dict(self) -> dict:
        """Serialize the node result to a JSON-friendly dictionary."""
        return {
            "node_type": self.node_type.value,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "retry_count": self.retry_count,
        }


@dataclass
class WorkflowExecution:
    """A single execution run of a workflow."""
    id: str = field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:8]}")
    workflow_id: str = ""
    workflow_name: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    node_results: list[NodeExecutionResult] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    robot_id: Optional[str] = None
    trigger_type: TriggerType = TriggerType.MANUAL
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    current_node_index: int = 0
    total_nodes: int = 0

    @property
    def progress(self) -> float:
        """Progress as 0.0 to 1.0."""
        if self.total_nodes == 0:
            return 0.0
        return min(self.current_node_index / self.total_nodes, 1.0)

    def to_dict(self) -> dict:
        """Serialize the execution state to a JSON-friendly dictionary."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status.value,
            "node_results": [r.to_dict() for r in self.node_results],
            "variables": self.variables,
            "robot_id": self.robot_id,
            "trigger_type": self.trigger_type.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "current_node_index": self.current_node_index,
            "total_nodes": self.total_nodes,
            "progress": self.progress,
        }
