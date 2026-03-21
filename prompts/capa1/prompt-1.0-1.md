## ═══════════════════════════════════════
## MICRO-FASE 1.0 — IAProvider Interface
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 1.0-1 [VSCODE] — Crear interfaz abstracta IAProvider

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.0 de Capa 1 (Esqueleto): crear la interfaz abstracta del proveedor de IA.

CONTEXTO:
- Capa 0 completada: PostgreSQL 16, Redis 7, Ollama, Python 3.11, todo funcionando
- Arquitectura hexagonal: las interfaces son PUERTOS que permiten intercambiar implementaciones
- Esta interfaz es el puerto que permite usar Ollama hoy y cualquier otro modelo mañana
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu
- Token budget total: 4000 tokens (system:300 + memories:1000 + history:1500 + input:500 + response:700)

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/ia
   mkdir -p tests/unit/ia

2. Crear archivo src/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/src/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo src/ia/__init__.py:

   Ruta: ~/yeyo-os/src/ia/__init__.py
   Contenido:
   from .interfaces import IAProvider, IAMessage, IAResponse

4. Crear archivo src/ia/interfaces.py:

   Ruta: ~/yeyo-os/src/ia/interfaces.py
   Contenido:

   """
   YeyoOS — IAProvider Interface (Puerto Hexagonal)
   Micro-fase 1.0 — Capa 1: Esqueleto
   
   Interfaz abstracta para proveedores de IA.
   Permite intercambiar Ollama por cualquier otro proveedor
   sin modificar el resto del sistema.
   """
   
   from abc import ABC, abstractmethod
   from typing import AsyncIterator
   from pydantic import BaseModel, Field
   
   
   class IAMessage(BaseModel):
       """Mensaje en una conversación con la IA."""
       role: str = Field(..., pattern="^(system|user|assistant)$")
       content: str = Field(..., min_length=1)
   
   
   class IAResponse(BaseModel):
       """Respuesta estructurada de la IA."""
       content: str
       model: str
       tokens_used: int = Field(..., ge=0)
       latency_ms: float = Field(..., ge=0.0)
   
   
   class IAProvider(ABC):
       """Puerto hexagonal para proveedores de IA."""
   
       @abstractmethod
       async def generate(
           self,
           prompt: str,
           system: str = "",
           temperature: float = 0.7,
       ) -> IAResponse:
           """Genera una respuesta a partir de un prompt simple."""
           ...
   
       @abstractmethod
       async def chat(
           self,
           messages: list[IAMessage],
           temperature: float = 0.7,
       ) -> IAResponse:
           """Genera respuesta a partir de historial de mensajes."""
           ...
   
       @abstractmethod
       async def chat_stream(
           self,
           messages: list[IAMessage],
           temperature: float = 0.7,
       ) -> AsyncIterator[str]:
           """Genera respuesta en streaming, yield de chunks de texto."""
           ...
   
       @abstractmethod
       async def get_embedding(self, text: str) -> list[float]:
           """Genera embedding vectorial para búsqueda semántica."""
           ...
   
       @abstractmethod
       async def health_check(self) -> bool:
           """Verifica que el proveedor de IA está disponible."""
           ...
   
       @abstractmethod
       def get_model_name(self) -> str:
           """Retorna el nombre del modelo en uso."""
           ...
   
       @abstractmethod
       def get_max_tokens(self) -> int:
           """Retorna el máximo de tokens soportado."""
           ...

5. Crear archivo tests/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/__init__.py
   Contenido: (archivo vacío)

6. Crear archivo tests/unit/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/unit/__init__.py
   Contenido: (archivo vacío)

7. Crear archivo tests/unit/ia/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/unit/ia/__init__.py
   Contenido: (archivo vacío)

