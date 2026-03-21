## ═══════════════════════════════════════
## MICRO-FASE 7.10 — Corporate Deployment
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.10-1 [VSCODE] — Crear herramientas de deployment corporativo

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.10 de Capa 7 (Evolución): crear herramientas para desplegar YeyoOS en entornos corporativos.

CONTEXTO:
- Micro-fases 7.0-7.9 completadas
- ISO pre-configurada con settings de la empresa
- Gestión centralizada de paquetes
- LDAP/AD integration (placeholder)
- Policy enforcement: paquetes restringidos, backups obligatorios
- Fleet management dashboard (placeholder)
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/deploy
   mkdir -p tests/unit/deploy

2. Crear archivo src/deploy/__init__.py:

   Ruta: ~/yeyo-os/src/deploy/__init__.py
   Contenido:
   from .corporate import CorporateDeployer, DeploymentConfig, Policy

3. Crear archivo src/deploy/corporate.py:

   Ruta: ~/yeyo-os/src/deploy/corporate.py
   Contenido:

   """
   YeyoOS — Corporate Deployment
   Micro-fase 7.10 — Capa 7: Evolución

   Herramientas para desplegar YeyoOS en entornos corporativos.
   ISO pre-configurada, políticas, gestión centralizada.
   """

   import json
   import logging
   from datetime import datetime
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.deploy.corporate")


   class Policy(BaseModel):
       """Política corporativa de YeyoOS."""
       name: str
       description: str = ""
       enforce_backups: bool = True
       backup_frequency_hours: int = Field(default=24, ge=1)
       restricted_packages: list[str] = Field(default_factory=list)
       allowed_package_sources: list[str] = Field(default_factory=lambda: ["official"])
       require_package_approval: bool = True
       max_gpu_per_user_pct: int = Field(default=50, ge=10, le=100)
       force_password_complexity: bool = True
       min_password_length: int = Field(default=12, ge=8)
       session_timeout_hours: int = Field(default=8, ge=1)
       enable_guest_access: bool = False
       audit_log_retention_days: int = Field(default=365, ge=30)
       ldap_enabled: bool = False
       ldap_server: str = ""
       ldap_base_dn: str = ""


   class DeploymentConfig(BaseModel):
       """Configuración de deployment corporativo."""
       company_name: str
       company_domain: str = ""
       deployment_id: str = ""
       default_language: str = "es"
       default_timezone: str = "America/Mexico_City"
       policy: Policy
       pre_installed_packages: list[str] = Field(default_factory=list)
       custom_branding: dict = Field(default_factory=dict)
       ollama_model: str = "qwen2.5:3b"
       fleet_server_url: str = ""
       created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


   class MachineInfo(BaseModel):
       """Información de una máquina del fleet."""
       machine_id: str
       hostname: str
       ip_address: str = ""
       os_version: str = ""
       last_seen: str = ""
       status: str = "unknown"
       user_count: int = 0
       gpu_model: str = ""
       policy_compliant: bool = True


   class CorporateDeployer:
       """Gestor de deployment corporativo de YeyoOS."""

       def __init__(self, config_dir: str = "data/corporate"):
           self.config_dir = Path(config_dir)
           self.config_dir.mkdir(parents=True, exist_ok=True)
           self._config: Optional[DeploymentConfig] = None
           self._fleet: dict[str, MachineInfo] = {}

       def create_deployment(self, config: DeploymentConfig) -> DeploymentConfig:
           """Crea una nueva configuración de deployment."""
           import uuid
           config.deployment_id = str(uuid.uuid4())
           self._config = config
           self._save_config(config)
           logger.info(f"Deployment creado: {config.company_name} ({config.deployment_id})")
           return config

       def get_config(self) -> Optional[DeploymentConfig]:
           return self._config

       def update_policy(self, policy: Policy) -> Policy:
           """Actualiza la política corporativa."""
           if not self._config:
               raise ValueError("No hay deployment configurado")
           self._config.policy = policy
           self._save_config(self._config)
           logger.info(f"Política actualizada: {policy.name}")
           return policy

       def is_package_allowed(self, package_name: str) -> bool:
           """Verifica si un paquete está permitido por la política."""
           if not self._config:
               return True  # Sin política, todo permitido
           policy = self._config.policy
           if package_name in policy.restricted_packages:
               logger.warning(f"Paquete restringido por política: {package_name}")
               return False
           return True

       def enforce_policy(self, action: str, context: dict = None) -> tuple[bool, str]:
           """Verifica si una acción cumple con la política."""
           if not self._config:
               return True, "Sin política configurada"

           policy = self._config.policy
           context = context or {}

           if action == "install_package":
               pkg_name = context.get("package_name", "")
               if pkg_name in policy.restricted_packages:
                   return False, f"Paquete '{pkg_name}' restringido por política"
               if policy.require_package_approval:
                   source = context.get("source", "unknown")
                   if source not in policy.allowed_package_sources:
                       return False, f"Fuente '{source}' no aprobada"

           elif action == "create_user":
               if not policy.enable_guest_access and context.get("role") == "guest":
                   return False, "Acceso guest deshabilitado por política"
               password = context.get("password", "")
               if policy.force_password_complexity and len(password) < policy.min_password_length:
                   return False, f"Contraseña mínima: {policy.min_password_length} caracteres"

           elif action == "disable_backup":
               if policy.enforce_backups:
                   return False, "Backups obligatorios por política corporativa"

           return True, "Acción permitida"

       def generate_iso_config(self) -> dict:
           """Genera configuración para ISO pre-configurada."""
           if not self._config:
               raise ValueError("No hay deployment configurado")

           return {
               "company_name": self._config.company_name,
               "language": self._config.default_language,
               "timezone": self._config.default_timezone,
               "ollama_model": self._config.ollama_model,
               "pre_installed_packages": self._config.pre_installed_packages,
               "policy": self._config.policy.model_dump(),
               "branding": self._config.custom_branding,
               "auto_setup": True,
               "skip_wizard_steps": ["language", "timezone"],
           }

       def register_machine(self, machine: MachineInfo) -> MachineInfo:
           """Registra una máquina en el fleet."""
           self._fleet[machine.machine_id] = machine
           logger.info(f"Máquina registrada: {machine.hostname} ({machine.machine_id})")
           return machine

       def get_fleet_status(self) -> dict:
           """Retorna estado del fleet."""
           machines = list(self._fleet.values())
           return {
               "total_machines": len(machines),
               "online": sum(1 for m in machines if m.status == "online"),
               "compliant": sum(1 for m in machines if m.policy_compliant),
               "machines": [m.model_dump() for m in machines],
           }

       def _save_config(self, config: DeploymentConfig):
           """Persiste configuración."""
           config_path = self.config_dir / "deployment.json"
           with open(config_path, 'w') as f:
               json.dump(config.model_dump(), f, indent=2)

