"""
YeyoOS — Observatory Event Tracker
Captures and stores events from workflow executions and agent activities.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Callable
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger("yeyoos.observatory.events")

# Canonical agent-to-sprite mapping
AGENT_SPRITES: dict[str, str] = {
    "miner": "miner",
    "scientist": "scientist",
    "tester": "tester",
    "writer": "writer",
    "optimizer": "optimizer",
    "guard": "guard",
    "sage": "sage",
    "yeyohack": "yeyohack",
    "guardian": "guardian",
    "robot": "robot",
}


@dataclass
class AgentEvent:
    """A single event emitted by an agent or workflow."""

    agent_name: str
    event_type: str  # "task_start", "task_complete", "error", "idle", …
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    building: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        """Serialise the event to a plain dict (JSON-friendly)."""
        return {
            "id": self.id,
            "agent_name": self.agent_name,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "building": self.building,
            "sprite": AGENT_SPRITES.get(self.agent_name),
        }


class EventTracker:
    """Captures, stores and broadcasts agent / workflow events."""

    def __init__(self, max_events: int = 1000) -> None:
        self.max_events = max_events
        self._events: deque[AgentEvent] = deque(maxlen=max_events)
        self._agent_states: dict[str, dict] = {}
        self._listeners: list[Callable] = []

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    async def track(
        self,
        agent_name: str,
        event_type: str,
        data: dict | None = None,
        building: str | None = None,
    ) -> AgentEvent:
        """Create, store, and broadcast a new event."""
        event = AgentEvent(
            agent_name=agent_name,
            event_type=event_type,
            data=data or {},
            building=building,
        )
        self._events.append(event)
        self._update_agent_state(event)
        await self._notify_listeners(event)
        logger.debug("Tracked event %s for %s (%s)", event.id, agent_name, event_type)
        return event

    def add_listener(self, callback: Callable) -> None:
        """Register an async callback invoked on every new event."""
        self._listeners.append(callback)

    def get_recent_events(self, limit: int = 50) -> list[dict]:
        """Return the *limit* most-recent events as dicts (newest first)."""
        items = list(self._events)[-limit:]
        items.reverse()
        return [e.to_dict() for e in items]

    def get_agent_state(self, agent_name: str) -> dict:
        """Return the current tracked state for *agent_name*."""
        return self._agent_states.get(agent_name, {
            "name": agent_name,
            "status": "unknown",
            "last_event": None,
            "building": None,
            "sprite": AGENT_SPRITES.get(agent_name),
        })

    def get_all_agents(self) -> list[dict]:
        """Return tracked state for every known agent."""
        return list(self._agent_states.values())

    def clear_old_events(self) -> None:
        """Trim events that exceed *max_events* (deque handles this, but kept for explicit use)."""
        while len(self._events) > self.max_events:
            self._events.popleft()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_agent_state(self, event: AgentEvent) -> None:
        """Refresh the cached state dict for the agent that emitted *event*."""
        status = "active"
        if event.event_type in ("idle", "task_complete"):
            status = "idle"
        elif event.event_type == "error":
            status = "error"

        self._agent_states[event.agent_name] = {
            "name": event.agent_name,
            "status": status,
            "last_event": event.event_type,
            "last_event_time": event.timestamp.isoformat(),
            "building": event.building,
            "sprite": AGENT_SPRITES.get(event.agent_name),
        }

    async def _notify_listeners(self, event: AgentEvent) -> None:
        """Fan-out event to all registered async listeners."""
        for callback in self._listeners:
            try:
                await callback(event)
            except Exception:
                logger.exception("Listener error while processing event %s", event.id)
