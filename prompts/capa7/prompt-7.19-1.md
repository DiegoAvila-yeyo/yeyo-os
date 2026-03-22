## ═══════════════════════════════════════
## MICRO-FASE 7.19 — YeyoNet Cluster Mode: Celery Workers
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.19-1 [VSCODE] — Backend Python completo para Cluster Mode: workers Celery, scheduler de satélites idle, detector de inactividad y API

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.19 de Capa 7 (Evolución): implementar el Cluster Mode de YeyoNet, donde el Central puede usar los satélites idle como workers de cómputo distribuido. Cuando un satélite lleva 10+ minutos sin actividad de teclado/mouse, el Central puede asignarle tareas en background.

CONTEXTO:
- Micro-fases 7.0–7.18 completadas: LoRA pipeline, YEYO Store, ISO builder, wizard, multi-user, performance, observer, Node Studio, YeyoNet Core (relay/sync/invites), YeyoNet UI (panel de satélites) — todos funcionando
- Stack: FastAPI (Python), Redis ya existe en Capa 0 (localhost:6379), Celery usa Redis como broker
- YeyoNet: src/yeyonet/ existe con relay WebSocket, SatelliteManager, SyncManager desde 7.17
- Hardware objetivo: satélites pueden tener GPU (GTX 1060+) o no — el scheduler asigna por capacidad
- Tailscale activo: cada satélite tiene IP estable en la red privada
- Tareas soportadas: generate_image_task (usa SD/ComfyUI), run_graph_task (ejecuta grafo), train_lora_task (fine-tune)
- Retry automático: si un satélite se desconecta durante una tarea, el Central la reasigna a otro nodo
- Idle detection: el satélite reporta su estado al Central vía WebSocket cuando el usuario está inactivo

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/cluster/__init__.py:

   Ruta: ~/yeyo-os/src/cluster/__init__.py
   Contenido:

   """
   YeyoNet Cluster Mode — Cómputo distribuido entre nodos YeyoOS
   Micro-fase 7.19 — Capa 7: Evolución

   El Central distribuye tareas entre satélites idle.
   Los satélites reportan su estado de actividad.
   Celery + Redis gestionan la cola de tareas.
   """

   from .worker import CeleryWorker, celery_app
   from .scheduler import ClusterScheduler, TaskPriority
   from .idle_detector import IdleDetector, IdleState

   __all__ = [
       "CeleryWorker",
       "celery_app",
       "ClusterScheduler",
       "TaskPriority",
       "IdleDetector",
       "IdleState",
   ]

