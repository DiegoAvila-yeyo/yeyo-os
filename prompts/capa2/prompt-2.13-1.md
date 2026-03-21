## ═══════════════════════════════════════
## MICRO-FASE 2.13 — System Prompt Builder
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 2.13-1 [VSCODE] — Implementar constructor dinámico de system prompt

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.13 de Capa 2 (Cerebro): implementar el SystemPromptBuilder que construye dinámicamente el system prompt incluyendo preferencias del usuario almacenadas en Flash Memory.

CONTEXTO:
- Micro-fases 2.0-2.12 completadas: Flash Memory, Chat, RAG funcionando
- El system prompt tiene un budget de 300 tokens máximo
- Debe incluir: prompt base + preferencias del usuario desde Flash Memory
- Las preferencias se obtienen de memorias tipo "preference" en Flash Memory
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/chat/system_prompt.py:

   Ruta: ~/yeyo-os/src/chat/system_prompt.py
   Contenido:

   """
   YeyoOS — SystemPromptBuilder (Constructor de System Prompt)
   Micro-fase 2.13 — Capa 2: Cerebro

   Construye dinámicamente el system prompt incluyendo:
   - Prompt base de YeyoOS
   - Preferencias del usuario desde Flash Memory
   - Contexto adicional según la situación

   LÍMITE: 300 tokens máximo para el system prompt.
   """

   import logging
   from typing import Optional

   from src.memory.flash_memory import FlashMemory
   from src.chat.token_budget import TokenBudget

   logger = logging.getLogger("yeyoos.system_prompt")

   BASE_PROMPT = (
       "Eres YeyoOS, un asistente de IA integrado en el sistema operativo del usuario. "
       "Eres directo, útil y respetuoso. Respondes en español a menos que el usuario "
       "te hable en otro idioma. Eres conciso pero completo."
   )

   MAX_PROMPT_TOKENS = TokenBudget.SYSTEM  # 300 tokens


   class SystemPromptBuilder:
       """
       Constructor dinámico del system prompt.
       Combina el prompt base con preferencias del usuario
       almacenadas en Flash Memory, respetando el budget de 300 tokens.
       """

       def __init__(self, flash_memory: Optional[FlashMemory] = None):
           self.memory = flash_memory

       async def build(self, context: dict = None) -> str:
           """
           Construye el system prompt completo.
           1. Empieza con el prompt base
           2. Agrega preferencias del usuario (si hay)
           3. Agrega contexto adicional (si se proporciona)
           4. Trunca a 300 tokens

           Args:
               context: dict opcional con info extra (ej: hora del día, modo)

           Returns:
               System prompt final (máx 300 tokens)
           """
           if context is None:
               context = {}

           parts = [BASE_PROMPT]
           tokens_used = TokenBudget.count_tokens(BASE_PROMPT)

           # Agregar preferencias del usuario desde Flash Memory
           if self.memory:
               preferences = await self._get_user_preferences()
               if preferences:
                   prefs_text = self._format_preferences(preferences)
                   prefs_tokens = TokenBudget.count_tokens(prefs_text)

                   if tokens_used + prefs_tokens <= MAX_PROMPT_TOKENS:
                       parts.append(prefs_text)
                       tokens_used += prefs_tokens

           # Agregar contexto adicional
           if context:
               ctx_text = self._format_context(context)
               ctx_tokens = TokenBudget.count_tokens(ctx_text)

               if tokens_used + ctx_tokens <= MAX_PROMPT_TOKENS:
                   parts.append(ctx_text)
                   tokens_used += ctx_tokens

           prompt = "\n\n".join(parts)

           # Truncar si excede el budget (safety net)
           if TokenBudget.count_tokens(prompt) > MAX_PROMPT_TOKENS:
               prompt = TokenBudget.truncate_to_budget(prompt, MAX_PROMPT_TOKENS)

           logger.debug(
               f"System prompt: {TokenBudget.count_tokens(prompt)}/{MAX_PROMPT_TOKENS} tokens"
           )
           return prompt

       async def _get_user_preferences(self, limit: int = 5) -> list[str]:
           """Obtiene preferencias del usuario desde Flash Memory."""
           try:
               memories = await self.memory.recall_by_type("preference", limit=limit)
               return [m.content for m in memories]
           except Exception as e:
               logger.warning(f"Error obteniendo preferencias: {e}")
               return []

       def _format_preferences(self, preferences: list[str]) -> str:
           """Formatea preferencias como texto para el prompt."""
           if not preferences:
               return ""
           prefs_list = "\n".join(f"- {p}" for p in preferences)
           return f"[Preferencias del usuario]\n{prefs_list}"

       def _format_context(self, context: dict) -> str:
           """Formatea contexto adicional como texto."""
           if not context:
               return ""
           ctx_parts = []
           if "mode" in context:
               ctx_parts.append(f"Modo: {context['mode']}")
           if "time_of_day" in context:
               ctx_parts.append(f"Momento: {context['time_of_day']}")
           if "language" in context:
               ctx_parts.append(f"Idioma preferido: {context['language']}")

           if ctx_parts:
               return "[Contexto]\n" + "\n".join(ctx_parts)
           return ""

       @staticmethod
       def get_base_prompt() -> str:
           """Retorna el prompt base sin personalización."""
           return BASE_PROMPT

       @staticmethod
       def get_max_tokens() -> int:
           """Retorna el máximo de tokens permitido."""
           return MAX_PROMPT_TOKENS

