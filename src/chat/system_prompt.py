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
