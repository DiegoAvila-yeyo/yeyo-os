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
    database_url: str = Field(..., description="URL de conexión a PostgreSQL principal")
    test_database_url: str = Field(default="", description="URL de conexión a PostgreSQL de test")

    # === Redis ===
    redis_url: str = Field(..., description="URL de conexión a Redis")

    # === Ollama ===
    ollama_host: str = Field(default="http://localhost:11434", description="Host de Ollama API")
    ollama_model: str = Field(default="qwen2.5:3b", description="Modelo de Ollama por defecto")
    ollama_embedding_model: str = Field(default="qwen2.5-coder:7b", description="Modelo de embeddings")
    ollama_timeout: float = Field(default=120.0, description="Timeout en segundos para llamadas a Ollama", ge=1.0)

    # === GPU ===
    gpu_vram_total_mb: int = Field(default=3072, description="VRAM total de la GPU en MB (GTX 1060 3GB)", ge=0)
    gpu_compositor_reserved_mb: int = Field(default=200, description="VRAM reservada para el compositor en MB", ge=0)

    # === Token Budget ===
    token_budget_system: int = Field(default=300, ge=0)
    token_budget_memories: int = Field(default=1000, ge=0)
    token_budget_history: int = Field(default=1500, ge=0)
    token_budget_input: int = Field(default=500, ge=0)
    token_budget_response: int = Field(default=700, ge=0)

    # === API ===
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(default=["http://localhost:3000"], description="Orígenes permitidos para CORS")
    websocket_max_connections: int = Field(default=50, ge=1)

    # === Security & Environment ===
    env: str = Field(default="development", description="Entorno: development | staging | production")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO", description="Nivel de logging: DEBUG | INFO | WARNING | ERROR")
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
