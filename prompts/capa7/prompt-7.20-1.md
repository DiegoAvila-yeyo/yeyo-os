## ═══════════════════════════════════════
## MICRO-FASE 7.20 — YeyoNet Cluster Mode: Distributed GPU Scheduler
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.20-1 [VSCODE] — GPU Pool distribuido con gRPC: registro de VRAM por nodo, allocate_best, integración con YeyoOrquestador

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.20 de Capa 7 (Evolución): implementar el GPU Pool distribuido con gRPC. Cada nodo de la red YeyoNet reporta su VRAM disponible en tiempo real. El YeyoOrquestador consulta al GPUPool para decidir en qué nodo ejecutar operaciones que requieren GPU, eligiendo siempre el nodo con más VRAM libre.

CONTEXTO:
- Micro-fase 7.19 completada: Celery workers, ClusterScheduler, IdleDetector, cluster_api funcionando
- Stack: FastAPI (Python), gRPC (grpcio, grpcio-tools), protobuf, Redis (ya existe)
- Cada nodo tiene un gRPC server (NodeService) que expone: GetStatus, AllocateGPU, ReleaseGPU, StreamMetrics
- El Central tiene el GPUPool que agrega VRAM de todos los nodos
- Integración con YeyoOrquestador: cuando un grafo necesita GPU, llama a GPUPool.allocate_best(vram_needed)
- La actualización de métricas es en tiempo real via gRPC streaming (no polling)
- Hardware objetivo: nodos pueden tener 0-24GB VRAM — el pool maneja todos los casos

Abre el directorio ~/yeyo-os en VS Code.

INSTALAR (ejecutar en terminal antes de crear archivos):
pip install grpcio grpcio-tools prometheus-client

CREAR:

1. Crear archivo src/cluster/node.proto:

   Ruta: ~/yeyo-os/src/cluster/node.proto
   Contenido:

   syntax = "proto3";

   package yeyonet.cluster;

   option py_generic_services = false;

   // NodeService — expuesto por cada nodo satélite
   service NodeService {
     // Obtiene el estado actual del nodo (VRAM, CPU, RAM, estado idle)
     rpc GetStatus (StatusRequest) returns (NodeStatus);

     // Reserva VRAM en el nodo para una tarea específica
     rpc AllocateGPU (AllocateRequest) returns (AllocateResponse);

     // Libera la VRAM reservada cuando la tarea termina
     rpc ReleaseGPU (ReleaseRequest) returns (ReleaseResponse);

     // Stream de métricas en tiempo real (cada N segundos)
     rpc StreamMetrics (MetricsStreamRequest) returns (stream NodeMetrics);
   }

   message StatusRequest {
     string requester_id = 1;
   }

   message NodeStatus {
     string node_id = 1;
     int64 vram_total_mb = 2;
     int64 vram_free_mb = 3;
     int64 vram_allocated_mb = 4;
     int64 ram_total_mb = 5;
     int64 ram_free_mb = 6;
     double cpu_percent = 7;
     bool is_idle = 8;
     string tailscale_ip = 9;
     int64 timestamp_unix = 10;
     repeated string active_task_ids = 11;
   }

   message AllocateRequest {
     string task_id = 1;
     int64 vram_needed_mb = 2;
     string requester_id = 3;
   }

   message AllocateResponse {
     bool success = 1;
     string allocation_id = 2;
     int64 vram_allocated_mb = 3;
     string error = 4;
   }

   message ReleaseRequest {
     string allocation_id = 1;
     string task_id = 2;
   }

   message ReleaseResponse {
     bool success = 1;
     int64 vram_freed_mb = 2;
     string error = 3;
   }

   message MetricsStreamRequest {
     string requester_id = 1;
     int32 interval_seconds = 2;  // intervalo entre métricas (default: 5)
   }

   message NodeMetrics {
     string node_id = 1;
     int64 vram_free_mb = 2;
     int64 vram_total_mb = 3;
     double cpu_percent = 4;
     int64 ram_free_mb = 5;
     double gpu_utilization_percent = 6;
     int64 timestamp_unix = 7;
   }

2. Crear script scripts/gen_grpc.sh (para generar el código Python desde el proto):

   Ruta: ~/yeyo-os/scripts/gen_grpc.sh
   Contenido:

   #!/bin/bash
   # Genera código Python gRPC desde src/cluster/node.proto
   # Uso: bash scripts/gen_grpc.sh
   set -euo pipefail

   PROTO_DIR="src/cluster"
   OUT_DIR="src/cluster"

   python -m grpc_tools.protoc \
       -I "$PROTO_DIR" \
       --python_out="$OUT_DIR" \
       --grpc_python_out="$OUT_DIR" \
       "$PROTO_DIR/node.proto"

   echo "✅ Código gRPC generado en $OUT_DIR/"
   echo "   - node_pb2.py"
   echo "   - node_pb2_grpc.py"

