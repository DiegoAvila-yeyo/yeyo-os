"""
YeyoOS — Observatory Service
Singleton service for real-time monitoring, WebSocket broadcasting, and API.
"""
import asyncio
import json
import logging
from typing import Optional, Any

from src.observatory.event_tracker import EventTracker, AgentEvent
from src.observatory.metrics import MetricsCollector, ObservatoryMetrics

logger = logging.getLogger("yeyoos.observatory.service")


class ObservatoryService:
    """Singleton that ties event tracking, metrics, and WebSocket broadcasting together."""

    _instance: Optional["ObservatoryService"] = None

    @classmethod
    def get_instance(cls) -> "ObservatoryService":
        """Return (and lazily create) the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.event_tracker = EventTracker()
        self.metrics_collector = MetricsCollector()
        self._ws_connections: set[Any] = set()
        self._running: bool = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the observatory service and begin listening for events."""
        if self._running:
            return
        self.event_tracker.add_listener(self.on_event)
        self._running = True
        logger.info("ObservatoryService started")

    async def stop(self) -> None:
        """Gracefully shut down the service and close WebSocket connections."""
        self._running = False
        for ws in list(self._ws_connections):
            try:
                await ws.close()
            except Exception:
                pass
        self._ws_connections.clear()
        logger.info("ObservatoryService stopped")

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def on_event(self, event: AgentEvent) -> None:
        """Callback invoked by EventTracker on every new event."""
        self.metrics_collector.record_event()

        if event.event_type == "task_start":
            self.metrics_collector.record_agent_active(event.agent_name)
            self.metrics_collector.record_workflow_start()
        elif event.event_type == "task_complete":
            self.metrics_collector.record_agent_idle(event.agent_name)
            self.metrics_collector.record_workflow_complete()
        elif event.event_type == "error":
            self.metrics_collector.record_agent_idle(event.agent_name)
            self.metrics_collector.record_workflow_error()
        elif event.event_type == "idle":
            self.metrics_collector.record_agent_idle(event.agent_name)

        await self.broadcast({"type": "event", "payload": event.to_dict()})

    # ------------------------------------------------------------------
    # WebSocket management
    # ------------------------------------------------------------------

    async def broadcast(self, data: dict) -> None:
        """Send *data* as JSON to every connected WebSocket client."""
        if not self._ws_connections:
            return
        message = json.dumps(data)
        stale: list[Any] = []
        for ws in list(self._ws_connections):
            try:
                await ws.send_text(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self._ws_connections.discard(ws)

    def add_ws(self, ws: Any) -> None:
        """Register a new WebSocket connection."""
        self._ws_connections.add(ws)
        logger.debug("WebSocket added (total=%d)", len(self._ws_connections))

    def remove_ws(self, ws: Any) -> None:
        """Unregister a WebSocket connection."""
        self._ws_connections.discard(ws)
        logger.debug("WebSocket removed (total=%d)", len(self._ws_connections))

    # ------------------------------------------------------------------
    # Convenience API
    # ------------------------------------------------------------------

    async def track_event(
        self,
        agent_name: str,
        event_type: str,
        data: dict | None = None,
        building: str | None = None,
    ) -> AgentEvent:
        """High-level helper — delegates to EventTracker.track()."""
        return await self.event_tracker.track(agent_name, event_type, data, building)

    def get_metrics(self) -> dict:
        """Return the current metrics as a dict."""
        return self.metrics_collector.get_metrics().to_dict()

    def get_agents(self) -> list[dict]:
        """Return all tracked agent states."""
        return self.event_tracker.get_all_agents()

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        """Return the most-recent events as dicts."""
        return self.event_tracker.get_recent_events(limit)


# ------------------------------------------------------------------
# FastAPI dependency
# ------------------------------------------------------------------

def get_observatory_service() -> ObservatoryService:
    """FastAPI dependency that returns the singleton ObservatoryService."""
    return ObservatoryService.get_instance()
