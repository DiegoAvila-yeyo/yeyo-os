## ═══════════════════════════════════════
## MICRO-FASE 1.3 — Orquestador Interface
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 1.3-1 [VSCODE] — Crear interfaz abstracta del Orquestador

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 1.3: crear la interfaz abstracta del Orquestador, el coordinador central que une IA + Memoria + Contexto.

CONTEXTO:
- Micro-fases 1.0-1.2 completadas: IAProvider, OllamaProvider, MemoriaProvider definidos
- El Orquestador es el CEREBRO: recibe input del usuario, busca memorias relevantes, arma el contexto, llama a la IA, y almacena la respuesta
- Token budget: system(300) + memories(1000) + history(1500) + input(500) + response(700) = 4000
- El Orquestador debe respetar este budget al armar prompts
- health_check retorna dict (no bool) porque verifica MÚLTIPLES subsistemas

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios:
   mkdir -p src/core
   mkdir -p tests/unit/core

2. Crear archivo src/core/__init__.py:

   Ruta: ~/yeyo-os/src/core/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo src/core/interfaces.py:

   Ruta: ~/yeyo-os/src/core/interfaces.py
   Contenido:

   """
   YeyoOS — Orquestador Interface (Puerto Hexagonal)
   Micro-fase 1.3 — Capa 1: Esqueleto
   
   Interfaz abstracta del Orquestador central.
   Coordina: IA (generar respuestas) + Memoria (contexto persistente)
   + Contexto (token budget management).
   
   Token Budget:
     system:   300 tokens
     memories: 1000 tokens
     history:  1500 tokens
     input:    500 tokens
     response: 700 tokens
     TOTAL:    4000 tokens máximo
   """
   
   from abc import ABC, abstractmethod
   from typing import AsyncIterator
   
   from pydantic import BaseModel, Field
   
   
   class TokenBudget(BaseModel):
       """Distribución del budget de tokens por sección."""
       system: int = Field(default=300, ge=0)
       memories: int = Field(default=1000, ge=0)
       history: int = Field(default=1500, ge=0)
       input: int = Field(default=500, ge=0)
       response: int = Field(default=700, ge=0)
   
       @property
       def total(self) -> int:
           return self.system + self.memories + self.history + self.input + self.response
   
   
   class OrquestadorContext(BaseModel):
       """Contexto armado por el Orquestador para enviar a la IA."""
       system_prompt: str = ""
       relevant_memories: list[str] = Field(default_factory=list)
       conversation_history: list[dict] = Field(default_factory=list)
       user_input: str = ""
       token_budget: TokenBudget = Field(default_factory=TokenBudget)
   
   
   class OrquestadorProvider(ABC):
       """
       Puerto hexagonal del Orquestador central de YeyoOS.
       
       Flujo:
       1. Recibe mensaje del usuario
       2. Busca memorias relevantes (Flash Memory)
       3. Arma contexto respetando token budget
       4. Llama a la IA (IAProvider)
       5. Almacena la interacción en memoria
       6. Retorna respuesta
       """
   
       @abstractmethod
       async def process_message(
           self, user_input: str, context: dict | None = None
       ) -> str:
           """
           Procesa un mensaje completo y retorna la respuesta.
           context: metadata adicional (session_id, user_id, etc.)
           """
           ...
   
       @abstractmethod
       async def process_message_stream(
           self, user_input: str, context: dict | None = None
       ) -> AsyncIterator[str]:
           """
           Procesa mensaje y retorna respuesta en streaming.
           Ideal para UI en tiempo real via WebSocket.
           """
           ...
   
       @abstractmethod
       async def get_context_for_prompt(
           self, user_input: str
       ) -> OrquestadorContext:
           """
           Arma el contexto completo para el prompt.
           Busca memorias, historial, y respeta token budget.
           """
           ...
   
       @abstractmethod
       async def health_check(self) -> dict:
           """
           Verifica estado de TODOS los subsistemas.
           Retorna dict (no bool) con estado individual:
           {
               "status": "healthy" | "degraded" | "unhealthy",
               "ia": {"status": "up", "model": "..."},
               "memory": {"status": "up", "total": N},
               "token_budget": {"total": 4000, "available": N}
           }
           """
           ...

