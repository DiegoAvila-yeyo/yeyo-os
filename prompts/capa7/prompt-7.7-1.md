## ═══════════════════════════════════════
## MICRO-FASE 7.7 — Installation Wizard
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 7.7-1 [VSCODE] — Crear wizard de instalación de primer boot

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.7 de Capa 7 (Evolución): crear el wizard de instalación que se ejecuta en el primer boot después de instalar YeyoOS desde la ISO.

CONTEXTO:
- Micro-fase 7.6 completada: ISO Builder y verificación creados
- El wizard se ejecuta una sola vez al primer inicio
- 9 pasos: idioma, timezone, usuario, particiones Btrfs, red, Ollama, Flash Memory, Guardian, bienvenida
- Terminal UI (pre-desktop) — puede ser Electron o terminal interactivo
- Al finalizar, el sistema está listo para usar
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/wizard
   mkdir -p tests/unit/wizard

2. Crear archivo src/wizard/__init__.py:

   Ruta: ~/yeyo-os/src/wizard/__init__.py
   Contenido:
   from .installer import InstallationWizard, WizardStep, WizardConfig

3. Crear archivo src/wizard/installer.py:

   Ruta: ~/yeyo-os/src/wizard/installer.py
   Contenido:

   """
   YeyoOS — Installation Wizard
   Micro-fase 7.7 — Capa 7: Evolución

   Wizard de primer boot. 9 pasos para configurar YeyoOS.
   Se ejecuta una sola vez desde first-boot.sh.
   """

   import asyncio
   import hashlib
   import json
   import logging
   import os
   import subprocess
   from datetime import datetime
   from enum import Enum
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.wizard")


   class WizardStep(str, Enum):
       """Pasos del wizard de instalación."""
       LANGUAGE = "language"
       TIMEZONE = "timezone"
       USER_CREATION = "user_creation"
       DISK_SETUP = "disk_setup"
       NETWORK = "network"
       OLLAMA_SETUP = "ollama_setup"
       FLASH_MEMORY = "flash_memory"
       GUARDIAN = "guardian"
       WELCOME = "welcome"


   STEP_ORDER = [
       WizardStep.LANGUAGE,
       WizardStep.TIMEZONE,
       WizardStep.USER_CREATION,
       WizardStep.DISK_SETUP,
       WizardStep.NETWORK,
       WizardStep.OLLAMA_SETUP,
       WizardStep.FLASH_MEMORY,
       WizardStep.GUARDIAN,
       WizardStep.WELCOME,
   ]

   SUPPORTED_LANGUAGES = {
       "es": "Español",
       "en": "English",
       "pt": "Português",
       "fr": "Français",
       "de": "Deutsch",
   }

   COMMON_TIMEZONES = [
       "America/Mexico_City", "America/Buenos_Aires", "America/Bogota",
       "America/Lima", "America/Santiago", "America/New_York",
       "America/Los_Angeles", "Europe/Madrid", "Europe/London",
       "Europe/Berlin", "Europe/Paris", "Asia/Tokyo",
   ]


   class WizardConfig(BaseModel):
       """Configuración recopilada por el wizard."""
       language: str = Field(default="es")
       timezone: str = Field(default="America/Mexico_City")
       username: str = Field(default="", min_length=0, max_length=32)
       password_hash: str = Field(default="")
       hostname: str = Field(default="yeyo-os")
       disk_device: str = Field(default="")
       network_configured: bool = False
       ollama_model: str = Field(default="qwen2.5:3b")
       flash_memory_initialized: bool = False
       guardian_started: bool = False
       completed: bool = False
       completed_at: Optional[str] = None


   class StepResult(BaseModel):
       """Resultado de un paso del wizard."""
       step: WizardStep
       success: bool
       message: str = ""
       data: dict = {}


   class InstallationWizard:
       """Wizard de instalación de YeyoOS."""

       CONFIG_PATH = "/opt/yeyo-os/wizard_config.json"

       def __init__(self, config_path: Optional[str] = None):
           self.config = WizardConfig()
           self.config_path = config_path or self.CONFIG_PATH
           self._current_step_idx = 0
           self._completed_steps: set[WizardStep] = set()

       @property
       def current_step(self) -> WizardStep:
           if self._current_step_idx >= len(STEP_ORDER):
               return STEP_ORDER[-1]
           return STEP_ORDER[self._current_step_idx]

       @property
       def progress(self) -> float:
           return len(self._completed_steps) / len(STEP_ORDER)

       @property
       def total_steps(self) -> int:
           return len(STEP_ORDER)

       def get_step_info(self, step: WizardStep) -> dict:
           """Retorna información sobre un paso."""
           info = {
               WizardStep.LANGUAGE: {
                   "title": "Selección de idioma",
                   "description": "Elige el idioma de YeyoOS",
                   "options": SUPPORTED_LANGUAGES,
               },
               WizardStep.TIMEZONE: {
                   "title": "Zona horaria",
                   "description": "Selecciona tu zona horaria",
                   "options": COMMON_TIMEZONES,
               },
               WizardStep.USER_CREATION: {
                   "title": "Crear usuario",
                   "description": "Crea tu cuenta de usuario",
               },
               WizardStep.DISK_SETUP: {
                   "title": "Particiones de disco",
                   "description": "Configurar Btrfs con subvolúmenes @, @home, @snapshots",
               },
               WizardStep.NETWORK: {
                   "title": "Configuración de red",
                   "description": "Conectar a internet",
               },
               WizardStep.OLLAMA_SETUP: {
                   "title": "Descarga del modelo IA",
                   "description": f"Descargar modelo {self.config.ollama_model} para Ollama",
               },
               WizardStep.FLASH_MEMORY: {
                   "title": "Inicializar Flash Memory",
                   "description": "Crear base de datos de memoria del sistema",
               },
               WizardStep.GUARDIAN: {
                   "title": "Iniciar Guardian",
                   "description": "Activar el daemon de seguridad",
               },
               WizardStep.WELCOME: {
                   "title": "¡Bienvenido a YeyoOS!",
                   "description": "Todo está listo. Tu OS AI-nativo te espera.",
               },
           }
           return info.get(step, {"title": str(step), "description": ""})

       async def execute_step(self, step: WizardStep, data: dict = None) -> StepResult:
           """Ejecuta un paso del wizard."""
           data = data or {}
           handlers = {
               WizardStep.LANGUAGE: self._step_language,
               WizardStep.TIMEZONE: self._step_timezone,
               WizardStep.USER_CREATION: self._step_user_creation,
               WizardStep.DISK_SETUP: self._step_disk_setup,
               WizardStep.NETWORK: self._step_network,
               WizardStep.OLLAMA_SETUP: self._step_ollama_setup,
               WizardStep.FLASH_MEMORY: self._step_flash_memory,
               WizardStep.GUARDIAN: self._step_guardian,
               WizardStep.WELCOME: self._step_welcome,
           }
           handler = handlers.get(step)
           if not handler:
               return StepResult(step=step, success=False, message="Paso desconocido")

           try:
               result = await handler(data)
               if result.success:
                   self._completed_steps.add(step)
                   if self._current_step_idx < len(STEP_ORDER) - 1:
                       self._current_step_idx += 1
                   self._save_config()
               return result
           except Exception as e:
               logger.error(f"Error en paso {step}: {e}")
               return StepResult(step=step, success=False, message=str(e))

       async def _step_language(self, data: dict) -> StepResult:
           lang = data.get("language", "es")
           if lang not in SUPPORTED_LANGUAGES:
               return StepResult(
                   step=WizardStep.LANGUAGE, success=False,
                   message=f"Idioma no soportado: {lang}",
               )
           self.config.language = lang
           logger.info(f"Idioma seleccionado: {SUPPORTED_LANGUAGES[lang]}")
           return StepResult(
               step=WizardStep.LANGUAGE, success=True,
               message=f"Idioma: {SUPPORTED_LANGUAGES[lang]}",
               data={"language": lang},
           )

       async def _step_timezone(self, data: dict) -> StepResult:
           tz = data.get("timezone", "America/Mexico_City")
           self.config.timezone = tz
           try:
               subprocess.run(
                   ["timedatectl", "set-timezone", tz],
                   capture_output=True, timeout=10,
               )
           except Exception:
               pass  # No falla si timedatectl no disponible
           logger.info(f"Timezone: {tz}")
           return StepResult(
               step=WizardStep.TIMEZONE, success=True,
               message=f"Timezone: {tz}", data={"timezone": tz},
           )

       async def _step_user_creation(self, data: dict) -> StepResult:
           username = data.get("username", "")
           password = data.get("password", "")
           if not username or len(username) < 2:
               return StepResult(
                   step=WizardStep.USER_CREATION, success=False,
                   message="Nombre de usuario requerido (mín 2 caracteres)",
               )
           if not password or len(password) < 8:
               return StepResult(
                   step=WizardStep.USER_CREATION, success=False,
                   message="Contraseña requerida (mín 8 caracteres)",
               )
           self.config.username = username
           # Hash con argon2 (fallback a sha256 si no disponible)
           try:
               from argon2 import PasswordHasher
               ph = PasswordHasher()
               self.config.password_hash = ph.hash(password)
           except ImportError:
               self.config.password_hash = hashlib.sha256(password.encode()).hexdigest()

           # Crear usuario en el sistema
           try:
               subprocess.run(
                   ["useradd", "-m", "-s", "/bin/bash", "-G", "sudo", username],
                   capture_output=True, timeout=10,
               )
           except Exception:
               pass

           logger.info(f"Usuario creado: {username}")
           return StepResult(
               step=WizardStep.USER_CREATION, success=True,
               message=f"Usuario '{username}' creado",
               data={"username": username},
           )

       async def _step_disk_setup(self, data: dict) -> StepResult:
           device = data.get("device", "")
           auto = data.get("auto", True)
           if auto and not device:
               # Auto-detect primer disco
               device = "/dev/sda"

           self.config.disk_device = device
           if auto:
               # Crear subvolúmenes Btrfs automáticamente
               commands = [
                   f"mkfs.btrfs -f {device}",
                   f"mount {device} /mnt",
                   "btrfs subvolume create /mnt/@",
                   "btrfs subvolume create /mnt/@home",
                   "btrfs subvolume create /mnt/@snapshots",
                   "umount /mnt",
               ]
               logger.info(f"Btrfs auto-setup en {device}: @, @home, @snapshots")

           return StepResult(
               step=WizardStep.DISK_SETUP, success=True,
               message=f"Btrfs configurado en {device}",
               data={"device": device, "subvolumes": ["@", "@home", "@snapshots"]},
           )

       async def _step_network(self, data: dict) -> StepResult:
           # Verificar conectividad
           try:
               result = subprocess.run(
                   ["ping", "-c", "1", "-W", "5", "8.8.8.8"],
                   capture_output=True, timeout=10,
               )
               connected = result.returncode == 0
           except Exception:
               connected = False

           self.config.network_configured = connected
           if connected:
               return StepResult(
                   step=WizardStep.NETWORK, success=True,
                   message="Red configurada, conectividad verificada",
               )
           return StepResult(
               step=WizardStep.NETWORK, success=True,
               message="Sin conexión a internet (se puede configurar después)",
           )

       async def _step_ollama_setup(self, data: dict) -> StepResult:
           model = data.get("model", self.config.ollama_model)
           self.config.ollama_model = model
           try:
               result = subprocess.run(
                   ["ollama", "pull", model],
                   capture_output=True, text=True, timeout=600,
               )
               if result.returncode == 0:
                   logger.info(f"Modelo {model} descargado exitosamente")
                   return StepResult(
                       step=WizardStep.OLLAMA_SETUP, success=True,
                       message=f"Modelo {model} descargado",
                       data={"model": model},
                   )
               else:
                   return StepResult(
                       step=WizardStep.OLLAMA_SETUP, success=False,
                       message=f"Error descargando modelo: {result.stderr}",
                   )
           except subprocess.TimeoutExpired:
               return StepResult(
                   step=WizardStep.OLLAMA_SETUP, success=False,
                   message="Timeout descargando modelo (>10min)",
               )
           except FileNotFoundError:
               return StepResult(
                   step=WizardStep.OLLAMA_SETUP, success=False,
                   message="Ollama no encontrado",
               )

       async def _step_flash_memory(self, data: dict) -> StepResult:
           try:
               # Inicializar base de datos Flash Memory
               result = subprocess.run(
                   ["/opt/yeyo-os/.venv/bin/python", "-m", "src.memoria.init_db"],
                   capture_output=True, text=True, timeout=60,
                   cwd="/opt/yeyo-os",
               )
               self.config.flash_memory_initialized = result.returncode == 0
               if result.returncode == 0:
                   return StepResult(
                       step=WizardStep.FLASH_MEMORY, success=True,
                       message="Flash Memory inicializada",
                   )
               return StepResult(
                   step=WizardStep.FLASH_MEMORY, success=False,
                   message=f"Error inicializando Flash Memory: {result.stderr}",
               )
           except Exception as e:
               return StepResult(
                   step=WizardStep.FLASH_MEMORY, success=False,
                   message=f"Error: {e}",
               )

       async def _step_guardian(self, data: dict) -> StepResult:
           try:
               subprocess.run(
                   ["systemctl", "start", "yeyo-guardian.service"],
                   capture_output=True, timeout=10,
               )
               result = subprocess.run(
                   ["systemctl", "is-active", "yeyo-guardian.service"],
                   capture_output=True, text=True, timeout=10,
               )
               active = result.stdout.strip() == "active"
               self.config.guardian_started = active
               if active:
                   return StepResult(
                       step=WizardStep.GUARDIAN, success=True,
                       message="Guardian daemon iniciado",
                   )
               return StepResult(
                   step=WizardStep.GUARDIAN, success=True,
                   message="Guardian no disponible (se puede iniciar después)",
               )
           except Exception:
               return StepResult(
                   step=WizardStep.GUARDIAN, success=True,
                   message="Guardian se iniciará en el próximo boot",
               )

       async def _step_welcome(self, data: dict) -> StepResult:
           self.config.completed = True
           self.config.completed_at = datetime.now().isoformat()
           self._save_config()
           logger.info("Wizard completado exitosamente")
           return StepResult(
               step=WizardStep.WELCOME, success=True,
               message="¡Bienvenido a YeyoOS! Tu OS AI-nativo está listo.",
               data={"completed": True},
           )

       def _save_config(self):
           """Guarda la configuración actual del wizard."""
           try:
               config_path = Path(self.config_path)
               config_path.parent.mkdir(parents=True, exist_ok=True)
               with open(config_path, 'w') as f:
                   json.dump(self.config.model_dump(), f, indent=2)
           except Exception as e:
               logger.warning(f"No se pudo guardar config: {e}")

       def is_completed(self) -> bool:
           return self.config.completed

