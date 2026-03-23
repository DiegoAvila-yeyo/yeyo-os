"""
YeyoOS — YEYO-HACK: Docker Arena
Micro-fase 6.12 — Capa 6: Sistema Inmune

Docker arena aislado para red team vs blue team.
"""

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("yeyo.security.hack.arena")


@dataclass
class ArenaConfig:
    container_name: str = "yeyo-hack-arena"
    network_name: str = "yeyo-hack-net"
    backend_port: int = 8001
    redis_port: int = 6380
    timeout_minutes: int = 60
    max_rounds: int = 10


class DockerArena:
    """Isolated Docker arena for security testing."""

    def __init__(self, config: Optional[ArenaConfig] = None):
        self.config = config or ArenaConfig()
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def create(self) -> bool:
        """Create isolated Docker arena."""
        logger.info(f"Creating Docker arena: {self.config.container_name}")
        # In production, this creates a Docker network + container
        # For now, just track state
        self._running = True
        return True

    def destroy(self) -> bool:
        """Destroy Docker arena completely."""
        logger.info(f"Destroying Docker arena: {self.config.container_name}")
        self._running = False
        return True

    def get_status(self) -> dict:
        return {
            "container": self.config.container_name,
            "running": self._running,
            "network": self.config.network_name,
            "backend_port": self.config.backend_port,
        }
