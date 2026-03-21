## ═══════════════════════════════════════
## MICRO-FASE 4.3 — Permission System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.3-1 [VSCODE] — Sistema de permisos estilo Android/iOS

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.3 de Capa 4 (Sistema Nervioso): crear el sistema de permisos estilo Android/iOS.

CONTEXTO:
- Micro-fases 4.0-4.2 completadas: ManifestParser, Builder, Installer funcionando
- Sistema de permisos ALLOWLIST: si no se solicita explícitamente, NO se concede
- No existe opción "conceder todo" — cada permiso se aprueba individualmente
- Nodos generados por IA SIEMPRE L5 (sandbox) — permisos mínimos
- 11 permisos definidos: memory.read/write, gpu.inference/training, network.localhost/internet, filesystem.read/write, camera, microphone, clipboard

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/security
   mkdir -p tests/unit/security

2. Crear archivo src/security/__init__.py:

   Ruta: ~/yeyo-os/src/security/__init__.py
   Contenido:
   from .permissions import Permission, PermissionManager, PermissionGrant

3. Crear archivo src/security/permissions.py:

   Ruta: ~/yeyo-os/src/security/permissions.py
   Contenido:

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

4. Crear archivo tests/unit/security/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/unit/security/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/security/test_permissions.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_permissions.py
   Contenido:

   """Tests para Permission System — Micro-fase 4.3"""

   import pytest
   from src.security.permissions import Permission, PermissionManager, PermissionGrant


   @pytest.fixture
   def manager():
       return PermissionManager()


   class TestPermission:
       """Tests para el enum Permission."""

       def test_all_permissions_defined(self):
           expected = {
               "memory.read", "memory.write",
               "gpu.inference", "gpu.training",
               "network.localhost", "network.internet",
               "filesystem.read", "filesystem.write",
               "camera", "microphone", "clipboard",
           }
           actual = {p.value for p in Permission}
           assert actual == expected

       def test_permission_count(self):
           assert len(Permission) == 11

       def test_permission_from_string(self):
           perm = Permission("memory.read")
           assert perm == Permission.MEMORY_READ

       def test_invalid_permission_raises(self):
           with pytest.raises(ValueError):
               Permission("invalid.permission")


   class TestPermissionGrant:
       """Tests para PermissionGrant."""

       def test_create_grant(self):
           grant = PermissionGrant(
               package_name="test-pkg",
               permission=Permission.MEMORY_READ,
               granted=True,
           )
           assert grant.package_name == "test-pkg"
           assert grant.permission == Permission.MEMORY_READ
           assert grant.granted is True

       def test_grant_defaults_to_not_granted(self):
           grant = PermissionGrant(
               package_name="test-pkg",
               permission=Permission.MEMORY_READ,
           )
           assert grant.granted is False


   class TestPermissionManager:
       """Tests para PermissionManager."""

       @pytest.mark.asyncio
       async def test_check_returns_false_before_grant(self, manager):
           result = await manager.check("test-pkg", Permission.MEMORY_READ)
           assert result is False

       @pytest.mark.asyncio
       async def test_check_returns_true_after_grant(self, manager):
           await manager.request("test-pkg", [Permission.MEMORY_READ])
           result = await manager.check("test-pkg", Permission.MEMORY_READ)
           assert result is True

       @pytest.mark.asyncio
       async def test_request_returns_granted_list(self, manager):
           result = await manager.request(
               "test-pkg",
               [Permission.MEMORY_READ, Permission.MEMORY_WRITE],
           )
           assert "memory.read" in result["granted"]
           assert "memory.write" in result["granted"]
           assert result["denied"] == []

       @pytest.mark.asyncio
       async def test_ungrant_permission_returns_false(self, manager):
           result = await manager.check("test-pkg", Permission.GPU_INFERENCE)
           assert result is False

       @pytest.mark.asyncio
       async def test_revoke_works(self, manager):
           await manager.request("test-pkg", [Permission.MEMORY_READ])
           assert await manager.check("test-pkg", Permission.MEMORY_READ) is True

           await manager.revoke("test-pkg", Permission.MEMORY_READ)
           assert await manager.check("test-pkg", Permission.MEMORY_READ) is False

       @pytest.mark.asyncio
       async def test_revoke_all_works(self, manager):
           await manager.request(
               "test-pkg",
               [Permission.MEMORY_READ, Permission.MEMORY_WRITE, Permission.CLIPBOARD],
           )
           assert len(await manager.get_grants("test-pkg")) == 3

           await manager.revoke_all("test-pkg")
           assert len(await manager.get_grants("test-pkg")) == 0

       @pytest.mark.asyncio
       async def test_get_grants_returns_active_only(self, manager):
           await manager.request(
               "test-pkg",
               [Permission.MEMORY_READ, Permission.GPU_INFERENCE],
           )
           await manager.revoke("test-pkg", Permission.GPU_INFERENCE)

           grants = await manager.get_grants("test-pkg")
           assert Permission.MEMORY_READ in grants
           assert Permission.GPU_INFERENCE not in grants

       @pytest.mark.asyncio
       async def test_get_grants_empty_for_unknown_package(self, manager):
           grants = await manager.get_grants("unknown-pkg")
           assert grants == []

       @pytest.mark.asyncio
       async def test_multiple_packages_isolated(self, manager):
           await manager.request("pkg-a", [Permission.MEMORY_READ])
           await manager.request("pkg-b", [Permission.GPU_INFERENCE])

           assert await manager.check("pkg-a", Permission.MEMORY_READ) is True
           assert await manager.check("pkg-a", Permission.GPU_INFERENCE) is False
           assert await manager.check("pkg-b", Permission.GPU_INFERENCE) is True
           assert await manager.check("pkg-b", Permission.MEMORY_READ) is False

       @pytest.mark.asyncio
       async def test_has_any_permission(self, manager):
           assert await manager.has_any_permission("test-pkg") is False
           await manager.request("test-pkg", [Permission.CLIPBOARD])
           assert await manager.has_any_permission("test-pkg") is True

       @pytest.mark.asyncio
       async def test_remove_package_clears_all(self, manager):
           await manager.request("test-pkg", [Permission.MEMORY_READ])
           await manager.remove_package("test-pkg")
           assert await manager.check("test-pkg", Permission.MEMORY_READ) is False
           assert await manager.get_grants("test-pkg") == []

       @pytest.mark.asyncio
       async def test_get_all_grants(self, manager):
           await manager.request("pkg-a", [Permission.MEMORY_READ])
           await manager.request("pkg-b", [Permission.CLIPBOARD])

           all_grants = await manager.get_all_grants()
           assert "pkg-a" in all_grants
           assert "pkg-b" in all_grants
           assert "memory.read" in all_grants["pkg-a"]

       @pytest.mark.asyncio
       async def test_no_grant_all_option(self, manager):
           """No existe forma de conceder todos los permisos de golpe."""
           all_perms = list(Permission)
           result = await manager.request("test-pkg", all_perms)
           assert len(result["granted"]) == len(all_perms)
           for perm in Permission:
               individual_check = await manager.check("test-pkg", perm)
               assert individual_check is True

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_permissions.py -v

VERIFICAR:
- [ ] Archivo src/security/permissions.py existe con Permission, PermissionManager, PermissionGrant
- [ ] 11 permisos definidos en el enum
- [ ] check retorna False ANTES de conceder (ALLOWLIST)
- [ ] check retorna True DESPUÉS de conceder
- [ ] revoke funciona correctamente
- [ ] revoke_all remueve todos los permisos
- [ ] Paquetes múltiples aislados entre sí
- [ ] remove_package limpia completamente
- [ ] TODOS los tests pasan

SI FALLA:
- pytest-asyncio no instalado: pip install pytest-asyncio
- Import error: verificar __init__.py en src/security/
- Enum: verificar que Permission usa str, Enum

NO HACER:
- No implementar persistencia en base de datos (eso es micro-fase 4.8)
- No implementar diálogo de UI (eso es micro-fase 4.12)
- No agregar lógica de niveles de privilegio (eso es micro-fase 4.5)
- No agregar opción "grant all" — NUNCA

GATE: PermissionManager implementa ALLOWLIST correctamente, check/request/revoke funcionan, paquetes aislados, todos los tests pasan.
```