4. Crear archivo tests/unit/deploy/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/deploy/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/deploy/test_corporate.py:

   Ruta: ~/yeyo-os/tests/unit/deploy/test_corporate.py
   Contenido:

   """Tests para Corporate Deployment — Micro-fase 7.10"""

   import tempfile
   import pytest
   from src.deploy.corporate import (
       CorporateDeployer, DeploymentConfig, Policy, MachineInfo,
   )


   class TestCorporateDeployer:
       """Tests para CorporateDeployer."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.deployer = CorporateDeployer(config_dir=self.tmp_dir)
           self.policy = Policy(
               name="Default Corp Policy",
               restricted_packages=["danger-pkg", "crypto-miner"],
               enable_guest_access=False,
           )
           self.config = DeploymentConfig(
               company_name="TestCorp",
               company_domain="testcorp.com",
               policy=self.policy,
               pre_installed_packages=["office-tools", "dev-utils"],
           )

       def test_create_deployment(self):
           result = self.deployer.create_deployment(self.config)
           assert result.deployment_id != ""
           assert result.company_name == "TestCorp"

       def test_restricted_package_blocked(self):
           self.deployer.create_deployment(self.config)
           assert self.deployer.is_package_allowed("danger-pkg") is False

       def test_allowed_package_passes(self):
           self.deployer.create_deployment(self.config)
           assert self.deployer.is_package_allowed("safe-tool") is True

       def test_enforce_policy_package_install(self):
           self.deployer.create_deployment(self.config)
           allowed, msg = self.deployer.enforce_policy(
               "install_package", {"package_name": "crypto-miner"},
           )
           assert allowed is False

       def test_enforce_policy_guest_disabled(self):
           self.deployer.create_deployment(self.config)
           allowed, msg = self.deployer.enforce_policy(
               "create_user", {"role": "guest"},
           )
           assert allowed is False

       def test_enforce_policy_backup_mandatory(self):
           self.deployer.create_deployment(self.config)
           allowed, msg = self.deployer.enforce_policy("disable_backup")
           assert allowed is False

       def test_enforce_policy_password_length(self):
           self.deployer.create_deployment(self.config)
           allowed, msg = self.deployer.enforce_policy(
               "create_user", {"password": "short"},
           )
           assert allowed is False

       def test_generate_iso_config(self):
           self.deployer.create_deployment(self.config)
           iso_config = self.deployer.generate_iso_config()
           assert iso_config["company_name"] == "TestCorp"
           assert iso_config["auto_setup"] is True
           assert "office-tools" in iso_config["pre_installed_packages"]

       def test_register_machine(self):
           machine = MachineInfo(
               machine_id="m-001", hostname="workstation-1",
               status="online",
           )
           result = self.deployer.register_machine(machine)
           assert result.machine_id == "m-001"

       def test_fleet_status(self):
           self.deployer.register_machine(MachineInfo(
               machine_id="m-001", hostname="ws-1", status="online",
           ))
           self.deployer.register_machine(MachineInfo(
               machine_id="m-002", hostname="ws-2", status="offline",
           ))
           status = self.deployer.get_fleet_status()
           assert status["total_machines"] == 2
           assert status["online"] == 1

       def test_update_policy(self):
           self.deployer.create_deployment(self.config)
           new_policy = Policy(
               name="Strict Policy",
               restricted_packages=["all-games"],
               max_gpu_per_user_pct=25,
           )
           result = self.deployer.update_policy(new_policy)
           assert result.name == "Strict Policy"

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/deploy/test_corporate.py -v

VERIFICAR:
- [ ] Archivo src/deploy/corporate.py existe con CorporateDeployer
- [ ] ISO pre-configurada con settings de empresa
- [ ] Paquetes restringidos bloqueados por política
- [ ] Guest access controlado por política
- [ ] Backups obligatorios por política
- [ ] Complejidad de contraseña enforced
- [ ] Fleet management con registro de máquinas
- [ ] ISO config generada con auto_setup y skip de pasos del wizard
- [ ] TODOS los tests pasan

NO HACER:
- No implementar LDAP real (placeholder)
- No implementar fleet dashboard real (placeholder)

GATE: Corporate deployment con políticas, ISO pre-configurada, fleet management, todos los tests pasan.
```