3. Crear archivo src/cluster/grpc_service.py:

   Ruta: ~/yeyo-os/src/cluster/grpc_service.py
   Contenido:

   """
   YeyoNet Cluster Mode — gRPC Server y Client para NodeService
   Micro-fase 7.20 — Capa 7: Evolución

   NodeServiceServer: corre en cada satélite, expone VRAM/CPU/RAM via gRPC
   NodeServiceClient: el Central lo usa para consultar y allocar GPU en satélites
   """

   from __future__ import annotations

   import asyncio
   import logging
   import os
   import time
   import uuid
   from dataclasses import dataclass, field
   from typing import AsyncIterator, Dict, List, Optional

   import grpc
   from grpc import aio as grpc_aio

   logger = logging.getLogger(__name__)

   # Puerto gRPC por defecto para el NodeService
   GRPC_PORT = int(os.environ.get("YEYO_GRPC_PORT", "50051"))


   def _get_gpu_metrics() -> Dict[str, int | float]:
       """Obtiene métricas GPU del nodo actual via nvidia-smi o pynvml."""
       try:
           import pynvml

           pynvml.nvmlInit()
           handle = pynvml.nvmlDeviceGetHandleByIndex(0)
           info = pynvml.nvmlDeviceGetMemoryInfo(handle)
           utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
           pynvml.nvmlShutdown()

           return {
               "vram_total_mb": info.total // (1024 * 1024),
               "vram_free_mb": info.free // (1024 * 1024),
               "gpu_utilization_percent": float(utilization.gpu),
           }
       except Exception:
           # Sin GPU o pynvml no disponible
           return {
               "vram_total_mb": 0,
               "vram_free_mb": 0,
               "gpu_utilization_percent": 0.0,
           }


   def _get_system_metrics() -> Dict[str, int | float]:
       """Obtiene métricas del sistema (CPU, RAM)."""
       try:
           import psutil

           mem = psutil.virtual_memory()
           cpu = psutil.cpu_percent(interval=0.1)
           return {
               "ram_total_mb": mem.total // (1024 * 1024),
               "ram_free_mb": mem.available // (1024 * 1024),
               "cpu_percent": cpu,
           }
       except Exception:
           return {"ram_total_mb": 0, "ram_free_mb": 0, "cpu_percent": 0.0}


   # ── gRPC Server (corre en el satélite) ──────────────────────────────────────

   class NodeServiceServicer:
       """
       Implementación del NodeService gRPC en el satélite.
       Expone métricas de hardware y gestiona allocaciones de VRAM.
       """

       def __init__(self, node_id: str, is_idle_fn=None) -> None:
           self.node_id = node_id
           self._is_idle_fn = is_idle_fn or (lambda: False)
           self._allocations: Dict[str, int] = {}  # allocation_id → vram_mb

       def _build_status(self) -> dict:
           gpu = _get_gpu_metrics()
           sys = _get_system_metrics()
           allocated = sum(self._allocations.values())
           return {
               "node_id": self.node_id,
               "vram_total_mb": gpu["vram_total_mb"],
               "vram_free_mb": max(0, gpu["vram_free_mb"] - allocated),
               "vram_allocated_mb": allocated,
               "ram_total_mb": sys["ram_total_mb"],
               "ram_free_mb": sys["ram_free_mb"],
               "cpu_percent": sys["cpu_percent"],
               "is_idle": self._is_idle_fn(),
               "tailscale_ip": os.environ.get("TAILSCALE_IP", ""),
               "timestamp_unix": int(time.time()),
               "active_task_ids": list(self._allocations.keys()),
           }

       async def GetStatus(self, request, context):
           """Retorna el estado actual del nodo."""
           try:
               from src.cluster import node_pb2
           except ImportError:
               # Mock para tests sin proto compilado
               return _MockNodeStatus(**self._build_status())

           status = self._build_status()
           return node_pb2.NodeStatus(**status)

       async def AllocateGPU(self, request, context):
           """Reserva VRAM para una tarea. Retorna allocation_id si hay suficiente VRAM libre."""
           try:
               from src.cluster import node_pb2
           except ImportError:
               return _MockAllocateResponse(
                   success=False, allocation_id="", vram_allocated_mb=0,
                   error="node_pb2 no compilado"
               )

           gpu = _get_gpu_metrics()
           allocated = sum(self._allocations.values())
           vram_free = max(0, gpu["vram_free_mb"] - allocated)

           if vram_free < request.vram_needed_mb:
               return node_pb2.AllocateResponse(
                   success=False,
                   allocation_id="",
                   vram_allocated_mb=0,
                   error=f"VRAM insuficiente: {vram_free}MB libre, {request.vram_needed_mb}MB necesario",
               )

           allocation_id = str(uuid.uuid4())
           self._allocations[allocation_id] = request.vram_needed_mb
           logger.info(
               "GPU allocada: node=%s task=%s allocation=%s vram=%dMB",
               self.node_id,
               request.task_id,
               allocation_id,
               request.vram_needed_mb,
           )
           return node_pb2.AllocateResponse(
               success=True,
               allocation_id=allocation_id,
               vram_allocated_mb=request.vram_needed_mb,
               error="",
           )

       async def ReleaseGPU(self, request, context):
           """Libera una reserva de VRAM."""
           try:
               from src.cluster import node_pb2
           except ImportError:
               return _MockReleaseResponse(success=True, vram_freed_mb=0, error="")

           freed = self._allocations.pop(request.allocation_id, 0)
           logger.info(
               "GPU liberada: node=%s allocation=%s vram_freed=%dMB",
               self.node_id,
               request.allocation_id,
               freed,
           )
           return node_pb2.ReleaseResponse(
               success=True,
               vram_freed_mb=freed,
               error="",
           )

       async def StreamMetrics(self, request, context):
           """Stream de métricas en tiempo real cada interval_seconds segundos."""
           try:
               from src.cluster import node_pb2
           except ImportError:
               return

           interval = max(1, request.interval_seconds or 5)
           while context.is_active():
               gpu = _get_gpu_metrics()
               sys_m = _get_system_metrics()
               allocated = sum(self._allocations.values())

               yield node_pb2.NodeMetrics(
                   node_id=self.node_id,
                   vram_free_mb=max(0, gpu["vram_free_mb"] - allocated),
                   vram_total_mb=gpu["vram_total_mb"],
                   cpu_percent=sys_m["cpu_percent"],
                   ram_free_mb=sys_m["ram_free_mb"],
                   gpu_utilization_percent=gpu["gpu_utilization_percent"],
                   timestamp_unix=int(time.time()),
               )
               await asyncio.sleep(interval)


   class NodeGRPCServer:
       """
       Servidor gRPC del NodeService. Corre en cada satélite.

       Usage:
           server = NodeGRPCServer(node_id="sat-1", port=50051)
           await server.start()
           await server.wait_for_termination()
       """

       def __init__(self, node_id: str, port: int = GRPC_PORT, is_idle_fn=None) -> None:
           self.node_id = node_id
           self.port = port
           self._servicer = NodeServiceServicer(node_id=node_id, is_idle_fn=is_idle_fn)
           self._server: Optional[grpc_aio.Server] = None

       async def start(self) -> None:
           """Inicia el servidor gRPC."""
           try:
               from src.cluster import node_pb2_grpc
           except ImportError:
               logger.warning(
                   "node_pb2_grpc no disponible — ejecutar scripts/gen_grpc.sh primero"
               )
               return

           self._server = grpc_aio.server()
           node_pb2_grpc.add_NodeServiceServicer_to_server(self._servicer, self._server)
           self._server.add_insecure_port(f"[::]:{self.port}")
           await self._server.start()
           logger.info("NodeGRPCServer iniciado: node=%s port=%d", self.node_id, self.port)

       async def stop(self) -> None:
           if self._server:
               await self._server.stop(grace=5)
               logger.info("NodeGRPCServer detenido: node=%s", self.node_id)

       async def wait_for_termination(self) -> None:
           if self._server:
               await self._server.wait_for_termination()


   # ── gRPC Client (corre en el Central) ───────────────────────────────────────

   @dataclass
   class NodeStatusSnapshot:
       """Snapshot del estado de un nodo obtenido via gRPC."""

       node_id: str
       vram_total_mb: int
       vram_free_mb: int
       vram_allocated_mb: int
       ram_free_mb: int
       cpu_percent: float
       is_idle: bool
       tailscale_ip: str
       timestamp: float = field(default_factory=time.time)


   class NodeGRPCClient:
       """
       Cliente gRPC que el Central usa para consultar un satélite.

       Usage:
           client = NodeGRPCClient(host="100.64.0.2", port=50051, node_id="sat-1")
           status = await client.get_status()
           alloc = await client.allocate_gpu(task_id="t1", vram_needed_mb=2048)
       """

       def __init__(self, host: str, port: int = GRPC_PORT, node_id: str = "") -> None:
           self.host = host
           self.port = port
           self.node_id = node_id
           self._channel: Optional[grpc_aio.Channel] = None
           self._stub = None

       async def connect(self) -> None:
           self._channel = grpc_aio.insecure_channel(f"{self.host}:{self.port}")
           try:
               from src.cluster import node_pb2_grpc
               self._stub = node_pb2_grpc.NodeServiceStub(self._channel)
           except ImportError:
               logger.warning("node_pb2_grpc no disponible para cliente")

       async def disconnect(self) -> None:
           if self._channel:
               await self._channel.close()

       async def get_status(self) -> Optional[NodeStatusSnapshot]:
           """Obtiene el estado actual del nodo via gRPC."""
           if not self._stub:
               return None
           try:
               from src.cluster import node_pb2

               resp = await self._stub.GetStatus(
                   node_pb2.StatusRequest(requester_id="central"),
                   timeout=5.0,
               )
               return NodeStatusSnapshot(
                   node_id=resp.node_id,
                   vram_total_mb=resp.vram_total_mb,
                   vram_free_mb=resp.vram_free_mb,
                   vram_allocated_mb=resp.vram_allocated_mb,
                   ram_free_mb=resp.ram_free_mb,
                   cpu_percent=resp.cpu_percent,
                   is_idle=resp.is_idle,
                   tailscale_ip=resp.tailscale_ip,
               )
           except grpc.RpcError as exc:
               logger.warning("gRPC GetStatus falló para %s: %s", self.node_id, exc)
               return None

       async def allocate_gpu(self, task_id: str, vram_needed_mb: int) -> Optional[str]:
           """
           Reserva VRAM en el nodo. Retorna allocation_id o None si falla.
           """
           if not self._stub:
               return None
           try:
               from src.cluster import node_pb2

               resp = await self._stub.AllocateGPU(
                   node_pb2.AllocateRequest(
                       task_id=task_id,
                       vram_needed_mb=vram_needed_mb,
                       requester_id="central",
                   ),
                   timeout=5.0,
               )
               if resp.success:
                   logger.info(
                       "GPU allocada: node=%s task=%s allocation=%s",
                       self.node_id,
                       task_id,
                       resp.allocation_id,
                   )
                   return resp.allocation_id
               logger.warning("AllocateGPU rechazado: %s", resp.error)
               return None
           except grpc.RpcError as exc:
               logger.warning("gRPC AllocateGPU falló: %s", exc)
               return None

       async def release_gpu(self, allocation_id: str, task_id: str) -> bool:
           """Libera una reserva de VRAM."""
           if not self._stub:
               return False
           try:
               from src.cluster import node_pb2

               resp = await self._stub.ReleaseGPU(
                   node_pb2.ReleaseRequest(
                       allocation_id=allocation_id,
                       task_id=task_id,
                   ),
                   timeout=5.0,
               )
               return resp.success
           except grpc.RpcError as exc:
               logger.warning("gRPC ReleaseGPU falló: %s", exc)
               return False

       async def stream_metrics(
           self, interval_seconds: int = 5
       ) -> AsyncIterator[NodeStatusSnapshot]:
           """Genera snapshots de métricas en tiempo real via gRPC streaming."""
           if not self._stub:
               return
           try:
               from src.cluster import node_pb2

               async for metrics in self._stub.StreamMetrics(
                   node_pb2.MetricsStreamRequest(
                       requester_id="central",
                       interval_seconds=interval_seconds,
                   )
               ):
                   yield NodeStatusSnapshot(
                       node_id=metrics.node_id,
                       vram_total_mb=metrics.vram_total_mb,
                       vram_free_mb=metrics.vram_free_mb,
                       vram_allocated_mb=0,
                       ram_free_mb=metrics.ram_free_mb,
                       cpu_percent=metrics.cpu_percent,
                       is_idle=False,
                       tailscale_ip="",
                       timestamp=float(metrics.timestamp_unix),
                   )
           except grpc.RpcError as exc:
               logger.warning("gRPC StreamMetrics falló: %s", exc)


   # ── Mocks para tests (cuando el proto no está compilado) ─────────────────────

   class _MockNodeStatus:
       def __init__(self, **kwargs):
           for k, v in kwargs.items():
               setattr(self, k, v)


   class _MockAllocateResponse:
       def __init__(self, **kwargs):
           for k, v in kwargs.items():
               setattr(self, k, v)


   class _MockReleaseResponse:
       def __init__(self, **kwargs):
           for k, v in kwargs.items():
               setattr(self, k, v)

