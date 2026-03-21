"""
YeyoOS — ConversationManager (Gestor de Conversaciones)
Micro-fase 2.7 — Capa 2: Cerebro

Gestiona sesiones de conversación: crear, agregar mensajes,
obtener historial. Todo persistido en PostgreSQL.
"""

import json
import uuid
import logging
from typing import Optional

import asyncpg

from src.ia.interfaces import IAMessage

logger = logging.getLogger("yeyoos.conversation")


class ConversationManager:
    """
    Gestiona conversaciones y su historial de mensajes.
    Almacena en PostgreSQL para persistencia.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    @classmethod
    async def create(cls, database_url: str) -> "ConversationManager":
        """Factory method con connection pool."""
        pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
        return cls(pool)

    async def create_conversation(self, title: str = "Nueva conversación") -> str:
        """Crea una nueva conversación. Retorna UUID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO conversations (title) VALUES ($1) RETURNING id",
                title,
            )
        conv_id = str(row["id"])
        logger.info(f"Conversación creada: {conv_id}")
        return conv_id

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tokens: int = 0,
        metadata: Optional[dict] = None,
    ):
        """
        Agrega un mensaje a la conversación.
        El trigger actualiza message_count y updated_at automáticamente.
        """
        conv_id = (
            conversation_id
            if isinstance(conversation_id, uuid.UUID)
            else uuid.UUID(conversation_id)
        )
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversation_messages
                    (conversation_id, role, content, tokens, metadata)
                VALUES ($1, $2, $3, $4, $5)
                """,
                conv_id,
                role,
                content,
                tokens,
                json.dumps(metadata or {}),
            )
        logger.debug(f"Mensaje agregado a {conversation_id}: role={role}")

    async def get_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> list[IAMessage]:
        """
        Obtiene los últimos `limit` mensajes en orden cronológico.
        """
        conv_id = (
            conversation_id
            if isinstance(conversation_id, uuid.UUID)
            else uuid.UUID(conversation_id)
        )
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content, created_at
                FROM conversation_messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                conv_id,
                limit,
            )
        # Revertir para orden cronológico
        return [IAMessage(role=row["role"], content=row["content"]) for row in reversed(rows)]

    async def list_conversations(self, limit: int = 50) -> list[dict]:
        """Lista conversaciones, las más recientes primero."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, message_count, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                LIMIT $1
                """,
                limit,
            )
        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "message_count": row["message_count"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            }
            for row in rows
        ]

    async def get_conversation(self, conversation_id: str) -> Optional[dict]:
        """Obtiene detalles de una conversación específica."""
        conv_id = (
            conversation_id
            if isinstance(conversation_id, uuid.UUID)
            else uuid.UUID(conversation_id)
        )
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, title, message_count, metadata, created_at, updated_at
                FROM conversations WHERE id = $1
                """,
                conv_id,
            )
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "title": row["title"],
            "message_count": row["message_count"],
            "metadata": row["metadata"] if row["metadata"] else {},
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }

    async def update_title(self, conversation_id: str, title: str):
        """Actualiza el título de una conversación."""
        conv_id = (
            conversation_id
            if isinstance(conversation_id, uuid.UUID)
            else uuid.UUID(conversation_id)
        )
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE conversations SET title = $1, updated_at = NOW() WHERE id = $2",
                title,
                conv_id,
            )

    async def close(self):
        """Cierra el connection pool."""
        await self.pool.close()