4. Crear archivo tests/unit/core/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/core/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/core/test_orquestador_interface.py:

   Ruta: ~/yeyo-os/tests/unit/core/test_orquestador_interface.py
   Contenido:

   """Tests para Orquestador Interface — Micro-fase 1.3"""
   
   import pytest
   from src.core.interfaces import (
       OrquestadorProvider,
       TokenBudget,
       OrquestadorContext,
   )
   
   
   class TestTokenBudget:
       """Tests para el modelo TokenBudget."""
   
       def test_default_values(self):
           budget = TokenBudget()
           assert budget.system == 300
           assert budget.memories == 1000
           assert budget.history == 1500
           assert budget.input == 500
           assert budget.response == 700
   
       def test_total_is_4000(self):
           budget = TokenBudget()
           assert budget.total == 4000
   
       def test_custom_values(self):
           budget = TokenBudget(system=200, memories=800, history=1000, input=400, response=600)
           assert budget.total == 3000
   
       def test_total_is_computed_property(self):
           budget = TokenBudget()
           assert isinstance(TokenBudget.total.fget(budget), int)
   
   
   class TestOrquestadorContext:
       """Tests para el modelo OrquestadorContext."""
   
       def test_default_context(self):
           ctx = OrquestadorContext()
           assert ctx.system_prompt == ""
           assert ctx.relevant_memories == []
           assert ctx.conversation_history == []
           assert ctx.user_input == ""
           assert ctx.token_budget.total == 4000
   
       def test_context_with_data(self):
           ctx = OrquestadorContext(
               system_prompt="Eres YeyoOS",
               relevant_memories=["memoria1", "memoria2"],
               user_input="Hola",
           )
           assert ctx.system_prompt == "Eres YeyoOS"
           assert len(ctx.relevant_memories) == 2
           assert ctx.user_input == "Hola"
   
   
   class TestOrquestadorProvider:
       """Tests para la interfaz abstracta OrquestadorProvider."""
   
       def test_cannot_instantiate_directly(self):
           with pytest.raises(TypeError):
               OrquestadorProvider()
   
       def test_all_methods_are_abstract(self):
           abstract_methods = OrquestadorProvider.__abstractmethods__
           expected = {
               "process_message",
               "process_message_stream",
               "get_context_for_prompt",
               "health_check",
           }
           assert abstract_methods == expected
   
       def test_has_four_abstract_methods(self):
           assert len(OrquestadorProvider.__abstractmethods__) == 4
   
       def test_health_check_returns_dict_not_bool(self):
           """health_check retorna dict porque verifica múltiples subsistemas."""
           import inspect
           sig = inspect.signature(OrquestadorProvider.health_check)
           annotations = sig.return_annotation
           assert annotations is dict
   
       def test_incomplete_implementation_fails(self):
           class Incomplete(OrquestadorProvider):
               async def process_message(self, user_input, context=None):
                   pass
   
           with pytest.raises(TypeError):
               Incomplete()

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/core/test_orquestador_interface.py -v

VERIFICAR:
- [ ] Archivo src/core/interfaces.py existe con OrquestadorProvider, TokenBudget, OrquestadorContext
- [ ] TODOS los tests pasan (0 failed)
- [ ] TokenBudget.total == 4000 por defecto
- [ ] OrquestadorProvider no se puede instanciar
- [ ] health_check retorna dict, no bool
- [ ] 4 métodos abstractos definidos
- [ ] Import funciona: `from src.core.interfaces import OrquestadorProvider`

SI FALLA:
- Import error: verificar __init__.py en src/core/
- AsyncIterator import: `from typing import AsyncIterator`
- Property error en TokenBudget: verificar sintaxis @property

NO HACER:
- No implementar el Orquestador concreto (eso es Capa 2)
- No conectar a IAProvider o MemoriaProvider todavía
- No agregar lógica de truncamiento de tokens
- No crear endpoints API aquí

GATE: OrquestadorProvider abstracto con 4 métodos, TokenBudget suma 4000, health_check retorna dict, todos los tests pasan.
```