4. Crear archivo src/cluster/gpu_pool.py:

   Ruta: ~/yeyo-os/src/cluster/gpu_pool.py
   Contenido:

   """
   YeyoNet Cluster Mode — GPU Pool distribuido
   Micro-fase 7.20 — Capa 7: Evolución

   GPUPool:
   - Registro de VRAM disponible en cada nodo de la red
   - allocate_best(vram_needed): retorna el nodo con más VRAM libre
   - Actualización en tiempo real via gRPC StreamMetrics
   - Integración con YeyoOrquestador para delegación automática
   """

   from __future__ import annotations

   import asyncio
   import logging
   import time
   from dataclasses import dataclass, field
   from typing import Dict, List, Optional

   import redis

   from .grpc_service import NodeGRPCClient, NodeStatusSnapshot

   logger = logging.getLogger(__name__)


   @dataclass
   class GPUAllocation:
       """Una reserva activa de GPU en un nodo."""

       allocation_id: str
       node_id: str
       task_id: str
       vram_mb: int
       created_at: float = field(default_factory=time.time)


   class GPUPool:
       """
       Pool de GPUs distribuido en toda la red YeyoNet.

       Mantiene un registro actualizado de la VRAM disponible en cada nodo.
       El Central lo usa para decidir dónde ejecutar tareas con GPU.

       Usage:
           pool = GPUPool(redis_client)
           await pool.add_node("sat-1", host="100.64.0.2")
           node_id, alloc_id = await pool.allocate_best(task_id="t1", vram_needed_mb=2048)
           await pool.release(alloc_id, task_id="t1")
       """

       SNAPSHOT_KEY = "gpupool:snapshot:{node_id}"
       ALLOC_KEY = "gpupool:alloc:{alloc_id}"
       NODES_KEY = "gpupool:nodes"

       def __init__(self, redis_client: redis.Redis) -> None:
           self._redis = redis_client
           self._clients: Dict[str, NodeGRPCClient] = {}
           self._streaming_tasks: Dict[str, asyncio.Task] = {}

       async def add_node(
           self, node_id: str, host: str, port: int = 50051
       ) -> None:
           """Añade un nodo al pool y comienza a recibir sus métricas via gRPC."""
           client = NodeGRPCClient(host=host, port=port, node_id=node_id)
           await client.connect()
           self._clients[node_id] = client
           self._redis.sadd(self.NODES_KEY, node_id)

           # Obtener snapshot inicial
           snapshot = await client.get_status()
           if snapshot:
               self._save_snapshot(snapshot)

           # Iniciar streaming de métricas en background
           task = asyncio.create_task(self._stream_node_metrics(node_id, client))
           self._streaming_tasks[node_id] = task
           logger.info("Nodo añadido al GPUPool: %s @ %s:%d", node_id, host, port)

       async def remove_node(self, node_id: str) -> None:
           """Elimina un nodo del pool."""
           if node_id in self._streaming_tasks:
               self._streaming_tasks[node_id].cancel()
               del self._streaming_tasks[node_id]

           if node_id in self._clients:
               await self._clients[node_id].disconnect()
               del self._clients[node_id]

           self._redis.srem(self.NODES_KEY, node_id)
           logger.info("Nodo eliminado del GPUPool: %s", node_id)

       def update_snapshot(self, snapshot: NodeStatusSnapshot) -> None:
           """Actualiza el snapshot de un nodo (llamado desde gRPC stream o REST)."""
           self._save_snapshot(snapshot)

       def get_snapshot(self, node_id: str) -> Optional[NodeStatusSnapshot]:
           """Obtiene el último snapshot conocido de un nodo."""
           import json

           raw = self._redis.get(self.SNAPSHOT_KEY.format(node_id=node_id))
           if not raw:
               return None
           data = json.loads(raw)
           return NodeStatusSnapshot(**data)

       def get_all_snapshots(self) -> List[NodeStatusSnapshot]:
           """Retorna snapshots de todos los nodos en el pool."""
           node_ids = self._redis.smembers(self.NODES_KEY)
           snapshots = []
           for nid in node_ids:
               s = self.get_snapshot(nid)
               if s:
                   snapshots.append(s)
           return snapshots

       async def allocate_best(
           self, task_id: str, vram_needed_mb: int
       ) -> Optional[tuple[str, str]]:
           """
           Selecciona el nodo con más VRAM libre y reserva la GPU para la tarea.

           Returns:
               (node_id, allocation_id) si hay nodo disponible, None si no.
           """
           snapshots = self.get_all_snapshots()
           if not snapshots:
               logger.warning("GPUPool vacío — no hay nodos disponibles")
               return None

           # Filtrar nodos con VRAM suficiente y snapshot reciente (<2 min)
           now = time.time()
           candidates = [
               s for s in snapshots
               if s.vram_free_mb >= vram_needed_mb and (now - s.timestamp) < 120
           ]

           if not candidates:
               logger.warning(
                   "Sin nodos con %dMB VRAM libre", vram_needed_mb
               )
               return None

           # Elegir el de mayor VRAM libre
           best = max(candidates, key=lambda s: s.vram_free_mb)

           # Intentar allocar via gRPC
           client = self._clients.get(best.node_id)
           if client:
               alloc_id = await client.allocate_gpu(task_id, vram_needed_mb)
               if alloc_id:
                   self._save_allocation(
                       GPUAllocation(
                           allocation_id=alloc_id,
                           node_id=best.node_id,
                           task_id=task_id,
                           vram_mb=vram_needed_mb,
                       )
                   )
                   logger.info(
                       "GPU allocada: node=%s task=%s vram=%dMB alloc=%s",
                       best.node_id,
                       task_id,
                       vram_needed_mb,
                       alloc_id,
                   )
                   return best.node_id, alloc_id
           else:
               # Sin cliente gRPC (modo REST fallback) — reserva optimista
               import uuid

               alloc_id = str(uuid.uuid4())
               self._save_allocation(
                   GPUAllocation(
                       allocation_id=alloc_id,
                       node_id=best.node_id,
                       task_id=task_id,
                       vram_mb=vram_needed_mb,
                   )
               )
               return best.node_id, alloc_id

           return None

       async def release(self, allocation_id: str, task_id: str) -> bool:
           """Libera una reserva de GPU."""
           import json

           raw = self._redis.get(self.ALLOC_KEY.format(alloc_id=allocation_id))
           if not raw:
               logger.warning("Allocation no encontrada: %s", allocation_id)
               return False

           alloc_data = json.loads(raw)
           node_id = alloc_data["node_id"]

           client = self._clients.get(node_id)
           if client:
               success = await client.release_gpu(allocation_id, task_id)
           else:
               success = True  # Fallback optimista

           self._redis.delete(self.ALLOC_KEY.format(alloc_id=allocation_id))
           logger.info(
               "GPU liberada: node=%s alloc=%s task=%s",
               node_id,
               allocation_id,
               task_id,
           )
           return success

       def get_total_vram_free(self) -> int:
           """VRAM libre total en toda la red."""
           return sum(s.vram_free_mb for s in self.get_all_snapshots())

       def get_total_vram(self) -> int:
           """VRAM total en toda la red."""
           return sum(s.vram_total_mb for s in self.get_all_snapshots())

       async def _stream_node_metrics(
           self, node_id: str, client: NodeGRPCClient
       ) -> None:
           """Stream continuo de métricas de un nodo. Se ejecuta en background."""
           logger.info("Iniciando stream de métricas para nodo: %s", node_id)
           try:
               async for snapshot in client.stream_metrics(interval_seconds=5):
                   self._save_snapshot(snapshot)
                   logger.debug(
                       "Métricas actualizadas: node=%s vram_free=%dMB",
                       node_id,
                       snapshot.vram_free_mb,
                   )
           except asyncio.CancelledError:
               logger.info("Stream cancelado para nodo: %s", node_id)
           except Exception as exc:
               logger.error("Stream de métricas falló para %s: %s", node_id, exc)

       def _save_snapshot(self, snapshot: NodeStatusSnapshot) -> None:
           """Guarda snapshot en Redis con TTL de 5 minutos."""
           import json
           import dataclasses

           key = self.SNAPSHOT_KEY.format(node_id=snapshot.node_id)
           data = dataclasses.asdict(snapshot)
           self._redis.set(key, json.dumps(data), ex=300)

       def _save_allocation(self, alloc: GPUAllocation) -> None:
           """Guarda una allocation en Redis con TTL de 2 horas."""
           import json
           import dataclasses

           key = self.ALLOC_KEY.format(alloc_id=alloc.allocation_id)
           self._redis.set(key, json.dumps(dataclasses.asdict(alloc)), ex=7200)

