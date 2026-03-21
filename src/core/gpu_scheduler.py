"""
YeyoOS — GPU Scheduler
Micro-fase 1.8 — Capa 1: Esqueleto

Scheduler de GPU basado en prioridades para GTX 1060 3GB.

Prioridades:
  P0 (COMPOSITOR): Siempre reservado, 200MB, NUNCA preemptable
  P1 (USER):       Peticiones del usuario, puede preemptar P2/P3
  P2 (BACKGROUND): Tareas de fondo, puede preemptar P3
  P3 (IDLE):       Tareas ociosas, NUNCA preempta

Reglas:
  - Compositor SIEMPRE tiene sus 200MB
  - VRAM disponible = total - compositor_reserved
  - Una tarea solo se ejecuta si cabe en VRAM disponible
  - Prioridad mayor puede preemptar menor
  - Ollama (~1800MB) y SD (~2500MB) NUNCA simultáneos
"""

import asyncio
import uuid
import time
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional


class GPUPriority(IntEnum):
    """Prioridad de tareas GPU. Menor número = mayor prioridad."""
    P0_COMPOSITOR = 0    # Siempre reservado, nunca preemptable
    P1_USER = 1          # Peticiones del usuario (chat, imagen)
    P2_BACKGROUND = 2    # Tareas de fondo (embeddings, mantenimiento)
    P3_IDLE = 3          # Tareas ociosas (optimización nocturna)


@dataclass
class GPUTask:
    """Tarea que necesita recursos GPU."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    priority: GPUPriority = GPUPriority.P2_BACKGROUND
    vram_needed_mb: int = 0
    status: str = "pending"   # pending | running | completed | preempted | failed
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def __lt__(self, other: "GPUTask") -> bool:
        return self.priority < other.priority


class GPUScheduler:
    """
    Scheduler de GPU basado en prioridades.

    Garantiza:
    1. Compositor SIEMPRE tiene 200MB reservados
    2. Tareas de mayor prioridad preemptan las de menor
    3. NUNCA se excede la VRAM total
    4. Solo UNA tarea pesada a la vez (Ollama O SD, nunca ambos)
    """

    def __init__(
        self,
        total_vram_mb: int = 3072,
        compositor_reserved_mb: int = 200,
    ):
        self.total_vram_mb = total_vram_mb
        self.compositor_reserved_mb = compositor_reserved_mb
        self.available_vram_mb = total_vram_mb - compositor_reserved_mb
        self._current_tasks: dict[str, GPUTask] = {}
        self._used_vram_mb: int = 0
        self._queue: asyncio.PriorityQueue[GPUTask] = asyncio.PriorityQueue()
        self._lock = asyncio.Lock()
        self._task_history: list[GPUTask] = []

    @property
    def free_vram_mb(self) -> int:
        """VRAM libre (sin contar la reserva del compositor)."""
        return self.available_vram_mb - self._used_vram_mb

    async def submit(self, task: GPUTask) -> str:
        """
        Envía una tarea al scheduler.
        Retorna el task_id.
        Si la tarea no cabe, intenta preemptar tareas de menor prioridad.
        """
        async with self._lock:
            if task.vram_needed_mb > self.available_vram_mb:
                task.status = "failed"
                self._task_history.append(task)
                raise ValueError(
                    f"Tarea {task.id} necesita {task.vram_needed_mb}MB "
                    f"pero solo hay {self.available_vram_mb}MB disponibles (total)"
                )

            if self.can_fit(task.vram_needed_mb):
                self._start_task(task)
                return task.id

            if await self._preempt_if_needed(task):
                self._start_task(task)
                return task.id

            task.status = "pending"
            await self._queue.put(task)
            return task.id

    def can_fit(self, vram_needed_mb: int) -> bool:
        return vram_needed_mb <= self.free_vram_mb

    def _start_task(self, task: GPUTask) -> None:
        task.status = "running"
        task.started_at = time.time()
        self._current_tasks[task.id] = task
        self._used_vram_mb += task.vram_needed_mb

    async def _preempt_if_needed(self, new_task: GPUTask) -> bool:
        """
        Intenta preemptar tareas de menor prioridad para hacer espacio.
        P3 nunca preempta. P2 preempta P3. P1 preempta P2 y P3.
        Retorna True si se liberó suficiente espacio.
        NOTA: Se llama con _lock ya adquirido — modifica estado directamente.
        """
        if new_task.priority >= GPUPriority.P3_IDLE:
            return False

        preemptable = sorted(
            [
                t for t in self._current_tasks.values()
                if t.priority > new_task.priority
            ],
            key=lambda t: t.priority,
            reverse=True,
        )

        freed = 0
        needed = new_task.vram_needed_mb - self.free_vram_mb
        preempted = []

        for task in preemptable:
            if freed >= needed:
                break
            freed += task.vram_needed_mb
            preempted.append(task)

        if freed >= needed:
            for task in preempted:
                # Modifica estado directamente (ya tenemos el lock)
                self._current_tasks.pop(task.id)
                self._used_vram_mb -= task.vram_needed_mb
                task.status = "preempted"
                task.completed_at = time.time()
                self._task_history.append(task)
            return True

        return False

    async def release(self, task_id: str, status: str = "completed") -> None:
        """Libera una tarea y su VRAM. Intenta iniciar la siguiente en cola."""
        async with self._lock:
            if task_id not in self._current_tasks:
                return

            task = self._current_tasks.pop(task_id)
            self._used_vram_mb -= task.vram_needed_mb
            task.status = status
            task.completed_at = time.time()
            self._task_history.append(task)

        await self._process_queue()

    async def _process_queue(self) -> None:
        while not self._queue.empty():
            try:
                task = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            async with self._lock:
                if self.can_fit(task.vram_needed_mb):
                    self._start_task(task)
                else:
                    await self._queue.put(task)
                    break

    def get_status(self) -> dict:
        return {
            "total_vram_mb": self.total_vram_mb,
            "compositor_reserved_mb": self.compositor_reserved_mb,
            "available_vram_mb": self.available_vram_mb,
            "used_vram_mb": self._used_vram_mb,
            "free_vram_mb": self.free_vram_mb,
            "current_tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "priority": t.priority.name,
                    "vram_mb": t.vram_needed_mb,
                    "status": t.status,
                }
                for t in self._current_tasks.values()
            ],
            "queue_size": self._queue.qsize(),
        }

    def get_current_tasks(self) -> list[GPUTask]:
        return list(self._current_tasks.values())

    def get_task_count(self) -> int:
        return len(self._current_tasks)
