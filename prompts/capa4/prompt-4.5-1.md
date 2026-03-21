## ═══════════════════════════════════════
## MICRO-FASE 4.5 — Privilege Levels
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.5-1 [VSCODE] — Sistema de 6 niveles de privilegio

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.5 de Capa 4 (Sistema Nervioso): implementar el sistema de 6 niveles de privilegio.

CONTEXTO:
- Micro-fases 4.0-4.4 completadas: Manifest, Builder, Installer, Permissions, Container Security
- 6 niveles de privilegio: ROOT(L0) > ADMIN(L1) > USER(L2) > LIMITED(L3) > GUEST(L4) > SANDBOX(L5)
- CRÍTICO: Nodos generados por IA SIEMPRE L5 (sandbox). Sin escalamiento posible desde L5
- ROOT(L0) solo para el OS core — paquetes externos NUNCA pueden ser L0
- Cada nivel tiene un techo máximo de permisos que no puede superar

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/security/privileges.py:

   Ruta: ~/yeyo-os/src/security/privileges.py
   Contenido:

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

2. Actualizar archivo src/security/__init__.py:

   Ruta: ~/yeyo-os/src/security/__init__.py
   Contenido:
   from .permissions import Permission, PermissionManager, PermissionGrant
   from .container import SecureContainer, ContainerManifest, ContainerSecurityError
   from .privileges import PrivilegeLevel, PrivilegeEnforcer, EscalationError, LEVEL_PERMISSIONS