5. Crear archivo src/cluster/orchestrator_integration.py:

   Ruta: ~/yeyo-os/src/cluster/orchestrator_integration.py
   Contenido:

   """
   YeyoNet Cluster Mode — Integración con YeyoOrquestador
   Micro-fase 7.20 — Capa 7: Evolución

   Cuando un grafo necesita GPU, el orquestador consulta al GPUPool
   cuál nodo tiene más VRAM libre y delega la ejecución ahí.
   """

   from __future__ import annotations

   import logging
   from typing import Any, Dict, Optional

   from .gpu_pool import GPUPool
   from .scheduler import ClusterScheduler, ClusterTask, TaskStatus

   logger = logging.getLogger(__name__)


   class ClusterAwareOrchestrator:
       """
       Wrapper del YeyoOrquestador que delega nodos GPU al cluster.

       Uso:
           orchestrator = ClusterAwareOrchestrator(gpu_pool, scheduler)
           result = await orchestrator.run_with_gpu(graph_def, inputs, vram_needed_mb=2048)
       """

       def __init__(self, gpu_pool: GPUPool, scheduler: ClusterScheduler) -> None:
           self._gpu_pool = gpu_pool
           self._scheduler = scheduler

       async def run_with_gpu(
           self,
           graph_definition: Dict[str, Any],
           inputs: Dict[str, Any],
           vram_needed_mb: int = 2048,
           graph_id: str = "auto",
           task_id: str = "auto",
       ) -> Dict[str, Any]:
           """
           Ejecuta un grafo usando el mejor nodo GPU disponible en el cluster.

           1. Consulta GPUPool para encontrar el nodo con más VRAM libre.
           2. Si hay nodo disponible, envía la tarea via ClusterScheduler.
           3. Si no hay nodo, ejecuta localmente.
           """
           import uuid
           if task_id == "auto":
               task_id = str(uuid.uuid4())
           if graph_id == "auto":
               graph_id = str(uuid.uuid4())

           # Buscar el mejor nodo GPU
           allocation = await self._gpu_pool.allocate_best(
               task_id=task_id,
               vram_needed_mb=vram_needed_mb,
           )

           if allocation:
               node_id, alloc_id = allocation
               logger.info(
                   "Delegando grafo al cluster: node=%s task=%s vram=%dMB",
                   node_id,
                   task_id,
                   vram_needed_mb,
               )

               task = ClusterTask(
                   task_id=task_id,
                   task_type="run_graph",
                   payload={
                       "graph_id": graph_id,
                       "graph_definition": graph_definition,
                       "inputs": inputs,
                   },
                   vram_needed_mb=vram_needed_mb,
               )
               # Forzar asignación al nodo seleccionado
               task.assigned_node = node_id
               task.status = TaskStatus.ASSIGNED
               self._scheduler.update_task(task)

               return {
                   "delegated": True,
                   "task_id": task_id,
                   "node_id": node_id,
                   "allocation_id": alloc_id,
                   "status": "delegated_to_cluster",
               }

           # Fallback: ejecutar localmente
           logger.info("Sin nodos GPU disponibles, ejecutando localmente: task=%s", task_id)
           return {
               "delegated": False,
               "task_id": task_id,
               "node_id": "local",
               "status": "executing_locally",
           }

       async def run_image_generation(
           self,
           prompt: str,
           negative_prompt: str = "",
           width: int = 512,
           height: int = 512,
           vram_needed_mb: int = 3000,
       ) -> Dict[str, Any]:
           """
           Genera una imagen usando el nodo GPU con más VRAM libre.
           Delega al cluster si hay nodos disponibles.
           """
           import uuid

           task_id = str(uuid.uuid4())
           allocation = await self._gpu_pool.allocate_best(
               task_id=task_id,
               vram_needed_mb=vram_needed_mb,
           )

           if allocation:
               node_id, alloc_id = allocation
               task = ClusterTask(
                   task_id=task_id,
                   task_type="generate_image",
                   payload={
                       "prompt": prompt,
                       "negative_prompt": negative_prompt,
                       "width": width,
                       "height": height,
                   },
                   vram_needed_mb=vram_needed_mb,
               )
               task.assigned_node = node_id
               task.status = TaskStatus.ASSIGNED
               self._scheduler.update_task(task)

               return {
                   "delegated": True,
                   "task_id": task_id,
                   "node_id": node_id,
                   "allocation_id": alloc_id,
               }

           return {
               "delegated": False,
               "task_id": task_id,
               "node_id": "local",
               "status": "no_gpu_available",
           }

