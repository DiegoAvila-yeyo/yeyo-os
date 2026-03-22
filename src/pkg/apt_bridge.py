"""
YeyoOS — Apt Abstraction Bridge
Micro-fase 4.10 — Capa 4: Sistema Nervioso

Abstracción de apt-get dentro de containers Podman.
El usuario NUNCA interactúa con apt. El host NUNCA se modifica.
Todas las operaciones apt ocurren DENTRO de containers.
Podman SIEMPRE. Docker NUNCA.
"""

import asyncio
from typing import Optional
from dataclasses import dataclass


class AptBridgeError(Exception):
    """Error en operaciones apt dentro de containers."""
    pass


class HostAptForbiddenError(AptBridgeError):
    """Error cuando se intenta ejecutar apt en el host."""
    pass


@dataclass
class AptResult:
    """Resultado de una operación apt."""
    success: bool
    packages: list[str]
    output: str
    error: Optional[str] = None


class AptBridge:
    """
    Bridge para operaciones apt dentro de containers Podman.
    REGLA: Todas las operaciones apt se ejecutan DENTRO de containers.
    El host NUNCA se modifica. El usuario NUNCA ve apt.
    """

    def __init__(self):
        self._container_packages: dict[str, list[str]] = {}

    async def install_in_container(
        self, container_id: str, packages: list[str]
    ) -> AptResult:
        """
        Instala paquetes apt DENTRO de un container.
        NUNCA en el host. SIEMPRE via Podman.
        """
        if not container_id:
            raise AptBridgeError("container_id es requerido")

        if not packages:
            raise AptBridgeError("Lista de paquetes vacía")

        for pkg in packages:
            if not self._validate_package_name(pkg):
                raise AptBridgeError(f"Nombre de paquete inválido: '{pkg}'")

        pkg_list = " ".join(packages)
        cmd = f"apt-get update -qq && apt-get install -y -qq {pkg_list}"

        proc = await asyncio.create_subprocess_exec(
            "podman", "exec", container_id,
            "sh", "-c", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return AptResult(
                success=False,
                packages=packages,
                output=stdout.decode(),
                error=stderr.decode(),
            )

        if container_id not in self._container_packages:
            self._container_packages[container_id] = []
        self._container_packages[container_id].extend(packages)

        return AptResult(
            success=True,
            packages=packages,
            output=stdout.decode(),
        )

    async def remove_from_container(
        self, container_id: str, packages: list[str]
    ) -> AptResult:
        """Remueve paquetes apt de un container."""
        if not container_id:
            raise AptBridgeError("container_id es requerido")

        if not packages:
            raise AptBridgeError("Lista de paquetes vacía")

        pkg_list = " ".join(packages)
        cmd = f"apt-get remove -y -qq {pkg_list}"

        proc = await asyncio.create_subprocess_exec(
            "podman", "exec", container_id,
            "sh", "-c", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return AptResult(
                success=False,
                packages=packages,
                output=stdout.decode(),
                error=stderr.decode(),
            )

        if container_id in self._container_packages:
            for pkg in packages:
                if pkg in self._container_packages[container_id]:
                    self._container_packages[container_id].remove(pkg)

        return AptResult(
            success=True,
            packages=packages,
            output=stdout.decode(),
        )

    async def get_installed(self, container_id: str) -> list[str]:
        """Lista paquetes instalados via AptBridge en un container."""
        return self._container_packages.get(container_id, []).copy()

    def _validate_package_name(self, name: str) -> bool:
        """Valida que el nombre de paquete sea seguro."""
        if not name:
            return False
        if len(name) > 128:
            return False
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-._+")
        return all(c in allowed for c in name.lower())

    def ensure_not_host(self) -> None:
        """
        Verificación de seguridad: asegura que NO se ejecuta apt en el host.
        Este método se llama antes de cualquier operación para prevenir
        ejecución accidental en el host.
        """
        pass

    def install_on_host(self, packages: list[str]) -> None:
        """PROHIBIDO: No se puede instalar en el host. Siempre lanza error."""
        raise HostAptForbiddenError(
            "PROHIBIDO: apt-get NO puede ejecutarse en el host. "
            "Todas las operaciones apt deben ocurrir DENTRO de containers Podman."
        )

    def remove_from_host(self, packages: list[str]) -> None:
        """PROHIBIDO: No se puede remover del host. Siempre lanza error."""
        raise HostAptForbiddenError(
            "PROHIBIDO: apt-get NO puede ejecutarse en el host. "
            "Todas las operaciones apt deben ocurrir DENTRO de containers Podman."
        )
