## ═══════════════════════════════════════
## MICRO-FASE 1.4 — Config System
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.4-1 [VSCODE] — Sistema de configuración centralizado

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.4: crear el sistema de configuración centralizado con validación, defaults y override en runtime.

CONTEXTO:
- Micro-fases 1.0-1.3 completadas: interfaces IAProvider, MemoriaProvider, Orquestador definidas
- Config centralizado: UN solo lugar para toda la configuración
- Lee de .env con pydantic-settings, valida tipos, tiene defaults sensatos
- Hardware: GTX 1060 3GB VRAM (3072 MB total), compositor reserva 200 MB
- Token budget: system(300) + memories(1000) + history(1500) + input(500) + response(700) = 4000
- Las micro-fases siguientes (Factory, API, etc.) dependen de este config

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Instalar dependencia:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install pydantic-settings

2. Crear archivo src/core/config.py:

   Ruta: ~/yeyo-os/src/core/config.py
   Contenido:

   """
   YeyoOS — Sistema de Configuración Centralizado
   Micro-fase 1.4 — Capa 1: Esqueleto
   
   Toda la configuración de YeyoOS en un solo lugar.
   Lee de variables de entorno y archivo .env.
   Valida tipos y aplica defaults sensatos.
   """
   
   from pydantic_settings import BaseSettings
   from pydantic import Field, field_validator
   
   
   class YeyoConfig(BaseSettings):
       """Configuración centralizada de YeyoOS."""
   
       # === Database ===
       database_url: str = Field(
           ...,
           description="URL de conexión a PostgreSQL principal",
       )
       test_database_url: str = Field(
           default="",
           description="URL de conexión a PostgreSQL de test",
       )
   
       # === Redis ===
       redis_url: str = Field(
           ...,
           description="URL de conexión a Redis",
       )
   
       # === Ollama ===
       ollama_host: str = Field(
           default="http://localhost:11434",
           description="Host de Ollama API",
       )
       ollama_model: str = Field(
           default="qwen2.5:3b",
           description="Modelo de Ollama por defecto",
       )
       ollama_embedding_model: str = Field(
           default="nomic-embed-text",
           description="Modelo de embeddings",
       )
       ollama_timeout: float = Field(
           default=120.0,
           description="Timeout en segundos para llamadas a Ollama",
           ge=1.0,
       )
   
       # === GPU ===
       gpu_vram_total_mb: int = Field(
           default=3072,
           description="VRAM total de la GPU en MB (GTX 1060 3GB)",
           ge=0,
       )
       gpu_compositor_reserved_mb: int = Field(
           default=200,
           description="VRAM reservada para el compositor en MB",
           ge=0,
       )
   
       # === Token Budget ===
       token_budget_system: int = Field(default=300, ge=0)
       token_budget_memories: int = Field(default=1000, ge=0)
       token_budget_history: int = Field(default=1500, ge=0)
       token_budget_input: int = Field(default=500, ge=0)
       token_budget_response: int = Field(default=700, ge=0)
   
       # === API ===
       api_host: str = Field(default="0.0.0.0")
       api_port: int = Field(default=8000, ge=1, le=65535)
       cors_origins: list[str] = Field(
           default=["http://localhost:3000"],
           description="Orígenes permitidos para CORS",
       )
       websocket_max_connections: int = Field(default=50, ge=1)
   
       # === Security & Environment ===
       env: str = Field(
           default="development",
           description="Entorno: development | staging | production",
       )
       debug: bool = Field(default=False)
       log_level: str = Field(
           default="INFO",
           description="Nivel de logging: DEBUG | INFO | WARNING | ERROR",
       )
       log_dir: str = Field(default="/var/log/yeyo")
   
       # === Version ===
       version: str = Field(default="0.1.0")
   
       @field_validator("env")
       @classmethod
       def validate_env(cls, v: str) -> str:
           allowed = {"development", "staging", "production"}
           if v not in allowed:
               raise ValueError(f"env debe ser uno de: {allowed}")
           return v
   
       @field_validator("log_level")
       @classmethod
       def validate_log_level(cls, v: str) -> str:
           allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
           v_upper = v.upper()
           if v_upper not in allowed:
               raise ValueError(f"log_level debe ser uno de: {allowed}")
           return v_upper
   
       @property
       def token_budget_total(self) -> int:
           """Suma total del token budget."""
           return (
               self.token_budget_system
               + self.token_budget_memories
               + self.token_budget_history
               + self.token_budget_input
               + self.token_budget_response
           )
   
       @property
       def gpu_available_vram_mb(self) -> int:
           """VRAM disponible después de reservar para el compositor."""
           return self.gpu_vram_total_mb - self.gpu_compositor_reserved_mb
   
       model_config = {
           "env_file": ".env",
           "env_file_encoding": "utf-8",
           "extra": "ignore",
       }
   
   
   def get_config(**overrides) -> YeyoConfig:
       """
       Crea instancia de configuración.
       Permite overrides para testing.
       """
       return YeyoConfig(**overrides)

