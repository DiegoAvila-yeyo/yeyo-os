"""
YeyoOS — Honeypots
Micro-fase 6.7 — Capa 6: Sistema Inmune

Archivos y servicios falsos para detectar intrusiones.
Cualquier acceso = ALERTA INMEDIATA. NUNCA exponer datos reales.
"""

import json
import logging
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Callable, Awaitable

logger = logging.getLogger("yeyo.security.honeypots")


@dataclass
class HoneypotFile:
    path: str
    description: str
    fake_content: str
    created: bool = False


@dataclass
class HoneypotAlert:
    timestamp: str
    honeypot_type: str
    honeypot_path: str
    source_info: str
    details: str
    severity: str = "critical"


@dataclass
class HoneypotConfig:
    alert_log_file: str = "/var/log/yeyo/honeypot-alerts.json"
    ssh_honeypot_port: int = 2222
    enabled: bool = True


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


class HoneypotManager:
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

    def deploy_file_honeypots(self) -> list[str]:
        deployed = []
        for hp in self.honeypot_files:
            try:
                path = Path(hp.path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(hp.fake_content)
                os.chmod(hp.path, 0o644)
                hp.created = True
                deployed.append(hp.path)
                logger.info(f"Honeypot desplegado: {hp.path} ({hp.description})")
            except (OSError, PermissionError) as e:
                logger.warning(f"No se pudo crear honeypot {hp.path}: {e}")
        return deployed

    def remove_file_honeypots(self) -> None:
        for hp in self.honeypot_files:
            try:
                Path(hp.path).unlink(missing_ok=True)
                hp.created = False
            except (OSError, PermissionError):
                pass

    async def on_file_accessed(self, filepath: str, source_info: str = "unknown") -> Optional[HoneypotAlert]:
        if not self.config.enabled:
            return None
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
                f"INTRUSION DETECTADA: Acceso a honeypot '{honeypot.description}' "
                f"en {filepath}. Fuente: {source_info}"
            ),
            severity="critical",
        )
        self._alerts.append(alert)
        self._log_alert(alert)
        logger.critical(alert.details)
        if self._on_alert:
            await self._on_alert(alert)
        return alert

    async def on_ssh_connection(self, source_ip: str, source_port: int, username: str, password: str = "") -> HoneypotAlert:
        alert = HoneypotAlert(
            timestamp=datetime.now(timezone.utc).isoformat(),
            honeypot_type="service",
            honeypot_path=f"ssh://0.0.0.0:{self.config.ssh_honeypot_port}",
            source_info=f"{source_ip}:{source_port}",
            details=(
                f"INTRUSION SSH: Conexion al honeypot SSH desde {source_ip}:{source_port}. "
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

    def _log_alert(self, alert: HoneypotAlert) -> None:
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

    def get_alerts(self) -> list[HoneypotAlert]:
        return self._alerts.copy()

    def get_deployed_files(self) -> list[str]:
        return [hp.path for hp in self.honeypot_files if hp.created]

    def get_status(self) -> dict:
        return {
            "enabled": self.config.enabled,
            "files_deployed": len(self.get_deployed_files()),
            "total_files": len(self.honeypot_files),
            "ssh_port": self.config.ssh_honeypot_port,
            "total_alerts": len(self._alerts),
            "file_alerts": sum(1 for a in self._alerts if a.honeypot_type == "file"),
            "service_alerts": sum(1 for a in self._alerts if a.honeypot_type == "service"),
        }