6. Crear archivo tests/test_gpu_pool.py:

   Ruta: ~/yeyo-os/tests/test_gpu_pool.py
   Contenido:

   """
   Tests para Distributed GPU Scheduler (7.20).
   Usa mock gRPC y fakeredis.
   """

   from __future__ import annotations

   import asyncio
   import time
   import uuid
   from dataclasses import dataclass
   from typing import Optional
   from unittest.mock import AsyncMock, MagicMock, patch

   import fakeredis
   import pytest

   from src.cluster.gpu_pool import GPUAllocation, GPUPool
   from src.cluster.grpc_service import NodeStatusSnapshot, NodeServiceServicer


   # ── Fixtures ─────────────────────────────────────────────────────────────────

   @pytest.fixture
   def redis_client():
       return fakeredis.FakeRedis(decode_responses=True)


   @pytest.fixture
   def gpu_pool(redis_client):
       return GPUPool(redis_client)


   def make_snapshot(node_id: str, vram_free: int, is_idle: bool = True, age_seconds: float = 0.0) -> NodeStatusSnapshot:
       return NodeStatusSnapshot(
           node_id=node_id,
           vram_total_mb=8192,
           vram_free_mb=vram_free,
           vram_allocated_mb=8192 - vram_free,
           ram_free_mb=16384,
           cpu_percent=5.0,
           is_idle=is_idle,
           tailscale_ip=f"100.64.0.{hash(node_id) % 254 + 1}",
           timestamp=time.time() - age_seconds,
       )


   # ── Tests: GPUPool ────────────────────────────────────────────────────────────

   class TestGPUPool:
       def test_update_and_get_snapshot(self, gpu_pool):
           snap = make_snapshot("sat-1", vram_free=4096)
           gpu_pool.update_snapshot(snap)
           result = gpu_pool.get_snapshot("sat-1")
           assert result is not None
           assert result.node_id == "sat-1"
           assert result.vram_free_mb == 4096

       def test_get_all_snapshots_empty(self, gpu_pool):
           snaps = gpu_pool.get_all_snapshots()
           assert snaps == []

       def test_get_all_snapshots_multiple(self, gpu_pool, redis_client):
           for i in range(3):
               snap = make_snapshot(f"sat-{i}", vram_free=2048 * (i + 1))
               gpu_pool.update_snapshot(snap)
               redis_client.sadd(gpu_pool.NODES_KEY, f"sat-{i}")
           snaps = gpu_pool.get_all_snapshots()
           assert len(snaps) == 3

       def test_total_vram_free(self, gpu_pool, redis_client):
           for i in range(3):
               snap = make_snapshot(f"node-{i}", vram_free=1024)
               gpu_pool.update_snapshot(snap)
               redis_client.sadd(gpu_pool.NODES_KEY, f"node-{i}")
           assert gpu_pool.get_total_vram_free() == 3072

       @pytest.mark.asyncio
       async def test_allocate_best_no_nodes(self, gpu_pool):
           result = await gpu_pool.allocate_best(task_id="t1", vram_needed_mb=2048)
           assert result is None

       @pytest.mark.asyncio
       async def test_allocate_best_selects_most_vram(self, gpu_pool, redis_client):
           for nid, vram in [("n-low", 1024), ("n-high", 6144), ("n-mid", 3072)]:
               snap = make_snapshot(nid, vram_free=vram)
               gpu_pool.update_snapshot(snap)
               redis_client.sadd(gpu_pool.NODES_KEY, nid)

           result = await gpu_pool.allocate_best(task_id="t1", vram_needed_mb=512)
           assert result is not None
           node_id, alloc_id = result
           assert node_id == "n-high"

       @pytest.mark.asyncio
       async def test_allocate_best_insufficient_vram(self, gpu_pool, redis_client):
           snap = make_snapshot("n1", vram_free=1024)
           gpu_pool.update_snapshot(snap)
           redis_client.sadd(gpu_pool.NODES_KEY, "n1")
           result = await gpu_pool.allocate_best(task_id="t1", vram_needed_mb=4096)
           assert result is None

       @pytest.mark.asyncio
       async def test_allocate_best_skips_stale_snapshot(self, gpu_pool, redis_client):
           snap = make_snapshot("stale-node", vram_free=8192, age_seconds=300)
           gpu_pool.update_snapshot(snap)
           redis_client.sadd(gpu_pool.NODES_KEY, "stale-node")
           result = await gpu_pool.allocate_best(task_id="t1", vram_needed_mb=1024)
           assert result is None

       @pytest.mark.asyncio
       async def test_release_nonexistent(self, gpu_pool):
           result = await gpu_pool.release("nonexistent-alloc", "task-1")
           assert result is False

       @pytest.mark.asyncio
       async def test_allocate_and_release(self, gpu_pool, redis_client):
           snap = make_snapshot("sat-1", vram_free=4096)
           gpu_pool.update_snapshot(snap)
           redis_client.sadd(gpu_pool.NODES_KEY, "sat-1")

           result = await gpu_pool.allocate_best(task_id="t1", vram_needed_mb=2048)
           assert result is not None
           node_id, alloc_id = result

           success = await gpu_pool.release(alloc_id, "t1")
           assert success is True


   # ── Tests: NodeServiceServicer ────────────────────────────────────────────────

   class TestNodeServiceServicer:
       def test_init(self):
           svc = NodeServiceServicer(node_id="sat-test")
           assert svc.node_id == "sat-test"
           assert svc._allocations == {}

       def test_build_status(self):
           svc = NodeServiceServicer(node_id="sat-test")
           with patch("src.cluster.grpc_service._get_gpu_metrics", return_value={
               "vram_total_mb": 6000, "vram_free_mb": 4096, "gpu_utilization_percent": 10.0
           }), patch("src.cluster.grpc_service._get_system_metrics", return_value={
               "ram_total_mb": 16384, "ram_free_mb": 8192, "cpu_percent": 15.0
           }):
               status = svc._build_status()
           assert status["node_id"] == "sat-test"
           assert status["vram_total_mb"] == 6000
           assert status["vram_free_mb"] == 4096

       def test_vram_reduces_with_allocation(self):
           svc = NodeServiceServicer(node_id="sat-test")
           svc._allocations["alloc-1"] = 2048

           with patch("src.cluster.grpc_service._get_gpu_metrics", return_value={
               "vram_total_mb": 6000, "vram_free_mb": 4096, "gpu_utilization_percent": 0.0
           }), patch("src.cluster.grpc_service._get_system_metrics", return_value={
               "ram_total_mb": 16384, "ram_free_mb": 8192, "cpu_percent": 5.0
           }):
               status = svc._build_status()
           # VRAM libre = 4096 - 2048 = 2048
           assert status["vram_free_mb"] == 2048
           assert status["vram_allocated_mb"] == 2048


   # ── Tests: ClusterAwareOrchestrator ──────────────────────────────────────────

   class TestClusterAwareOrchestrator:
       @pytest.mark.asyncio
       async def test_run_with_gpu_no_nodes(self, redis_client):
           from src.cluster.orchestrator_integration import ClusterAwareOrchestrator
           from src.cluster.scheduler import ClusterScheduler

           pool = GPUPool(redis_client)
           sched = ClusterScheduler(redis_client)
           orch = ClusterAwareOrchestrator(pool, sched)

           result = await orch.run_with_gpu(
               graph_definition={}, inputs={}, vram_needed_mb=2048
           )
           assert result["delegated"] is False
           assert result["node_id"] == "local"

       @pytest.mark.asyncio
       async def test_run_with_gpu_with_node(self, redis_client):
           from src.cluster.orchestrator_integration import ClusterAwareOrchestrator
           from src.cluster.scheduler import ClusterScheduler

           pool = GPUPool(redis_client)
           snap = make_snapshot("sat-gpu", vram_free=4096)
           pool.update_snapshot(snap)
           redis_client.sadd(pool.NODES_KEY, "sat-gpu")

           sched = ClusterScheduler(redis_client)
           orch = ClusterAwareOrchestrator(pool, sched)

           result = await orch.run_with_gpu(
               graph_definition={"nodes": []}, inputs={}, vram_needed_mb=2048
           )
           assert result["delegated"] is True
           assert result["node_id"] == "sat-gpu"
           assert "allocation_id" in result

