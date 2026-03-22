"""
YeyoOS — Permission System (ALLOWLIST)
Micro-fase 4.3 — Capa 4: Sistema Nervioso

Sistema de permisos estilo Android/iOS.
ALLOWLIST: si no se solicita, NO se concede. Sin opción "grant all".
Nodos IA SIEMPRE L5 (sandbox) con permisos mínimos.
"""

from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class Permission(str, Enum):
    """Permisos disponibles en YeyoOS."""
    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"
    GPU_INFERENCE = "gpu.inference"
    GPU_TRAINING = "gpu.training"
    NETWORK_LOCALHOST = "network.localhost"
    NETWORK_INTERNET = "network.internet"
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    CAMERA = "camera"
    MICROPHONE = "microphone"
    CLIPBOARD = "clipboard"


class PermissionGrant(BaseModel):
    """Registro de un permiso concedido a un paquete."""
    package_name: str
    permission: Permission
    granted: bool = False
    granted_at: Optional[datetime] = None
    granted_by: str = "user"


class PermissionManager:
    """Gestor de permisos ALLOWLIST para paquetes de YeyoOS."""

    def __init__(self):
        self._grants: dict[str, dict[str, PermissionGrant]] = {}

    async def request(
        self, package_name: str, permissions: list[Permission]
    ) -> dict:
        """
        Solicita permisos para un paquete.
        ALLOWLIST: cada permiso debe ser concedido explícitamente.
        Retorna {granted: [...], denied: [...]}.
        """
        if package_name not in self._grants:
            self._grants[package_name] = {}

        granted = []
        denied = []

        for perm in permissions:
            if not isinstance(perm, Permission):
                try:
                    perm = Permission(perm)
                except ValueError:
                    denied.append(str(perm))
                    continue

            grant = PermissionGrant(
                package_name=package_name,
                permission=perm,
                granted=True,
                granted_at=datetime.now(timezone.utc),
                granted_by="user",
            )
            self._grants[package_name][perm.value] = grant
            granted.append(perm.value)

        return {"granted": granted, "denied": denied}

    async def check(self, package_name: str, permission: Permission) -> bool:
        """
        Verifica si un paquete tiene un permiso concedido.
        ALLOWLIST: si no fue explícitamente concedido, retorna False.
        """
        if package_name not in self._grants:
            return False
        grant = self._grants[package_name].get(permission.value)
        if grant is None:
            return False
        return grant.granted

    async def revoke(self, package_name: str, permission: Permission) -> None:
        """Revoca un permiso de un paquete."""
        if package_name not in self._grants:
            return
        if permission.value in self._grants[package_name]:
            self._grants[package_name][permission.value].granted = False
            self._grants[package_name][permission.value].granted_at = None

    async def revoke_all(self, package_name: str) -> None:
        """Revoca todos los permisos de un paquete."""
        if package_name in self._grants:
            for perm_key in self._grants[package_name]:
                self._grants[package_name][perm_key].granted = False
                self._grants[package_name][perm_key].granted_at = None

    async def get_grants(self, package_name: str) -> list[Permission]:
        """Retorna la lista de permisos activos de un paquete."""
        if package_name not in self._grants:
            return []
        return [
            Permission(grant.permission)
            for grant in self._grants[package_name].values()
            if grant.granted
        ]

    async def get_all_grants(self) -> dict[str, list[str]]:
        """Retorna todos los permisos activos de todos los paquetes."""
        result = {}
        for pkg_name, grants in self._grants.items():
            active = [
                grant.permission.value
                for grant in grants.values()
                if grant.granted
            ]
            if active:
                result[pkg_name] = active
        return result

    async def has_any_permission(self, package_name: str) -> bool:
        """Verifica si un paquete tiene algún permiso activo."""
        grants = await self.get_grants(package_name)
        return len(grants) > 0

    async def remove_package(self, package_name: str) -> None:
        """Elimina todos los registros de permisos de un paquete."""
        if package_name in self._grants:
            del self._grants[package_name]
