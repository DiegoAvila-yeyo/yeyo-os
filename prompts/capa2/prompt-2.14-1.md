## ═══════════════════════════════════════
## MICRO-FASE 2.14 — Feedback Loop
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.14-1 [VSCODE] — Implementar sistema de feedback del usuario

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.14 de Capa 2 (Cerebro): implementar el sistema de feedback que permite al usuario calificar respuestas y reportar errores, alimentando el ciclo de mejora de Flash Memory.

CONTEXTO:
- Micro-fases 2.0-2.13 completadas: Flash Memory, Chat, RAG funcionando
- El feedback se almacena en PostgreSQL
- Correcciones del usuario crean memorias tipo "correction" en Flash Memory
- Rating de 1-5 (1=malo, 5=excelente)
- Las correcciones son las MÁS valiosas: alimentan directamente Flash Memory
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear migración para tabla de feedback:

   Ruta: ~/yeyo-os/db/migrations/004_feedback.sql
   Contenido:

   -- ============================================
   -- YeyoOS — Feedback Schema
   -- Micro-fase 2.14 — Capa 2: Cerebro
   -- ============================================

   CREATE TABLE IF NOT EXISTS feedback (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       message_id UUID NOT NULL,
       conversation_id UUID,
       rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
       comment TEXT DEFAULT '',
       correction TEXT DEFAULT '',
       metadata JSONB DEFAULT '{}',
       created_at TIMESTAMPTZ DEFAULT NOW()
   );

   CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id);
   CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);
   CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback(created_at DESC);

2. Ejecutar migración:
   cd ~/yeyo-os
   source .venv/bin/activate
   python db/run_migration.py db/migrations/004_feedback.sql

3. Crear archivo src/chat/feedback.py:

   Ruta: ~/yeyo-os/src/chat/feedback.py
   Contenido:

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

4. Actualizar src/chat/__init__.py:

   Ruta: ~/yeyo-os/src/chat/__init__.py
   Contenido:

   from .service import ChatService
   from .contextual_service import ContextualChatService
   from .conversation import ConversationManager
   from .token_budget import TokenBudget
   from .system_prompt import SystemPromptBuilder
   from .feedback import FeedbackService

5. Crear tests:

   Ruta: ~/yeyo-os/tests/unit/chat/test_feedback.py
   Contenido:

   """
   Tests para FeedbackService — Micro-fase 2.14
   Tests unitarios y de integración.
   """

   import pytest
   import uuid
   from unittest.mock import AsyncMock, MagicMock
   from src.chat.feedback import FeedbackService


   class TestFeedbackValidation:
       """Tests de validación de input."""

       def test_rating_must_be_1_to_5(self):
           """Solo ratings 1-5 son válidos."""
           service = FeedbackService(pool=MagicMock())
           with pytest.raises(ValueError, match="entre 1 y 5"):
               import asyncio
               asyncio.get_event_loop().run_until_complete(
                   service.rate_response(str(uuid.uuid4()), rating=0)
               )

       def test_rating_6_rejected(self):
           service = FeedbackService(pool=MagicMock())
           with pytest.raises(ValueError):
               import asyncio
               asyncio.get_event_loop().run_until_complete(
                   service.rate_response(str(uuid.uuid4()), rating=6)
               )

       def test_empty_correction_rejected(self):
           service = FeedbackService(pool=MagicMock())
           with pytest.raises(ValueError, match="vacía"):
               import asyncio
               asyncio.get_event_loop().run_until_complete(
                   service.report_incorrect(str(uuid.uuid4()), correction="")
               )


   @pytest.mark.integration
   class TestFeedbackIntegration:
       """Tests de integración con PostgreSQL."""

       @pytest.fixture
       async def feedback_service(self):
           import os
           db_url = os.getenv(
               "DATABASE_URL",
               "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
           )
           mock_memory = AsyncMock()
           mock_memory.store.return_value = MagicMock(id="mem-123")
           service = await FeedbackService.create(db_url, flash_memory=mock_memory)
           yield service
           await service.close()

       @pytest.mark.asyncio
       async def test_rate_response(self, feedback_service):
           msg_id = str(uuid.uuid4())
           result = await feedback_service.rate_response(
               message_id=msg_id,
               rating=4,
               comment="Buena respuesta",
           )
           assert result["rating"] == 4
           assert result["message_id"] == msg_id

       @pytest.mark.asyncio
       async def test_rate_all_valid_ratings(self, feedback_service):
           for rating in [1, 2, 3, 4, 5]:
               result = await feedback_service.rate_response(
                   message_id=str(uuid.uuid4()),
                   rating=rating,
               )
               assert result["rating"] == rating

       @pytest.mark.asyncio
       async def test_report_incorrect_creates_correction(self, feedback_service):
           result = await feedback_service.report_incorrect(
               message_id=str(uuid.uuid4()),
               correction="Mi nombre es Diego, no Juan",
           )
           assert result["correction"] == "Mi nombre es Diego, no Juan"
           assert result["memory_created"] is not None

       @pytest.mark.asyncio
       async def test_get_feedback_stats(self, feedback_service):
           # Crear algunos feedbacks
           for i in range(3):
               await feedback_service.rate_response(
                   message_id=str(uuid.uuid4()),
                   rating=4,
               )
           stats = await feedback_service.get_feedback_stats()
           assert isinstance(stats, dict)
           assert "total_feedback" in stats
           assert "average_rating" in stats
           assert "rating_distribution" in stats
           assert "total_corrections" in stats
           assert stats["total_feedback"] > 0

       @pytest.mark.asyncio
       async def test_get_feedback_for_message(self, feedback_service):
           msg_id = str(uuid.uuid4())
           await feedback_service.rate_response(msg_id, rating=5, comment="Perfecto")
           results = await feedback_service.get_feedback_for_message(msg_id)
           assert len(results) >= 1
           assert results[0]["rating"] == 5

6. Ejecutar migración:
   python db/run_migration.py db/migrations/004_feedback.sql

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/chat/test_feedback.py -v -k "Validation"
   python -m pytest tests/unit/chat/test_feedback.py -v -k "Integration" -m integration

VERIFICAR:
- [ ] Archivo db/migrations/004_feedback.sql creado y ejecutado
- [ ] Archivo src/chat/feedback.py existe
- [ ] rate_response() almacena calificación (1-5)
- [ ] report_incorrect() crea memoria tipo "correction" en Flash Memory
- [ ] Ratings fuera de rango rechazados (no 1-5)
- [ ] Corrección vacía rechazada
- [ ] get_feedback_stats() retorna estadísticas
- [ ] get_feedback_for_message() retorna feedback específico
- [ ] TODOS los tests pasan

SI FALLA:
- Schema no creado: ejecutar migración 004_feedback.sql
- asyncpg error: verificar DATABASE_URL
- Flash Memory mock: verificar que store() retorna Memory con id

NO HACER:
- No permitir ratings fuera de 1-5
- No borrar feedback (append-only)
- No ignorar correcciones del usuario (son las más valiosas para Flash Memory)
- No exponer datos sensibles en stats

GATE: FeedbackService almacena ratings, correcciones crean memorias en Flash Memory, validación funciona, stats calculados, todos los tests pasan.
```
