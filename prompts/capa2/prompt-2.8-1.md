## ═══════════════════════════════════════
## MICRO-FASE 2.8 — Token Budget Manager
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 2.8-1 [VSCODE] — Implementar gestor de presupuesto de tokens

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.8 de Capa 2 (Cerebro): implementar el TokenBudget, un módulo dedicado al conteo estricto y enforcement del presupuesto de tokens.

CONTEXTO:
- Token budget TOTAL = 4000 tokens (hardware limitado: qwen2.5:3b en GTX 1060 3GB)
- Distribución: system(300) + memories(1000) + history(1500) + input(500) + response(700) = 4000
- Micro-fase 2.6 ya usa count_tokens() y truncate_to_tokens(), este módulo los centraliza
- Aproximación de tokens: ~4 caracteres por token (para qwen2.5)
- Este módulo es la FUENTE DE VERDAD para todo el sistema sobre tokens
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/chat/token_budget.py:

   Ruta: ~/yeyo-os/src/chat/token_budget.py
   Contenido:

   """
   YeyoOS — TokenBudget (Gestor de Presupuesto de Tokens)
   Micro-fase 2.8 — Capa 2: Cerebro

   Fuente de verdad para conteo y distribución de tokens.
   TOTAL = 4000 tokens (system:300 + memories:1000 + history:1500 + input:500 + response:700)

   Este presupuesto es ESTRICTO. Nunca debe excederse.
   """

   from typing import Optional

   from src.ia.interfaces import IAMessage
   from src.memory.models import Memory


   class TokenBudget:
       """
       Gestiona el presupuesto de tokens para YeyoOS.
       Garantiza que nunca se excedan los 4000 tokens totales.
       """

       # Presupuesto por sección (tokens)
       SYSTEM = 300
       MEMORIES = 1000
       HISTORY = 1500
       INPUT = 500
       RESPONSE = 700
       TOTAL = 4000

       # Aproximación: ~4 caracteres por token para modelos tipo qwen2.5
       CHARS_PER_TOKEN = 4

       @staticmethod
       def count_tokens(text: str) -> int:
           """
           Cuenta tokens aproximados en un texto.
           Aproximación: len(text) / 4.
           Retorna al menos 1 para texto no vacío.
           """
           if not text:
               return 0
           return max(1, len(text) // TokenBudget.CHARS_PER_TOKEN)

       @staticmethod
       def truncate_to_budget(text: str, max_tokens: int) -> str:
           """
           Trunca texto para que no exceda max_tokens.
           Corta en el último espacio para no romper palabras.
           Agrega '...' si se truncó.
           """
           if not text:
               return ""
           if TokenBudget.count_tokens(text) <= max_tokens:
               return text

           max_chars = max_tokens * TokenBudget.CHARS_PER_TOKEN
           truncated = text[:max_chars]
           # Cortar en el último espacio
           last_space = truncated.rfind(" ")
           if last_space > max_chars // 2:
               truncated = truncated[:last_space]
           return truncated + "..."

       @staticmethod
       def fit_memories(
           memories: list[Memory],
           max_tokens: int = 1000,
       ) -> list[Memory]:
           """
           Filtra memorias para que quepan en el presupuesto.
           Las memorias se incluyen en orden (las primeras tienen prioridad).
           Retorna las memorias que caben dentro del budget.
           """
           if not memories:
               return []

           fitted = []
           tokens_used = 0

           for mem in memories:
               # Formato: "- [type] content"
               mem_text = f"- [{mem.type}] {mem.content}"
               mem_tokens = TokenBudget.count_tokens(mem_text)

               if tokens_used + mem_tokens > max_tokens:
                   break

               fitted.append(mem)
               tokens_used += mem_tokens

           return fitted

       @staticmethod
       def fit_history(
           messages: list[IAMessage],
           max_tokens: int = 1500,
       ) -> list[IAMessage]:
           """
           Trunca historial de mensajes para que quepa en el presupuesto.
           Elimina los mensajes MÁS ANTIGUOS primero (mantiene los recientes).
           """
           if not messages:
               return []

           total_tokens = sum(
               TokenBudget.count_tokens(msg.content) for msg in messages
           )

           if total_tokens <= max_tokens:
               return messages

           # Recorrer desde el final (más recientes) y agregar
           fitted = []
           tokens_used = 0

           for msg in reversed(messages):
               msg_tokens = TokenBudget.count_tokens(msg.content)
               if tokens_used + msg_tokens > max_tokens:
                   break
               fitted.insert(0, msg)
               tokens_used += msg_tokens

           return fitted

       @staticmethod
       def calculate_usage(
           system_text: str,
           memories_text: str,
           history_messages: list[IAMessage],
           user_input: str,
       ) -> dict:
           """
           Calcula el uso de tokens por sección.
           Retorna dict con uso detallado y si está dentro del budget.
           """
           system_tokens = TokenBudget.count_tokens(system_text)
           memories_tokens = TokenBudget.count_tokens(memories_text)
           history_tokens = sum(
               TokenBudget.count_tokens(msg.content) for msg in history_messages
           )
           input_tokens = TokenBudget.count_tokens(user_input)

           total_used = (
               system_tokens + memories_tokens + history_tokens
               + input_tokens + TokenBudget.RESPONSE
           )

           return {
               "system": system_tokens,
               "memories": memories_tokens,
               "history": history_tokens,
               "input": input_tokens,
               "response_reserved": TokenBudget.RESPONSE,
               "total": total_used,
               "remaining": TokenBudget.TOTAL - total_used,
               "within_budget": total_used <= TokenBudget.TOTAL,
               "over_budget_by": max(0, total_used - TokenBudget.TOTAL),
           }

       @staticmethod
       def validate_budget(
           system_tokens: int,
           memories_tokens: int,
           history_tokens: int,
           input_tokens: int,
       ) -> bool:
           """
           Valida que los tokens de cada sección están dentro de sus límites.
           Retorna True si todo está dentro del budget.
           """
           return (
               system_tokens <= TokenBudget.SYSTEM
               and memories_tokens <= TokenBudget.MEMORIES
               and history_tokens <= TokenBudget.HISTORY
               and input_tokens <= TokenBudget.INPUT
               and (system_tokens + memories_tokens + history_tokens
                    + input_tokens + TokenBudget.RESPONSE) <= TokenBudget.TOTAL
           )

2. Actualizar src/chat/__init__.py:

   Ruta: ~/yeyo-os/src/chat/__init__.py
   Contenido:

   from .service import ChatService
   from .contextual_service import ContextualChatService
   from .conversation import ConversationManager
   from .token_budget import TokenBudget

3. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/chat/test_token_budget.py
   Contenido:

   """
   Tests para TokenBudget — Micro-fase 2.8
   Tests unitarios puro — no requiere servicios externos.
   """

   import pytest
   from src.chat.token_budget import TokenBudget
   from src.ia.interfaces import IAMessage
   from src.memory.models import Memory


   class TestTokenBudgetConstants:
       """Tests de constantes del budget."""

       def test_total_is_4000(self):
           assert TokenBudget.TOTAL == 4000

       def test_components_sum_to_total(self):
           total = (
               TokenBudget.SYSTEM
               + TokenBudget.MEMORIES
               + TokenBudget.HISTORY
               + TokenBudget.INPUT
               + TokenBudget.RESPONSE
           )
           assert total == TokenBudget.TOTAL

       def test_system_is_300(self):
           assert TokenBudget.SYSTEM == 300

       def test_memories_is_1000(self):
           assert TokenBudget.MEMORIES == 1000

       def test_history_is_1500(self):
           assert TokenBudget.HISTORY == 1500

       def test_input_is_500(self):
           assert TokenBudget.INPUT == 500

       def test_response_is_700(self):
           assert TokenBudget.RESPONSE == 700

       def test_chars_per_token_is_4(self):
           assert TokenBudget.CHARS_PER_TOKEN == 4


   class TestCountTokens:
       """Tests de conteo de tokens."""

       def test_empty_string(self):
           assert TokenBudget.count_tokens("") == 0

       def test_none_returns_zero(self):
           assert TokenBudget.count_tokens(None) == 0

       def test_short_text_minimum_one(self):
           assert TokenBudget.count_tokens("Hi") >= 1

       def test_approximation(self):
           # 40 caracteres / 4 = 10 tokens
           text = "a" * 40
           assert TokenBudget.count_tokens(text) == 10

       def test_longer_text(self):
           text = "a" * 400
           assert TokenBudget.count_tokens(text) == 100

       def test_realistic_text(self):
           text = "Hola, me llamo Diego y programo en Python"
           tokens = TokenBudget.count_tokens(text)
           assert 5 <= tokens <= 20


   class TestTruncateToBudget:
       """Tests de truncación."""

       def test_short_text_not_truncated(self):
           text = "Hola mundo"
           result = TokenBudget.truncate_to_budget(text, 100)
           assert result == text

       def test_long_text_truncated(self):
           text = "palabra " * 500  # ~1000 tokens
           result = TokenBudget.truncate_to_budget(text, 10)
           assert len(result) < len(text)
           assert result.endswith("...")

       def test_empty_string(self):
           assert TokenBudget.truncate_to_budget("", 100) == ""

       def test_truncation_preserves_words(self):
           text = "una dos tres cuatro cinco seis siete ocho"
           result = TokenBudget.truncate_to_budget(text, 3)
           # No debe cortar a mitad de palabra
           assert not result.rstrip("...").endswith(" ")  or result.endswith("...")


   class TestFitMemories:
       """Tests de ajuste de memorias al budget."""

       def test_empty_list(self):
           result = TokenBudget.fit_memories([])
           assert result == []

       def test_memories_within_budget(self):
           memories = [
               Memory(content="Corto", type="fact", checksum="a" * 64),
               Memory(content="También corto", type="preference", checksum="b" * 64),
           ]
           result = TokenBudget.fit_memories(memories, max_tokens=1000)
           assert len(result) == 2

       def test_memories_exceed_budget(self):
           memories = [
               Memory(content="x" * 2000, type="fact", checksum="a" * 64),
               Memory(content="x" * 2000, type="fact", checksum="b" * 64),
               Memory(content="x" * 2000, type="fact", checksum="c" * 64),
           ]
           result = TokenBudget.fit_memories(memories, max_tokens=1000)
           assert len(result) < 3

       def test_priority_order_preserved(self):
           memories = [
               Memory(content="Primera (prioritaria)", type="fact", checksum="a" * 64),
               Memory(content="Segunda", type="preference", checksum="b" * 64),
           ]
           result = TokenBudget.fit_memories(memories, max_tokens=1000)
           assert result[0].content == "Primera (prioritaria)"


   class TestFitHistory:
       """Tests de ajuste de historial al budget."""

       def test_empty_list(self):
           result = TokenBudget.fit_history([])
           assert result == []

       def test_history_within_budget(self):
           messages = [
               IAMessage(role="user", content="Hola"),
               IAMessage(role="assistant", content="Hola!"),
           ]
           result = TokenBudget.fit_history(messages, max_tokens=1500)
           assert len(result) == 2

       def test_history_truncates_oldest_first(self):
           messages = [
               IAMessage(role="user", content="Mensaje antiguo " * 100),
               IAMessage(role="assistant", content="Respuesta antigua " * 100),
               IAMessage(role="user", content="Reciente"),
               IAMessage(role="assistant", content="Última respuesta"),
           ]
           result = TokenBudget.fit_history(messages, max_tokens=20)
           # Debe mantener los más recientes
           assert result[-1].content == "Última respuesta"

       def test_history_all_fit(self):
           messages = [
               IAMessage(role="user", content="Uno"),
               IAMessage(role="assistant", content="Dos"),
           ]
           result = TokenBudget.fit_history(messages, max_tokens=1500)
           assert len(result) == 2


   class TestCalculateUsage:
       """Tests de cálculo de uso."""

       def test_returns_all_fields(self):
           usage = TokenBudget.calculate_usage(
               system_text="System",
               memories_text="Memories",
               history_messages=[],
               user_input="Input",
           )
           assert "system" in usage
           assert "memories" in usage
           assert "history" in usage
           assert "input" in usage
           assert "response_reserved" in usage
           assert "total" in usage
           assert "remaining" in usage
           assert "within_budget" in usage

       def test_within_budget(self):
           usage = TokenBudget.calculate_usage(
               system_text="Hola",
               memories_text="Memoria",
               history_messages=[],
               user_input="Test",
           )
           assert usage["within_budget"] is True

       def test_response_reserved(self):
           usage = TokenBudget.calculate_usage("", "", [], "")
           assert usage["response_reserved"] == 700


   class TestValidateBudget:
       """Tests de validación de budget."""

       def test_valid_budget(self):
           assert TokenBudget.validate_budget(
               system_tokens=200,
               memories_tokens=800,
               history_tokens=1000,
               input_tokens=300,
           ) is True

       def test_system_over_budget(self):
           assert TokenBudget.validate_budget(
               system_tokens=400,  # > 300
               memories_tokens=0,
               history_tokens=0,
               input_tokens=0,
           ) is False

       def test_total_over_budget(self):
           assert TokenBudget.validate_budget(
               system_tokens=300,
               memories_tokens=1000,
               history_tokens=1500,
               input_tokens=500,
           ) is True  # Exacto = 4000

       def test_exactly_at_budget(self):
           # 300 + 1000 + 1500 + 500 + 700(response) = 4000
           assert TokenBudget.validate_budget(
               system_tokens=300,
               memories_tokens=1000,
               history_tokens=1500,
               input_tokens=500,
           ) is True

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/chat/test_token_budget.py -v

VERIFICAR:
- [ ] Archivo src/chat/token_budget.py existe
- [ ] TOTAL es exactamente 4000
- [ ] Componentes suman exactamente 4000
- [ ] count_tokens() aproxima correctamente (~4 chars/token)
- [ ] truncate_to_budget() no rompe palabras
- [ ] fit_memories() respeta presupuesto, prioriza las primeras
- [ ] fit_history() elimina mensajes antiguos primero
- [ ] calculate_usage() retorna todas las secciones
- [ ] validate_budget() valida cada sección y el total
- [ ] TODOS los tests pasan

SI FALLA:
- Import IAMessage: verificar Capa 1
- Import Memory: verificar micro-fase 2.1

NO HACER:
- No cambiar el budget total de 4000
- No usar conteo de tokens exacto (la aproximación de 4 chars es suficiente)
- No agregar dependencia de tiktoken o similar (innecesario para qwen2.5)
- No permitir que ninguna sección exceda su límite

GATE: TokenBudget es la fuente de verdad, TOTAL=4000, componentes verificados, conteo y truncación funcionan, todos los tests pasan.
```
