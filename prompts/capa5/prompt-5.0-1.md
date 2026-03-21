## ═══════════════════════════════════════
## MICRO-FASE 5.0 — NodeBase Template
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.0-1 [VSCODE] — Clase base abstracta NodeBase + NodeWrapper frontend

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.0 de Capa 5 (Órganos): crear la clase base abstracta NodeBase de la que heredan TODOS los nodos del sistema, y el wrapper frontend que les da estructura visual.

CONTEXTO:
- Capas 0-4 completadas: infraestructura, esqueleto, cerebro, cuerpo/UI, sistema nervioso
- Capa 5 = los ÓRGANOS de YeyoOS. Cada nodo es un órgano especializado
- Cada nodo corre en un container (Capa 4), tiene permisos, usa GPU scheduler
- Frontend: Next.js 14 + PixiJS 8 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI + PostgreSQL + Redis + Ollama qwen2.5:3b
- Hardware: GTX 1060 3GB VRAM, 16GB RAM
- NodeBase proporciona: lifecycle estándar, gestión de container, verificación de permisos, solicitud de GPU

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/nodes
   mkdir -p tests/unit/nodes
   mkdir -p frontend/src/components/nodes

2. Crear archivo src/nodes/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/__init__.py
   Contenido:
   from .base import NodeBase, NodeStatus, PrivilegeLevel

3. Crear archivo src/nodes/base.py:

   Ruta: ~/yeyo-os/src/nodes/base.py
   Contenido:

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

       # ═══════════════════════════════════
       # MÉTODOS ABSTRACTOS (cada nodo implementa)
       # ═══════════════════════════════════

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
           from src.gpu.scheduler import GPUScheduler

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
               from src.gpu.scheduler import GPUScheduler

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

