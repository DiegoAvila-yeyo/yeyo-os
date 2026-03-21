## ═══════════════════════════════════════
## MICRO-FASE 4.0 — YEYO-PKG Manifest Format
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.0-1 [VSCODE] — Definir especificación del manifest .ypkg

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.0 de Capa 4 (Sistema Nervioso): definir la especificación del manifest .ypkg para paquetes de YeyoOS.

CONTEXTO:
- Capas 0-3 completadas: infraestructura, esqueleto, cerebro, cuerpo/UI
- Capa 4 es el sistema nervioso: paquetes, permisos, containers, pipelines
- YEYO-PKG: formato .ypkg = tar.gz con manifest.yml + imagen container + bundle UI + assets + firma
- Ciclo de vida: create → build → install → use → update → remove
- Container isolation: Podman (NUNCA Docker), non-root, seccomp, no-new-privileges
- 6 niveles de privilegio: ROOT(L0) > ADMIN(L1) > USER(L2) > LIMITED(L3) > GUEST(L4) > SANDBOX(L5)
- Nodos generados por IA SIEMPRE L5 (sandbox)
- Permisos: ALLOWLIST — si no se solicita, no se concede

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/pkg
   mkdir -p tests/unit/pkg

2. Crear archivo src/pkg/__init__.py:

   Ruta: ~/yeyo-os/src/pkg/__init__.py
   Contenido:
   from .manifest import ManifestParser, PackageManifest

3. Crear archivo src/pkg/manifest.py:

   Ruta: ~/yeyo-os/src/pkg/manifest.py
   Contenido:

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

