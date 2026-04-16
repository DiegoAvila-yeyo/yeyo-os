"""
YeyoOS — Arena Service
Singleton service for managing YeyoHack Arena battles.
"""
import asyncio
import json
import logging
from typing import Any, Optional

from src.arena.battle import BattleManager
from src.arena.metrics import ArenaMetricsCollector

logger = logging.getLogger("yeyoos.arena.service")


class ArenaService:
    """Singleton service that owns the BattleManager, metrics collector, and
    WebSocket connections for live battle streaming.
    """

    _instance: Optional["ArenaService"] = None

    def __init__(self) -> None:
        self.battle_manager = BattleManager()
        self.metrics_collector = ArenaMetricsCollector()
        self._ws_connections: set[Any] = set()

        # Wire up event callback for live streaming
        self.battle_manager.set_event_callback(self._on_battle_event)

    @classmethod
    def get_instance(cls) -> "ArenaService":
        """Return the global singleton, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls()
            logger.info("ArenaService singleton created.")
        return cls._instance

    # -- WebSocket management ----------------------------------------------

    def add_ws(self, ws: Any) -> None:
        """Register a WebSocket connection for live updates."""
        self._ws_connections.add(ws)
        logger.info("WebSocket added — %d active connections.", len(self._ws_connections))

    def remove_ws(self, ws: Any) -> None:
        """Unregister a WebSocket connection."""
        self._ws_connections.discard(ws)
        logger.info("WebSocket removed — %d active connections.", len(self._ws_connections))

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send *data* to all connected WebSockets."""
        if not self._ws_connections:
            return
        payload = json.dumps(data)
        dead: list[Any] = []
        for ws in self._ws_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_connections.discard(ws)

    async def _on_battle_event(self, data: dict[str, Any]) -> None:
        """Internal callback invoked by BattleManager on every event."""
        await self.broadcast(data)

    # -- public API --------------------------------------------------------

    async def start_battle(self, max_rounds: int = 100) -> dict[str, Any]:
        """Start a new battle session.

        Returns the initial session data.
        """
        session = await self.battle_manager.start_session(max_rounds=max_rounds)
        return session.to_dict()

    async def stop_battle(self) -> dict[str, Any]:
        """Stop the running battle and record metrics."""
        await self.battle_manager.stop_session()
        status = self.battle_manager.get_status()

        # Persist session data for aggregate metrics
        self.metrics_collector.record_session({
            **status,
            "rounds": self.battle_manager.get_history(),
        })
        return status

    def get_status(self) -> dict[str, Any]:
        """Return the current session status."""
        return self.battle_manager.get_status()

    def get_metrics(self) -> dict[str, Any]:
        """Return per-session and aggregate metrics."""
        return {
            "current": self.battle_manager.get_metrics(),
            "aggregate": self.metrics_collector.get_aggregate_metrics().to_dict(),
        }

    def get_history(self) -> list[dict[str, Any]]:
        """Return round-by-round history of the current session."""
        return self.battle_manager.get_history()


def get_arena_service() -> ArenaService:
    """FastAPI dependency — returns the ArenaService singleton."""
    return ArenaService.get_instance()