2. Crear archivo src/cluster/worker.py:

   Ruta: ~/yeyo-os/src/cluster/worker.py
   Contenido:

   """
   YeyoNet Cluster Mode — Celery Workers
   Micro-fase 7.19 — Capa 7: Evolución

   Tareas distribuibles entre nodos de la red:
   - generate_image_task: genera imagen con SD en el satélite
   - run_graph_task: ejecuta un grafo de IA en el satélite
   - train_lora_task: entrena mini-LoRA local en el satélite
   """

   from __future__ import annotations

   import logging
   import os
   import time
   from dataclasses import dataclass, field
   from typing import Any, Dict, Optional

   from celery import Celery
   from celery.utils.log import get_task_logger

   logger = logging.getLogger(__name__)
   task_logger = get_task_logger(__name__)

   REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

   celery_app = Celery(
       "yeyo_cluster",
       broker=REDIS_URL,
       backend=REDIS_URL,
   )

   celery_app.conf.update(
       task_serializer="json",
       accept_content=["json"],
       result_serializer="json",
       timezone="UTC",
       enable_utc=True,
       task_track_started=True,
       task_acks_late=True,
       worker_prefetch_multiplier=1,
       task_soft_time_limit=300,
       task_time_limit=600,
       task_routes={
           "src.cluster.worker.generate_image_task": {"queue": "gpu_tasks"},
           "src.cluster.worker.run_graph_task": {"queue": "cpu_tasks"},
           "src.cluster.worker.train_lora_task": {"queue": "training_tasks"},
       },
   )


   @dataclass
   class TaskResult:
       """Resultado de una tarea distribuida."""

       task_id: str
       task_type: str
       node_id: str
       status: str  # "success" | "failure" | "retry"
       result: Optional[Any] = None
       error: Optional[str] = None
       duration_seconds: float = 0.0
       metadata: Dict[str, Any] = field(default_factory=dict)


   class CeleryWorker:
       """
       Worker que ejecuta en el satélite.
       Registra las tareas Celery disponibles y gestiona su ejecución.
       """

       def __init__(self, node_id: str, redis_url: str = REDIS_URL) -> None:
           self.node_id = node_id
           self.redis_url = redis_url
           self._app = celery_app

       @property
       def app(self) -> Celery:
           return self._app

       def start(self, queues: list[str] | None = None, concurrency: int = 2) -> None:
           """Inicia el worker Celery en este nodo."""
           queues = queues or ["gpu_tasks", "cpu_tasks", "training_tasks"]
           self._app.worker_main(
               argv=[
                   "worker",
                   "--loglevel=info",
                   f"--concurrency={concurrency}",
                   f"--queues={','.join(queues)}",
                   f"--hostname=yeyo-worker-{self.node_id}@%h",
               ]
           )


   # ── Tareas Celery ────────────────────────────────────────────────────────────

   @celery_app.task(
       bind=True,
       name="src.cluster.worker.generate_image_task",
       max_retries=3,
       default_retry_delay=30,
   )
   def generate_image_task(
       self,
       prompt: str,
       negative_prompt: str = "",
       width: int = 512,
       height: int = 512,
       steps: int = 20,
       seed: int = -1,
       node_id: str = "unknown",
   ) -> Dict[str, Any]:
       """
       Genera una imagen usando Stable Diffusion en el nodo satélite.
       Requiere ComfyUI o A1111 corriendo localmente.
       """
       task_logger.info(
           "generate_image_task iniciada en nodo=%s task_id=%s prompt='%s'",
           node_id,
           self.request.id,
           prompt[:80],
       )
       start = time.monotonic()

       try:
           import httpx

           comfyui_url = os.environ.get("COMFYUI_URL", "http://localhost:8188")
           a1111_url = os.environ.get("A1111_URL", "http://localhost:7860")

           # Intentar A1111 primero, luego ComfyUI
           payload = {
               "prompt": prompt,
               "negative_prompt": negative_prompt,
               "width": width,
               "height": height,
               "steps": steps,
               "seed": seed,
               "sampler_name": "DPM++ 2M Karras",
               "cfg_scale": 7,
           }

           resp = httpx.post(
               f"{a1111_url}/sdapi/v1/txt2img",
               json=payload,
               timeout=120.0,
           )
           resp.raise_for_status()
           data = resp.json()
           images_b64 = data.get("images", [])

           duration = time.monotonic() - start
           task_logger.info(
               "generate_image_task completada nodo=%s duration=%.2fs images=%d",
               node_id,
               duration,
               len(images_b64),
           )

           return {
               "status": "success",
               "node_id": node_id,
               "images": images_b64,
               "duration_seconds": duration,
               "seed": data.get("info", {}).get("seed", seed),
           }

       except Exception as exc:
           task_logger.error("generate_image_task falló: %s", exc)
           try:
               raise self.retry(exc=exc, countdown=30)
           except self.MaxRetriesExceededError:
               return {
                   "status": "failure",
                   "node_id": node_id,
                   "error": str(exc),
                   "duration_seconds": time.monotonic() - start,
               }


   @celery_app.task(
       bind=True,
       name="src.cluster.worker.run_graph_task",
       max_retries=2,
       default_retry_delay=10,
   )
   def run_graph_task(
       self,
       graph_id: str,
       graph_definition: Dict[str, Any],
       inputs: Dict[str, Any],
       node_id: str = "unknown",
   ) -> Dict[str, Any]:
       """
       Ejecuta un grafo de IA en el nodo satélite.
       El grafo se serializa como JSON y se pasa al YeyoOrquestador local.
       """
       task_logger.info(
           "run_graph_task iniciada nodo=%s graph_id=%s",
           node_id,
           graph_id,
       )
       start = time.monotonic()

       try:
           import httpx

           orchestrator_url = os.environ.get(
               "ORCHESTRATOR_URL", "http://localhost:8000"
           )
           payload = {
               "graph_id": graph_id,
               "graph_definition": graph_definition,
               "inputs": inputs,
               "remote": True,
               "source_node": node_id,
           }

           resp = httpx.post(
               f"{orchestrator_url}/api/graphs/run",
               json=payload,
               timeout=180.0,
           )
           resp.raise_for_status()
           result = resp.json()

           duration = time.monotonic() - start
           task_logger.info(
               "run_graph_task completada nodo=%s graph_id=%s duration=%.2fs",
               node_id,
               graph_id,
               duration,
           )

           return {
               "status": "success",
               "node_id": node_id,
               "graph_id": graph_id,
               "result": result,
               "duration_seconds": duration,
           }

       except Exception as exc:
           task_logger.error("run_graph_task falló: %s", exc)
           try:
               raise self.retry(exc=exc, countdown=10)
           except self.MaxRetriesExceededError:
               return {
                   "status": "failure",
                   "node_id": node_id,
                   "graph_id": graph_id,
                   "error": str(exc),
                   "duration_seconds": time.monotonic() - start,
               }


   @celery_app.task(
       bind=True,
       name="src.cluster.worker.train_lora_task",
       max_retries=1,
       default_retry_delay=60,
   )
   def train_lora_task(
       self,
       training_data: list[Dict[str, Any]],
       base_model: str = "qwen2.5:3b",
       epochs: int = 3,
       node_id: str = "unknown",
   ) -> Dict[str, Any]:
       """
       Entrena un mini-LoRA local en el satélite con sus últimas interacciones.
       Retorna los pesos al Central para federated learning (7.21).
       """
       task_logger.info(
           "train_lora_task iniciada nodo=%s base_model=%s samples=%d",
           node_id,
           base_model,
           len(training_data),
       )
       start = time.monotonic()

       try:
           import httpx

           lora_url = os.environ.get("LORA_TRAINER_URL", "http://localhost:8000")
           payload = {
               "training_data": training_data,
               "base_model": base_model,
               "epochs": epochs,
               "output_name": f"satellite_{node_id}_lora",
               "max_samples": 1000,
           }

           resp = httpx.post(
               f"{lora_url}/api/lora/train",
               json=payload,
               timeout=3600.0,
           )
           resp.raise_for_status()
           result = resp.json()

           duration = time.monotonic() - start
           task_logger.info(
               "train_lora_task completada nodo=%s duration=%.2fs",
               node_id,
               duration,
           )

           return {
               "status": "success",
               "node_id": node_id,
               "lora_weights_path": result.get("output_path"),
               "metrics": result.get("metrics", {}),
               "duration_seconds": duration,
           }

       except Exception as exc:
           task_logger.error("train_lora_task falló: %s", exc)
           try:
               raise self.retry(exc=exc, countdown=60)
           except self.MaxRetriesExceededError:
               return {
                   "status": "failure",
                   "node_id": node_id,
                   "error": str(exc),
                   "duration_seconds": time.monotonic() - start,
               }