4. Crear archivo tests/unit/nodes/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/nodes/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/nodes/test_node_base.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/test_node_base.py
   Contenido:

   """Tests para NodeBase Template — Micro-fase 5.0"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.base import NodeBase, NodeStatus, PrivilegeLevel, NodeEvent


   class ConcreteNode(NodeBase):
       """Implementación concreta para testing."""

       async def initialize(self):
           pass

       async def render_ui(self) -> dict:
           return {"component": "TestNode", "props": {}}

       async def process(self, input_data: dict) -> dict:
           return {"result": "processed", **input_data}

       async def cleanup(self):
           pass


   class TestNodeBaseAbstract:
       """Tests para verificar que NodeBase es abstracta."""

       def test_cannot_instantiate_directly(self):
           with pytest.raises(TypeError):
               NodeBase(name="test", version="1.0")

       def test_all_abstract_methods_present(self):
           abstract_methods = NodeBase.__abstractmethods__
           expected = {"initialize", "render_ui", "process", "cleanup"}
           assert abstract_methods == expected

       def test_has_four_abstract_methods(self):
           assert len(NodeBase.__abstractmethods__) == 4


   class TestNodeBaseLifecycle:
       """Tests para el lifecycle del nodo."""

       def test_concrete_node_instantiates(self):
           node = ConcreteNode(name="Test", version="1.0")
           assert node.name == "Test"
           assert node.version == "1.0"
           assert node.status == NodeStatus.CREATED

       def test_node_has_unique_id(self):
           node1 = ConcreteNode(name="A", version="1.0")
           node2 = ConcreteNode(name="B", version="1.0")
           assert node1.id != node2.id

       def test_default_privilege_is_sandbox(self):
           node = ConcreteNode(name="Test", version="1.0")
           assert node.privilege_level == PrivilegeLevel.SANDBOX

       def test_custom_privilege_level(self):
           node = ConcreteNode(
               name="Test", version="1.0",
               privilege_level=PrivilegeLevel.USER,
           )
           assert node.privilege_level == PrivilegeLevel.USER

       @pytest.mark.asyncio
       async def test_open_sets_ready(self):
           node = ConcreteNode(name="Test", version="1.0")
           await node.open()
           assert node.status == NodeStatus.READY

       @pytest.mark.asyncio
       async def test_close_sets_closed(self):
           node = ConcreteNode(name="Test", version="1.0")
           await node.open()
           await node.close()
           assert node.status == NodeStatus.CLOSED

       @pytest.mark.asyncio
       async def test_process_returns_result(self):
           node = ConcreteNode(name="Test", version="1.0")
           result = await node.process({"key": "value"})
           assert result["result"] == "processed"
           assert result["key"] == "value"

       @pytest.mark.asyncio
       async def test_render_ui_returns_component(self):
           node = ConcreteNode(name="Test", version="1.0")
           ui = await node.render_ui()
           assert "component" in ui

       @pytest.mark.asyncio
       async def test_get_status_returns_info(self):
           node = ConcreteNode(name="Test", version="1.0")
           status = await node.get_status()
           assert status["name"] == "Test"
           assert status["status"] == "created"
           assert status["gpu_allocated"] is False

       @pytest.mark.asyncio
       async def test_emit_event_stores_event(self):
           node = ConcreteNode(name="Test", version="1.0")
           await node.emit_event("test_event", {"data": 123})
           assert len(node._events) == 1
           assert node._events[0].event_type == "test_event"


   class TestNodeBaseGPU:
       """Tests para solicitud de GPU."""

       @pytest.mark.asyncio
       async def test_request_gpu_calls_scheduler(self):
           node = ConcreteNode(name="Test", version="1.0")
           mock_scheduler = MagicMock()
           mock_scheduler.allocate = AsyncMock(return_value=True)
           mock_scheduler.get_instance = MagicMock(return_value=mock_scheduler)

           with patch("src.nodes.base.GPUScheduler", mock_scheduler):
               result = await node.request_gpu(vram_mb=1024, priority=3)
               assert result is True
               assert node._gpu_allocated is True
               assert node._gpu_vram_mb == 1024

       @pytest.mark.asyncio
       async def test_release_gpu_frees_resources(self):
           node = ConcreteNode(name="Test", version="1.0")
           node._gpu_allocated = True
           node._gpu_vram_mb = 1024
           mock_scheduler = MagicMock()
           mock_scheduler.release = AsyncMock()
           mock_scheduler.get_instance = MagicMock(return_value=mock_scheduler)

           with patch("src.nodes.base.GPUScheduler", mock_scheduler):
               await node.release_gpu()
               assert node._gpu_allocated is False
               assert node._gpu_vram_mb == 0


   class TestNodeBasePermissions:
       """Tests para verificación de permisos."""

       @pytest.mark.asyncio
       async def test_check_permission_calls_manager(self):
           node = ConcreteNode(name="Test", version="1.0")
           mock_manager = MagicMock()
           mock_manager.check = AsyncMock(return_value=True)
           mock_manager.get_instance = MagicMock(return_value=mock_manager)

           with patch("src.nodes.base.PermissionManager", mock_manager):
               result = await node.check_permission("file.read")
               assert result is True
               assert "file.read" in node._permissions_granted

6. Crear archivo frontend/src/components/nodes/NodeWrapper.tsx:

   Ruta: ~/yeyo-os/frontend/src/components/nodes/NodeWrapper.tsx
   Contenido:

   /**
    * YeyoOS — NodeWrapper
    * Micro-fase 5.0 — Capa 5: Órganos
    *
    * Wrapper que proporciona header, minimizar, cerrar, redimensionar
    * a TODOS los nodos del Neural Hub.
    */

   'use client';

   import React, { useState, useCallback, ReactNode } from 'react';

   interface NodeWrapperProps {
     nodeId: string;
     title: string;
     icon?: string;
     children: ReactNode;
     onClose?: (nodeId: string) => void;
     onMinimize?: (nodeId: string) => void;
     initialWidth?: number;
     initialHeight?: number;
     className?: string;
   }

   interface NodeSize {
     width: number;
     height: number;
   }

   export default function NodeWrapper({
     nodeId,
     title,
     icon = '📦',
     children,
     onClose,
     onMinimize,
     initialWidth = 600,
     initialHeight = 400,
     className = '',
   }: NodeWrapperProps) {
     const [isMinimized, setIsMinimized] = useState(false);
     const [size, setSize] = useState<NodeSize>({
       width: initialWidth,
       height: initialHeight,
     });

     const handleMinimize = useCallback(() => {
       setIsMinimized((prev) => !prev);
       onMinimize?.(nodeId);
     }, [nodeId, onMinimize]);

     const handleClose = useCallback(() => {
       onClose?.(nodeId);
     }, [nodeId, onClose]);

     return (
       <div
         className={`flex flex-col bg-gray-900 border border-gray-700 rounded-lg
                     shadow-xl overflow-hidden ${className}`}
         style={{
           width: size.width,
           height: isMinimized ? 40 : size.height,
         }}
       >
         {/* Header */}
         <div className="flex items-center justify-between px-3 py-2
                         bg-gray-800 border-b border-gray-700 cursor-move
                         select-none shrink-0"
         >
           <div className="flex items-center gap-2">
             <span className="text-sm">{icon}</span>
             <span className="text-sm font-medium text-gray-200 truncate">
               {title}
             </span>
           </div>

           <div className="flex items-center gap-1">
             {/* Minimizar */}
             <button
               onClick={handleMinimize}
               className="w-6 h-6 flex items-center justify-center rounded
                          hover:bg-gray-600 text-gray-400 hover:text-yellow-400
                          transition-colors"
               aria-label="Minimizar"
             >
               <span className="text-xs">─</span>
             </button>

             {/* Cerrar */}
             <button
               onClick={handleClose}
               className="w-6 h-6 flex items-center justify-center rounded
                          hover:bg-red-600 text-gray-400 hover:text-white
                          transition-colors"
               aria-label="Cerrar"
             >
               <span className="text-xs">✕</span>
             </button>
           </div>
         </div>

         {/* Content */}
         {!isMinimized && (
           <div className="flex-1 overflow-auto p-3">
             {children}
           </div>
         )}

         {/* Resize handle */}
         {!isMinimized && (
           <div
             className="absolute bottom-0 right-0 w-4 h-4 cursor-se-resize
                        opacity-50 hover:opacity-100"
             aria-label="Redimensionar"
           >
             <svg viewBox="0 0 16 16" className="w-full h-full text-gray-500">
               <path
                 d="M14 14H10M14 14V10M14 8V14H8"
                 stroke="currentColor"
                 strokeWidth="1.5"
                 fill="none"
               />
             </svg>
           </div>
         )}
       </div>
     );
   }

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/test_node_base.py -v

VERIFICAR:
- [ ] Archivo src/nodes/base.py existe con NodeBase, NodeStatus, PrivilegeLevel
- [ ] NodeBase NO se puede instanciar directamente (abstracta)
- [ ] 4 métodos abstractos: initialize, render_ui, process, cleanup
- [ ] Métodos comunes: request_gpu, release_gpu, check_permission, emit_event, get_status
- [ ] Lifecycle open() y close() funcionan
- [ ] Frontend: NodeWrapper.tsx existe con header, minimizar, cerrar, resize
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py en todos los directorios
- GPUScheduler no existe: los tests usan mocks, no necesita existir aún
- PermissionManager no existe: los tests usan mocks
- pytest-asyncio: `pip install pytest-asyncio`

NO HACER:
- No implementar nodos concretos aún (eso es 5.1+)
- No crear containers reales
- No conectar con GPU scheduler real (solo interfaz)
- No implementar drag & drop en NodeWrapper (eso es Capa 4.6)

GATE: NodeBase es abstracta con 4 métodos, lifecycle funciona, GPU request y permisos a través de mocks, NodeWrapper renderiza con header/minimize/close, todos los tests pasan.
```
