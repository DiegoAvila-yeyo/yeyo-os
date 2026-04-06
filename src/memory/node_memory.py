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

from src.memory.pipeline_events import pipeline_buffer

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

    async def store_result(
        self,
        content: str,
        namespace: str,
        memory_type: str = "skill",
        source: str = "node_generation",
        metadata: dict | None = None,
        _pipeline_id: str | None = None,
    ) -> bool:
        """
        Guarda el resultado de una generación de nodo como memoria.
        Genera embedding y emite evento al pipeline visual.
        Si _pipeline_id se provee, emite EMBEDDING/STORED en ese pipeline existente.
        Retorna True si se guardó exitosamente.
        """
        if not content or not content.strip():
            return False

        # Use existing pipeline or create a new one
        pid = _pipeline_id
        if not pid:
            pid = pipeline_buffer.new_pipeline(source=source)
            pipeline_buffer.emit(pid, "RECEIVED", "ok", f"[{source}] {content[:60]}",
                                 {"content": content[:200], "source": source})

        embedding = None
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self.embeddings.generate, content[:500]
            )
            pipeline_buffer.emit(pid, "EMBEDDING", "ok",
                                 f"Vector generado ({len(embedding)} dims)")
        except Exception as e:
            pipeline_buffer.emit(pid, "EMBEDDING", "error", f"Falló: {str(e)[:80]}")

        try:
            await self.memory.store(
                content=content,
                type=memory_type,
                metadata=metadata or {},
                embedding=embedding,
                source=source,
                namespace=namespace,
            )
            pipeline_buffer.emit(pid, "STORED", "ok",
                                 f"→ {namespace} ({memory_type})",
                                 {"namespace": namespace, "type": memory_type})
            logger.info(f"[{source}] Memoria guardada en {namespace}: {content[:60]}")
            return True
        except Exception as e:
            pipeline_buffer.emit(pid, "STORED", "error", f"Error: {str(e)[:80]}")
            logger.warning(f"[{source}] Error guardando memoria: {e}")
            return False