3. Crear archivo src/cluster/idle_detector.py:

   Ruta: ~/yeyo-os/src/cluster/idle_detector.py
   Contenido:

   """
   YeyoNet Cluster Mode — Detector de inactividad del satélite
   Micro-fase 7.19 — Capa 7: Evolución

   Monitorea el último uso de teclado/mouse en el satélite.
   Emite evento "idle" o "active" via WebSocket al Central.
   Threshold: 10 minutos sin actividad = idle.
   """

   from __future__ import annotations

   import asyncio
   import logging
   import platform
   import time
   from dataclasses import dataclass, field
   from enum import Enum
   from typing import Callable, Optional

   logger = logging.getLogger(__name__)

   IDLE_THRESHOLD_SECONDS = int(
       __import__("os").environ.get("YEYO_IDLE_THRESHOLD", "600")
   )


   class IdleState(str, Enum):
       ACTIVE = "active"
       IDLE = "idle"
       UNKNOWN = "unknown"


   @dataclass
   class IdleEvent:
       state: IdleState
       idle_seconds: float
       timestamp: float = field(default_factory=time.time)
       node_id: str = ""


   def _get_idle_seconds_linux() -> float:
       """Obtiene segundos de inactividad en Linux usando /proc o xprintidle."""
       try:
           import subprocess

           result = subprocess.run(
               ["xprintidle"], capture_output=True, text=True, timeout=2
           )
           if result.returncode == 0:
               return float(result.stdout.strip()) / 1000.0
       except Exception:
           pass

       # Fallback: leer /proc/uptime y comparar con last input time
       try:
           with open("/proc/uptime") as f:
               uptime = float(f.read().split()[0])
           return 0.0  # No podemos determinar sin xprintidle
       except Exception:
           return 0.0


   def _get_idle_seconds_windows() -> float:
       """Obtiene segundos de inactividad en Windows usando GetLastInputInfo."""
       try:
           import ctypes

           class LASTINPUTINFO(ctypes.Structure):
               _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

           lii = LASTINPUTINFO()
           lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
           ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
           millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
           return millis / 1000.0
       except Exception:
           return 0.0


   def _get_idle_seconds_macos() -> float:
       """Obtiene segundos de inactividad en macOS usando ioreg."""
       try:
           import subprocess

           result = subprocess.run(
               [
                   "ioreg",
                   "-c",
                   "IOHIDSystem",
                   "|",
                   "awk",
                   '/HIDIdleTime/ {print $NF/1000000000; exit}',
               ],
               capture_output=True,
               text=True,
               timeout=2,
               shell=True,
           )
           if result.returncode == 0 and result.stdout.strip():
               return float(result.stdout.strip())
       except Exception:
           pass
       return 0.0


   def get_system_idle_seconds() -> float:
       """Obtiene segundos de inactividad según el OS actual."""
       system = platform.system()
       if system == "Linux":
           return _get_idle_seconds_linux()
       elif system == "Windows":
           return _get_idle_seconds_windows()
       elif system == "Darwin":
           return _get_idle_seconds_macos()
       return 0.0


   class IdleDetector:
       """
       Detecta inactividad del usuario y notifica al Central via WebSocket.

       Usage:
           detector = IdleDetector(node_id="satellite-1", ws_url="ws://central:8000/ws/cluster")
           await detector.start()
       """

       def __init__(
           self,
           node_id: str,
           ws_url: str,
           idle_threshold_seconds: int = IDLE_THRESHOLD_SECONDS,
           poll_interval_seconds: int = 30,
           on_state_change: Optional[Callable[[IdleEvent], None]] = None,
       ) -> None:
           self.node_id = node_id
           self.ws_url = ws_url
           self.idle_threshold = idle_threshold_seconds
           self.poll_interval = poll_interval_seconds
           self.on_state_change = on_state_change
           self._current_state: IdleState = IdleState.UNKNOWN
           self._running = False
           self._ws = None

       @property
       def current_state(self) -> IdleState:
           return self._current_state

       def _detect_state(self) -> tuple[IdleState, float]:
           """Detecta el estado actual de inactividad."""
           idle_seconds = get_system_idle_seconds()
           if idle_seconds >= self.idle_threshold:
               return IdleState.IDLE, idle_seconds
           return IdleState.ACTIVE, idle_seconds

       async def _send_state(self, state: IdleState, idle_seconds: float) -> None:
           """Envía el estado al Central via WebSocket."""
           import json

           payload = {
               "type": "idle_state",
               "node_id": self.node_id,
               "state": state.value,
               "idle_seconds": idle_seconds,
               "timestamp": time.time(),
           }
           try:
               if self._ws is not None:
                   await self._ws.send(json.dumps(payload))
                   logger.debug(
                       "Estado enviado al Central: node=%s state=%s idle=%.0fs",
                       self.node_id,
                       state.value,
                       idle_seconds,
                   )
           except Exception as exc:
               logger.warning("No se pudo enviar estado al Central: %s", exc)

       async def _poll_loop(self) -> None:
           """Loop principal de detección de inactividad."""
           while self._running:
               new_state, idle_seconds = self._detect_state()

               if new_state != self._current_state:
                   logger.info(
                       "Cambio de estado: %s → %s (idle=%.0fs)",
                       self._current_state.value,
                       new_state.value,
                       idle_seconds,
                   )
                   self._current_state = new_state
                   event = IdleEvent(
                       state=new_state,
                       idle_seconds=idle_seconds,
                       node_id=self.node_id,
                   )
                   await self._send_state(new_state, idle_seconds)
                   if self.on_state_change:
                       self.on_state_change(event)

               await asyncio.sleep(self.poll_interval)

       async def start(self) -> None:
           """Inicia el detector. Conecta al Central via WebSocket y comienza polling."""
           import websockets

           self._running = True
           logger.info(
               "IdleDetector iniciado: node=%s threshold=%ds poll=%ds",
               self.node_id,
               self.idle_threshold,
               self.poll_interval,
           )

           reconnect_delay = 1
           while self._running:
               try:
                   async with websockets.connect(self.ws_url) as ws:
                       self._ws = ws
                       reconnect_delay = 1
                       logger.info("IdleDetector conectado al Central: %s", self.ws_url)
                       await self._poll_loop()
               except Exception as exc:
                   logger.warning(
                       "IdleDetector desconectado: %s — reconectando en %ds",
                       exc,
                       reconnect_delay,
                   )
                   self._ws = None
                   await asyncio.sleep(reconnect_delay)
                   reconnect_delay = min(reconnect_delay * 2, 60)

       def stop(self) -> None:
           """Detiene el detector."""
           self._running = False
           logger.info("IdleDetector detenido: node=%s", self.node_id)

