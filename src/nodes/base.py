"""
YeyoOS — NodeBase Template
Micro-fase 5.0 — Capa 5: Órganos

Clase base abstracta de la que heredan TODOS los nodos.
Proporciona lifecycle estándar, gestión de container,
verificación de permisos y solicitud de GPU.
"""

import uuid
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass, field


class NodeStatus(str, Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    CLOSING = "closing"
    CLOSED = "closed"


class PrivilegeLevel(int, Enum):
    """Niveles de privilegio de Capa 4."""
    ROOT = 0      # L0 — Solo sistema
    ADMIN = 1     # L1 — Administrador
    USER = 2      # L2 — Usuario normal
    LIMITED = 3   # L3 — Limitado
    GUEST = 4     # L4 — Invitado
    SANDBOX = 5   # L5 — Sandbox (nodos IA SIEMPRE aquí)


@dataclass
class NodeEvent:
    """Evento emitido por un nodo."""
    event_type: str
    data: Any
    node_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NodeBase(ABC):
    """
    Clase base abstracta para TODOS los nodos de YeyoOS.
    Cada nodo es un órgano especializado que cobra vida dentro del Neural Hub.
    """

    def __init__(
        self,
        name: str,
        version: str,
        privilege_level: PrivilegeLevel = PrivilegeLevel.SANDBOX,
        container_config: Optional[dict] = None,
    ):
        self.id = f"node-{uuid.uuid4().hex[:8]}"
        self.name = name
        self.version = version
        self.privilege_level = privilege_level
        self.container_config = container_config or {}
        self.status = NodeStatus.CREATED
        self.created_at = datetime.now(timezone.utc)
        self._events: list[NodeEvent] = []
        self._permissions_granted: set[str] = set()
        self._gpu_allocated: bool = False
        self._gpu_vram_mb: int = 0
        self._memory_service = None  # NodeMemoryService — inyectado después de crear el nodo

    # ═══════════════════════════════════
    # MÉTODOS ABSTRACTOS (cada nodo implementa)
    # ═══════════════════════════════════

    def set_memory_service(self, service) -> None:
        """Inyecta el servicio de memoria del nodo (NodeMemoryService)."""
        self._memory_service = service

    @abstractmethod
    async def initialize(self) -> None:
        """Inicializa el nodo: carga recursos, prepara container."""
        ...

    @abstractmethod
    async def render_ui(self) -> dict:
        """Retorna configuración del componente React para el frontend."""
        ...

    @abstractmethod
    async def process(self, input_data: dict) -> dict:
        """Procesa datos de entrada y retorna resultado."""
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Limpia recursos: cierra container, libera GPU, etc."""
        ...

    # ═══════════════════════════════════
    # MÉTODOS COMUNES (heredados por todos)
    # ═══════════════════════════════════

    async def request_gpu(self, vram_mb: int, priority: int = 5) -> bool:
        """
        Solicita VRAM al GPU Scheduler (Capa 3).
        priority: 1 (máxima) a 10 (mínima).
        Retorna True si la GPU fue asignada.
        """
        from src.core.gpu_scheduler import GPUScheduler

        scheduler = GPUScheduler.get_instance()
        allocated = await scheduler.allocate(
            node_id=self.id,
            vram_mb=vram_mb,
            priority=priority,
        )

        if allocated:
            self._gpu_allocated = True
            self._gpu_vram_mb = vram_mb
            await self.emit_event("gpu_allocated", {"vram_mb": vram_mb})

        return allocated

    async def release_gpu(self) -> None:
        """Libera la GPU asignada."""
        if self._gpu_allocated:
            from src.core.gpu_scheduler import GPUScheduler

            scheduler = GPUScheduler.get_instance()
            await scheduler.release(node_id=self.id)
            self._gpu_allocated = False
            self._gpu_vram_mb = 0
            await self.emit_event("gpu_released", {})

    async def check_permission(self, permission: str) -> bool:
        """
        Verifica si el nodo tiene un permiso específico.
        Usa el sistema de permisos ALLOWLIST de Capa 4.
        """
        from src.security.permissions import PermissionManager

        manager = PermissionManager.get_instance()
        allowed = await manager.check(
            node_id=self.id,
            privilege_level=self.privilege_level,
            permission=permission,
        )

        if allowed:
            self._permissions_granted.add(permission)

        return allowed

    async def emit_event(self, event_type: str, data: Any) -> None:
        """Emite un evento del nodo (para comunicación entre nodos)."""
        event = NodeEvent(
            event_type=event_type,
            data=data,
            node_id=self.id,
        )
        self._events.append(event)

    async def get_status(self) -> dict:
        """Retorna el estado completo del nodo."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "privilege_level": self.privilege_level.value,
            "gpu_allocated": self._gpu_allocated,
            "gpu_vram_mb": self._gpu_vram_mb,
            "permissions": list(self._permissions_granted),
            "created_at": self.created_at.isoformat(),
            "events_count": len(self._events),
        }

    async def open(self) -> None:
        """Lifecycle: abre el nodo (initialize + render)."""
        self.status = NodeStatus.INITIALIZING
        try:
            await self.initialize()
            self.status = NodeStatus.READY
            await self.emit_event("node_opened", {"name": self.name})
        except Exception as e:
            self.status = NodeStatus.ERROR
            await self.emit_event("node_error", {"error": str(e)})
            raise

    async def close(self) -> None:
        """Lifecycle: cierra el nodo (cleanup + release)."""
        self.status = NodeStatus.CLOSING
        try:
            await self.release_gpu()
            await self.cleanup()
            self.status = NodeStatus.CLOSED
            await self.emit_event("node_closed", {"name": self.name})
        except Exception as e:
            self.status = NodeStatus.ERROR
            await self.emit_event("node_error", {"error": str(e)})
            raise
