"""
YeyoOS — Secure Container Manager (Podman)
Micro-fase 4.4 — Capa 4: Sistema Nervioso

Gestiona containers Podman con hardening de seguridad.
REGLAS ABSOLUTAS:
- Podman SIEMPRE. Docker NUNCA.
- Docker socket JAMÁS montado.
- No privileged mode. No SYS_ADMIN. No NET_RAW.
- no-new-privileges SIEMPRE. ALL capabilities dropped.
- Root filesystem read-only.
"""

import asyncio
from typing import Optional
from dataclasses import dataclass, field


FORBIDDEN_MOUNTS = [
    "/var/run/docker.sock",
    "/run/docker.sock",
    "/var/run/podman/podman.sock",
]

FORBIDDEN_CAPABILITIES = [
    "SYS_ADMIN",
    "NET_RAW",
    "SYS_PTRACE",
    "NET_ADMIN",
    "SYS_MODULE",
    "SYS_RAWIO",
    "MKNOD",
]

REQUIRED_SECURITY_OPTS = [
    "no-new-privileges:true",
]


@dataclass
class ContainerManifest:
    """Datos del manifest relevantes para seguridad del container."""
    image: str
    memory_limit: str = "512m"
    cpu_limit: str = "1.0"
    network: str = "none"
    privilege_level: str = "L2"
    pids_limit: int = 256
    extra_mounts: list[str] = field(default_factory=list)
    extra_caps: list[str] = field(default_factory=list)


class ContainerSecurityError(Exception):
    """Error de seguridad en configuración de container."""
    pass


class SecureContainer:
    """Gestiona containers Podman con hardening de seguridad máximo."""

    def __init__(self):
        self._running_containers: dict[str, dict] = {}

    def get_run_args(self, manifest: ContainerManifest) -> list[str]:
        """
        Genera argumentos de Podman seguros para ejecutar un container.
        Aplica TODAS las restricciones de seguridad.
        """
        self._validate_security(manifest)

        args = [
            "--rm",
            "--security-opt=no-new-privileges:true",
            "--cap-drop=ALL",
            "--read-only",
            "--tmpfs=/tmp:rw,noexec,nosuid",
            f"--memory={manifest.memory_limit}",
            f"--cpus={manifest.cpu_limit}",
            f"--pids-limit={manifest.pids_limit}",
            f"--network={manifest.network}",
            "--userns=keep-id",
            "--security-opt=seccomp=default",
            "--log-driver=journald",
        ]

        if manifest.privilege_level == "L5":
            args.extend([
                "--memory=256m",
                "--cpus=0.5",
                "--pids-limit=64",
                "--network=none",
                "--read-only",
            ])

        return args

    def _validate_security(self, manifest: ContainerManifest) -> None:
        """
        Valida que la configuración del container no viole reglas de seguridad.
        Lanza ContainerSecurityError si hay violaciones.
        """
        for mount in manifest.extra_mounts:
            for forbidden in FORBIDDEN_MOUNTS:
                if forbidden in mount:
                    raise ContainerSecurityError(
                        f"PROHIBIDO: Montar {forbidden} no está permitido. "
                        f"Docker socket JAMÁS se monta en containers."
                    )

        for cap in manifest.extra_caps:
            cap_upper = cap.upper()
            if cap_upper in FORBIDDEN_CAPABILITIES:
                raise ContainerSecurityError(
                    f"PROHIBIDO: Capability {cap_upper} no está permitida."
                )

    async def run(
        self,
        manifest: ContainerManifest,
        command: Optional[list[str]] = None,
    ) -> dict:
        """Ejecuta un container con seguridad hardened."""
        self._validate_security(manifest)
        args = self.get_run_args(manifest)

        cmd = ["podman", "run"] + args + [manifest.image]
        if command:
            cmd.extend(command)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        container_id = stdout.decode().strip()[:12] if stdout else "unknown"

        result = {
            "container_id": container_id,
            "exit_code": proc.returncode,
            "stdout": stdout.decode() if stdout else "",
            "stderr": stderr.decode() if stderr else "",
            "image": manifest.image,
            "status": "exited",
        }

        return result

    async def run_detached(self, manifest: ContainerManifest) -> str:
        """Ejecuta un container en background y retorna el container_id."""
        self._validate_security(manifest)
        args = self.get_run_args(manifest)

        # Remover --rm para containers detached (se limpia al stop)
        args_detached = [a for a in args if a != "--rm"]
        args_detached.append("-d")

        cmd = ["podman", "run"] + args_detached + [manifest.image]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise ContainerSecurityError(
                f"Podman run falló: {stderr.decode()}"
            )

        container_id = stdout.decode().strip()[:12]
        self._running_containers[container_id] = {
            "image": manifest.image,
            "status": "running",
            "manifest": manifest,
        }
        return container_id

    async def stop(self, container_id: str) -> None:
        """Detiene un container en ejecución."""
        proc = await asyncio.create_subprocess_exec(
            "podman", "stop", container_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        proc_rm = await asyncio.create_subprocess_exec(
            "podman", "rm", container_id, "--force",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc_rm.communicate()

        if container_id in self._running_containers:
            self._running_containers[container_id]["status"] = "stopped"

    async def get_status(self, container_id: str) -> dict:
        """Obtiene el estado de un container."""
        proc = await asyncio.create_subprocess_exec(
            "podman", "inspect", container_id,
            "--format", "{{.State.Status}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            return {"container_id": container_id, "status": "not_found"}

        status = stdout.decode().strip()
        return {
            "container_id": container_id,
            "status": status,
        }

    def get_running_containers(self) -> dict[str, dict]:
        """Retorna los containers registrados como en ejecución."""
        return {
            cid: info
            for cid, info in self._running_containers.items()
            if info["status"] == "running"
        }
