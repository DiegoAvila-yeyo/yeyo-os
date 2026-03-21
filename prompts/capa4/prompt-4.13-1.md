## ═══════════════════════════════════════
## MICRO-FASE 4.13 — Integration Test Capa 4
## Tipo: MIXTA | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 4.13-1 [MIXTA] — Test de integración completo de Capa 4 + regresión Capas 0-3

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.13 de Capa 4 (Sistema Nervioso): test de integración completo de toda la Capa 4 más regresión de Capas 0-3.

CONTEXTO:
- Todas las micro-fases 4.0-4.12 completadas
- Test end-to-end: build package → install → verify permissions → run in container → uninstall
- Validar que las reglas de seguridad se cumplen en TODOS los escenarios
- Regresión de Capas 0-3: verificar que nada se rompió
- REGLAS ABSOLUTAS: Podman SIEMPRE, Docker NUNCA, IA → L5, Docker socket JAMÁS

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p tests/integration

2. Crear archivo tests/integration/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/integration/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo tests/integration/test_capa4_integration.py:

   Ruta: ~/yeyo-os/tests/integration/test_capa4_integration.py
   Contenido:

   """
   Test de Integración — Capa 4: Sistema Nervioso
   Micro-fase 4.13

   Test end-to-end del ciclo de vida completo de paquetes.
   Verifica que todas las reglas de seguridad se cumplen.
   """

   import os
   import json
   import tempfile
   import hashlib
   import tarfile
   import pytest
   from pathlib import Path
   from unittest.mock import AsyncMock, patch

   from src.pkg.manifest import ManifestParser, PackageManifest, ValidPermission
   from src.pkg.builder import PackageBuilder
   from src.pkg.installer import PackageInstaller, SignatureError, PermissionDeniedError
   from src.pkg.database import PackageDatabase
   from src.pkg.updater import PackageUpdater, UpdateError, RollbackError
   from src.pkg.apt_bridge import AptBridge, HostAptForbiddenError
   from src.security.permissions import Permission, PermissionManager
   from src.security.container import SecureContainer, ContainerManifest, ContainerSecurityError
   from src.security.privileges import PrivilegeLevel, PrivilegeEnforcer, EscalationError, LEVEL_PERMISSIONS
   from src.pipeline.engine import PipelineEngine, PipelineStep, CycleDetectedError, PipelineStatus


   class TestFullPackageLifecycle:
       """Test end-to-end: build → install → permissions → run → uninstall."""

       @pytest.mark.asyncio
       async def test_full_lifecycle(self):
           """Ciclo completo de vida de un paquete."""
           with tempfile.TemporaryDirectory(prefix="yeyo-integration-") as tmpdir:
               # 1. Crear source directory con manifest
               source_dir = Path(tmpdir) / "source"
               source_dir.mkdir()

               manifest_yaml = """
   name: "integration-test"
   version: "1.0.0"
   author: "YeyoOS"
   description: "Integration test package"
   type: "node"
   container:
     image: "yeyo-integration:1.0.0"
     memory_limit: "256m"
     cpu_limit: "0.5"
     network: "none"
   permissions:
     - "memory.read"
     - "memory.write"
   privilege_level: "L2"
   """
               (source_dir / "manifest.yml").write_text(manifest_yaml)
               (source_dir / "index.html").write_text("<html>Integration Test</html>")
               (source_dir / "Containerfile").write_text("FROM alpine:latest\nCMD [\"echo\"]")

               # 2. Parsear manifest
               manifest = ManifestParser.parse_file(str(source_dir / "manifest.yml"))
               assert manifest.name == "integration-test"
               assert manifest.version == "1.0.0"
               assert manifest.privilege_level.value == "L2"

               # 3. Verificar permisos son válidos
               for perm in manifest.permissions:
                   assert perm in {p.value for p in ValidPermission}

               # 4. Verificar container security
               container = SecureContainer()
               cm = ContainerManifest(
                   image=manifest.container.image,
                   memory_limit=manifest.container.memory_limit,
                   cpu_limit=manifest.container.cpu_limit,
                   network=manifest.container.network,
               )
               args = container.get_run_args(cm)
               assert "--security-opt=no-new-privileges:true" in args
               assert "--cap-drop=ALL" in args
               assert "--read-only" in args

               # 5. Verificar privilege enforcer
               enforcer = PrivilegeEnforcer()
               enforcer.register_package("integration-test", PrivilegeLevel.USER)
               assert await enforcer.enforce("integration-test", "memory.read") is True
               assert await enforcer.enforce("integration-test", "network.internet") is False

               # 6. Verificar permission manager
               perm_mgr = PermissionManager()
               result = await perm_mgr.request(
                   "integration-test",
                   [Permission.MEMORY_READ, Permission.MEMORY_WRITE],
               )
               assert len(result["granted"]) == 2
               assert await perm_mgr.check("integration-test", Permission.MEMORY_READ) is True

               # 7. Revocar y verificar
               await perm_mgr.revoke("integration-test", Permission.MEMORY_WRITE)
               assert await perm_mgr.check("integration-test", Permission.MEMORY_WRITE) is False

               # 8. Cleanup
               await perm_mgr.remove_package("integration-test")
               enforcer.unregister_package("integration-test")


   class TestSecurityRulesEnforced:
       """Verifica que TODAS las reglas de seguridad se cumplen."""

       def test_docker_socket_never_mountable(self):
           container = SecureContainer()
           sockets = [
               "/var/run/docker.sock:/var/run/docker.sock",
               "/run/docker.sock:/run/docker.sock",
               "/var/run/podman/podman.sock:/run/podman.sock",
           ]
           for socket_mount in sockets:
               manifest = ContainerManifest(
                   image="test:1.0",
                   extra_mounts=[socket_mount],
               )
               with pytest.raises(ContainerSecurityError):
                   container.get_run_args(manifest)

       def test_ia_nodes_always_l5(self):
           enforcer = PrivilegeEnforcer()
           for level in [PrivilegeLevel.ADMIN, PrivilegeLevel.USER, PrivilegeLevel.LIMITED]:
               enforcer.register_package(
                   f"ia-node-{level.name}",
                   level,
                   ia_generated=True,
               )
               assert enforcer.get_level(f"ia-node-{level.name}") == PrivilegeLevel.SANDBOX

       @pytest.mark.asyncio
       async def test_l5_escalation_always_blocked(self):
           enforcer = PrivilegeEnforcer()
           enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
           for target in [PrivilegeLevel.ADMIN, PrivilegeLevel.USER, PrivilegeLevel.LIMITED, PrivilegeLevel.GUEST]:
               with pytest.raises(EscalationError):
                   await enforcer.try_escalate("sandbox-pkg", target)

       @pytest.mark.asyncio
       async def test_l5_minimal_permissions(self):
           enforcer = PrivilegeEnforcer()
           enforcer.register_package("sandbox-pkg", PrivilegeLevel.SANDBOX)
           assert await enforcer.enforce("sandbox-pkg", "memory.read") is True
           for perm in ["memory.write", "gpu.inference", "gpu.training",
                        "network.localhost", "network.internet",
                        "filesystem.read", "filesystem.write",
                        "camera", "microphone", "clipboard"]:
               assert await enforcer.enforce("sandbox-pkg", perm) is False, \
                   f"L5 should NOT have {perm}"

       def test_no_privileged_capabilities(self):
           container = SecureContainer()
           for cap in ["SYS_ADMIN", "NET_RAW", "SYS_PTRACE", "NET_ADMIN"]:
               manifest = ContainerManifest(
                   image="test:1.0",
                   extra_caps=[cap],
               )
               with pytest.raises(ContainerSecurityError):
                   container.get_run_args(manifest)

       def test_root_level_blocked_for_packages(self):
           enforcer = PrivilegeEnforcer()
           with pytest.raises(EscalationError):
               enforcer.register_package("evil-pkg", PrivilegeLevel.ROOT)

       def test_manifest_rejects_l0(self):
           from pydantic import ValidationError
           data = {
               "name": "evil-pkg",
               "version": "1.0.0",
               "author": "hacker",
               "description": "evil",
               "type": "node",
               "container": {"image": "evil:1.0"},
               "privilege_level": "L0",
           }
           with pytest.raises(ValidationError):
               ManifestParser.parse(data)

       def test_host_apt_always_forbidden(self):
           bridge = AptBridge()
           with pytest.raises(HostAptForbiddenError):
               bridge.install_on_host(["malware"])
           with pytest.raises(HostAptForbiddenError):
               bridge.remove_from_host(["systemd"])

       def test_container_always_has_security_args(self):
           container = SecureContainer()
           manifest = ContainerManifest(image="any:1.0")
           args = container.get_run_args(manifest)
           required = [
               "--security-opt=no-new-privileges:true",
               "--cap-drop=ALL",
               "--read-only",
           ]
           for req in required:
               assert req in args, f"Falta argumento de seguridad: {req}"


   class TestPipelineIntegration:
       """Tests de integración del motor de pipelines."""

       @pytest.mark.asyncio
       async def test_pipeline_with_multiple_steps(self):
           engine = PipelineEngine()
           results = []

           async def step_executor(step, inputs):
               results.append(step.id)
               return {"step": step.id, "data": f"processed-{step.id}"}

           engine.register_executor("processor", step_executor)

           steps = [
               {"id": "input", "name": "Input", "node_type": "processor"},
               {"id": "transform", "name": "Transform", "node_type": "processor", "depends_on": ["input"]},
               {"id": "output", "name": "Output", "node_type": "processor", "depends_on": ["transform"]},
           ]

           pipeline_id = await engine.create_pipeline("integration-pipeline", steps)
           result = await engine.execute(pipeline_id, input_data={"raw": "data"})

           assert result.status == PipelineStatus.COMPLETED
           assert results == ["input", "transform", "output"]

       @pytest.mark.asyncio
       async def test_pipeline_cycle_rejected(self):
           engine = PipelineEngine()
           with pytest.raises(Exception):
               await engine.create_pipeline("cycle-test", [
                   {"id": "a", "name": "A", "depends_on": ["b"]},
                   {"id": "b", "name": "B", "depends_on": ["a"]},
               ])

       @pytest.mark.asyncio
       async def test_pipeline_fail_fast(self):
           engine = PipelineEngine()

           async def failing_step(step, inputs):
               if step.id == "fail":
                   raise RuntimeError("Deliberate failure")
               return "ok"

           engine.register_executor("generic", failing_step)

           pipeline_id = await engine.create_pipeline("fail-test", [
               {"id": "ok-step", "name": "OK", "node_type": "generic"},
               {"id": "fail", "name": "Fail", "node_type": "generic", "depends_on": ["ok-step"]},
               {"id": "after-fail", "name": "After", "node_type": "generic", "depends_on": ["fail"]},
           ])
           result = await engine.execute(pipeline_id)

           assert result.status == PipelineStatus.FAILED


   class TestPermissionAllowlist:
       """Tests de integración del sistema ALLOWLIST."""

       @pytest.mark.asyncio
       async def test_allowlist_denies_by_default(self):
           mgr = PermissionManager()
           for perm in Permission:
               assert await mgr.check("any-pkg", perm) is False

       @pytest.mark.asyncio
       async def test_allowlist_grants_individually(self):
           mgr = PermissionManager()
           await mgr.request("pkg", [Permission.MEMORY_READ])
           assert await mgr.check("pkg", Permission.MEMORY_READ) is True
           assert await mgr.check("pkg", Permission.MEMORY_WRITE) is False

       @pytest.mark.asyncio
       async def test_revoke_removes_access(self):
           mgr = PermissionManager()
           await mgr.request("pkg", [Permission.CLIPBOARD])
           await mgr.revoke("pkg", Permission.CLIPBOARD)
           assert await mgr.check("pkg", Permission.CLIPBOARD) is False


   class TestDatabaseIntegration:
       """Tests de integración de la base de datos."""

       @pytest.mark.asyncio
       async def test_db_lifecycle(self):
           with tempfile.TemporaryDirectory() as tmpdir:
               db = PackageDatabase(db_path=os.path.join(tmpdir, "test.db"))
               await db.connect()

               await db.register({
                   "name": "db-test",
                   "version": "1.0.0",
                   "author": "Test",
                   "description": "DB test",
                   "type": "node",
               })

               pkg = await db.get("db-test")
               assert pkg["name"] == "db-test"

               await db.grant_permission("db-test", "memory.read")
               assert await db.has_permission("db-test", "memory.read") is True

               await db.revoke_permission("db-test", "memory.read")
               assert await db.has_permission("db-test", "memory.read") is False

               await db.unregister("db-test")
               packages = await db.list_all()
               assert len(packages) == 0

               await db.close()


   class TestUpdateRollbackIntegration:
       """Tests de integración del sistema de actualización."""

       @pytest.mark.asyncio
       async def test_update_with_rollback(self):
           with tempfile.TemporaryDirectory() as tmpdir:
               install_dir = os.path.join(tmpdir, "installed")
               snapshots_dir = os.path.join(tmpdir, "snapshots")
               pkg_dir = os.path.join(install_dir, "rollback-test")
               os.makedirs(pkg_dir)
               Path(pkg_dir, "version.txt").write_text("1.0.0")
               Path(pkg_dir, "manifest.yml").write_text("name: rollback-test")

               async def failing_health(name):
                   return False

               updater = PackageUpdater(
                   install_dir=install_dir,
                   snapshots_dir=snapshots_dir,
                   health_check=failing_health,
               )

               updater.register_available_update("rollback-test", "2.0.0", "/fake")

               with pytest.raises(UpdateError, match="Health check"):
                   await updater.update("rollback-test")

               version = Path(pkg_dir, "version.txt").read_text()
               assert version == "1.0.0", "Rollback debería restaurar versión 1.0.0"

