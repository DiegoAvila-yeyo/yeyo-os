"""
YeyoOS — Workflow Triggers
Supports Manual, Cron (APScheduler), and Event-based triggers.
"""
import asyncio
import logging
import re
from typing import Callable, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger("yeyoos.workflows.triggers")


def _parse_cron_expression(cron_expression: str) -> int:
    """Parse a simple cron expression into interval seconds.

    Supports formats: "every Xs", "every Xm", "every Xh".
    Returns 60 if the expression cannot be parsed.
    """
    match = re.match(r"every\s+(\d+)\s*([smh])", cron_expression.strip().lower())
    if not match:
        logger.warning(
            f"Unparseable cron expression '{cron_expression}', defaulting to 60s"
        )
        return 60

    value = int(match.group(1))
    unit = match.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600}
    return value * multipliers[unit]


class TriggerManager:
    """Manages cron-like and event-based triggers for workflows."""

    def __init__(self) -> None:
        self._cron_jobs: dict[str, asyncio.Task] = {}
        self._event_listeners: dict[str, dict[str, Callable]] = {}

    async def _cron_loop(
        self, workflow_id: str, interval_seconds: int, callback: Callable
    ) -> None:
        """Internal loop that repeatedly invokes *callback* every *interval_seconds*."""
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                await callback()
            except Exception as e:
                logger.error(f"Cron trigger error for {workflow_id}: {e}")

    async def start_cron(
        self, workflow_id: str, cron_expression: str, callback: Callable
    ) -> None:
        """Start a cron-like trigger for *workflow_id*.

        *cron_expression* is parsed into a fixed interval
        (e.g. ``"every 30s"``, ``"every 5m"``, ``"every 1h"``).
        """
        if workflow_id in self._cron_jobs:
            logger.warning(
                f"Cron already active for {workflow_id}, stopping previous one"
            )
            await self.stop_cron(workflow_id)

        interval = _parse_cron_expression(cron_expression)
        task = asyncio.create_task(
            self._cron_loop(workflow_id, interval, callback),
            name=f"cron-{workflow_id}",
        )
        self._cron_jobs[workflow_id] = task
        logger.info(
            f"Started cron trigger for {workflow_id}: every {interval}s"
        )

    async def stop_cron(self, workflow_id: str) -> None:
        """Cancel the cron task for *workflow_id*."""
        task = self._cron_jobs.pop(workflow_id, None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            logger.info(f"Stopped cron trigger for {workflow_id}")
        else:
            logger.warning(f"No cron trigger found for {workflow_id}")

    def register_event(
        self, event_name: str, workflow_id: str, callback: Callable
    ) -> None:
        """Register *callback* as an event listener for *event_name*."""
        self._event_listeners.setdefault(event_name, {})[workflow_id] = callback
        logger.info(
            f"Registered event listener: {event_name} -> {workflow_id}"
        )

    async def fire_event(self, event_name: str, data: dict | None = None) -> None:
        """Fire *event_name*, invoking all registered callbacks with *data*."""
        listeners = self._event_listeners.get(event_name, {})
        if not listeners:
            logger.debug(f"No listeners for event '{event_name}'")
            return

        for wf_id, callback in listeners.items():
            try:
                await callback(data)
            except Exception as e:
                logger.error(
                    f"Event '{event_name}' handler error for {wf_id}: {e}"
                )

    def unregister_event(self, event_name: str, workflow_id: str) -> None:
        """Remove the event listener for *workflow_id* on *event_name*."""
        listeners = self._event_listeners.get(event_name, {})
        if workflow_id in listeners:
            del listeners[workflow_id]
            if not listeners:
                del self._event_listeners[event_name]
            logger.info(
                f"Unregistered event listener: {event_name} -> {workflow_id}"
            )
        else:
            logger.warning(
                f"No event listener found: {event_name} -> {workflow_id}"
            )

    async def stop_all(self) -> None:
        """Stop all cron triggers and clear all event listeners."""
        for workflow_id in list(self._cron_jobs):
            await self.stop_cron(workflow_id)
        self._event_listeners.clear()
        logger.info("All triggers stopped and cleared")

    def get_active_triggers(self) -> list[dict]:
        """Return a list of dicts describing every active trigger."""
        triggers: list[dict] = []

        for workflow_id, task in self._cron_jobs.items():
            triggers.append(
                {
                    "type": "cron",
                    "workflow_id": workflow_id,
                    "running": not task.done(),
                }
            )

        for event_name, listeners in self._event_listeners.items():
            for workflow_id in listeners:
                triggers.append(
                    {
                        "type": "event",
                        "event_name": event_name,
                        "workflow_id": workflow_id,
                    }
                )

        return triggers