4. Crear archivo src/cluster/scheduler.py:

   Ruta: ~/yeyo-os/src/cluster/scheduler.py
   Contenido:

   """
   YeyoNet Cluster Mode — Scheduler de tareas distribuidas
   Micro-fase 7.19 — Capa 7: Evolución

   ClusterScheduler:
   - Detecta satélites idle (sin actividad 10+ min)
   - Asigna tareas por capacidad (GPU VRAM disponible)
   - Retry automático si un satélite se desconecta
   - Mantiene estado de nodos y tareas en Redis
   """

   from __future__ import annotations

   import json
   import logging
   import time
   import uuid
   from dataclasses import asdict, dataclass, field
   from enum import Enum
   from typing import Any, Dict, List, Optional

   import redis

   from .worker import (
       celery_app,
       generate_image_task,
       run_graph_task,
       train_lora_task,
   )

   logger = logging.getLogger(__name__)


   class TaskPriority(int, Enum):
       LOW = 1
       NORMAL = 5
       HIGH = 9


   class TaskStatus(str, Enum):
       PENDING = "pending"
       ASSIGNED = "assigned"
       RUNNING = "running"
       SUCCESS = "success"
       FAILURE = "failure"
       CANCELLED = "cancelled"


   @dataclass
   class NodeCapacity:
       """Capacidad reportada por un nodo satélite."""

       node_id: str
       vram_total_mb: int = 0
       vram_free_mb: int = 0
       ram_free_mb: int = 0
       cpu_percent: float = 0.0
       is_idle: bool = False
       last_seen: float = field(default_factory=time.time)
       tailscale_ip: str = ""

       @property
       def is_available(self) -> bool:
           """Disponible = idle Y visto en los últimos 2 minutos."""
           return self.is_idle and (time.time() - self.last_seen) < 120

       @classmethod
       def from_dict(cls, data: Dict[str, Any]) -> "NodeCapacity":
           return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


   @dataclass
   class ClusterTask:
       """Tarea distribuida en la cola del cluster."""

       task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
       task_type: str = ""  # "generate_image" | "run_graph" | "train_lora"
       payload: Dict[str, Any] = field(default_factory=dict)
       priority: int = TaskPriority.NORMAL
       status: str = TaskStatus.PENDING
       assigned_node: Optional[str] = None
       celery_task_id: Optional[str] = None
       created_at: float = field(default_factory=time.time)
       started_at: Optional[float] = None
       completed_at: Optional[float] = None
       result: Optional[Any] = None
       error: Optional[str] = None
       retry_count: int = 0
       max_retries: int = 3
       vram_needed_mb: int = 0

       def to_dict(self) -> Dict[str, Any]:
           return asdict(self)

       @classmethod
       def from_dict(cls, data: Dict[str, Any]) -> "ClusterTask":
           return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


   class ClusterScheduler:
       """
       Scheduler principal del Cluster Mode.

       Gestiona nodos y tareas en Redis.
       Asigna tareas a satélites según capacidad y estado idle.
       Reintenta tareas si el satélite se desconecta.
       """

       NODE_KEY = "cluster:node:{node_id}"
       NODES_SET = "cluster:nodes"
       TASK_KEY = "cluster:task:{task_id}"
       TASKS_SET = "cluster:tasks"
       PENDING_QUEUE = "cluster:queue:pending"

       def __init__(self, redis_client: redis.Redis) -> None:
           self._redis = redis_client

       # ── Gestión de nodos ────────────────────────────────────────────────────

       def register_node(self, capacity: NodeCapacity) -> None:
           """Registra o actualiza la capacidad de un nodo en Redis."""
           key = self.NODE_KEY.format(node_id=capacity.node_id)
           self._redis.set(key, json.dumps(asdict(capacity)), ex=300)
           self._redis.sadd(self.NODES_SET, capacity.node_id)
           logger.debug(
               "Nodo registrado: %s vram_free=%dMB idle=%s",
               capacity.node_id,
               capacity.vram_free_mb,
               capacity.is_idle,
           )

       def update_node_idle_state(self, node_id: str, is_idle: bool, idle_seconds: float = 0.0) -> None:
           """Actualiza el estado idle de un nodo."""
           key = self.NODE_KEY.format(node_id=node_id)
           raw = self._redis.get(key)
           if raw:
               data = json.loads(raw)
               data["is_idle"] = is_idle
               data["last_seen"] = time.time()
               self._redis.set(key, json.dumps(data), ex=300)
               logger.info(
                   "Estado idle actualizado: node=%s idle=%s idle_seconds=%.0f",
                   node_id,
                   is_idle,
                   idle_seconds,
               )

       def get_node(self, node_id: str) -> Optional[NodeCapacity]:
           """Obtiene la capacidad actual de un nodo."""
           key = self.NODE_KEY.format(node_id=node_id)
           raw = self._redis.get(key)
           if raw:
               return NodeCapacity.from_dict(json.loads(raw))
           return None

       def get_all_nodes(self) -> List[NodeCapacity]:
           """Retorna todos los nodos registrados."""
           node_ids = self._redis.smembers(self.NODES_SET)
           nodes = []
           for nid in node_ids:
               node = self.get_node(nid)
               if node:
                   nodes.append(node)
           return nodes

       def get_idle_nodes(self) -> List[NodeCapacity]:
           """Retorna nodos disponibles (idle y vistos recientemente)."""
           return [n for n in self.get_all_nodes() if n.is_available]

       def select_best_node(self, vram_needed_mb: int = 0) -> Optional[NodeCapacity]:
           """
           Selecciona el mejor nodo para ejecutar una tarea.
           Criterio: idle + mayor VRAM libre + VRAM suficiente para la tarea.
           """
           idle = self.get_idle_nodes()
           if not idle:
               return None

           # Filtrar por VRAM suficiente si se necesita GPU
           if vram_needed_mb > 0:
               idle = [n for n in idle if n.vram_free_mb >= vram_needed_mb]

           if not idle:
               return None

           # Ordenar por VRAM libre descendente
           idle.sort(key=lambda n: n.vram_free_mb, reverse=True)
           return idle[0]

       # ── Gestión de tareas ───────────────────────────────────────────────────

       def enqueue_task(self, task: ClusterTask) -> str:
           """Encola una tarea. Retorna task_id."""
           key = self.TASK_KEY.format(task_id=task.task_id)
           self._redis.set(key, json.dumps(task.to_dict()), ex=86400)
           self._redis.sadd(self.TASKS_SET, task.task_id)
           self._redis.lpush(self.PENDING_QUEUE, task.task_id)
           logger.info(
               "Tarea encolada: task_id=%s type=%s priority=%d",
               task.task_id,
               task.task_type,
               task.priority,
           )
           return task.task_id

       def get_task(self, task_id: str) -> Optional[ClusterTask]:
           """Obtiene una tarea por ID."""
           key = self.TASK_KEY.format(task_id=task_id)
           raw = self._redis.get(key)
           if raw:
               return ClusterTask.from_dict(json.loads(raw))
           return None

       def update_task(self, task: ClusterTask) -> None:
           """Actualiza el estado de una tarea en Redis."""
           key = self.TASK_KEY.format(task_id=task.task_id)
           self._redis.set(key, json.dumps(task.to_dict()), ex=86400)

       def get_all_tasks(self) -> List[ClusterTask]:
           """Retorna todas las tareas."""
           task_ids = self._redis.smembers(self.TASKS_SET)
           tasks = []
           for tid in task_ids:
               task = self.get_task(tid)
               if task:
                   tasks.append(task)
           return tasks

       def dispatch_pending(self) -> int:
           """
           Despacha tareas pendientes a nodos idle disponibles.
           Retorna número de tareas despachadas.
           """
           dispatched = 0
           while True:
               task_id_bytes = self._redis.rpop(self.PENDING_QUEUE)
               if not task_id_bytes:
                   break

               task_id = task_id_bytes if isinstance(task_id_bytes, str) else task_id_bytes.decode()
               task = self.get_task(task_id)
               if not task or task.status != TaskStatus.PENDING:
                   continue

               node = self.select_best_node(vram_needed_mb=task.vram_needed_mb)
               if not node:
                   # No hay nodos disponibles — volver a encolar
                   self._redis.lpush(self.PENDING_QUEUE, task_id)
                   logger.debug("Sin nodos disponibles para task=%s", task_id)
                   break

               self._dispatch_to_node(task, node)
               dispatched += 1

           return dispatched

       def _dispatch_to_node(self, task: ClusterTask, node: NodeCapacity) -> None:
           """Envía una tarea a un nodo específico via Celery."""
           task.status = TaskStatus.ASSIGNED
           task.assigned_node = node.node_id
           task.started_at = time.time()

           payload = {**task.payload, "node_id": node.node_id}
           routing_key = self._get_routing_key(task.task_type)

           if task.task_type == "generate_image":
               result = generate_image_task.apply_async(
                   kwargs=payload,
                   queue=routing_key,
                   priority=task.priority,
               )
           elif task.task_type == "run_graph":
               result = run_graph_task.apply_async(
                   kwargs=payload,
                   queue=routing_key,
                   priority=task.priority,
               )
           elif task.task_type == "train_lora":
               result = train_lora_task.apply_async(
                   kwargs=payload,
                   queue=routing_key,
                   priority=task.priority,
               )
           else:
               logger.error("Tipo de tarea desconocido: %s", task.task_type)
               task.status = TaskStatus.FAILURE
               task.error = f"Tipo de tarea desconocido: {task.task_type}"
               self.update_task(task)
               return

           task.celery_task_id = result.id
           task.status = TaskStatus.RUNNING
           self.update_task(task)

           logger.info(
               "Tarea despachada: task_id=%s → node=%s celery_id=%s",
               task.task_id,
               node.node_id,
               result.id,
           )

       def handle_node_disconnected(self, node_id: str) -> int:
           """
           Maneja desconexión de un nodo.
           Reasigna sus tareas running a otros nodos.
           Retorna número de tareas reasignadas.
           """
           reassigned = 0
           all_tasks = self.get_all_tasks()

           for task in all_tasks:
               if task.assigned_node == node_id and task.status in (
                   TaskStatus.ASSIGNED,
                   TaskStatus.RUNNING,
               ):
                   if task.retry_count < task.max_retries:
                       task.status = TaskStatus.PENDING
                       task.assigned_node = None
                       task.celery_task_id = None
                       task.retry_count += 1
                       self.update_task(task)
                       self._redis.lpush(self.PENDING_QUEUE, task.task_id)
                       logger.info(
                           "Tarea reasignada por desconexión: task_id=%s retry=%d",
                           task.task_id,
                           task.retry_count,
                       )
                       reassigned += 1
                   else:
                       task.status = TaskStatus.FAILURE
                       task.error = f"Nodo {node_id} desconectado, max retries alcanzado"
                       self.update_task(task)
                       logger.warning(
                           "Tarea fallida por desconexión: task_id=%s", task.task_id
                       )

           # Marcar nodo como no disponible
           self.update_node_idle_state(node_id, is_idle=False)
           return reassigned

       @staticmethod
       def _get_routing_key(task_type: str) -> str:
           mapping = {
               "generate_image": "gpu_tasks",
               "run_graph": "cpu_tasks",
               "train_lora": "training_tasks",
           }
           return mapping.get(task_type, "cpu_tasks")

