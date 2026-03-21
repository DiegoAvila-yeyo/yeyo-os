## ═══════════════════════════════════════
## MICRO-FASE 6.7 — Honeypots
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 6.7-1 [VSCODE] — Honeypots para detección de intrusiones

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.7 de Capa 6 (Sistema Inmune): implementar honeypots — archivos y servicios falsos que detectan intrusiones.

CONTEXTO:
- Micro-fases 6.0-6.6 completadas: Guardian + Anomaly + Auto-Response + Kill Switch + Snapshots + Backup + Anti-Ransomware
- Honeypots: archivos falsos y servicios falsos para detectar intrusiones
- Archivos falsos: ~/.ssh/id_rsa.fake, /etc/shadow.fake, etc.
- Servicio falso: SSH en puerto 2222 (loguea todo, no concede nada)
- Cualquier acceso = ALERTA INMEDIATA a Guardian
- Log en audit trail con detalles completos
- No exponer datos reales NUNCA

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/security/honeypots.py:

   Ruta: ~/yeyo-os/src/security/honeypots.py
   Contenido:

   """
   YeyoOS — Honeypots
   Micro-fase 6.7 — Capa 6: Sistema Inmune

   Archivos y servicios falsos para detectar intrusiones.
   Cualquier acceso = ALERTA INMEDIATA.
   NUNCA exponer datos reales.
   """

   import asyncio
   import json
   import logging
   import os
   import time
   from datetime import datetime, timezone
   from dataclasses import dataclass, field, asdict
   from pathlib import Path
   from typing import Optional, Callable, Awaitable

   logger = logging.getLogger("yeyo.security.honeypots")

   # ═══════════════════════════════════
   # TIPOS DE DATOS
   # ═══════════════════════════════════

   @dataclass
   class HoneypotFile:
       """Definición de un archivo honeypot."""
       path: str
       description: str
       fake_content: str
       created: bool = False

   @dataclass
   class HoneypotAlert:
       """Alerta generada por acceso a honeypot."""
       timestamp: str
       honeypot_type: str  # "file" o "service"
       honeypot_path: str
       source_info: str
       details: str
       severity: str = "critical"

   @dataclass
   class HoneypotConfig:
       """Configuración del sistema de honeypots."""
       alert_log_file: str = "/var/log/yeyo/honeypot-alerts.json"
       ssh_honeypot_port: int = 2222
       enabled: bool = True

   # ═══════════════════════════════════
   # ARCHIVOS HONEYPOT — Contenido falso
   # ═══════════════════════════════════

   HONEYPOT_FILES = [
       HoneypotFile(
           path="/home/user/.ssh/id_rsa.fake",
           description="Clave SSH falsa",
           fake_content=(
               "-----BEGIN OPENSSH PRIVATE KEY-----\n"
               "HONEYPOT-THIS-IS-NOT-A-REAL-KEY-DO-NOT-USE\n"
               "YeyoOS-Guardian-Intrusion-Detection-System\n"
               "Any-access-to-this-file-triggers-an-alert\n"
               "-----END OPENSSH PRIVATE KEY-----\n"
           ),
       ),
       HoneypotFile(
           path="/etc/shadow.fake",
           description="Shadow falso",
           fake_content=(
               "root:$6$HONEYPOT$FAKEHASH:19000:0:99999:7:::\n"
               "user:$6$HONEYPOT$FAKEHASH:19000:0:99999:7:::\n"
               "# YeyoOS Guardian Honeypot — This is not real\n"
           ),
       ),
       HoneypotFile(
           path="/home/user/.aws/credentials.fake",
           description="Credenciales AWS falsas",
           fake_content=(
               "[default]\n"
               "aws_access_key_id = AKIAHONEYPOTFAKEKEY00\n"
               "aws_secret_access_key = HONEYPOT/FakeSecretKey/YeyoOSGuardian\n"
               "# YeyoOS Guardian Honeypot\n"
           ),
       ),
       HoneypotFile(
           path="/home/user/.env.backup",
           description="Archivo .env falso",
           fake_content=(
               "DATABASE_URL=postgresql://honeypot:fake@localhost/trap\n"
               "SECRET_KEY=yeyo-guardian-honeypot-not-real\n"
               "API_KEY=HONEYPOT-FAKE-API-KEY-GUARDIAN\n"
               "# YeyoOS Guardian Honeypot\n"
           ),
       ),
       HoneypotFile(
           path="/var/lib/yeyo/wallet.dat.fake",
           description="Wallet falso",
           fake_content=(
               "# YeyoOS Guardian Honeypot Wallet\n"
               "# This is not a real wallet file\n"
               "# Any access triggers immediate alert\n"
               "FAKE_WALLET_DATA_HONEYPOT\n"
           ),
       ),
   ]

   # ═══════════════════════════════════
   # HONEYPOT MANAGER
   # ═══════════════════════════════════

   class HoneypotManager:
       """Gestor de honeypots de archivos y servicios."""

       def __init__(
           self,
           config: Optional[HoneypotConfig] = None,
           honeypot_files: Optional[list[HoneypotFile]] = None,
           on_alert: Optional[Callable[[HoneypotAlert], Awaitable[None]]] = None,
       ):
           self.config = config or HoneypotConfig()
           self.honeypot_files = honeypot_files or HONEYPOT_FILES
           self._alerts: list[HoneypotAlert] = []
           self._on_alert = on_alert
           self._watchers_running = False

       # ═══════════════════════════════════
       # DESPLEGAR HONEYPOTS
       # ═══════════════════════════════════

       def deploy_file_honeypots(self) -> list[str]:
           """Crea todos los archivos honeypot en el sistema."""
           deployed = []

           for hp in self.honeypot_files:
               try:
                   path = Path(hp.path)
                   path.parent.mkdir(parents=True, exist_ok=True)
                   path.write_text(hp.fake_content)

                   # Hacer el archivo atractivo pero monitoreable
                   os.chmod(hp.path, 0o644)

                   hp.created = True
                   deployed.append(hp.path)
                   logger.info(f"Honeypot desplegado: {hp.path} ({hp.description})")

               except (OSError, PermissionError) as e:
                   logger.warning(f"No se pudo crear honeypot {hp.path}: {e}")

           return deployed

       def remove_file_honeypots(self) -> None:
           """Elimina todos los archivos honeypot."""
           for hp in self.honeypot_files:
               try:
                   Path(hp.path).unlink(missing_ok=True)
                   hp.created = False
               except (OSError, PermissionError):
                   pass

       # ═══════════════════════════════════
       # DETECCIÓN DE ACCESO
       # ═══════════════════════════════════

       async def on_file_accessed(self, filepath: str, source_info: str = "unknown") -> Optional[HoneypotAlert]:
           """
           Se llama cuando se detecta acceso a un archivo honeypot.
           Genera alerta INMEDIATA.
           """
           if not self.config.enabled:
               return None

           # Verificar si es un archivo honeypot
           honeypot = None
           for hp in self.honeypot_files:
               if hp.path == filepath:
                   honeypot = hp
                   break

           if honeypot is None:
               return None

           alert = HoneypotAlert(
               timestamp=datetime.now(timezone.utc).isoformat(),
               honeypot_type="file",
               honeypot_path=filepath,
               source_info=source_info,
               details=(
                   f"🚨 INTRUSIÓN DETECTADA: Acceso a honeypot '{honeypot.description}' "
                   f"en {filepath}. Fuente: {source_info}"
               ),
               severity="critical",
           )

           self._alerts.append(alert)
           self._log_alert(alert)

           logger.critical(alert.details)

           # Callback si está configurado
           if self._on_alert:
               await self._on_alert(alert)

           return alert

       async def on_ssh_connection(
           self,
           source_ip: str,
           source_port: int,
           username: str,
           password: str = "",
       ) -> HoneypotAlert:
           """
           Se llama cuando alguien se conecta al SSH honeypot.
           Genera alerta INMEDIATA con detalles completos.
           """
           alert = HoneypotAlert(
               timestamp=datetime.now(timezone.utc).isoformat(),
               honeypot_type="service",
               honeypot_path=f"ssh://0.0.0.0:{self.config.ssh_honeypot_port}",
               source_info=f"{source_ip}:{source_port}",
               details=(
                   f"🚨 INTRUSIÓN SSH: Conexión al honeypot SSH desde {source_ip}:{source_port}. "
                   f"Usuario intentado: '{username}'"
               ),
               severity="critical",
           )

           self._alerts.append(alert)
           self._log_alert(alert)

           logger.critical(alert.details)

           if self._on_alert:
               await self._on_alert(alert)

           return alert

       # ═══════════════════════════════════
       # LOGGING
       # ═══════════════════════════════════

       def _log_alert(self, alert: HoneypotAlert) -> None:
           """Guarda alerta en archivo de log."""
           try:
               path = Path(self.config.alert_log_file)
               path.parent.mkdir(parents=True, exist_ok=True)

               alerts = []
               if path.exists():
                   try:
                       alerts = json.loads(path.read_text())
                   except json.JSONDecodeError:
                       alerts = []

               alerts.append(asdict(alert))
               path.write_text(json.dumps(alerts, indent=2))

           except (OSError, PermissionError) as e:
               logger.error(f"No se pudo guardar alerta honeypot: {e}")

       # ═══════════════════════════════════
       # CONSULTAS
       # ═══════════════════════════════════

       def get_alerts(self) -> list[HoneypotAlert]:
           """Retorna todas las alertas de honeypot."""
           return self._alerts.copy()

       def get_deployed_files(self) -> list[str]:
           """Retorna lista de archivos honeypot desplegados."""
           return [hp.path for hp in self.honeypot_files if hp.created]

       def get_status(self) -> dict:
           """Retorna estado del sistema de honeypots."""
           return {
               "enabled": self.config.enabled,
               "files_deployed": len(self.get_deployed_files()),
               "total_files": len(self.honeypot_files),
               "ssh_port": self.config.ssh_honeypot_port,
               "total_alerts": len(self._alerts),
               "file_alerts": sum(1 for a in self._alerts if a.honeypot_type == "file"),
               "service_alerts": sum(1 for a in self._alerts if a.honeypot_type == "service"),
           }

