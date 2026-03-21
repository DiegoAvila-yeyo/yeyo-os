"""
YeyoOS — Event Bus
Micro-fase 1.9 — Capa 1: Esqueleto

Bus de eventos interno para comunicación pub/sub entre servicios.
Patrón Singleton: una sola instancia compartida.
"""

import asyncio
import logging
from typing import Callable, Any, Awaitable


SYSTEM_EVENTS = {
    "gpu.task.started",
    "gpu.task.completed",
    "gpu.task.preempted",
    "memory.stored",
    "memory.recalled",
    "memory.promoted",
    "memory.demoted",
    "chat.message",
    "chat.stream.start",
    "chat.stream.end",
    "system.error",
    "system.startup",
    "system.shutdown",
    "node.opened",
    "node.closed",
}

EventCallback = Callable[[Any], Awaitable[None]]

logger = logging.getLogger("yeyo.event_bus")


class EventBus:
    """
    Bus de eventos con patrón Singleton.
    Suscriptores reciben eventos de forma asíncrona.
    Si un suscriptor falla, los demás siguen recibiendo.
    """

    _instance: "EventBus | None" = None

    def __init__(self):
        self._subscribers: dict[str, list[EventCallback]] = {}

    @classmethod
    def instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = EventBus()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: EventCallback) -> None:
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    async def publish(self, event_type: str, data: Any = None) -> None:
        """
        Publica un evento a todos los suscriptores.
        Si un suscriptor falla, loguea el error y continúa.
        """
        if event_type not in self._subscribers:
            return

        for callback in self._subscribers[event_type]:
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Error en suscriptor de '{event_type}': {e}", exc_info=True)

    def get_subscriber_count(self, event_type: str) -> int:
        return len(self._subscribers.get(event_type, []))

    def get_all_event_types(self) -> list[str]:
        return list(self._subscribers.keys())

    def clear(self) -> None:
        self._subscribers.clear()