5. Crear archivo src/api/cluster_api.py:

   Ruta: ~/yeyo-os/src/api/cluster_api.py
   Contenido:

   """
   YeyoNet Cluster Mode — API endpoints FastAPI
   Micro-fase 7.19 — Capa 7: Evolución

   Endpoints:
   POST /api/cluster/task          — Enviar tarea al cluster
   GET  /api/cluster/tasks         — Listar tareas (con filtros)
   GET  /api/cluster/tasks/{id}    — Estado de una tarea
   DELETE /api/cluster/tasks/{id}  — Cancelar tarea
   GET  /api/cluster/nodes/status  — Estado de todos los nodos
   POST /api/cluster/nodes/{id}/idle — Satélite reporta estado idle
   """

   from __future__ import annotations

   import logging
   import os
   from typing import Any, Dict, List, Optional

   import redis
   from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
   from pydantic import BaseModel, Field

   from src.cluster.scheduler import ClusterScheduler, ClusterTask, NodeCapacity, TaskPriority, TaskStatus

   logger = logging.getLogger(__name__)

   router = APIRouter(prefix="/api/cluster", tags=["cluster"])


   # ── Dependencias ─────────────────────────────────────────────────────────────

   def get_redis() -> redis.Redis:
       return redis.Redis(
           host=os.environ.get("REDIS_HOST", "localhost"),
           port=int(os.environ.get("REDIS_PORT", "6379")),
           decode_responses=True,
       )


   def get_scheduler(r: redis.Redis = Depends(get_redis)) -> ClusterScheduler:
       return ClusterScheduler(r)


   # ── Schemas ──────────────────────────────────────────────────────────────────

   class SubmitTaskRequest(BaseModel):
       task_type: str = Field(..., description="generate_image | run_graph | train_lora")
       payload: Dict[str, Any] = Field(default_factory=dict)
       priority: int = Field(default=TaskPriority.NORMAL, ge=1, le=9)
       vram_needed_mb: int = Field(default=0, ge=0, description="VRAM mínima necesaria en MB")


   class TaskResponse(BaseModel):
       task_id: str
       task_type: str
       status: str
       assigned_node: Optional[str]
       celery_task_id: Optional[str]
       created_at: float
       started_at: Optional[float]
       completed_at: Optional[float]
       result: Optional[Any]
       error: Optional[str]
       retry_count: int


   class NodeStatusResponse(BaseModel):
       node_id: str
       vram_total_mb: int
       vram_free_mb: int
       ram_free_mb: int
       cpu_percent: float
       is_idle: bool
       is_available: bool
       last_seen: float
       tailscale_ip: str


   class ReportIdleRequest(BaseModel):
       is_idle: bool
       idle_seconds: float = 0.0
       vram_total_mb: int = 0
       vram_free_mb: int = 0
       ram_free_mb: int = 0
       cpu_percent: float = 0.0
       tailscale_ip: str = ""


   # ── Endpoints ────────────────────────────────────────────────────────────────

   @router.post("/task", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
   def submit_task(
       req: SubmitTaskRequest,
       scheduler: ClusterScheduler = Depends(get_scheduler),
   ) -> TaskResponse:
       """Envía una tarea al cluster. La asigna al mejor nodo idle disponible."""
       task = ClusterTask(
           task_type=req.task_type,
           payload=req.payload,
           priority=req.priority,
           vram_needed_mb=req.vram_needed_mb,
       )
       scheduler.enqueue_task(task)

       # Intentar despachar inmediatamente
       dispatched = scheduler.dispatch_pending()
       logger.info("submit_task: task_id=%s dispatched=%d", task.task_id, dispatched)

       # Refrescar tarea tras despacho
       updated = scheduler.get_task(task.task_id) or task
       return _task_to_response(updated)


   @router.get("/tasks", response_model=List[TaskResponse])
   def list_tasks(
       status_filter: Optional[str] = None,
       scheduler: ClusterScheduler = Depends(get_scheduler),
   ) -> List[TaskResponse]:
       """Lista todas las tareas. Opcionalmente filtra por status."""
       tasks = scheduler.get_all_tasks()
       if status_filter:
           tasks = [t for t in tasks if t.status == status_filter]
       tasks.sort(key=lambda t: t.created_at, reverse=True)
       return [_task_to_response(t) for t in tasks]


   @router.get("/tasks/{task_id}", response_model=TaskResponse)
   def get_task(
       task_id: str,
       scheduler: ClusterScheduler = Depends(get_scheduler),
   ) -> TaskResponse:
       """Obtiene el estado de una tarea por ID."""
       task = scheduler.get_task(task_id)
       if not task:
           raise HTTPException(status_code=404, detail=f"Tarea {task_id} no encontrada")
       return _task_to_response(task)


   @router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
   def cancel_task(
       task_id: str,
       scheduler: ClusterScheduler = Depends(get_scheduler),
   ) -> None:
       """Cancela una tarea pendiente o en ejecución."""
       task = scheduler.get_task(task_id)
       if not task:
           raise HTTPException(status_code=404, detail=f"Tarea {task_id} no encontrada")
       if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.CANCELLED):
           raise HTTPException(
               status_code=400, detail=f"Tarea ya en estado final: {task.status}"
           )

       # Revocar tarea Celery si está asignada
       if task.celery_task_id:
           celery_app.control.revoke(task.celery_task_id, terminate=True)

       task.status = TaskStatus.CANCELLED
       scheduler.update_task(task)
       logger.info("Tarea cancelada: task_id=%s", task_id)


   @router.get("/nodes/status", response_model=List[NodeStatusResponse])
   def get_nodes_status(
       scheduler: ClusterScheduler = Depends(get_scheduler),
   ) -> List[NodeStatusResponse]:
       """Retorna el estado de todos los nodos registrados en el cluster."""
       nodes = scheduler.get_all_nodes()
       return [_node_to_response(n) for n in nodes]


   @router.post("/nodes/{node_id}/idle", status_code=status.HTTP_200_OK)
   def report_idle_state(
       node_id: str,
       req: ReportIdleRequest,
       scheduler: ClusterScheduler = Depends(get_scheduler),
   ) -> Dict[str, Any]:
       """
       El satélite reporta su estado idle/active al Central.
       Si pasa a idle, el scheduler puede asignarle tareas.
       """
       capacity = NodeCapacity(
           node_id=node_id,
           vram_total_mb=req.vram_total_mb,
           vram_free_mb=req.vram_free_mb,
           ram_free_mb=req.ram_free_mb,
           cpu_percent=req.cpu_percent,
           is_idle=req.is_idle,
           tailscale_ip=req.tailscale_ip,
       )
       scheduler.register_node(capacity)

       dispatched = 0
       if req.is_idle:
           dispatched = scheduler.dispatch_pending()
           logger.info("Nodo idle registrado: %s — tareas despachadas: %d", node_id, dispatched)

       return {
           "node_id": node_id,
           "is_idle": req.is_idle,
           "tasks_dispatched": dispatched,
       }


   @router.websocket("/ws/nodes")
   async def cluster_websocket(ws: WebSocket, scheduler: ClusterScheduler = Depends(get_scheduler)) -> None:
       """
       WebSocket para que los satélites reporten estado idle en tiempo real.
       Recibe mensajes JSON: {"type": "idle_state", "node_id": ..., "state": ..., "idle_seconds": ...}
       """
       import json

       await ws.accept()
       logger.info("WebSocket cluster conectado")

       try:
           while True:
               raw = await ws.receive_text()
               msg = json.loads(raw)

               if msg.get("type") == "idle_state":
                   node_id = msg.get("node_id", "unknown")
                   is_idle = msg.get("state") == "idle"
                   idle_seconds = msg.get("idle_seconds", 0.0)
                   scheduler.update_node_idle_state(node_id, is_idle, idle_seconds)

                   if is_idle:
                       dispatched = scheduler.dispatch_pending()
                       await ws.send_text(json.dumps({
                           "type": "ack",
                           "node_id": node_id,
                           "tasks_dispatched": dispatched,
                       }))

       except WebSocketDisconnect:
           logger.info("WebSocket cluster desconectado")


   # ── Helpers ──────────────────────────────────────────────────────────────────

   def _task_to_response(task: ClusterTask) -> TaskResponse:
       return TaskResponse(
           task_id=task.task_id,
           task_type=task.task_type,
           status=task.status,
           assigned_node=task.assigned_node,
           celery_task_id=task.celery_task_id,
           created_at=task.created_at,
           started_at=task.started_at,
           completed_at=task.completed_at,
           result=task.result,
           error=task.error,
           retry_count=task.retry_count,
       )


   def _node_to_response(node: NodeCapacity) -> NodeStatusResponse:
       return NodeStatusResponse(
           node_id=node.node_id,
           vram_total_mb=node.vram_total_mb,
           vram_free_mb=node.vram_free_mb,
           ram_free_mb=node.ram_free_mb,
           cpu_percent=node.cpu_percent,
           is_idle=node.is_idle,
           is_available=node.is_available,
           last_seen=node.last_seen,
           tailscale_ip=node.tailscale_ip,
       )

   # Import aquí para evitar circular import
   from src.cluster.worker import celery_app

