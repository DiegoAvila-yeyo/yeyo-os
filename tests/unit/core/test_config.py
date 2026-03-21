"""Tests para Config System — Micro-fase 1.4"""

import pytest
from pydantic import ValidationError
from src.core.config import YeyoConfig, get_config


@pytest.fixture
def minimal_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://yeyo:yeyo_dev_2026@localhost:5432/yeyo_db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture
def config(minimal_env):
    return get_config(
        database_url="postgresql://yeyo:yeyo_dev_2026@localhost:5432/yeyo_db",
        redis_url="redis://localhost:6379/0",
    )


class TestYeyoConfigDefaults:
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
    def test_missing_database_url_raises(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(ValidationError):
            YeyoConfig(_env_file=None, redis_url="redis://localhost:6379/0")

    def test_missing_redis_url_raises(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        with pytest.raises(ValidationError):
            YeyoConfig(_env_file=None, database_url="postgresql://test@localhost/test")

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
