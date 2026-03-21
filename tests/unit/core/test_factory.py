"""Tests para ProviderFactory — Micro-fase 1.5"""

import pytest
from unittest.mock import MagicMock
from src.core.factory import ProviderFactory
from src.core.config import get_config
from src.ia.interfaces import IAProvider
from src.memory.interfaces import MemoriaProvider


@pytest.fixture(autouse=True)
def reset_factory():
    """Limpia el factory antes y después de cada test."""
    ProviderFactory.reset()
    ProviderFactory._config = None
    yield
    ProviderFactory.reset()
    ProviderFactory._config = None


@pytest.fixture
def test_config():
    return get_config(
        database_url="postgresql://test@localhost/test",
        redis_url="redis://localhost:6379/0",
    )


class TestProviderFactoryIA:
    def test_get_ia_provider_returns_ia_provider(self, test_config):
        provider = ProviderFactory.get_ia_provider(config=test_config)
        assert isinstance(provider, IAProvider)

    def test_ia_provider_is_singleton(self, test_config):
        p1 = ProviderFactory.get_ia_provider(config=test_config)
        p2 = ProviderFactory.get_ia_provider(config=test_config)
        assert p1 is p2

    def test_set_ia_provider_works(self):
        mock_provider = MagicMock(spec=IAProvider)
        ProviderFactory.set_ia_provider(mock_provider)
        result = ProviderFactory.get_ia_provider()
        assert result is mock_provider

    def test_ia_provider_uses_config_values(self, test_config):
        provider = ProviderFactory.get_ia_provider(config=test_config)
        assert provider.get_model_name() == test_config.ollama_model


class TestProviderFactoryMemoria:
    def test_get_memoria_raises_not_implemented(self):
        with pytest.raises(NotImplementedError) as exc_info:
            ProviderFactory.get_memoria_provider()
        assert "Capa 2" in str(exc_info.value)

    def test_set_memoria_provider_works(self):
        mock_provider = MagicMock(spec=MemoriaProvider)
        ProviderFactory.set_memoria_provider(mock_provider)
        result = ProviderFactory.get_memoria_provider()
        assert result is mock_provider


class TestProviderFactoryReset:
    def test_reset_clears_ia(self, test_config):
        ProviderFactory.get_ia_provider(config=test_config)
        assert ProviderFactory._ia_provider is not None
        ProviderFactory.reset()
        assert ProviderFactory._ia_provider is None

    def test_reset_clears_memoria(self):
        mock = MagicMock(spec=MemoriaProvider)
        ProviderFactory.set_memoria_provider(mock)
        assert ProviderFactory._memoria_provider is not None
        ProviderFactory.reset()
        assert ProviderFactory._memoria_provider is None

    def test_after_reset_new_instance_created(self, test_config):
        p1 = ProviderFactory.get_ia_provider(config=test_config)
        ProviderFactory.reset()
        p2 = ProviderFactory.get_ia_provider(config=test_config)
        assert p1 is not p2


class TestProviderFactoryConfig:
    def test_set_config(self, test_config):
        ProviderFactory.set_config(test_config)
        assert ProviderFactory._config is test_config

    def test_set_config_resets_providers(self, test_config):
        mock = MagicMock(spec=IAProvider)
        ProviderFactory.set_ia_provider(mock)
        ProviderFactory.set_config(test_config)
        assert ProviderFactory._ia_provider is None
