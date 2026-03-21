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