3. Crear archivo tests/unit/security/test_privileges.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_privileges.py
   Contenido:

   """Tests para Privilege Level System — Micro-fase 4.5"""

   import pytest
   from src.security.privileges import (
       PrivilegeLevel,
       PrivilegeEnforcer,
       EscalationError,
       LEVEL_PERMISSIONS,
   )
   from src.security.permissions import Permission


   @pytest.fixture
   def enforcer():
       return PrivilegeEnforcer()


   class TestPrivilegeLevel:
       """Tests para el enum PrivilegeLevel."""

       def test_six_levels_defined(self):
           assert len(PrivilegeLevel) == 6

       def test_level_ordering(self):
           assert PrivilegeLevel.ROOT < PrivilegeLevel.ADMIN
           assert PrivilegeLevel.ADMIN < PrivilegeLevel.USER
           assert PrivilegeLevel.USER < PrivilegeLevel.LIMITED
           assert PrivilegeLevel.LIMITED < PrivilegeLevel.GUEST
           assert PrivilegeLevel.GUEST < PrivilegeLevel.SANDBOX

       def test_root_is_zero(self):
           assert PrivilegeLevel.ROOT == 0

       def test_sandbox_is_five(self):
           assert PrivilegeLevel.SANDBOX == 5


   class TestLevelPermissions:
       """Tests para el mapa de permisos por nivel."""

       def test_l5_sandbox_only_memory_read(self):
           perms = LEVEL_PERMISSIONS[5]
           assert perms == ["memory.read"]

       def test_l4_guest_minimal(self):
           perms = LEVEL_PERMISSIONS[4]
           assert "memory.read" in perms
           assert "clipboard" in perms
           assert "network.internet" not in perms

       def test_l2_user_standard(self):
           perms = LEVEL_PERMISSIONS[2]
           assert "memory.read" in perms
           assert "memory.write" in perms
           assert "gpu.inference" in perms
           assert "network.localhost" in perms
           assert "network.internet" not in perms

       def test_l1_admin_has_internet(self):
           perms = LEVEL_PERMISSIONS[1]
           assert "network.internet" in perms
           assert "filesystem.read" in perms
           assert "filesystem.write" in perms

       def test_l0_root_has_wildcard(self):
           perms = LEVEL_PERMISSIONS[0]
           assert "*" in perms


   class TestPrivilegeEnforcer:
       """Tests para PrivilegeEnforcer."""

       def test_register_package(self, enforcer):
           enforcer.register_package("test-pkg", PrivilegeLevel.USER)
           assert enforcer.get_level("test-pkg") == PrivilegeLevel.USER

       def test_register_root_blocked(self, enforcer):
           with pytest.raises(EscalationError, match="ROOT"):
               enforcer.register_package("test-pkg", PrivilegeLevel.ROOT)

       def test_ia_package_always_l5(self, enforcer):
           enforcer.register_package("ia-node", PrivilegeLevel.USER, ia_generated=True)
           assert enforcer.get_level("ia-node") == PrivilegeLevel.SANDBOX

       def test_ia_package_forced_l5_even_if_admin(self, enforcer):
           enforcer.register_package("ia-node", PrivilegeLevel.ADMIN, ia_generated=True)
           assert enforcer.get_level("ia-node") == PrivilegeLevel.SANDBOX

       def test_is_ia_generated(self, enforcer):
           enforcer.register_package("ia-node", PrivilegeLevel.USER, ia_generated=True)
           assert enforcer.is_ia_generated("ia-node") is True
           enforcer.register_package("normal-pkg", PrivilegeLevel.USER)
           assert enforcer.is_ia_generated("normal-pkg") is False

       @pytest.mark.asyncio
       async def test_l5_can_only_read_memory(self, enforcer):
           enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
           assert await enforcer.enforce("sandbox-pkg", "memory.read") is True
           assert await enforcer.enforce("sandbox-pkg", "memory.write") is False
           assert await enforcer.enforce("sandbox-pkg", "gpu.inference") is False
           assert await enforcer.enforce("sandbox-pkg", "network.internet") is False

       @pytest.mark.asyncio
       async def test_l2_cant_access_internet(self, enforcer):
           enforcer.register_package("user-pkg", PrivilegeLevel.USER)
           assert await enforcer.enforce("user-pkg", "network.internet") is False
           assert await enforcer.enforce("user-pkg", "memory.read") is True
           assert await enforcer.enforce("user-pkg", "gpu.inference") is True

       @pytest.mark.asyncio
       async def test_enforce_unknown_package_denied(self, enforcer):
           assert await enforcer.enforce("unknown-pkg", "memory.read") is False

       @pytest.mark.asyncio
       async def test_escalation_from_l5_blocked(self, enforcer):
           enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
           with pytest.raises(EscalationError, match="BLOQUEADO"):
               await enforcer.try_escalate("sandbox-pkg", PrivilegeLevel.USER)

       @pytest.mark.asyncio
       async def test_escalation_from_ia_l5_blocked(self, enforcer):
           enforcer.register_package("ia-node", PrivilegeLevel.USER, ia_generated=True)
           with pytest.raises(EscalationError, match="BLOQUEADO"):
               await enforcer.try_escalate("ia-node", PrivilegeLevel.USER)

       @pytest.mark.asyncio
       async def test_escalation_to_root_blocked(self, enforcer):
           enforcer.register_package("admin-pkg", PrivilegeLevel.ADMIN)
           with pytest.raises(EscalationError, match="BLOQUEADO"):
               await enforcer.try_escalate("admin-pkg", PrivilegeLevel.ROOT)

       @pytest.mark.asyncio
       async def test_valid_escalation_works(self, enforcer):
           enforcer.register_package("limited-pkg", PrivilegeLevel.LIMITED)
           await enforcer.try_escalate("limited-pkg", PrivilegeLevel.USER)
           assert enforcer.get_level("limited-pkg") == PrivilegeLevel.USER

       @pytest.mark.asyncio
       async def test_level_enforced_on_every_action(self, enforcer):
           enforcer.register_package("test-pkg", PrivilegeLevel.GUEST)
           for perm in Permission:
               result = await enforcer.enforce("test-pkg", perm.value)
               allowed = perm.value in LEVEL_PERMISSIONS[4]
               assert result == allowed, f"L4 enforce mismatch for {perm.value}"

       def test_unregister_package(self, enforcer):
           enforcer.register_package("test-pkg", PrivilegeLevel.USER)
           enforcer.unregister_package("test-pkg")
           assert enforcer.get_level("test-pkg") is None

       def test_get_max_permissions(self, enforcer):
           perms = enforcer.get_max_permissions(PrivilegeLevel.SANDBOX)
           assert perms == ["memory.read"]

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_privileges.py -v

VERIFICAR:
- [ ] Archivo src/security/privileges.py existe con PrivilegeLevel, PrivilegeEnforcer
- [ ] 6 niveles definidos: ROOT(0) a SANDBOX(5)
- [ ] L5 SOLO puede leer memoria — nada más
- [ ] L2 NO puede acceder a internet
- [ ] L0 tiene todos los permisos (wildcard *)
- [ ] Nodos IA SIEMPRE forzados a L5 sin importar lo que soliciten
- [ ] Escalamiento desde L5 BLOQUEADO siempre
- [ ] Escalamiento a L0 BLOQUEADO siempre
- [ ] Paquetes externos NO pueden ser L0
- [ ] Level enforced en cada acción
- [ ] TODOS los tests pasan

SI FALLA:
- IntEnum: verificar que PrivilegeLevel usa IntEnum no Enum
- Import circular: verificar imports entre permissions y privileges
- Asyncio: verificar pytest-asyncio instalado

NO HACER:
- No permitir L0 para paquetes externos
- No permitir escalamiento desde L5 — NUNCA
- No crear bypass para nodos IA
- No agregar lógica de container (ya está en 4.4)

GATE: PrivilegeEnforcer implementa 6 niveles, IA forzado a L5, escalamiento bloqueado, permisos enforced correctamente, todos los tests pasan.
```
