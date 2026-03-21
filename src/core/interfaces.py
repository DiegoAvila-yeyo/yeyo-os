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
