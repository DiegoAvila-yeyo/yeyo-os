"""
YeyoOS — YEYO-PKG Manifest Parser & Validator
Micro-fase 4.0 — Capa 4: Sistema Nervioso

Define la especificación del manifest.yml para paquetes .ypkg.
Valida campos requeridos, niveles de privilegio y permisos.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class PackageType(str, Enum):
    NODE = "node"
    SERVICE = "service"
    THEME = "theme"
    PLUGIN = "plugin"


class PrivilegeLevel(str, Enum):
    L0 = "L0"  # ROOT — solo OS core
    L1 = "L1"  # ADMIN — servicios del sistema
    L2 = "L2"  # USER — paquetes estándar
    L3 = "L3"  # LIMITED — permisos reducidos
    L4 = "L4"  # GUEST — permisos mínimos
    L5 = "L5"  # SANDBOX — nodos IA, máximo aislamiento


class ValidPermission(str, Enum):
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


VALID_PERMISSIONS = {p.value for p in ValidPermission}

VALID_NETWORKS = {"none", "host", "bridge"}


class ContainerConfig(BaseModel):
    """Configuración del container Podman para el paquete."""
    image: str = Field(..., min_length=1)
    memory_limit: str = Field(default="512m", pattern=r"^\d+[kmg]$")
    cpu_limit: str = Field(default="1.0", pattern=r"^\d+(\.\d+)?$")
    network: str = Field(default="none")

    @field_validator("network")
    @classmethod
    def validate_network(cls, v: str) -> str:
        if v not in VALID_NETWORKS:
            raise ValueError(f"Network inválido: {v}. Válidos: {VALID_NETWORKS}")
        return v


class PackageManifest(BaseModel):
    """Manifest completo de un paquete .ypkg."""
    name: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9\-]*$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    author: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    type: PackageType
    icon: str = Field(default="default.svg")
    entry_point: str = Field(default="index.html")
    container: ContainerConfig
    permissions: list[str] = Field(default_factory=list)
    privilege_level: PrivilegeLevel = Field(default=PrivilegeLevel.L2)
    dependencies: list[str] = Field(default_factory=list)
    signature: Optional[str] = Field(default=None)

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v: list[str]) -> list[str]:
        for perm in v:
            if perm not in VALID_PERMISSIONS:
                raise ValueError(
                    f"Permiso inválido: '{perm}'. "
                    f"Permisos válidos: {sorted(VALID_PERMISSIONS)}"
                )
        return v

    @field_validator("privilege_level")
    @classmethod
    def validate_privilege_not_root(cls, v: PrivilegeLevel) -> PrivilegeLevel:
        if v == PrivilegeLevel.L0:
            raise ValueError(
                "Nivel de privilegio L0 (ROOT) no permitido para paquetes externos. "
                "Solo el OS core puede usar L0."
            )
        return v


class ManifestParser:
    """Parser y validador de manifests YEYO-PKG."""

    @staticmethod
    def parse(data: dict) -> PackageManifest:
        """Parsea un diccionario a PackageManifest validado."""
        return PackageManifest(**data)

    @staticmethod
    def parse_yaml(yaml_content: str) -> PackageManifest:
        """Parsea contenido YAML a PackageManifest validado."""
        import yaml
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict):
            raise ValueError("El manifest YAML debe ser un diccionario")
        return ManifestParser.parse(data)

    @staticmethod
    def parse_file(file_path: str) -> PackageManifest:
        """Parsea un archivo manifest.yml a PackageManifest validado."""
        with open(file_path, "r") as f:
            return ManifestParser.parse_yaml(f.read())

    @staticmethod
    def to_yaml(manifest: PackageManifest) -> str:
        """Serializa un PackageManifest a YAML."""
        import yaml
        data = manifest.model_dump()
        data["type"] = manifest.type.value
        data["privilege_level"] = manifest.privilege_level.value
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