3. Crear archivo tests/unit/core/test_config.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_config.py
   Contenido:

   """Tests para Config System — Micro-fase 1.4"""
   
   import os
   import pytest
   from pydantic import ValidationError
   from src.core.config import YeyoConfig, get_config
   
   
   @pytest.fixture
   def minimal_env(monkeypatch):
       """Configura variables de entorno mínimas requeridas."""
       monkeypatch.setenv("DATABASE_URL", "postgresql://yeyo:yeyo_dev_2026@localhost:5432/yeyo_db")
       monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
   
   
   @pytest.fixture
   def config(minimal_env):
       """Crea config con valores mínimos."""
       return get_config(
           database_url="postgresql://yeyo:yeyo_dev_2026@localhost:5432/yeyo_db",
           redis_url="redis://localhost:6379/0",
       )
   
   
   class TestYeyoConfigDefaults:
       """Tests para valores por defecto."""
   
       def test_ollama_host_default(self, config):
           assert config.ollama_host == "http://localhost:11434"
   
       def test_ollama_model_default(self, config):
           assert config.ollama_model == "qwen2.5:3b"
   
       def test_gpu_vram_default(self, config):
           assert config.gpu_vram_total_mb == 3072
   
       def test_gpu_compositor_reserved_default(self, config):
           assert config.gpu_compositor_reserved_mb == 200
   
       def test_env_default(self, config):
           assert config.env == "development"
   
       def test_debug_default(self, config):
           assert config.debug is False
   
       def test_log_level_default(self, config):
           assert config.log_level == "INFO"
   
       def test_api_port_default(self, config):
           assert config.api_port == 8000
   
       def test_version_default(self, config):
           assert config.version == "0.1.0"
   
       def test_websocket_max_connections_default(self, config):
           assert config.websocket_max_connections == 50
   
   
   class TestYeyoConfigTokenBudget:
       """Tests para token budget."""
   
       def test_token_budget_system(self, config):
           assert config.token_budget_system == 300
   
       def test_token_budget_memories(self, config):
           assert config.token_budget_memories == 1000
   
       def test_token_budget_history(self, config):
           assert config.token_budget_history == 1500
   
       def test_token_budget_input(self, config):
           assert config.token_budget_input == 500
   
       def test_token_budget_response(self, config):
           assert config.token_budget_response == 700
   
       def test_token_budget_total_is_4000(self, config):
           assert config.token_budget_total == 4000
   
   
   class TestYeyoConfigGPU:
       """Tests para configuración de GPU."""
   
       def test_available_vram(self, config):
           assert config.gpu_available_vram_mb == 2872  # 3072 - 200
   
       def test_custom_vram(self, minimal_env):
           c = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
               gpu_vram_total_mb=6144,
               gpu_compositor_reserved_mb=300,
           )
           assert c.gpu_available_vram_mb == 5844
   
   
   class TestYeyoConfigValidation:
       """Tests para validación."""
   
       def test_missing_database_url_raises(self, monkeypatch):
           monkeypatch.delenv("DATABASE_URL", raising=False)
           monkeypatch.delenv("REDIS_URL", raising=False)
           with pytest.raises(ValidationError):
               YeyoConfig(redis_url="redis://localhost:6379/0")
   
       def test_missing_redis_url_raises(self, monkeypatch):
           monkeypatch.delenv("DATABASE_URL", raising=False)
           monkeypatch.delenv("REDIS_URL", raising=False)
           with pytest.raises(ValidationError):
               YeyoConfig(database_url="postgresql://test@localhost/test")
   
       def test_invalid_env_raises(self, minimal_env):
           with pytest.raises(ValidationError):
               get_config(
                   database_url="postgresql://test@localhost/test",
                   redis_url="redis://localhost:6379/0",
                   env="invalid",
               )
   
       def test_invalid_log_level_raises(self, minimal_env):
           with pytest.raises(ValidationError):
               get_config(
                   database_url="postgresql://test@localhost/test",
                   redis_url="redis://localhost:6379/0",
                   log_level="INVALID",
               )
   
       def test_negative_vram_raises(self, minimal_env):
           with pytest.raises(ValidationError):
               get_config(
                   database_url="postgresql://test@localhost/test",
                   redis_url="redis://localhost:6379/0",
                   gpu_vram_total_mb=-1,
               )
   
       def test_cors_origins_default(self, config):
           assert config.cors_origins == ["http://localhost:3000"]
   
   
   class TestYeyoConfigOverride:
       """Tests para override en runtime."""
   
       def test_override_model(self, minimal_env):
           c = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
               ollama_model="llama3:8b",
           )
           assert c.ollama_model == "llama3:8b"
   
       def test_override_debug(self, minimal_env):
           c = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
               debug=True,
           )
           assert c.debug is True
   
       def test_override_env(self, minimal_env):
           c = get_config(
               database_url="postgresql://test@localhost/test",
               redis_url="redis://localhost:6379/0",
               env="production",
           )
           assert c.env == "production"

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_config.py -v

VERIFICAR:
- [ ] Archivo src/core/config.py existe con YeyoConfig y get_config
- [ ] TODOS los tests pasan (0 failed)
- [ ] Token budget total == 4000 por defecto
- [ ] GPU available VRAM == 2872 (3072 - 200)
- [ ] Missing DATABASE_URL lanza ValidationError
- [ ] Missing REDIS_URL lanza ValidationError
- [ ] Override en runtime funciona
- [ ] CORS origins default es ["http://localhost:3000"]

SI FALLA:
- pydantic-settings no instalado: `pip install pydantic-settings`
- .env no existe: los tests usan monkeypatch, no necesitan .env real
- Import error: verificar que existe src/core/__init__.py

NO HACER:
- No crear un singleton global `config = YeyoConfig()` porque falla sin .env
- No hardcodear passwords en el config
- No agregar secretos al código
- No validar conexiones reales a BD en el config (eso es health_check)

GATE: YeyoConfig valida tipos y defaults correctamente, token budget suma 4000, GPU VRAM calculado bien, todos los tests pasan.
```
