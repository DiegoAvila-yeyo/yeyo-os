## ═══════════════════════════════════════
## MICRO-FASE 2.7 — Conversation Manager
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.7-1 [VSCODE] — Implementar gestor de conversaciones

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.7 de Capa 2 (Cerebro): implementar el ConversationManager que gestiona sesiones de conversación y persiste el historial en PostgreSQL.

CONTEXTO:
- Micro-fases 2.0-2.6 completadas: Flash Memory, Cache, Embeddings, Chat Contextual funcionando
- Las conversaciones se almacenan en PostgreSQL (no en memoria)
- Cada conversación tiene un UUID único
- Los mensajes se almacenan en orden cronológico
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear migración para tablas de conversaciones:

   Ruta: ~/yeyo-os/db/migrations/003_conversations.sql
   Contenido:

   -- ============================================
   -- YeyoOS — Conversations Schema
   -- Micro-fase 2.7 — Capa 2: Cerebro
   -- ============================================

   CREATE TABLE IF NOT EXISTS conversations (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       title VARCHAR(200) DEFAULT 'Nueva conversación',
       metadata JSONB DEFAULT '{}',
       message_count INTEGER DEFAULT 0,
       created_at TIMESTAMPTZ DEFAULT NOW(),
       updated_at TIMESTAMPTZ DEFAULT NOW()
   );

   CREATE TABLE IF NOT EXISTS conversation_messages (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       conversation_id UUID NOT NULL REFERENCES conversations(id),
       role VARCHAR(20) NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
       content TEXT NOT NULL,
       tokens INTEGER DEFAULT 0,
       metadata JSONB DEFAULT '{}',
       created_at TIMESTAMPTZ DEFAULT NOW()
   );

   CREATE INDEX IF NOT EXISTS idx_messages_conversation
       ON conversation_messages(conversation_id, created_at);
   CREATE INDEX IF NOT EXISTS idx_conversations_updated
       ON conversations(updated_at DESC);

   -- Trigger para actualizar message_count y updated_at
   CREATE OR REPLACE FUNCTION update_conversation_on_message()
   RETURNS TRIGGER AS $$
   BEGIN
       UPDATE conversations
       SET message_count = message_count + 1,
           updated_at = NOW()
       WHERE id = NEW.conversation_id;
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER auto_update_conversation
       AFTER INSERT ON conversation_messages
       FOR EACH ROW
       EXECUTE FUNCTION update_conversation_on_message();

2. Ejecutar migración:
   cd ~/yeyo-os
   source .venv/bin/activate
   python db/run_migration.py db/migrations/003_conversations.sql

