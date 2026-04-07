"""
YeyoOS — Pipeline Event Buffer

Buffer circular en memoria para eventos del pipeline de extracción/generación.
El frontend lo consume via polling para visualizar el flujo de la IA en tiempo real.

Cada fuente (chat, code_dojo, image, automation) tiene sus propios pasos.
El frontend se adapta dinámicamente al tipo de pipeline.
"""

import uuid
import logging
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

logger = logging.getLogger("yeyoos.pipeline")

# ─── Definiciones de pipeline por fuente ──────────────────────────────────────

PIPELINE_DEFS: dict[str, list[dict]] = {
    "chat": [
        {"key": "RECEIVED",           "icon": "📨", "label": "RECIBIDO"},
        {"key": "NOISE_CHECK",        "icon": "🧹", "label": "FILTRO"},
        {"key": "TYPE_CLASSIFY",      "icon": "🏷️", "label": "TIPO"},
        {"key": "EMBEDDING",          "icon": "🧬", "label": "EMBEDDING"},
        {"key": "STORED",             "icon": "💾", "label": "GUARDADO"},
        {"key": "NAMESPACE_CLASSIFY", "icon": "📂", "label": "NAMESPACE"},
    ],
    "code_dojo": [
        {"key": "RECEIVED",       "icon": "📨", "label": "RECIBIDO"},
        {"key": "ARCHITECT",      "icon": "📐", "label": "ARQUITECTO"},
        {"key": "BACKEND_GEN",    "icon": "⚙️", "label": "BACKEND"},
        {"key": "CRITIC_EVAL",    "icon": "🔍", "label": "CRÍTICO"},
        {"key": "AST_PARSE",      "icon": "🌳", "label": "AST"},
        {"key": "TESTS_RUN",      "icon": "🧪", "label": "TESTS"},
        {"key": "FUNC_VERIFY",   "icon": "🎯", "label": "EJECUCIÓN"},
        {"key": "SECURITY_SCAN",  "icon": "🛡️", "label": "SEGURIDAD"},
        {"key": "PERF_ANALYSIS",  "icon": "⚡", "label": "PERFORMANCE"},
        {"key": "EMBEDDING",      "icon": "🧬", "label": "EMBEDDING"},
        {"key": "STORED",         "icon": "💾", "label": "GUARDADO"},
    ],
    "image": [
        {"key": "RECEIVED",  "icon": "📨", "label": "RECIBIDO"},
        {"key": "GENERATE",  "icon": "🎨", "label": "GENERAR"},
        {"key": "EMBEDDING", "icon": "🧬", "label": "EMBEDDING"},
        {"key": "STORED",    "icon": "💾", "label": "GUARDADO"},
    ],
    "automation": [
        {"key": "RECEIVED",     "icon": "📨", "label": "RECIBIDO"},
        {"key": "CONTEXT_LOAD", "icon": "🧠", "label": "CONTEXTO"},
        {"key": "EXECUTE",      "icon": "▶️",  "label": "EJECUTAR"},
        {"key": "EMBEDDING",    "icon": "🧬", "label": "EMBEDDING"},
        {"key": "STORED",       "icon": "💾", "label": "GUARDADO"},
    ],
}

# Legacy flat list (union of all steps for stats)
PIPELINE_STEPS = sorted({
    step["key"]
    for steps in PIPELINE_DEFS.values()
    for step in steps
})

STEP_ORDER = {step: i for i, step in enumerate(PIPELINE_STEPS)}


@dataclass
class PipelineEvent:
    pipeline_id: str
    step: str
    status: str  # "ok" | "error" | "skip"
    detail: str
    metadata: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class PipelineBuffer:
    """Ring buffer thread-safe para eventos del pipeline."""

    def __init__(self, maxlen: int = 500):
        self._events: deque[PipelineEvent] = deque(maxlen=maxlen)
        self._pipelines: dict[str, list[PipelineEvent]] = {}
        self._pipeline_sources: dict[str, str] = {}
        self._pipeline_deque: deque[str] = deque(maxlen=100)

    def new_pipeline(self, source: str = "chat") -> str:
        """Crea un nuevo pipeline_id para agrupar eventos de un mensaje."""
        pid = str(uuid.uuid4())[:8]
        self._pipelines[pid] = []
        self._pipeline_sources[pid] = source
        self._pipeline_deque.append(pid)
        # Limpiar pipelines viejos
        while len(self._pipelines) > 100:
            old = self._pipeline_deque.popleft()
            self._pipelines.pop(old, None)
            self._pipeline_sources.pop(old, None)
        return pid

    def emit(
        self,
        pipeline_id: str,
        step: str,
        status: str = "ok",
        detail: str = "",
        metadata: dict | None = None,
    ) -> PipelineEvent:
        """Registra un evento en el buffer."""
        event = PipelineEvent(
            pipeline_id=pipeline_id,
            step=step,
            status=status,
            detail=detail,
            metadata=metadata or {},
        )
        self._events.append(event)
        if pipeline_id in self._pipelines:
            self._pipelines[pipeline_id].append(event)
        logger.debug(f"[PIPELINE:{pipeline_id}] {step} → {status}: {detail}")
        return event

    def get_recent(self, limit: int = 100) -> list[dict]:
        """Retorna los últimos N eventos."""
        events = list(self._events)[-limit:]
        return [e.to_dict() for e in events]

    def get_pipelines(self, limit: int = 20) -> list[dict]:
        """Retorna los últimos N pipelines completos con sus eventos y definición de pasos."""
        pids = list(self._pipeline_deque)[-limit:]
        result = []
        for pid in reversed(pids):
            events = self._pipelines.get(pid, [])
            if not events:
                continue

            statuses = [e.status for e in events]
            overall = "error" if "error" in statuses else "ok"
            steps_completed = [e.step for e in events]
            source = self._pipeline_sources.get(pid, "chat")

            result.append({
                "pipeline_id": pid,
                "source": source,
                "status": overall,
                "steps": [e.to_dict() for e in events],
                "steps_completed": steps_completed,
                "step_defs": PIPELINE_DEFS.get(source, PIPELINE_DEFS["chat"]),
                "started_at": events[0].timestamp if events else None,
                "message_preview": next(
                    (e.metadata.get("content", "")[:80] for e in events if e.step == "RECEIVED"),
                    "",
                ),
            })
        return result

    def get_step_stats(self) -> dict:
        """Estadísticas por paso: total, ok, error, skip."""
        stats: dict[str, dict[str, int]] = {}
        for step in PIPELINE_STEPS:
            stats[step] = {"total": 0, "ok": 0, "error": 0, "skip": 0}

        for event in self._events:
            if event.step in stats:
                stats[event.step]["total"] += 1
                stats[event.step][event.status] = stats[event.step].get(event.status, 0) + 1

        return stats


# Singleton global
pipeline_buffer = PipelineBuffer()