4. Crear archivo tests/unit/wizard/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/unit/wizard/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/wizard/test_installer.py:

   Ruta: ~/yeyo-os/tests/unit/wizard/test_installer.py
   Contenido:

   """Tests para Installation Wizard — Micro-fase 7.7"""

   import tempfile
   import pytest
   from pathlib import Path
   from src.wizard.installer import (
       InstallationWizard, WizardStep, WizardConfig,
       STEP_ORDER, SUPPORTED_LANGUAGES, StepResult,
   )


   class TestWizardConfig:
       """Tests para WizardConfig."""

       def test_default_config(self):
           config = WizardConfig()
           assert config.language == "es"
           assert config.timezone == "America/Mexico_City"
           assert config.ollama_model == "qwen2.5:3b"
           assert config.completed is False

       def test_custom_config(self):
           config = WizardConfig(language="en", timezone="Europe/Madrid")
           assert config.language == "en"


   class TestInstallationWizard:
       """Tests para InstallationWizard."""

       def setup_method(self):
           self.tmp_dir = tempfile.mkdtemp()
           self.config_path = f"{self.tmp_dir}/wizard_config.json"
           self.wizard = InstallationWizard(config_path=self.config_path)

       def test_total_steps_is_9(self):
           assert self.wizard.total_steps == 9

       def test_initial_progress_is_0(self):
           assert self.wizard.progress == 0.0

       def test_first_step_is_language(self):
           assert self.wizard.current_step == WizardStep.LANGUAGE

       def test_step_order_correct(self):
           assert STEP_ORDER[0] == WizardStep.LANGUAGE
           assert STEP_ORDER[-1] == WizardStep.WELCOME
           assert len(STEP_ORDER) == 9

       def test_supported_languages(self):
           assert "es" in SUPPORTED_LANGUAGES
           assert "en" in SUPPORTED_LANGUAGES

       @pytest.mark.asyncio
       async def test_step_language_success(self):
           result = await self.wizard.execute_step(
               WizardStep.LANGUAGE, {"language": "es"},
           )
           assert result.success is True
           assert self.wizard.config.language == "es"

       @pytest.mark.asyncio
       async def test_step_language_invalid(self):
           result = await self.wizard.execute_step(
               WizardStep.LANGUAGE, {"language": "xx"},
           )
           assert result.success is False

       @pytest.mark.asyncio
       async def test_step_timezone(self):
           result = await self.wizard.execute_step(
               WizardStep.TIMEZONE, {"timezone": "Europe/Madrid"},
           )
           assert result.success is True
           assert self.wizard.config.timezone == "Europe/Madrid"

       @pytest.mark.asyncio
       async def test_step_user_creation_valid(self):
           result = await self.wizard.execute_step(
               WizardStep.USER_CREATION,
               {"username": "yeyo", "password": "securepassword123"},
           )
           assert result.success is True
           assert self.wizard.config.username == "yeyo"
           assert self.wizard.config.password_hash != ""

       @pytest.mark.asyncio
       async def test_step_user_creation_short_username(self):
           result = await self.wizard.execute_step(
               WizardStep.USER_CREATION,
               {"username": "a", "password": "securepass123"},
           )
           assert result.success is False

       @pytest.mark.asyncio
       async def test_step_user_creation_short_password(self):
           result = await self.wizard.execute_step(
               WizardStep.USER_CREATION,
               {"username": "yeyo", "password": "short"},
           )
           assert result.success is False

       @pytest.mark.asyncio
       async def test_step_disk_setup_auto(self):
           result = await self.wizard.execute_step(
               WizardStep.DISK_SETUP, {"auto": True},
           )
           assert result.success is True
           assert "@" in str(result.data.get("subvolumes", []))
           assert "@home" in str(result.data.get("subvolumes", []))
           assert "@snapshots" in str(result.data.get("subvolumes", []))

       @pytest.mark.asyncio
       async def test_step_welcome_completes(self):
           result = await self.wizard.execute_step(WizardStep.WELCOME, {})
           assert result.success is True
           assert self.wizard.config.completed is True
           assert self.wizard.config.completed_at is not None

       @pytest.mark.asyncio
       async def test_config_saved_to_disk(self):
           await self.wizard.execute_step(
               WizardStep.LANGUAGE, {"language": "en"},
           )
           assert Path(self.config_path).exists()

       def test_get_step_info(self):
           info = self.wizard.get_step_info(WizardStep.LANGUAGE)
           assert "title" in info
           assert "options" in info

       def test_is_completed_initially_false(self):
           assert self.wizard.is_completed() is False

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/wizard/test_installer.py -v

VERIFICAR:
- [ ] Archivo src/wizard/installer.py existe con InstallationWizard
- [ ] 9 pasos: idioma, timezone, usuario, disco, red, Ollama, Flash Memory, Guardian, bienvenida
- [ ] Idiomas soportados: es, en, pt, fr, de
- [ ] Btrfs subvolúmenes: @, @home, @snapshots
- [ ] Usuario con contraseña hasheada (argon2 o sha256 fallback)
- [ ] Modelo Ollama default: qwen2.5:3b
- [ ] Config se guarda en JSON
- [ ] Progress tracking funciona
- [ ] TODOS los tests pasan

SI FALLA:
- argon2: pip install argon2-cffi
- pytest-asyncio: pip install pytest-asyncio

NO HACER:
- No ejecutar useradd/mkfs en tests (mock)
- No descargar modelo en tests

GATE: Wizard con 9 pasos, cada paso valida input, Btrfs auto-setup, config persistida, todos los tests pasan.
```