4. Ejecutar TODOS los tests de Capa 4:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/pkg/ tests/unit/security/ tests/unit/pipeline/ tests/integration/ -v --tb=short

5. Si el frontend tiene tests, ejecutar también:
   cd ~/yeyo-os/frontend
   npx jest --no-cache --passWithNoTests 2>/dev/null || echo "Frontend tests: ver resultados arriba"

VERIFICAR:
- [ ] TODOS los tests de Capa 4 pasan (unit + integration)
- [ ] Ciclo completo: manifest → permisos → container → enforce → cleanup
- [ ] Docker socket JAMÁS montable en ningún escenario
- [ ] Nodos IA SIEMPRE L5 sin importar lo que soliciten
- [ ] Escalamiento desde L5 SIEMPRE bloqueado
- [ ] L5 SOLO puede leer memoria
- [ ] Capabilities peligrosas SIEMPRE bloqueadas
- [ ] L0 (ROOT) SIEMPRE rechazado para paquetes externos
- [ ] Apt NUNCA se ejecuta en el host
- [ ] Pipeline detecta ciclos y hace fail-fast
- [ ] ALLOWLIST: todo denegado por defecto
- [ ] Rollback automático funciona al fallar health check
- [ ] Base de datos persiste y limpia correctamente

SI FALLA:
- Imports: verificar que TODOS los __init__.py existen
- Dependencies: pip install pydantic pyyaml aiosqlite pytest pytest-asyncio
- Async fixtures: verificar que usa @pytest.fixture con async def

NO HACER:
- No modificar código de las micro-fases anteriores (solo tests)
- No saltarse ninguna verificación de seguridad
- No crear bypass para reglas de seguridad

GATE FINAL CAPA 4:
✅ Manifest Parser valida paquetes completos
✅ Builder construye .ypkg con Podman (NUNCA Docker)
✅ Installer verifica firmas, solicita permisos, registra
✅ Permission System ALLOWLIST — todo denegado por defecto
✅ Container Security hardened — Docker socket JAMÁS
✅ Privilege Levels — IA siempre L5, sin escalamiento
✅ Drag & Drop entre nodos funcional
✅ Pipeline Engine con detección de ciclos (DAG)
✅ Package Database persiste en SQLite
✅ Auto-Update con rollback automático
✅ Apt abstracción — host NUNCA modificado
✅ API REST completa
✅ UI funcional con PermissionDialog ALLOWLIST
✅ Todos los tests pasan — unit + integration + frontend
```