4. Crear archivo tests/unit/pkg/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/unit/pkg/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/pkg/test_manifest.py:

   Ruta: ~/yeyo-os/tests/unit/pkg/test_manifest.py
   Contenido:

   """Tests para YEYO-PKG Manifest Parser — Micro-fase 4.0"""

   import pytest
   from pydantic import ValidationError
   from src.pkg.manifest import (
       ManifestParser,
       PackageManifest,
       PackageType,
       PrivilegeLevel,
       ContainerConfig,
       ValidPermission,
       VALID_PERMISSIONS,
   )


   VALID_MANIFEST_DATA = {
       "name": "node-chat",
       "version": "1.0.0",
       "author": "YeyoOS",
       "description": "Chat node for YeyoOS",
       "type": "node",
       "icon": "chat.svg",
       "entry_point": "index.html",
       "container": {
           "image": "yeyo-chat:1.0.0",
           "memory_limit": "512m",
           "cpu_limit": "1.0",
           "network": "none",
       },
       "permissions": ["memory.read", "memory.write", "gpu.inference", "network.localhost"],
       "privilege_level": "L2",
       "dependencies": ["yeyo-core >= 0.1.0"],
       "signature": "sha256:abc123",
   }


   class TestPackageManifest:
       """Tests para el modelo PackageManifest."""

       def test_valid_manifest_parses(self):
           manifest = ManifestParser.parse(VALID_MANIFEST_DATA)
           assert manifest.name == "node-chat"
           assert manifest.version == "1.0.0"
           assert manifest.author == "YeyoOS"
           assert manifest.type == PackageType.NODE
           assert manifest.privilege_level == PrivilegeLevel.L2

       def test_valid_manifest_has_container(self):
           manifest = ManifestParser.parse(VALID_MANIFEST_DATA)
           assert manifest.container.image == "yeyo-chat:1.0.0"
           assert manifest.container.memory_limit == "512m"
           assert manifest.container.cpu_limit == "1.0"
           assert manifest.container.network == "none"

       def test_valid_manifest_has_permissions(self):
           manifest = ManifestParser.parse(VALID_MANIFEST_DATA)
           assert "memory.read" in manifest.permissions
           assert "memory.write" in manifest.permissions
           assert "gpu.inference" in manifest.permissions
           assert len(manifest.permissions) == 4

       def test_missing_name_fails(self):
           data = {**VALID_MANIFEST_DATA}
           del data["name"]
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_missing_version_fails(self):
           data = {**VALID_MANIFEST_DATA}
           del data["version"]
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_missing_author_fails(self):
           data = {**VALID_MANIFEST_DATA}
           del data["author"]
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_missing_description_fails(self):
           data = {**VALID_MANIFEST_DATA}
           del data["description"]
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_missing_type_fails(self):
           data = {**VALID_MANIFEST_DATA}
           del data["type"]
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_missing_container_fails(self):
           data = {**VALID_MANIFEST_DATA}
           del data["container"]
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_invalid_name_format_fails(self):
           data = {**VALID_MANIFEST_DATA, "name": "Invalid Name!"}
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_invalid_version_format_fails(self):
           data = {**VALID_MANIFEST_DATA, "version": "v1.0"}
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_invalid_type_fails(self):
           data = {**VALID_MANIFEST_DATA, "type": "invalid_type"}
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_invalid_permission_rejected(self):
           data = {**VALID_MANIFEST_DATA, "permissions": ["hack.system"]}
           with pytest.raises(ValidationError) as exc_info:
               ManifestParser.parse(data)
           assert "Permiso inválido" in str(exc_info.value)

       def test_privilege_l0_rejected_for_packages(self):
           data = {**VALID_MANIFEST_DATA, "privilege_level": "L0"}
           with pytest.raises(ValidationError) as exc_info:
               ManifestParser.parse(data)
           assert "L0" in str(exc_info.value)

       def test_privilege_l5_sandbox_accepted(self):
           data = {**VALID_MANIFEST_DATA, "privilege_level": "L5", "permissions": ["memory.read"]}
           manifest = ManifestParser.parse(data)
           assert manifest.privilege_level == PrivilegeLevel.L5

       def test_all_valid_package_types(self):
           for pkg_type in ["node", "service", "theme", "plugin"]:
               data = {**VALID_MANIFEST_DATA, "type": pkg_type}
               manifest = ManifestParser.parse(data)
               assert manifest.type.value == pkg_type

       def test_all_privilege_levels_except_l0(self):
           for level in ["L1", "L2", "L3", "L4", "L5"]:
               data = {**VALID_MANIFEST_DATA, "privilege_level": level}
               manifest = ManifestParser.parse(data)
               assert manifest.privilege_level.value == level

       def test_empty_permissions_allowed(self):
           data = {**VALID_MANIFEST_DATA, "permissions": []}
           manifest = ManifestParser.parse(data)
           assert manifest.permissions == []

       def test_invalid_network_rejected(self):
           data = {**VALID_MANIFEST_DATA}
           data["container"] = {**data["container"], "network": "privileged"}
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)


   class TestContainerConfig:
       """Tests para ContainerConfig."""

       def test_valid_config(self):
           config = ContainerConfig(image="yeyo-chat:1.0.0")
           assert config.image == "yeyo-chat:1.0.0"
           assert config.memory_limit == "512m"
           assert config.cpu_limit == "1.0"
           assert config.network == "none"

       def test_missing_image_fails(self):
           with pytest.raises(ValidationError):
               ContainerConfig()

       def test_custom_limits(self):
           config = ContainerConfig(
               image="test:1.0",
               memory_limit="1g",
               cpu_limit="2.0",
               network="bridge",
           )
           assert config.memory_limit == "1g"
           assert config.cpu_limit == "2.0"
           assert config.network == "bridge"


   class TestManifestParser:
       """Tests para ManifestParser."""

       def test_parse_yaml_string(self):
           yaml_str = """
   name: "test-pkg"
   version: "1.0.0"
   author: "Test"
   description: "Test package"
   type: "node"
   container:
     image: "test:1.0.0"
   permissions:
     - "memory.read"
   privilege_level: "L2"
   """
           manifest = ManifestParser.parse_yaml(yaml_str)
           assert manifest.name == "test-pkg"
           assert manifest.version == "1.0.0"

       def test_parse_yaml_invalid_raises(self):
           with pytest.raises(Exception):
               ManifestParser.parse_yaml("not: [valid: yaml: {")

       def test_to_yaml_roundtrip(self):
           manifest = ManifestParser.parse(VALID_MANIFEST_DATA)
           yaml_output = ManifestParser.to_yaml(manifest)
           assert "node-chat" in yaml_output
           assert "1.0.0" in yaml_output

       def test_all_valid_permissions_exist(self):
           expected = {
               "memory.read", "memory.write",
               "gpu.inference", "gpu.training",
               "network.localhost", "network.internet",
               "filesystem.read", "filesystem.write",
               "camera", "microphone", "clipboard",
           }
           assert VALID_PERMISSIONS == expected

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/pkg/test_manifest.py -v

VERIFICAR:
- [ ] Archivo src/pkg/manifest.py existe con PackageManifest, ManifestParser, ContainerConfig
- [ ] Manifest válido parsea correctamente con todos los campos
- [ ] Campo faltante requerido (name, version, author, description, type, container) falla
- [ ] Permiso inválido es rechazado
- [ ] Nivel de privilegio L0 rechazado para paquetes externos
- [ ] Todos los tipos de paquete aceptados: node, service, theme, plugin
- [ ] Network inválido rechazado (solo none, host, bridge)
- [ ] YAML roundtrip funciona
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar que existen todos los __init__.py
- pyyaml no instalado: pip install pyyaml
- pydantic no instalado: pip install pydantic

NO HACER:
- No implementar el builder aún (eso es micro-fase 4.1)
- No crear containers reales
- No conectar con la base de datos de paquetes
- No implementar lógica de firma

GATE: ManifestParser parsea y valida manifests completos, rechaza datos inválidos, soporta YAML, todos los tests pasan.
```