2. Crear archivo tests/unit/security/test_honeypots.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_honeypots.py
   Contenido:

   """Tests para Honeypots — Micro-fase 6.7"""

   import pytest
   import asyncio
   from pathlib import Path
   from src.security.honeypots import (
       HoneypotManager,
       HoneypotConfig,
       HoneypotFile,
       HoneypotAlert,
       HONEYPOT_FILES,
   )


   @pytest.fixture
   def tmp_config(tmp_path):
       return HoneypotConfig(
           alert_log_file=str(tmp_path / "alerts.json"),
           ssh_honeypot_port=2222,
       )


   @pytest.fixture
   def tmp_honeypots(tmp_path):
       return [
           HoneypotFile(
               path=str(tmp_path / ".ssh" / "id_rsa.fake"),
               description="Clave SSH falsa",
               fake_content="FAKE KEY CONTENT",
           ),
           HoneypotFile(
               path=str(tmp_path / "shadow.fake"),
               description="Shadow falso",
               fake_content="FAKE SHADOW",
           ),
       ]


   @pytest.fixture
   def manager(tmp_config, tmp_honeypots):
       return HoneypotManager(
           config=tmp_config,
           honeypot_files=tmp_honeypots,
       )


   class TestHoneypotDeployment:
       def test_deploy_creates_files(self, manager, tmp_honeypots):
           deployed = manager.deploy_file_honeypots()
           assert len(deployed) == 2
           for hp in tmp_honeypots:
               assert Path(hp.path).exists()

       def test_deploy_marks_created(self, manager, tmp_honeypots):
           manager.deploy_file_honeypots()
           for hp in tmp_honeypots:
               assert hp.created is True

       def test_remove_deletes_files(self, manager, tmp_honeypots):
           manager.deploy_file_honeypots()
           manager.remove_file_honeypots()
           for hp in tmp_honeypots:
               assert not Path(hp.path).exists()

       def test_fake_content_not_real(self, tmp_honeypots):
           for hp in tmp_honeypots:
               assert "FAKE" in hp.fake_content or "HONEYPOT" in hp.fake_content


   class TestHoneypotAlerts:
       @pytest.mark.asyncio
       async def test_file_access_triggers_alert(self, manager, tmp_honeypots):
           manager.deploy_file_honeypots()
           alert = await manager.on_file_accessed(
               tmp_honeypots[0].path,
               source_info="pid:1234",
           )
           assert alert is not None
           assert alert.honeypot_type == "file"
           assert alert.severity == "critical"

       @pytest.mark.asyncio
       async def test_non_honeypot_no_alert(self, manager):
           alert = await manager.on_file_accessed("/etc/passwd", "pid:1234")
           assert alert is None

       @pytest.mark.asyncio
       async def test_ssh_connection_triggers_alert(self, manager):
           alert = await manager.on_ssh_connection(
               source_ip="192.168.1.100",
               source_port=54321,
               username="root",
               password="admin123",
           )
           assert alert is not None
           assert alert.honeypot_type == "service"
           assert "192.168.1.100" in alert.source_info
           assert "root" in alert.details

       @pytest.mark.asyncio
       async def test_alert_includes_full_details(self, manager, tmp_honeypots):
           manager.deploy_file_honeypots()
           alert = await manager.on_file_accessed(
               tmp_honeypots[0].path,
               source_info="user:attacker pid:9999 cmd:cat",
           )
           assert "attacker" in alert.source_info or "attacker" in alert.details

       @pytest.mark.asyncio
       async def test_alert_logged_to_file(self, manager, tmp_config, tmp_honeypots):
           manager.deploy_file_honeypots()
           await manager.on_file_accessed(tmp_honeypots[0].path, "test")
           log_path = Path(tmp_config.alert_log_file)
           assert log_path.exists()

       @pytest.mark.asyncio
       async def test_callback_called(self, tmp_config, tmp_honeypots):
           callback_called = []

           async def on_alert(alert):
               callback_called.append(alert)

           mgr = HoneypotManager(
               config=tmp_config,
               honeypot_files=tmp_honeypots,
               on_alert=on_alert,
           )
           mgr.deploy_file_honeypots()
           await mgr.on_file_accessed(tmp_honeypots[0].path, "test")
           assert len(callback_called) == 1


   class TestHoneypotStatus:
       def test_status_shows_deployed(self, manager):
           manager.deploy_file_honeypots()
           status = manager.get_status()
           assert status["files_deployed"] == 2
           assert status["enabled"] is True

       def test_no_real_data_exposed(self):
           for hp in HONEYPOT_FILES:
               content = hp.fake_content.upper()
               assert "HONEYPOT" in content or "FAKE" in content or "NOT REAL" in content.replace("-", " ")

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_honeypots.py -v

VERIFICAR:
- [ ] Archivo src/security/honeypots.py existe con HoneypotManager
- [ ] Archivos honeypot se despliegan con contenido falso
- [ ] Acceso a honeypot genera alerta CRITICAL inmediata
- [ ] SSH honeypot loguea conexión con detalles completos
- [ ] Alerta incluye: timestamp, tipo, fuente, detalles
- [ ] No se exponen datos reales NUNCA
- [ ] Log persistido en archivo JSON
- [ ] TODOS los tests pasan

SI FALLA:
- Permisos: usar tmp_path en tests
- async tests: instalar pytest-asyncio
- Import error: verificar __init__.py

NO HACER:
- No poner datos REALES en los honeypots (solo contenido falso)
- No permitir acceso real al SSH honeypot
- No borrar alertas (son evidencia de intrusión)
- No desactivar honeypots en producción

GATE: HoneypotManager despliega archivos falsos, detecta acceso inmediatamente, SSH honeypot loguea conexiones, no expone datos reales, alertas persistidas, todos los tests pasan.
```