8. Crear archivo tests/unit/ia/test_ia_interfaces.py:

   Ruta: ~/yeyo-os/tests/unit/ia/test_ia_interfaces.py
   Contenido:

   """Tests para IAProvider Interface — Micro-fase 1.0"""
   
   import pytest
   from pydantic import ValidationError
   from src.ia.interfaces import IAProvider, IAMessage, IAResponse
   
   
   class TestIAMessage:
       """Tests para el modelo IAMessage."""
   
       def test_valid_user_message(self):
           msg = IAMessage(role="user", content="Hola YeyoOS")
           assert msg.role == "user"
           assert msg.content == "Hola YeyoOS"
   
       def test_valid_system_message(self):
           msg = IAMessage(role="system", content="Eres un asistente")
           assert msg.role == "system"
   
       def test_valid_assistant_message(self):
           msg = IAMessage(role="assistant", content="Hola!")
           assert msg.role == "assistant"
   
       def test_invalid_role_rejected(self):
           with pytest.raises(ValidationError):
               IAMessage(role="admin", content="test")
   
       def test_empty_content_rejected(self):
           with pytest.raises(ValidationError):
               IAMessage(role="user", content="")
   
       def test_missing_role_rejected(self):
           with pytest.raises(ValidationError):
               IAMessage(content="test")
   
       def test_missing_content_rejected(self):
           with pytest.raises(ValidationError):
               IAMessage(role="user")
   
   
   class TestIAResponse:
       """Tests para el modelo IAResponse."""
   
       def test_valid_response(self):
           resp = IAResponse(
               content="Hola",
               model="qwen2.5:3b",
               tokens_used=42,
               latency_ms=150.5,
           )
           assert resp.content == "Hola"
           assert resp.model == "qwen2.5:3b"
           assert resp.tokens_used == 42
           assert resp.latency_ms == 150.5
   
       def test_has_all_required_fields(self):
           fields = IAResponse.model_fields
           assert "content" in fields
           assert "model" in fields
           assert "tokens_used" in fields
           assert "latency_ms" in fields
   
       def test_negative_tokens_rejected(self):
           with pytest.raises(ValidationError):
               IAResponse(
                   content="test",
                   model="test",
                   tokens_used=-1,
                   latency_ms=10.0,
               )
   
       def test_negative_latency_rejected(self):
           with pytest.raises(ValidationError):
               IAResponse(
                   content="test",
                   model="test",
                   tokens_used=10,
                   latency_ms=-1.0,
               )
   
       def test_missing_field_rejected(self):
           with pytest.raises(ValidationError):
               IAResponse(content="test", model="test")
   
   
   class TestIAProvider:
       """Tests para la interfaz abstracta IAProvider."""
   
       def test_cannot_instantiate_directly(self):
           with pytest.raises(TypeError):
               IAProvider()
   
       def test_all_methods_are_abstract(self):
           abstract_methods = IAProvider.__abstractmethods__
           expected = {
               "generate",
               "chat",
               "chat_stream",
               "get_embedding",
               "health_check",
               "get_model_name",
               "get_max_tokens",
           }
           assert abstract_methods == expected
   
       def test_has_seven_abstract_methods(self):
           assert len(IAProvider.__abstractmethods__) == 7
   
       def test_incomplete_implementation_fails(self):
           class Incomplete(IAProvider):
               async def generate(self, prompt, system="", temperature=0.7):
                   pass
   
           with pytest.raises(TypeError):
               Incomplete()

9. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/ia/test_ia_interfaces.py -v

VERIFICAR:
- [ ] Archivo src/ia/interfaces.py existe y tiene IAProvider, IAMessage, IAResponse
- [ ] Archivo tests/unit/ia/test_ia_interfaces.py existe
- [ ] TODOS los tests pasan: pytest muestra 0 failed
- [ ] IAProvider no se puede instanciar directamente
- [ ] IAMessage rechaza roles inválidos
- [ ] IAResponse tiene los 4 campos requeridos
- [ ] Import funciona: `from src.ia.interfaces import IAProvider, IAMessage, IAResponse`

SI FALLA:
- Import error: verificar que existen todos los __init__.py
- Pydantic no instalado: `pip install pydantic`
- pytest no encontrado: `pip install pytest`

NO HACER:
- No implementar ningún método concreto (eso es micro-fase 1.1)
- No agregar dependencias a bases de datos
- No crear archivos de configuración aún
- No agregar lógica de negocio

GATE: IAProvider es abstracta con 7 métodos, IAMessage/IAResponse validan correctamente, todos los tests pasan.
```