VERIFICAR:
- [ ] src/cluster/node.proto define NodeService con GetStatus, AllocateGPU, ReleaseGPU, StreamMetrics
- [ ] src/cluster/grpc_service.py tiene NodeGRPCServer, NodeGRPCClient, NodeServiceServicer
- [ ] src/cluster/gpu_pool.py tiene GPUPool con allocate_best() que elige nodo por VRAM libre
- [ ] src/cluster/orchestrator_integration.py integra GPUPool con YeyoOrquestador
- [ ] scripts/gen_grpc.sh genera node_pb2.py y node_pb2_grpc.py correctamente
- [ ] Tests pasan: pytest tests/test_gpu_pool.py (requiere fakeredis, grpcio)

SI FALLA:
- grpcio no instalado: pip install grpcio grpcio-tools
- node_pb2.py no generado: bash scripts/gen_grpc.sh
- pynvml no disponible: tests mockean _get_gpu_metrics, no falla
- psutil no instalado: pip install psutil
- asyncio tests: pip install pytest-asyncio, añadir @pytest.mark.asyncio

NO HACER:
- No usar gRPC síncrono en FastAPI (usar grpc.aio siempre)
- No implementar WebRTC en esta fase (Tailscale es suficiente para Capa 7)
- No almacenar allocations de GPU en memoria local solamente — usar Redis para persistencia
- No implementar GPU sharing entre tareas (una tarea = una allocation)
- No implementar federated learning aquí (eso es 7.21)

GATE: GPUPool con 2+ nodos registrados (snapshots en Redis). Llamada a allocate_best(vram_needed_mb=2048) retorna el nodo con más VRAM libre. ClusterAwareOrchestrator delega run_with_gpu al nodo correcto. Todos los tests pasan (≥20 tests).
```
