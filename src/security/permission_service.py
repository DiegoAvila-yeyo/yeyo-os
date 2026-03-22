"""
YeyoOS — PermissionService
Micro-fase 3.21 — Capa 3: Cuerpo

Servicio de permisos con tres zonas de riesgo:
- Verde: auto-aprueba silenciosamente y loguea.
- Amarilla/Roja: emite evento WebSocket al frontend y espera respuesta
  (asyncio.Event con timeout de 60 segundos).
- Timeout → retorna denegado por seguridad.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict
import time

logger = logging.getLogger(__name__)


class PermissionZone(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class PackageInfo:
    name: str
    origin: str
    size: str


@dataclass
class PermissionRequest:
    node_id: str
    permission: str
    permission_label: str
    zone: PermissionZone
    task_description: str
    package_info: Optional[PackageInfo] = None
    request_id: str = field(default_factory=lambda: str(time.time_ns()))


@dataclass
class PermissionDecision:
    allowed: bool
    remember: bool
    timestamp: float = field(default_factory=time.time)
    request_id: str = ""


class PermissionService:
    """
    Servicio central de permisos. Instancia única (singleton) compartida
    entre el endpoint WebSocket y los nodos que solicitan permisos.
    """

    TIMEOUT_SECONDS = 60.0

    def __init__(self) -> None:
        self._pending: Dict[str, asyncio.Event] = {}
        self._decisions: Dict[str, PermissionDecision] = {}
        self._ws_send_callback: Optional[callable] = None

    def set_ws_callback(self, callback: callable) -> None:
        """Registra la función que enviará eventos por WebSocket al frontend."""
        self._ws_send_callback = callback

    async def request(self, req: PermissionRequest) -> PermissionDecision:
        """
        Procesa una solicitud de permiso según la zona:
        - Verde → auto-aprueba inmediatamente.
        - Amarilla/Roja → espera decisión del frontend via WebSocket.
        """
        if req.zone == PermissionZone.GREEN:
            logger.info(f"[security] AUTO-ALLOW {req.node_id}:{req.permission}")
            decision = PermissionDecision(
                allowed=True,
                remember=True,
                request_id=req.request_id,
            )
            return decision

        # Zona amarilla o roja: emitir al frontend y esperar
        event = asyncio.Event()
        self._pending[req.request_id] = event

        if self._ws_send_callback:
            payload = {
                "type": "permission_request",
                "request_id": req.request_id,
                "node_id": req.node_id,
                "permission": req.permission,
                "permission_label": req.permission_label,
                "zone": req.zone.value,
                "task_description": req.task_description,
                "package_info": {
                    "name": req.package_info.name,
                    "origin": req.package_info.origin,
                    "size": req.package_info.size,
                } if req.package_info else None,
            }
            try:
                await self._ws_send_callback(payload)
            except Exception as e:
                logger.error(f"[security] WS send error: {e}")
                self._pending.pop(req.request_id, None)
                return PermissionDecision(
                    allowed=False, remember=False, request_id=req.request_id
                )

        logger.info(f"[security] WAITING {req.node_id}:{req.permission} (zone={req.zone.value})")

        try:
            await asyncio.wait_for(event.wait(), timeout=self.TIMEOUT_SECONDS)
            decision = self._decisions.pop(req.request_id, None)
            if decision:
                logger.info(
                    f"[security] DECISION {req.node_id}:{req.permission} "
                    f"allowed={decision.allowed} remember={decision.remember}"
                )
                return decision
        except asyncio.TimeoutError:
            logger.warning(
                f"[security] TIMEOUT {req.node_id}:{req.permission} → denied"
            )
        finally:
            self._pending.pop(req.request_id, None)

        return PermissionDecision(allowed=False, remember=False, request_id=req.request_id)

    def resolve(self, request_id: str, allowed: bool, remember: bool) -> bool:
        """
        Recibe la decisión del frontend. Llamado desde el WebSocket handler.
        Retorna True si había una solicitud pendiente, False si no.
        """
        event = self._pending.get(request_id)
        if not event:
            logger.warning(f"[security] resolve: no pending request_id={request_id}")
            return False

        self._decisions[request_id] = PermissionDecision(
            allowed=allowed,
            remember=remember,
            request_id=request_id,
        )
        event.set()
        return True


# Singleton global
permission_service = PermissionService()