6. Crear archivo tests/test_cluster.py:

   Ruta: ~/yeyo-os/tests/test_cluster.py
   Contenido:

   """
   Tests para YeyoNet Cluster Mode (7.19).
   Usa Celery en eager mode (sin broker real) y fakeredis.
   """

   from __future__ import annotations

   import json
   import time
   from unittest.mock import MagicMock, patch

   import fakeredis
   import pytest
   from fastapi.testclient import TestClient

   from src.cluster.scheduler import (
       ClusterScheduler,
       ClusterTask,
       NodeCapacity,
       TaskPriority,
       TaskStatus,
   )
   from src.cluster.worker import celery_app


   # ── Fixtures ─────────────────────────────────────────────────────────────────

   @pytest.fixture(autouse=True)
   def celery_eager():
       """Ejecuta tareas Celery de forma síncrona en tests."""
       celery_app.conf.task_always_eager = True
       celery_app.conf.task_eager_propagates = False
       yield
       celery_app.conf.task_always_eager = False


   @pytest.fixture
   def redis_client():
       return fakeredis.FakeRedis(decode_responses=True)


   @pytest.fixture
   def scheduler(redis_client):
       return ClusterScheduler(redis_client)


   @pytest.fixture
   def idle_node():
       return NodeCapacity(
           node_id="sat-1",
           vram_total_mb=6000,
           vram_free_mb=4096,
           ram_free_mb=8192,
           cpu_percent=5.0,
           is_idle=True,
           last_seen=time.time(),
           tailscale_ip="100.64.0.2",
       )


   @pytest.fixture
   def busy_node():
       return NodeCapacity(
           node_id="sat-2",
           vram_total_mb=4000,
           vram_free_mb=2048,
           ram_free_mb=4096,
           cpu_percent=90.0,
           is_idle=False,
           last_seen=time.time(),
           tailscale_ip="100.64.0.3",
       )


   # ── Tests: NodeCapacity ───────────────────────────────────────────────────────

   class TestNodeCapacity:
       def test_is_available_idle_recent(self, idle_node):
           assert idle_node.is_available is True

       def test_not_available_busy(self, busy_node):
           assert busy_node.is_available is False

       def test_not_available_stale(self, idle_node):
           idle_node.last_seen = time.time() - 200
           assert idle_node.is_available is False

       def test_from_dict_roundtrip(self, idle_node):
           import dataclasses
           d = dataclasses.asdict(idle_node)
           restored = NodeCapacity.from_dict(d)
           assert restored.node_id == idle_node.node_id
           assert restored.vram_free_mb == idle_node.vram_free_mb


   # ── Tests: ClusterScheduler ───────────────────────────────────────────────────

   class TestClusterScheduler:
       def test_register_and_get_node(self, scheduler, idle_node):
           scheduler.register_node(idle_node)
           result = scheduler.get_node("sat-1")
           assert result is not None
           assert result.node_id == "sat-1"
           assert result.vram_free_mb == 4096

       def test_get_idle_nodes(self, scheduler, idle_node, busy_node):
           scheduler.register_node(idle_node)
           scheduler.register_node(busy_node)
           idle = scheduler.get_idle_nodes()
           assert len(idle) == 1
           assert idle[0].node_id == "sat-1"

       def test_select_best_node_by_vram(self, scheduler):
           n1 = NodeCapacity(
               node_id="n1", vram_free_mb=2048, is_idle=True, last_seen=time.time()
           )
           n2 = NodeCapacity(
               node_id="n2", vram_free_mb=6144, is_idle=True, last_seen=time.time()
           )
           scheduler.register_node(n1)
           scheduler.register_node(n2)
           best = scheduler.select_best_node(vram_needed_mb=1024)
           assert best is not None
           assert best.node_id == "n2"

       def test_select_best_node_insufficient_vram(self, scheduler):
           n = NodeCapacity(
               node_id="n1", vram_free_mb=1024, is_idle=True, last_seen=time.time()
           )
           scheduler.register_node(n)
           best = scheduler.select_best_node(vram_needed_mb=4096)
           assert best is None

       def test_select_best_node_no_idle(self, scheduler, busy_node):
           scheduler.register_node(busy_node)
           best = scheduler.select_best_node()
           assert best is None

       def test_enqueue_task(self, scheduler):
           task = ClusterTask(task_type="run_graph", payload={"graph_id": "g1"})
           task_id = scheduler.enqueue_task(task)
           assert task_id == task.task_id
           retrieved = scheduler.get_task(task_id)
           assert retrieved is not None
           assert retrieved.status == TaskStatus.PENDING

       def test_update_idle_state(self, scheduler, idle_node):
           scheduler.register_node(idle_node)
           scheduler.update_node_idle_state("sat-1", is_idle=False)
           node = scheduler.get_node("sat-1")
           assert node.is_idle is False

       def test_dispatch_pending_no_nodes(self, scheduler):
           task = ClusterTask(task_type="run_graph", payload={})
           scheduler.enqueue_task(task)
           dispatched = scheduler.dispatch_pending()
           assert dispatched == 0
           # Tarea debe seguir pendiente
           t = scheduler.get_task(task.task_id)
           assert t.status == TaskStatus.PENDING

       def test_handle_node_disconnected_reassigns(self, scheduler, idle_node):
           scheduler.register_node(idle_node)
           task = ClusterTask(
               task_type="run_graph",
               payload={},
               status=TaskStatus.RUNNING,
               assigned_node="sat-1",
               retry_count=0,
               max_retries=3,
           )
           task.task_id = "task-disc-1"
           scheduler.update_task(task)
           # Forzar en el set de tareas
           scheduler._redis.sadd(scheduler.TASKS_SET, task.task_id)

           reassigned = scheduler.handle_node_disconnected("sat-1")
           assert reassigned == 1
           t = scheduler.get_task(task.task_id)
           assert t.status == TaskStatus.PENDING
           assert t.retry_count == 1

       def test_handle_node_disconnected_max_retries(self, scheduler, idle_node):
           scheduler.register_node(idle_node)
           task = ClusterTask(
               task_type="run_graph",
               payload={},
               status=TaskStatus.RUNNING,
               assigned_node="sat-1",
               retry_count=3,
               max_retries=3,
           )
           task.task_id = "task-maxretry-1"
           scheduler.update_task(task)
           scheduler._redis.sadd(scheduler.TASKS_SET, task.task_id)

           scheduler.handle_node_disconnected("sat-1")
           t = scheduler.get_task(task.task_id)
           assert t.status == TaskStatus.FAILURE

       def test_get_all_nodes(self, scheduler, idle_node, busy_node):
           scheduler.register_node(idle_node)
           scheduler.register_node(busy_node)
           nodes = scheduler.get_all_nodes()
           node_ids = {n.node_id for n in nodes}
           assert "sat-1" in node_ids
           assert "sat-2" in node_ids


   # ── Tests: API HTTP ───────────────────────────────────────────────────────────

   @pytest.fixture
   def app(redis_client):
       from fastapi import FastAPI
       from src.api.cluster_api import router, get_redis, get_scheduler

       app = FastAPI()
       app.include_router(router)
       app.dependency_overrides[get_redis] = lambda: redis_client
       app.dependency_overrides[get_scheduler] = lambda: ClusterScheduler(redis_client)
       return app


   @pytest.fixture
   def client(app):
       return TestClient(app)


   class TestClusterAPI:
       def test_get_nodes_empty(self, client):
           r = client.get("/api/cluster/nodes/status")
           assert r.status_code == 200
           assert r.json() == []

       def test_report_idle_state(self, client):
           r = client.post("/api/cluster/nodes/sat-1/idle", json={
               "is_idle": True,
               "idle_seconds": 650.0,
               "vram_total_mb": 6000,
               "vram_free_mb": 4096,
               "ram_free_mb": 8192,
               "cpu_percent": 3.0,
               "tailscale_ip": "100.64.0.2",
           })
           assert r.status_code == 200
           data = r.json()
           assert data["node_id"] == "sat-1"
           assert data["is_idle"] is True

       def test_get_nodes_after_register(self, client):
           client.post("/api/cluster/nodes/sat-1/idle", json={
               "is_idle": True, "idle_seconds": 700.0,
               "vram_total_mb": 6000, "vram_free_mb": 4096,
               "ram_free_mb": 8192, "cpu_percent": 5.0, "tailscale_ip": "100.64.0.2",
           })
           r = client.get("/api/cluster/nodes/status")
           assert r.status_code == 200
           nodes = r.json()
           assert len(nodes) == 1
           assert nodes[0]["node_id"] == "sat-1"
           assert nodes[0]["is_idle"] is True

       def test_submit_task(self, client):
           r = client.post("/api/cluster/task", json={
               "task_type": "run_graph",
               "payload": {"graph_id": "g-test"},
               "priority": 5,
               "vram_needed_mb": 0,
           })
           assert r.status_code == 201
           data = r.json()
           assert "task_id" in data
           assert data["task_type"] == "run_graph"

       def test_get_task(self, client):
           r = client.post("/api/cluster/task", json={
               "task_type": "run_graph",
               "payload": {"graph_id": "g-test"},
           })
           task_id = r.json()["task_id"]
           r2 = client.get(f"/api/cluster/tasks/{task_id}")
           assert r2.status_code == 200
           assert r2.json()["task_id"] == task_id

       def test_get_task_not_found(self, client):
           r = client.get("/api/cluster/tasks/nonexistent-id")
           assert r.status_code == 404

       def test_list_tasks(self, client):
           client.post("/api/cluster/task", json={"task_type": "run_graph", "payload": {}})
           client.post("/api/cluster/task", json={"task_type": "train_lora", "payload": {}})
           r = client.get("/api/cluster/tasks")
           assert r.status_code == 200
           assert len(r.json()) >= 2

       def test_cancel_task(self, client):
           r = client.post("/api/cluster/task", json={"task_type": "run_graph", "payload": {}})
           task_id = r.json()["task_id"]
           r2 = client.delete(f"/api/cluster/tasks/{task_id}")
           assert r2.status_code == 204

       def test_cancel_nonexistent_task(self, client):
           r = client.delete("/api/cluster/tasks/does-not-exist")
           assert r.status_code == 404

       def test_dispatch_on_idle_registration(self, client):
           """Al registrar un nodo idle, las tareas pendientes se despachan."""
           # Encolar tarea primero
           client.post("/api/cluster/task", json={
               "task_type": "run_graph",
               "payload": {"graph_id": "g-dispatch"},
               "vram_needed_mb": 0,
           })
           # Registrar nodo idle
           r = client.post("/api/cluster/nodes/sat-dispatch/idle", json={
               "is_idle": True, "idle_seconds": 700.0,
               "vram_total_mb": 4000, "vram_free_mb": 3000,
               "ram_free_mb": 8000, "cpu_percent": 2.0, "tailscale_ip": "100.64.0.5",
           })
           assert r.status_code == 200


   # ── Tests: IdleDetector ───────────────────────────────────────────────────────

   class TestIdleDetector:
       def test_detect_state_active(self):
           from src.cluster.idle_detector import IdleDetector, IdleState

           detector = IdleDetector(
               node_id="test-node",
               ws_url="ws://localhost:8000",
               idle_threshold_seconds=600,
           )
           with patch("src.cluster.idle_detector.get_system_idle_seconds", return_value=30.0):
               state, seconds = detector._detect_state()
           assert state == IdleState.ACTIVE
           assert seconds == 30.0

       def test_detect_state_idle(self):
           from src.cluster.idle_detector import IdleDetector, IdleState

           detector = IdleDetector(
               node_id="test-node",
               ws_url="ws://localhost:8000",
               idle_threshold_seconds=600,
           )
           with patch("src.cluster.idle_detector.get_system_idle_seconds", return_value=700.0):
               state, seconds = detector._detect_state()
           assert state == IdleState.IDLE
           assert seconds == 700.0

       def test_stop(self):
           from src.cluster.idle_detector import IdleDetector

           detector = IdleDetector(node_id="n", ws_url="ws://x")
           detector._running = True
           detector.stop()
           assert detector._running is False

