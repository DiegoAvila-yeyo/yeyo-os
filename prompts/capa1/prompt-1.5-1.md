## ═══════════════════════════════════════
## MICRO-FASE 1.5 — Factory Pattern
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 1.5-1 [VSCODE] — Factory para creación de proveedores

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.5: crear el Factory que instancia los proveedores correctos según configuración. Cambiar componente = cambiar 1 variable de entorno.

CONTEXTO:
- Micro-fases 1.0-1.4 completadas: IAProvider, OllamaProvider, MemoriaProvider, Orquestador interfaces, Config system
- Factory Pattern: centraliza la creación de todos los proveedores
- Singleton: cada proveedor se crea UNA sola vez y se reutiliza
- reset() permite limpiar cache (útil para tests)
- MemoriaProvider lanza NotImplementedError (se implementa en Capa 2)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/core/factory.py:

   Ruta: ~/yeyo-os/src/core/factory.py
   Contenido:

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

2. Crear archivo tests/unit/core/test_factory.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_factory.py
   Contenido:

   """Tests para ProviderFactory — Micro-fase 1.5"""
   
   import pytest
   from unittest.mock import MagicMock, AsyncMock
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
       """Tests para obtener IAProvider."""
   
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
       """Tests para obtener MemoriaProvider."""
   
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
       """Tests para el reset del factory."""
   
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
       """Tests para gestión de configuración."""
   
       def test_set_config(self, test_config):
           ProviderFactory.set_config(test_config)
           assert ProviderFactory._config is test_config
   
       def test_set_config_resets_providers(self, test_config):
           mock = MagicMock(spec=IAProvider)
           ProviderFactory.set_ia_provider(mock)
           ProviderFactory.set_config(test_config)
           assert ProviderFactory._ia_provider is None

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_factory.py -v

VERIFICAR:
- [ ] Archivo src/core/factory.py existe con ProviderFactory
- [ ] TODOS los tests pasan (0 failed)
- [ ] get_ia_provider retorna IAProvider
- [ ] Singleton pattern: misma instancia en llamadas repetidas
- [ ] reset() limpia cache
- [ ] get_memoria_provider lanza NotImplementedError (esperado hasta Capa 2)
- [ ] set_ia_provider permite inyectar mocks
- [ ] Después de reset, nueva instancia es diferente

SI FALLA:
- Import circular: los imports se hacen dentro de los métodos (lazy import)
- Config error: asegurar que test_config fixture provee valores requeridos
- Mock error: `from unittest.mock import MagicMock`

NO HACER:
- No implementar MemoriaProvider concreto (Capa 2)
- No crear providers automáticamente al importar el módulo
- No usar global state fuera de la clase
- No cachear el config globalmente (puede cambiar en tests)

GATE: ProviderFactory retorna IAProvider singleton, memoria lanza NotImplementedError, reset funciona, todos los tests pasan.
```
