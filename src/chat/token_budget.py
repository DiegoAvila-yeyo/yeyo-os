"""
YeyoOS — TokenBudget (Gestor de Presupuesto de Tokens)
Micro-fase 2.8 — Capa 2: Cerebro

Fuente de verdad para conteo y distribución de tokens.
TOTAL = 4000 tokens (system:300 + memories:1000 + history:1500 + input:500 + response:700)

Este presupuesto es ESTRICTO. Nunca debe excederse.
"""

from src.ia.interfaces import IAMessage
from src.memory.models import Memory


class TokenBudget:
    """
    Gestiona el presupuesto de tokens para YeyoOS.
    Garantiza que nunca se excedan los 4000 tokens totales.
    """

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
        Aproximación: len(text) / 4. Retorna al menos 1 para texto no vacío.
        """
        if not text:
            return 0
        return max(1, len(text) // TokenBudget.CHARS_PER_TOKEN)

    @staticmethod
    def truncate_to_budget(text: str, max_tokens: int) -> str:
        """
        Trunca texto para que no exceda max_tokens.
        Corta en el último espacio para no romper palabras.
        """
        if not text:
            return ""
        if TokenBudget.count_tokens(text) <= max_tokens:
            return text
        max_chars = max_tokens * TokenBudget.CHARS_PER_TOKEN
        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        if last_space > max_chars // 2:
            truncated = truncated[:last_space]
        return truncated + "..."

    @staticmethod
    def fit_memories(memories: list[Memory], max_tokens: int = 1000) -> list[Memory]:
        """
        Filtra memorias para que quepan en el presupuesto.
        Las memorias se incluyen en orden (las primeras tienen prioridad).
        """
        if not memories:
            return []
        fitted = []
        tokens_used = 0
        for mem in memories:
            mem_text = f"- [{mem.type}] {mem.content}"
            mem_tokens = TokenBudget.count_tokens(mem_text)
            if tokens_used + mem_tokens > max_tokens:
                break
            fitted.append(mem)
            tokens_used += mem_tokens
        return fitted

    @staticmethod
    def fit_history(messages: list[IAMessage], max_tokens: int = 1500) -> list[IAMessage]:
        """
        Trunca historial para que quepa en el presupuesto.
        Elimina los mensajes MÁS ANTIGUOS primero (mantiene los recientes).
        """
        if not messages:
            return []
        total_tokens = sum(TokenBudget.count_tokens(msg.content) for msg in messages)
        if total_tokens <= max_tokens:
            return messages
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
        history_tokens = sum(TokenBudget.count_tokens(msg.content) for msg in history_messages)
        input_tokens = TokenBudget.count_tokens(user_input)
        total_used = system_tokens + memories_tokens + history_tokens + input_tokens + TokenBudget.RESPONSE

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
        """Valida que los tokens de cada sección están dentro de sus límites."""
        return (
            system_tokens <= TokenBudget.SYSTEM
            and memories_tokens <= TokenBudget.MEMORIES
            and history_tokens <= TokenBudget.HISTORY
            and input_tokens <= TokenBudget.INPUT
            and (system_tokens + memories_tokens + history_tokens
                 + input_tokens + TokenBudget.RESPONSE) <= TokenBudget.TOTAL
        )