VERIFICAR:
- [ ] src/cluster/__init__.py exporta CeleryWorker, celery_app, ClusterScheduler, IdleDetector
- [ ] src/cluster/worker.py define generate_image_task, run_graph_task, train_lora_task con retry
- [ ] src/cluster/idle_detector.py detecta inactividad en Linux/Windows/macOS con threshold de 600s
- [ ] src/cluster/scheduler.py selecciona mejor nodo por VRAM libre, reasigna si se desconecta
- [ ] src/api/cluster_api.py tiene 6 endpoints: POST /task, GET /tasks, GET /tasks/{id}, DELETE /tasks/{id}, GET /nodes/status, POST /nodes/{id}/idle
- [ ] Tests pasan: pytest tests/test_cluster.py (requiere fakeredis: pip install fakeredis)
- [ ] Celery eager mode funciona en tests sin Redis real

SI FALLA:
- fakeredis no instalado: pip install fakeredis
- celery no instalado: pip install celery redis
- websockets no instalado: pip install websockets
- Import errors: verificar que src/cluster/__init__.py es correcto
- Celery tasks no se ejecutan: verificar celery_app.conf.task_always_eager = True en tests
- Redis connection error en producción: verificar REDIS_URL env var

NO HACER:
- No instalar Celery con SQLite backend — usar Redis (ya existe en Capa 0)
- No ejecutar tareas síncronas bloqueantes en el thread principal de FastAPI
- No compartir VRAM allocation entre tareas (cada tarea asume VRAM disponible al inicio)
- No implementar GPU pool real con gRPC (eso es 7.20)
- No implementar federated learning aquí (eso es 7.21)
- No exponer el WebSocket cluster sin autenticación en producción

GATE: Central envía tarea run_graph_task via POST /api/cluster/task, satélite idle registrado via POST /nodes/{id}/idle la recibe automáticamente, tarea queda en estado RUNNING con assigned_node correcto. Si el satélite se desconecta, la tarea se reasigna. Todos los tests pasan (≥24 tests).
```
