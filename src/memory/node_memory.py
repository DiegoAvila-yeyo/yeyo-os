"""
YeyoOS — NodeMemoryService
Fase 6: Servicio de memoria reutilizable para nodos de IA.

Permite a cualquier nodo (Image, Code, Video, Automatizacion) buscar
memorias relevantes de sus namespaces (:usuario y :conocimiento)
antes de generar contenido, enriqueciendo los prompts con contexto.
"""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger("yeyoos.memory.node_memory")


class NodeMemoryService:
    """
    Servicio de memoria para nodos de IA.
    Cada nodo recibe una instancia configurada con sus namespaces propios.
    """

    def __init__(self, flash_memory, embeddings):
        self.memory = flash_memory
        self.embeddings = embeddings

    async def get_context(
        self,
        query: str,
        namespaces: list[str],
        limit: int = 3,
        threshold: float = 0.3,
    ) -> str:
        """
        Busca memorias relevantes para el query en los namespaces indicados.
        Retorna texto formateado listo para inyectar en system prompt.
        Retorna "" si no hay memorias relevantes o si falla.
        """
        if not query or not query.strip():
            return ""
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self.embeddings.generate, query
            )
            memories = await self.memory.search_semantic(
                embedding=embedding,
                threshold=threshold,
                limit=limit,
                namespaces=namespaces,
            )
            if not memories:
                return ""
            return "\n".join(f"- {m.content}" for m in memories)
        except Exception as e:
            logger.warning(f"NodeMemoryService.get_context error: {e}")
            return ""

    async def get_image_context(self, query: str, limit: int = 3) -> str:
        """Contexto de imagen: conocimiento general + preferencias del usuario."""
        return await self.get_context(
            query,
            namespaces=["imagen:conocimiento", "imagen:usuario"],
            limit=limit,
        )

    async def get_code_context(self, query: str, limit: int = 3) -> str:
        """Contexto de código: buenas prácticas + preferencias del usuario."""
        return await self.get_context(
            query,
            namespaces=["codigo:conocimiento", "codigo:usuario"],
            limit=limit,
        )

    async def get_video_context(self, query: str, limit: int = 3) -> str:
        """Contexto de video: conocimiento general + preferencias del usuario."""
        return await self.get_context(
            query,
            namespaces=["video:conocimiento", "video:usuario"],
            limit=limit,
        )

    async def get_automation_context(self, query: str, limit: int = 3) -> str:
        """Contexto de automatización: patrones + preferencias del usuario."""
        return await self.get_context(
            query,
            namespaces=["automatizacion:conocimiento", "automatizacion:usuario"],
            limit=limit,
        )