2. Actualizar src/chat/__init__.py:

   Ruta: ~/yeyo-os/src/chat/__init__.py
   Contenido:

   from .service import ChatService
   from .contextual_service import ContextualChatService
   from .conversation import ConversationManager
   from .token_budget import TokenBudget
   from .system_prompt import SystemPromptBuilder

3. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/chat/test_system_prompt.py
   Contenido:

   """
   Tests para SystemPromptBuilder — Micro-fase 2.13
   Tests unitarios.
   """

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   from src.chat.system_prompt import (
       SystemPromptBuilder,
       BASE_PROMPT,
       MAX_PROMPT_TOKENS,
   )
   from src.chat.token_budget import TokenBudget
   from src.memory.models import Memory


   class TestBasePrompt:
       """Tests del prompt base."""

       def test_base_prompt_exists(self):
           assert BASE_PROMPT is not None
           assert len(BASE_PROMPT) > 0

       def test_base_prompt_contains_yeyoos(self):
           assert "YeyoOS" in BASE_PROMPT

       def test_base_prompt_in_spanish(self):
           assert "español" in BASE_PROMPT

       def test_base_prompt_fits_budget(self):
           tokens = TokenBudget.count_tokens(BASE_PROMPT)
           assert tokens <= MAX_PROMPT_TOKENS

       def test_max_tokens_is_300(self):
           assert MAX_PROMPT_TOKENS == 300

       def test_get_base_prompt_static(self):
           assert SystemPromptBuilder.get_base_prompt() == BASE_PROMPT

       def test_get_max_tokens_static(self):
           assert SystemPromptBuilder.get_max_tokens() == 300


   class TestBuildPrompt:
       """Tests de construcción dinámica."""

       @pytest.mark.asyncio
       async def test_build_without_memory(self):
           builder = SystemPromptBuilder(flash_memory=None)
           prompt = await builder.build()
           assert BASE_PROMPT in prompt

       @pytest.mark.asyncio
       async def test_build_fits_in_300_tokens(self):
           builder = SystemPromptBuilder(flash_memory=None)
           prompt = await builder.build()
           assert TokenBudget.count_tokens(prompt) <= 300

       @pytest.mark.asyncio
       async def test_build_with_preferences(self):
           mock_memory = AsyncMock()
           mock_memory.recall_by_type.return_value = [
               Memory(
                   content="Prefiere Python",
                   type="preference",
                   checksum="a" * 64,
               ),
               Memory(
                   content="Le gusta el modo oscuro",
                   type="preference",
                   checksum="b" * 64,
               ),
           ]
           builder = SystemPromptBuilder(flash_memory=mock_memory)
           prompt = await builder.build()
           assert "Prefiere Python" in prompt
           assert "modo oscuro" in prompt

       @pytest.mark.asyncio
       async def test_build_never_exceeds_budget(self):
           mock_memory = AsyncMock()
           # Muchas preferencias largas
           mock_memory.recall_by_type.return_value = [
               Memory(
                   content="x" * 500,
                   type="preference",
                   checksum=f"{i}" * 64,
               )
               for i in range(10)
           ]
           builder = SystemPromptBuilder(flash_memory=mock_memory)
           prompt = await builder.build()
           assert TokenBudget.count_tokens(prompt) <= 300

       @pytest.mark.asyncio
       async def test_build_with_context(self):
           builder = SystemPromptBuilder(flash_memory=None)
           prompt = await builder.build(context={
               "mode": "programación",
               "language": "español",
           })
           assert "programación" in prompt

       @pytest.mark.asyncio
       async def test_build_with_empty_context(self):
           builder = SystemPromptBuilder(flash_memory=None)
           prompt = await builder.build(context={})
           assert BASE_PROMPT in prompt

       @pytest.mark.asyncio
       async def test_build_memory_error_handled(self):
           """Error en Flash Memory no crashea el builder."""
           mock_memory = AsyncMock()
           mock_memory.recall_by_type.side_effect = Exception("DB error")
           builder = SystemPromptBuilder(flash_memory=mock_memory)
           prompt = await builder.build()
           assert BASE_PROMPT in prompt  # Fallback al base

       @pytest.mark.asyncio
       async def test_build_includes_preferences_section(self):
           mock_memory = AsyncMock()
           mock_memory.recall_by_type.return_value = [
               Memory(
                   content="Le gusta café",
                   type="preference",
                   checksum="a" * 64,
               ),
           ]
           builder = SystemPromptBuilder(flash_memory=mock_memory)
           prompt = await builder.build()
           assert "[Preferencias del usuario]" in prompt

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/chat/test_system_prompt.py -v

VERIFICAR:
- [ ] Archivo src/chat/system_prompt.py existe
- [ ] Prompt base contiene "YeyoOS"
- [ ] Prompt base cabe en 300 tokens
- [ ] build() incluye preferencias si hay
- [ ] build() NUNCA excede 300 tokens
- [ ] build() con contexto adicional funciona
- [ ] Error en Flash Memory no crashea (fallback a base)
- [ ] get_base_prompt() retorna prompt estático
- [ ] TODOS los tests pasan

SI FALLA:
- Import TokenBudget: verificar micro-fase 2.8
- Import FlashMemory: verificar micro-fase 2.1
- AsyncMock: verificar Python 3.8+

NO HACER:
- No exceder 300 tokens en el system prompt
- No incluir información sensible en el prompt base
- No hacer llamadas costosas a la IA para construir el prompt (es solo formateo)
- No cambiar el idioma base del prompt (siempre español por defecto)

GATE: SystemPromptBuilder construye prompt dinámico, incluye preferencias del usuario, respeta budget de 300 tokens, maneja errores grácilmente, todos los tests pasan.
```
