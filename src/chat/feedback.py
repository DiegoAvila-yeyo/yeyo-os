"""
YeyoOS — FeedbackService (Sistema de Feedback)
Micro-fase 2.14 — Capa 2: Cerebro

Permite al usuario calificar respuestas y reportar errores.
Las correcciones alimentan Flash Memory como memorias tipo 'correction'.
Rating: 1 (malo) a 5 (excelente).
"""

import json
import logging
from typing import Optional

import asyncpg

from src.memory.flash_memory import FlashMemory

logger = logging.getLogger("yeyoos.feedback")


class FeedbackService:
    """
    Servicio de feedback del usuario.
    Almacena calificaciones y usa correcciones para
    mejorar Flash Memory.
    """

    def __init__(self, pool: asyncpg.Pool, flash_memory: Optional[FlashMemory] = None):
        self.pool = pool
        self.memory = flash_memory

    @classmethod
    async def create(
        cls,
        database_url: str,
        flash_memory: Optional[FlashMemory] = None,
    ) -> "FeedbackService":
        """Factory method con connection pool."""
        pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=5,
        )
        return cls(pool, flash_memory)

    async def rate_response(
        self,
        message_id: str,
        rating: int,
        comment: str = "",
        conversation_id: str = None,
    ) -> dict:
        """
        Califica una respuesta.
        rating: 1 (malo) a 5 (excelente).
        """
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            raise ValueError("Rating debe ser un entero entre 1 y 5")

        import uuid as uuid_mod
        msg_id = uuid_mod.UUID(message_id) if isinstance(message_id, str) else message_id
        conv_id = None
        if conversation_id:
            conv_id = (
                uuid_mod.UUID(conversation_id)
                if isinstance(conversation_id, str) else conversation_id
            )

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO feedback (message_id, conversation_id, rating, comment)
                VALUES ($1, $2, $3, $4)
                RETURNING id, message_id, rating, comment, created_at
                """,
                msg_id,
                conv_id,
                rating,
                comment,
            )

        logger.info(f"Feedback registrado: message={message_id}, rating={rating}")
        return {
            "id": str(row["id"]),
            "message_id": str(row["message_id"]),
            "rating": row["rating"],
            "comment": row["comment"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }

    async def report_incorrect(
        self,
        message_id: str,
        correction: str,
        conversation_id: str = None,
    ) -> dict:
        """
        Reporta una respuesta incorrecta con corrección.
        Crea automáticamente una memoria tipo 'correction' en Flash Memory.
        """
        if not correction or not correction.strip():
            raise ValueError("La corrección no puede estar vacía")

        import uuid as uuid_mod
        msg_id = uuid_mod.UUID(message_id) if isinstance(message_id, str) else message_id
        conv_id = None
        if conversation_id:
            conv_id = (
                uuid_mod.UUID(conversation_id)
                if isinstance(conversation_id, str) else conversation_id
            )

        # Registrar feedback con rating 1 (incorrecto)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO feedback
                    (message_id, conversation_id, rating, correction, comment)
                VALUES ($1, $2, 1, $3, 'Respuesta incorrecta reportada')
                RETURNING id
                """,
                msg_id,
                conv_id,
                correction.strip(),
            )

        # Crear memoria de corrección en Flash Memory
        memory_created = None
        if self.memory:
            try:
                mem = await self.memory.store(
                    content=correction.strip(),
                    type="correction",
                    metadata={
                        "source_message_id": str(message_id),
                        "feedback_id": str(row["id"]),
                    },
                    source="user_correction",
                )
                memory_created = mem.id
                logger.info(
                    f"Memoria de corrección creada: {mem.id} "
                    f"para mensaje {message_id}"
                )
            except Exception as e:
                logger.error(f"Error creando memoria de corrección: {e}")

        return {
            "feedback_id": str(row["id"]),
            "message_id": str(message_id),
            "correction": correction.strip(),
            "memory_created": memory_created,
        }

    async def get_feedback_stats(self) -> dict:
        """Estadísticas de feedback."""
        async with self.pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM feedback")
            avg_rating = await conn.fetchval(
                "SELECT AVG(rating)::FLOAT FROM feedback"
            )
            rating_dist = await conn.fetch(
                """
                SELECT rating, COUNT(*) as count
                FROM feedback
                GROUP BY rating
                ORDER BY rating
                """
            )
            corrections_count = await conn.fetchval(
                "SELECT COUNT(*) FROM feedback WHERE correction != ''"
            )

        return {
            "total_feedback": total or 0,
            "average_rating": round(avg_rating, 2) if avg_rating else 0.0,
            "rating_distribution": {
                row["rating"]: row["count"] for row in rating_dist
            },
            "total_corrections": corrections_count or 0,
        }

    async def get_feedback_for_message(self, message_id: str) -> list[dict]:
        """Obtiene todo el feedback para un mensaje específico."""
        import uuid as uuid_mod
        msg_id = uuid_mod.UUID(message_id) if isinstance(message_id, str) else message_id

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, rating, comment, correction, created_at
                FROM feedback
                WHERE message_id = $1
                ORDER BY created_at DESC
                """,
                msg_id,
            )

        return [
            {
                "id": str(row["id"]),
                "rating": row["rating"],
                "comment": row["comment"],
                "correction": row["correction"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]

    async def close(self):
        """Cierra el connection pool."""
        await self.pool.close()
