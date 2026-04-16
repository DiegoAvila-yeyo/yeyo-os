"""
YeyoOS — Observatory Metrics
Aggregated metrics for workflows, agents, and system health.
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("yeyoos.observatory.metrics")


@dataclass
class ObservatoryMetrics:
    """Snapshot of current observatory metrics."""

    workflows_active: int = 0
    workflows_completed: int = 0
    workflows_failed: int = 0
    agents_active: int = 0
    agents_idle: int = 0
    total_events: int = 0
    events_per_minute: float = 0.0
    uptime_seconds: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Serialise metrics to a JSON-friendly dict."""
        return {
            "workflows_active": self.workflows_active,
            "workflows_completed": self.workflows_completed,
            "workflows_failed": self.workflows_failed,
            "agents_active": self.agents_active,
            "agents_idle": self.agents_idle,
            "total_events": self.total_events,
            "events_per_minute": round(self.events_per_minute, 2),
            "uptime_seconds": round(self.uptime_seconds, 2),
            "last_updated": self.last_updated.isoformat(),
        }


class MetricsCollector:
    """Accumulates counters and computes aggregate observatory metrics."""

    def __init__(self) -> None:
        self._start_time: float = time.monotonic()
        self._workflows_active: int = 0
        self._workflows_completed: int = 0
        self._workflows_failed: int = 0
        self._active_agents: set[str] = set()
        self._idle_agents: set[str] = set()
        self._total_events: int = 0

    # ------------------------------------------------------------------
    # Workflow counters
    # ------------------------------------------------------------------

    def record_workflow_start(self) -> None:
        """Record that a new workflow has started."""
        self._workflows_active += 1
        logger.debug("Workflow started (active=%d)", self._workflows_active)

    def record_workflow_complete(self) -> None:
        """Record that a workflow completed successfully."""
        self._workflows_active = max(0, self._workflows_active - 1)
        self._workflows_completed += 1
        logger.debug("Workflow completed (completed=%d)", self._workflows_completed)

    def record_workflow_error(self) -> None:
        """Record that a workflow failed."""
        self._workflows_active = max(0, self._workflows_active - 1)
        self._workflows_failed += 1
        logger.debug("Workflow failed (failed=%d)", self._workflows_failed)

    # ------------------------------------------------------------------
    # Agent counters
    # ------------------------------------------------------------------

    def record_agent_active(self, name: str) -> None:
        """Mark an agent as active."""
        self._active_agents.add(name)
        self._idle_agents.discard(name)

    def record_agent_idle(self, name: str) -> None:
        """Mark an agent as idle."""
        self._idle_agents.add(name)
        self._active_agents.discard(name)

    # ------------------------------------------------------------------
    # Event counter
    # ------------------------------------------------------------------

    def record_event(self) -> None:
        """Increment the global event counter."""
        self._total_events += 1

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def get_metrics(self) -> ObservatoryMetrics:
        """Calculate and return the current metrics snapshot."""
        uptime = time.monotonic() - self._start_time
        epm = (self._total_events / (uptime / 60.0)) if uptime > 0 else 0.0

        return ObservatoryMetrics(
            workflows_active=self._workflows_active,
            workflows_completed=self._workflows_completed,
            workflows_failed=self._workflows_failed,
            agents_active=len(self._active_agents),
            agents_idle=len(self._idle_agents),
            total_events=self._total_events,
            events_per_minute=epm,
            uptime_seconds=uptime,
            last_updated=datetime.now(timezone.utc),
        )

    def reset(self) -> None:
        """Reset all counters and restart the uptime clock."""
        self._start_time = time.monotonic()
        self._workflows_active = 0
        self._workflows_completed = 0
        self._workflows_failed = 0
        self._active_agents.clear()
        self._idle_agents.clear()
        self._total_events = 0
        logger.info("MetricsCollector reset")
