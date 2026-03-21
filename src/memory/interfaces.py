"""
YeyoOS — MemoriaProvider Interface (Puerto Hexagonal)
Micro-fase 1.2 — Capa 1: Esqueleto

Interfaz abstracta para Flash Memory.
La memoria en YeyoOS es PERMANENTE — nunca se elimina,
solo se mueve entre tiers (HOT/WARM/COLD).
Cada memoria tiene checksum SHA-256 para garantizar integridad.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MemoryTier(str, Enum):
    """Tier de acceso de la memoria."""
    HOT = "HOT"      # Acceso frecuente, en cache Redis
    WARM = "WARM"    # Acceso medio, solo en PostgreSQL
    COLD = "COLD"    # Archivo, comprimido, acceso raro


class MemoryType(str, Enum):
    """Tipo semántico de la memoria."""
    CONVERSATION = "conversation"  # Fragmentos de conversación
    PREFERENCE = "preference"      # Preferencias del usuario
    FACT = "fact"                  # Hechos aprendidos
    CORRECTION = "correction"      # Correcciones del usuario
    SKILL = "skill"                # Habilidades aprendidas


class Memory(BaseModel):
    """Modelo de una memoria persistente en Flash Memory."""
    id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    type: MemoryType
    tier: MemoryTier = MemoryTier.WARM
    embedding: Optional[list[float]] = None
    checksum: str = Field(..., min_length=64, max_length=64)  # SHA-256
    created_at: datetime
    accessed_at: datetime
    access_count: int = Field(default=0, ge=0)
    metadata: dict = Field(default_factory=dict)


class MemoriaProvider(ABC):
    """
    Puerto hexagonal para Flash Memory.

    IMPORTANTE: No existe método delete().
    La memoria en YeyoOS es PERMANENTE por diseño.
    Solo se mueve entre tiers para gestionar rendimiento.
    """

    @abstractmethod
    async def store(
        self,
        content: str,
        type: MemoryType,
        metadata: dict | None = None,
    ) -> Memory:
        """
        Almacena nueva memoria. Genera checksum SHA-256 automáticamente.
        Nuevas memorias entran como WARM por defecto.
        """
        ...

    @abstractmethod
    async def recall(self, query: str, limit: int = 5) -> list[Memory]:
        """
        Busca memorias relevantes por query (combinación de texto y semántica).
        Actualiza accessed_at y access_count de las memorias encontradas.
        """
        ...

    @abstractmethod
    async def recall_by_type(
        self, type: MemoryType, limit: int = 10
    ) -> list[Memory]:
        """Busca memorias por tipo, ordenadas por acceso más reciente."""
        ...

    @abstractmethod
    async def get_by_id(self, id: str) -> Memory | None:
        """Obtiene una memoria específica por su ID."""
        ...

    @abstractmethod
    async def search_semantic(
        self,
        query: str,
        threshold: float = 0.7,
        limit: int = 5,
    ) -> list[Memory]:
        """
        Búsqueda puramente semántica via embeddings pgvector.
        threshold: similitud mínima (0.0 a 1.0).
        """
        ...

    @abstractmethod
    async def promote_tier(self, id: str) -> Memory:
        """
        Promueve una memoria: COLD → WARM → HOT.
        Si ya es HOT, no hace nada.
        """
        ...

    @abstractmethod
    async def demote_tier(self, id: str) -> Memory:
        """
        Degrada una memoria: HOT → WARM → COLD.
        Si ya es COLD, no hace nada.
        """
        ...

    @abstractmethod
    async def get_stats(self) -> dict:
        """
        Retorna estadísticas de Flash Memory:
        - Conteo por tier (HOT/WARM/COLD)
        - Conteo por tipo
        - Total de memorias
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica conexión a PostgreSQL + pgvector."""
        ...
