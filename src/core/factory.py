"""
YeyoOS — Provider Factory
Micro-fase 1.5 — Capa 1: Esqueleto

Factory centralizado para crear proveedores.
Patrón Singleton: cada proveedor se instancia una sola vez.
Cambiar implementación = cambiar 1 env var (o 1 línea aquí).
"""

from src.ia.interfaces import IAProvider
from src.memory.interfaces import MemoriaProvider
from src.core.config import YeyoConfig, get_config


class ProviderFactory:
    """Factory centralizado para proveedores de YeyoOS."""

    _ia_provider: IAProvider | None = None
    _memoria_provider: MemoriaProvider | None = None
    _config: YeyoConfig | None = None

    @classmethod
    def get_config(cls) -> YeyoConfig:
        """Obtiene o crea la configuración."""
        if cls._config is None:
            cls._config = get_config()
        return cls._config

    @classmethod
    def set_config(cls, config: YeyoConfig) -> None:
        """Establece configuración manualmente (útil para tests)."""
        cls._config = config
        cls.reset()

    @classmethod
    def get_ia_provider(cls, config: YeyoConfig | None = None) -> IAProvider:
        """
        Obtiene el proveedor de IA (singleton).
        Por ahora solo Ollama, pero preparado para más.
        """
        if cls._ia_provider is None:
            cfg = config or cls.get_config()
            from src.ia.ollama_provider import OllamaProvider

            cls._ia_provider = OllamaProvider(
                host=cfg.ollama_host,
                model=cfg.ollama_model,
                embedding_model=cfg.ollama_embedding_model,
                timeout=cfg.ollama_timeout,
            )
        return cls._ia_provider

    @classmethod
    def get_memoria_provider(cls) -> MemoriaProvider:
        """
        Obtiene el proveedor de memoria (singleton).
        NOTA: La implementación concreta viene en Capa 2.
        """
        if cls._memoria_provider is None:
            raise NotImplementedError(
                "MemoriaProvider concreto se implementa en Capa 2. "
                "Usa un mock para testing."
            )
        return cls._memoria_provider

    @classmethod
    def set_ia_provider(cls, provider: IAProvider) -> None:
        """Establece proveedor de IA manualmente (útil para tests/mocks)."""
        cls._ia_provider = provider

    @classmethod
    def set_memoria_provider(cls, provider: MemoriaProvider) -> None:
        """Establece proveedor de memoria manualmente (útil para tests/mocks)."""
        cls._memoria_provider = provider

    @classmethod
    def reset(cls) -> None:
        """Limpia todos los proveedores cacheados. Útil para tests."""
        cls._ia_provider = None
        cls._memoria_provider = None
