"""
YeyoOS — Privilege Level System
Micro-fase 4.5 — Capa 4: Sistema Nervioso

6 niveles de privilegio con techo máximo de permisos por nivel.
CRÍTICO: Nodos IA SIEMPRE L5. Escalamiento desde L5 BLOQUEADO.
"""

from enum import IntEnum
from typing import Optional

from .permissions import Permission


class PrivilegeLevel(IntEnum):
    """Niveles de privilegio de YeyoOS (menor número = más privilegio)."""
    ROOT = 0       # OS core SOLAMENTE — paquetes externos NUNCA
    ADMIN = 1      # Servicios del sistema
    USER = 2       # Paquetes estándar del usuario
    LIMITED = 3    # Permisos reducidos
    GUEST = 4      # Permisos mínimos
    SANDBOX = 5    # Nodos IA — máximo aislamiento, SIN escalamiento


LEVEL_PERMISSIONS: dict[int, list[str]] = {
    5: [
        Permission.MEMORY_READ.value,
    ],
    4: [
        Permission.MEMORY_READ.value,
        Permission.CLIPBOARD.value,
    ],
    3: [
        Permission.MEMORY_READ.value,
        Permission.MEMORY_WRITE.value,
        Permission.CLIPBOARD.value,
    ],
    2: [
        Permission.MEMORY_READ.value,
        Permission.MEMORY_WRITE.value,
        Permission.GPU_INFERENCE.value,
        Permission.NETWORK_LOCALHOST.value,
        Permission.CLIPBOARD.value,
    ],
    1: [
        Permission.MEMORY_READ.value,
        Permission.MEMORY_WRITE.value,
        Permission.GPU_INFERENCE.value,
        Permission.GPU_TRAINING.value,
        Permission.NETWORK_LOCALHOST.value,
        Permission.NETWORK_INTERNET.value,
        Permission.FILESYSTEM_READ.value,
        Permission.FILESYSTEM_WRITE.value,
    ],
    0: ["*"],  # ROOT: todos los permisos (solo OS core)
}


class EscalationError(Exception):
    """Error de escalamiento de privilegios."""
    pass


class PrivilegeEnforcer:
    """Enforcer de niveles de privilegio para paquetes."""

    def __init__(self):
        self._package_levels: dict[str, PrivilegeLevel] = {}
        self._ia_generated: set[str] = set()

    def register_package(
        self,
        package_name: str,
        level: PrivilegeLevel,
        ia_generated: bool = False,
    ) -> None:
        """
        Registra un paquete con su nivel de privilegio.
        Paquetes IA SIEMPRE se fuerzan a L5.
        """
        if ia_generated:
            self._ia_generated.add(package_name)
            level = PrivilegeLevel.SANDBOX  # FORZAR L5

        if level == PrivilegeLevel.ROOT:
            raise EscalationError(
                "Nivel ROOT (L0) no permitido para paquetes. Solo OS core."
            )

        self._package_levels[package_name] = level

    def get_level(self, package_name: str) -> Optional[PrivilegeLevel]:
        """Obtiene el nivel de privilegio de un paquete."""
        return self._package_levels.get(package_name)

    def is_ia_generated(self, package_name: str) -> bool:
        """Verifica si un paquete fue generado por IA."""
        return package_name in self._ia_generated

    async def enforce(self, package_name: str, action: str) -> bool:
        """
        Verifica si un paquete puede ejecutar una acción según su nivel.
        Retorna True si está permitido, False si no.
        """
        level = self._package_levels.get(package_name)
        if level is None:
            return False

        max_perms = self.get_max_permissions(level)

        if "*" in max_perms:
            return True

        return action in max_perms

    def get_max_permissions(self, level: PrivilegeLevel) -> list[str]:
        """Retorna los permisos máximos para un nivel de privilegio."""
        return LEVEL_PERMISSIONS.get(int(level), [])

    async def try_escalate(
        self, package_name: str, new_level: PrivilegeLevel
    ) -> None:
        """
        Intenta escalar el nivel de privilegio de un paquete.
        BLOQUEADO para L5 (sandbox/IA). Bloquea escalamiento a L0.
        """
        current = self._package_levels.get(package_name)
        if current is None:
            raise EscalationError(f"Paquete '{package_name}' no registrado")

        if package_name in self._ia_generated:
            raise EscalationError(
                f"BLOQUEADO: Paquete IA '{package_name}' está en L5 (sandbox). "
                f"Escalamiento desde L5 NO está permitido."
            )

        if current == PrivilegeLevel.SANDBOX:
            raise EscalationError(
                f"BLOQUEADO: Paquete '{package_name}' está en L5 (sandbox). "
                f"No se puede escalar desde L5."
            )

        if new_level == PrivilegeLevel.ROOT:
            raise EscalationError(
                "BLOQUEADO: Escalamiento a ROOT (L0) no permitido."
            )

        if new_level >= current:
            raise EscalationError(
                f"No es escalamiento: nivel actual {current.name} ({current}) "
                f"→ nuevo nivel {new_level.name} ({new_level})"
            )

        self._package_levels[package_name] = new_level

    def unregister_package(self, package_name: str) -> None:
        """Elimina el registro de nivel de privilegio de un paquete."""
        self._package_levels.pop(package_name, None)
        self._ia_generated.discard(package_name)