3. Crear archivo src/chat/conversation.py:

   Ruta: ~/yeyo-os/src/chat/conversation.py
   Contenido:

   """
   YeyoOS — ConversationManager (Gestor de Conversaciones)
   Micro-fase 2.7 — Capa 2: Cerebro

   Gestiona sesiones de conversación: crear, agregar mensajes,
   obtener historial. Todo persistido en PostgreSQL.
   """

   import json
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
           pool = await asyncpg.create_pool(
               database_url,
               min_size=2,
               max_size=10,
           )
           return cls(pool)

       async def create_conversation(self, title: str = "Nueva conversación") -> str:
           """
           Crea una nueva conversación.
           Retorna el UUID de la conversación creada.
           """
           async with self.pool.acquire() as conn:
               row = await conn.fetchrow(
                   """
                   INSERT INTO conversations (title)
                   VALUES ($1)
                   RETURNING id
                   """,
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
           import uuid as uuid_mod
           conv_id = (
               conversation_id
               if isinstance(conversation_id, uuid_mod.UUID)
               else uuid_mod.UUID(conversation_id)
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
           Obtiene el historial de mensajes de una conversación.
           Retorna los últimos `limit` mensajes en orden cronológico.
           """
           import uuid as uuid_mod
           conv_id = (
               conversation_id
               if isinstance(conversation_id, uuid_mod.UUID)
               else uuid_mod.UUID(conversation_id)
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

           # Revertir para orden cronológico (los más recientes están primero en la query)
           messages = [
               IAMessage(role=row["role"], content=row["content"])
               for row in reversed(rows)
           ]
           return messages

       async def list_conversations(self, limit: int = 50) -> list[dict]:
           """Lista todas las conversaciones, las más recientes primero."""
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
           import uuid as uuid_mod
           conv_id = (
               conversation_id
               if isinstance(conversation_id, uuid_mod.UUID)
               else uuid_mod.UUID(conversation_id)
           )

           async with self.pool.acquire() as conn:
               row = await conn.fetchrow(
                   """
                   SELECT id, title, message_count, metadata, created_at, updated_at
                   FROM conversations
                   WHERE id = $1
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
           import uuid as uuid_mod
           conv_id = (
               conversation_id
               if isinstance(conversation_id, uuid_mod.UUID)
               else uuid_mod.UUID(conversation_id)
           )

           async with self.pool.acquire() as conn:
               await conn.execute(
                   """
                   UPDATE conversations SET title = $1, updated_at = NOW()
                   WHERE id = $2
                   """,
                   title,
                   conv_id,
               )

       async def close(self):
           """Cierra el connection pool."""
           await self.pool.close()

4. Actualizar src/chat/__init__.py:

   Ruta: ~/yeyo-os/src/chat/__init__.py
   Contenido:

   from .service import ChatService
   from .contextual_service import ContextualChatService
   from .conversation import ConversationManager

5. Crear tests:

   Ruta: ~/yeyo-os/tests/integration/chat/__init__.py
   Contenido: (archivo vacío)

   Ruta: ~/yeyo-os/tests/integration/chat/test_conversation_manager.py
   Contenido:

   """
   Tests de integración para ConversationManager — Micro-fase 2.7
   Requieren PostgreSQL corriendo con schema de conversaciones.
   """

   import pytest
   import os
   from src.chat.conversation import ConversationManager
   from src.ia.interfaces import IAMessage


   pytestmark = pytest.mark.integration

   DATABASE_URL = os.getenv(
       "DATABASE_URL",
       "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
   )


   @pytest.fixture
   async def conv_manager():
       cm = await ConversationManager.create(DATABASE_URL)
       yield cm
       await cm.close()


   @pytest.mark.asyncio
   async def test_create_conversation_returns_uuid(conv_manager):
       """create_conversation() debe retornar un UUID válido."""
       conv_id = await conv_manager.create_conversation()
       assert isinstance(conv_id, str)
       assert len(conv_id) == 36  # UUID format


   @pytest.mark.asyncio
   async def test_create_conversation_with_title(conv_manager):
       """Conversación debe tener el título especificado."""
       conv_id = await conv_manager.create_conversation(title="Mi chat")
       conv = await conv_manager.get_conversation(conv_id)
       assert conv is not None
       assert conv["title"] == "Mi chat"


   @pytest.mark.asyncio
   async def test_add_message(conv_manager):
       """add_message() debe agregar mensaje a la conversación."""
       conv_id = await conv_manager.create_conversation()
       await conv_manager.add_message(conv_id, "user", "Hola YeyoOS")
       history = await conv_manager.get_history(conv_id)
       assert len(history) == 1
       assert history[0].role == "user"
       assert history[0].content == "Hola YeyoOS"


   @pytest.mark.asyncio
   async def test_messages_in_order(conv_manager):
       """Los mensajes deben retornarse en orden cronológico."""
       conv_id = await conv_manager.create_conversation()
       await conv_manager.add_message(conv_id, "user", "Primero")
       await conv_manager.add_message(conv_id, "assistant", "Segundo")
       await conv_manager.add_message(conv_id, "user", "Tercero")
       history = await conv_manager.get_history(conv_id)
       assert len(history) == 3
       assert history[0].content == "Primero"
       assert history[1].content == "Segundo"
       assert history[2].content == "Tercero"


   @pytest.mark.asyncio
   async def test_history_limit(conv_manager):
       """get_history() debe respetar el límite."""
       conv_id = await conv_manager.create_conversation()
       for i in range(10):
           await conv_manager.add_message(conv_id, "user", f"Mensaje {i}")
       history = await conv_manager.get_history(conv_id, limit=3)
       assert len(history) == 3
       # Debe retornar los 3 más recientes
       assert history[-1].content == "Mensaje 9"


   @pytest.mark.asyncio
   async def test_get_history_returns_ia_messages(conv_manager):
       """get_history() debe retornar IAMessage."""
       conv_id = await conv_manager.create_conversation()
       await conv_manager.add_message(conv_id, "user", "Test")
       history = await conv_manager.get_history(conv_id)
       assert all(isinstance(m, IAMessage) for m in history)


   @pytest.mark.asyncio
   async def test_list_conversations(conv_manager):
       """list_conversations() debe retornar lista de conversaciones."""
       await conv_manager.create_conversation(title="Conv test")
       convos = await conv_manager.list_conversations()
       assert isinstance(convos, list)
       assert len(convos) > 0
       assert all("id" in c for c in convos)
       assert all("title" in c for c in convos)


   @pytest.mark.asyncio
   async def test_get_conversation_not_found(conv_manager):
       """get_conversation() con ID inexistente retorna None."""
       result = await conv_manager.get_conversation(
           "00000000-0000-0000-0000-000000000000"
       )
       assert result is None


   @pytest.mark.asyncio
   async def test_message_count_auto_increments(conv_manager):
       """message_count debe incrementarse automáticamente con trigger."""
       conv_id = await conv_manager.create_conversation()
       await conv_manager.add_message(conv_id, "user", "Uno")
       await conv_manager.add_message(conv_id, "assistant", "Dos")
       conv = await conv_manager.get_conversation(conv_id)
       assert conv["message_count"] == 2


   @pytest.mark.asyncio
   async def test_messages_have_timestamps(conv_manager):
       """Los mensajes deben tener timestamps."""
       conv_id = await conv_manager.create_conversation()
       await conv_manager.add_message(conv_id, "user", "Test timestamp")
       conv = await conv_manager.get_conversation(conv_id)
       assert conv["created_at"] is not None
       assert conv["updated_at"] is not None

6. Ejecutar migración:
   python db/run_migration.py db/migrations/003_conversations.sql

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/integration/chat/test_conversation_manager.py -v

VERIFICAR:
- [ ] Archivo db/migrations/003_conversations.sql creado y ejecutado
- [ ] Archivo src/chat/conversation.py existe
- [ ] create_conversation() retorna UUID
- [ ] add_message() almacena mensajes
- [ ] get_history() retorna mensajes en orden cronológico
- [ ] get_history() respeta límite
- [ ] list_conversations() retorna todas las conversaciones
- [ ] message_count se incrementa automáticamente (trigger)
- [ ] get_conversation() retorna None para ID inexistente
- [ ] TODOS los tests pasan

SI FALLA:
- Schema no creado: ejecutar migración 003_conversations.sql
- asyncpg error: verificar DATABASE_URL
- Trigger error: verificar que la migración se ejecutó correctamente
- Import IAMessage: verificar Capa 1

NO HACER:
- No borrar conversaciones (consistente con la filosofía de no borrar)
- No almacenar respuestas en Flash Memory automáticamente (eso es micro-fase 2.9)
- No implementar búsqueda de conversaciones por contenido todavía

GATE: ConversationManager funcional, conversaciones y mensajes persisten en PG, historial en orden cronológico, message_count auto-incrementa, todos los tests pasan.
```
