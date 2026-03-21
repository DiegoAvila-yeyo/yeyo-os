## ═══════════════════════════════════════
## MICRO-FASE 2.0 — Flash Memory Schema
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 2.0-1 [VSCODE] — Crear schema PostgreSQL para Flash Memory

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 2.0 de Capa 2 (Cerebro): crear el schema de PostgreSQL para Flash Memory, el sistema de memoria persistente de la IA.

CONTEXTO:
- Capa 0 completada: PostgreSQL 16 + pgvector, Redis 7, Ollama, Python 3.11, todo funcionando
- Capa 1 completada: Interfaces IAProvider, MemoriaProvider, Orquestador definidas
- Flash Memory es el corazón de la memoria de YeyoOS: NADA se borra, NUNCA
- Tiers: HOT (Redis, <1ms) / WARM (PG activo, <10ms) / COLD (PG archivo, <50ms)
- Embeddings: sentence-transformers, 384 dimensiones (CPU, no GPU)
- Checksums SHA-256 automáticos para integridad
- Hardware: GTX 1060 3GB VRAM, 16GB RAM, WSL2 Ubuntu

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear directorio de migraciones si no existe:
   mkdir -p db/migrations

2. Crear archivo db/migrations/002_flash_memory.sql:

   Ruta: ~/yeyo-os/db/migrations/002_flash_memory.sql
   Contenido:

   -- ============================================
   -- YeyoOS — Flash Memory Schema
   -- Micro-fase 2.0 — Capa 2: Cerebro
   -- REGLA SAGRADA: Las memorias NUNCA se borran
   -- ============================================

   -- Habilitar extensiones necesarias
   CREATE EXTENSION IF NOT EXISTS "pgcrypto";
   CREATE EXTENSION IF NOT EXISTS "vector";

   -- ============================================
   -- Tabla principal: flash_memories
   -- ============================================
   CREATE TABLE IF NOT EXISTS flash_memories (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       content TEXT NOT NULL,
       type VARCHAR(20) NOT NULL CHECK (type IN ('conversation', 'preference', 'fact', 'correction', 'skill')),
       tier VARCHAR(4) NOT NULL DEFAULT 'WARM' CHECK (tier IN ('HOT', 'WARM', 'COLD')),
       embedding vector(384),
       checksum VARCHAR(64) NOT NULL,
       access_count INTEGER DEFAULT 0,
       metadata JSONB DEFAULT '{}',
       source VARCHAR(100) DEFAULT 'user',
       created_at TIMESTAMPTZ DEFAULT NOW(),
       accessed_at TIMESTAMPTZ DEFAULT NOW(),
       updated_at TIMESTAMPTZ DEFAULT NOW()
   );

   -- ============================================
   -- TRIGGER SAGRADO: Prohibir DELETE
   -- ============================================
   CREATE OR REPLACE FUNCTION prevent_memory_delete()
   RETURNS TRIGGER AS $$
   BEGIN
       RAISE EXCEPTION 'Flash Memory: DELETE is FORBIDDEN. Memories are NEVER deleted.';
       RETURN NULL;
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER no_delete_memories
       BEFORE DELETE ON flash_memories
       FOR EACH ROW
       EXECUTE FUNCTION prevent_memory_delete();

   -- ============================================
   -- TRIGGER: Auto-generar checksum SHA-256
   -- ============================================
   CREATE OR REPLACE FUNCTION generate_memory_checksum()
   RETURNS TRIGGER AS $$
   BEGIN
       NEW.checksum = encode(digest(NEW.content || NEW.type || NEW.created_at::TEXT, 'sha256'), 'hex');
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER auto_checksum
       BEFORE INSERT ON flash_memories
       FOR EACH ROW
       EXECUTE FUNCTION generate_memory_checksum();

   -- ============================================
   -- TRIGGER: Actualizar updated_at automáticamente
   -- ============================================
   CREATE OR REPLACE FUNCTION update_memory_timestamp()
   RETURNS TRIGGER AS $$
   BEGIN
       NEW.updated_at = NOW();
       RETURN NEW;
   END;
   $$ LANGUAGE plpgsql;

   CREATE TRIGGER auto_update_timestamp
       BEFORE UPDATE ON flash_memories
       FOR EACH ROW
       EXECUTE FUNCTION update_memory_timestamp();

   -- ============================================
   -- Índices para rendimiento
   -- ============================================
   CREATE INDEX IF NOT EXISTS idx_memories_tier ON flash_memories(tier);
   CREATE INDEX IF NOT EXISTS idx_memories_type ON flash_memories(type);
   CREATE INDEX IF NOT EXISTS idx_memories_accessed ON flash_memories(accessed_at);
   CREATE INDEX IF NOT EXISTS idx_memories_access_count ON flash_memories(access_count DESC);
   CREATE INDEX IF NOT EXISTS idx_memories_created ON flash_memories(created_at DESC);

   -- Índice vectorial para búsqueda semántica (cosine similarity)
   -- ivfflat requiere al menos 100 filas para lists=100, usar lists=10 inicialmente
   -- Se puede recrear con más lists cuando haya más datos
   CREATE INDEX IF NOT EXISTS idx_memories_embedding
       ON flash_memories
       USING ivfflat (embedding vector_cosine_ops)
       WITH (lists = 10);

   -- ============================================
   -- Tabla: memory_associations
   -- Red neuronal de conexiones entre memorias
   -- ============================================
   CREATE TABLE IF NOT EXISTS memory_associations (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       source_id UUID NOT NULL REFERENCES flash_memories(id),
       target_id UUID NOT NULL REFERENCES flash_memories(id),
       relation_type VARCHAR(50) NOT NULL,
       strength FLOAT DEFAULT 1.0 CHECK (strength >= 0 AND strength <= 1),
       created_at TIMESTAMPTZ DEFAULT NOW(),
       CONSTRAINT no_self_association CHECK (source_id != target_id),
       CONSTRAINT unique_association UNIQUE (source_id, target_id, relation_type)
   );

   CREATE INDEX IF NOT EXISTS idx_associations_source ON memory_associations(source_id);
   CREATE INDEX IF NOT EXISTS idx_associations_target ON memory_associations(target_id);
   CREATE INDEX IF NOT EXISTS idx_associations_type ON memory_associations(relation_type);

   -- ============================================
   -- Tabla: memory_audit_log (append-only)
   -- Registro inmutable de todas las operaciones
   -- ============================================
   CREATE TABLE IF NOT EXISTS memory_audit_log (
       id BIGSERIAL PRIMARY KEY,
       memory_id UUID,
       action VARCHAR(20) NOT NULL,
       details JSONB DEFAULT '{}',
       created_at TIMESTAMPTZ DEFAULT NOW()
   );

   CREATE INDEX IF NOT EXISTS idx_audit_memory_id ON memory_audit_log(memory_id);
   CREATE INDEX IF NOT EXISTS idx_audit_action ON memory_audit_log(action);
   CREATE INDEX IF NOT EXISTS idx_audit_created ON memory_audit_log(created_at DESC);

3. Crear script para ejecutar la migración:

   Ruta: ~/yeyo-os/db/run_migration.py
   Contenido:

   """
   YeyoOS — Ejecutor de migraciones
   Ejecuta archivos SQL contra PostgreSQL.
   Uso: python db/run_migration.py db/migrations/002_flash_memory.sql
   """

   import sys
   import os
   import asyncio
   import asyncpg


   async def run_migration(sql_file: str):
       database_url = os.getenv(
           "DATABASE_URL",
           "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
       )

       conn = await asyncpg.connect(database_url)
       try:
           with open(sql_file, "r") as f:
               sql = f.read()
           await conn.execute(sql)
           print(f"✅ Migración ejecutada: {sql_file}")
       except Exception as e:
           print(f"❌ Error en migración: {e}")
           raise
       finally:
           await conn.close()


   if __name__ == "__main__":
       if len(sys.argv) < 2:
           print("Uso: python db/run_migration.py <archivo.sql>")
           sys.exit(1)
       asyncio.run(run_migration(sys.argv[1]))

4. Crear tests del schema:

   Ruta: ~/yeyo-os/tests/integration/memory/__init__.py
   Contenido: (archivo vacío)

   Ruta: ~/yeyo-os/tests/integration/memory/test_flash_memory_schema.py
   Contenido:

   """
   Tests de integración para Flash Memory Schema — Micro-fase 2.0
   Requieren PostgreSQL corriendo con pgvector.
   Ejecutar con: pytest tests/integration/memory/test_flash_memory_schema.py -v
   """

   import pytest
   import asyncpg
   import os
   import uuid


   pytestmark = pytest.mark.integration

   DATABASE_URL = os.getenv(
       "DATABASE_URL",
       "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
   )


   @pytest.fixture
   async def db_conn():
       conn = await asyncpg.connect(DATABASE_URL)
       yield conn
       await conn.close()


   @pytest.mark.asyncio
   async def test_flash_memories_table_exists(db_conn):
       """La tabla flash_memories debe existir."""
       result = await db_conn.fetchval(
           "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'flash_memories')"
       )
       assert result is True


   @pytest.mark.asyncio
   async def test_memory_associations_table_exists(db_conn):
       """La tabla memory_associations debe existir."""
       result = await db_conn.fetchval(
           "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memory_associations')"
       )
       assert result is True


   @pytest.mark.asyncio
   async def test_memory_audit_log_table_exists(db_conn):
       """La tabla memory_audit_log debe existir."""
       result = await db_conn.fetchval(
           "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memory_audit_log')"
       )
       assert result is True


   @pytest.mark.asyncio
   async def test_insert_memory_generates_checksum(db_conn):
       """INSERT debe auto-generar checksum SHA-256."""
       row = await db_conn.fetchrow(
           """
           INSERT INTO flash_memories (content, type, checksum)
           VALUES ($1, $2, 'placeholder')
           RETURNING id, checksum
           """,
           "Test memory content",
           "fact"
       )
       assert row["checksum"] is not None
       assert len(row["checksum"]) == 64  # SHA-256 hex = 64 chars
       assert row["checksum"] != "placeholder"  # trigger overwrites
       # Limpiar: mover a COLD en vez de borrar (no podemos borrar)
       await db_conn.execute(
           "UPDATE flash_memories SET tier = 'COLD' WHERE id = $1",
           row["id"]
       )


   @pytest.mark.asyncio
   async def test_delete_memory_raises_exception(db_conn):
       """DELETE debe ser IMPOSIBLE — trigger lo previene."""
       row = await db_conn.fetchrow(
           """
           INSERT INTO flash_memories (content, type, checksum)
           VALUES ($1, $2, 'placeholder')
           RETURNING id
           """,
           "Memory that must never be deleted",
           "fact"
       )
       with pytest.raises(asyncpg.RaiseError, match="FORBIDDEN"):
           await db_conn.execute(
               "DELETE FROM flash_memories WHERE id = $1",
               row["id"]
           )


   @pytest.mark.asyncio
   async def test_invalid_type_rejected(db_conn):
       """Solo los tipos permitidos son aceptados."""
       with pytest.raises(asyncpg.CheckViolationError):
           await db_conn.execute(
               """
               INSERT INTO flash_memories (content, type, checksum)
               VALUES ($1, $2, 'placeholder')
               """,
               "Invalid type test",
               "invalid_type"
           )


   @pytest.mark.asyncio
   async def test_invalid_tier_rejected(db_conn):
       """Solo los tiers HOT/WARM/COLD son aceptados."""
       with pytest.raises(asyncpg.CheckViolationError):
           await db_conn.execute(
               """
               INSERT INTO flash_memories (content, type, tier, checksum)
               VALUES ($1, $2, $3, 'placeholder')
               """,
               "Invalid tier test",
               "fact",
               "INVALID"
           )


   @pytest.mark.asyncio
   async def test_default_tier_is_warm(db_conn):
       """El tier por defecto debe ser WARM."""
       row = await db_conn.fetchrow(
           """
           INSERT INTO flash_memories (content, type, checksum)
           VALUES ($1, $2, 'placeholder')
           RETURNING tier
           """,
           "Default tier test",
           "conversation"
       )
       assert row["tier"] == "WARM"


   @pytest.mark.asyncio
   async def test_pgvector_index_exists(db_conn):
       """El índice vectorial para embeddings debe existir."""
       result = await db_conn.fetchval(
           """
           SELECT EXISTS (
               SELECT 1 FROM pg_indexes
               WHERE indexname = 'idx_memories_embedding'
           )
           """
       )
       assert result is True


   @pytest.mark.asyncio
   async def test_associations_self_reference_blocked(db_conn):
       """No se pueden crear asociaciones consigo mismo."""
       row = await db_conn.fetchrow(
           """
           INSERT INTO flash_memories (content, type, checksum)
           VALUES ($1, $2, 'placeholder')
           RETURNING id
           """,
           "Self-reference test",
           "fact"
       )
       with pytest.raises(asyncpg.CheckViolationError):
           await db_conn.execute(
               """
               INSERT INTO memory_associations (source_id, target_id, relation_type)
               VALUES ($1, $1, 'self')
               """,
               row["id"]
           )


   @pytest.mark.asyncio
   async def test_audit_log_insert(db_conn):
       """Se pueden insertar registros en audit_log."""
       test_id = uuid.uuid4()
       await db_conn.execute(
           """
           INSERT INTO memory_audit_log (memory_id, action, details)
           VALUES ($1, $2, $3)
           """,
           test_id,
           "CREATE",
           '{"test": true}'
       )
       row = await db_conn.fetchrow(
           "SELECT * FROM memory_audit_log WHERE memory_id = $1",
           test_id
       )
       assert row is not None
       assert row["action"] == "CREATE"


   @pytest.mark.asyncio
   async def test_association_strength_range(db_conn):
       """La fuerza de asociación debe estar entre 0 y 1."""
       row1 = await db_conn.fetchrow(
           """
           INSERT INTO flash_memories (content, type, checksum)
           VALUES ($1, $2, 'placeholder') RETURNING id
           """,
           "Strength test 1", "fact"
       )
       row2 = await db_conn.fetchrow(
           """
           INSERT INTO flash_memories (content, type, checksum)
           VALUES ($1, $2, 'placeholder') RETURNING id
           """,
           "Strength test 2", "fact"
       )
       with pytest.raises(asyncpg.CheckViolationError):
           await db_conn.execute(
               """
               INSERT INTO memory_associations (source_id, target_id, relation_type, strength)
               VALUES ($1, $2, 'related', 1.5)
               """,
               row1["id"], row2["id"]
           )

5. Instalar dependencia:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install asyncpg

6. Ejecutar la migración:
   cd ~/yeyo-os
   source .venv/bin/activate
   python db/run_migration.py db/migrations/002_flash_memory.sql

7. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/integration/memory/test_flash_memory_schema.py -v

VERIFICAR:
- [ ] Archivo db/migrations/002_flash_memory.sql existe
- [ ] Migración ejecuta sin errores
- [ ] Tabla flash_memories creada con todas las columnas
- [ ] Tabla memory_associations creada con constraints
- [ ] Tabla memory_audit_log creada
- [ ] Trigger prevent_memory_delete funciona: DELETE lanza excepción
- [ ] Trigger auto_checksum funciona: checksum se genera automáticamente
- [ ] Índice pgvector creado para búsqueda semántica
- [ ] Tipos inválidos rechazados (CHECK constraint)
- [ ] Tiers inválidos rechazados (CHECK constraint)
- [ ] TODOS los tests pasan

SI FALLA:
- pgvector no instalado: `CREATE EXTENSION vector` falla → instalar pgvector en PostgreSQL
- pgcrypto no disponible: `CREATE EXTENSION pgcrypto` falla → instalar extensión
- asyncpg no instalado: `pip install asyncpg`
- Conexión rechazada: verificar que PostgreSQL está corriendo
- Base de datos no existe: `createdb yeyoos`

NO HACER:
- No crear ningún método DELETE en código
- No crear ningún endpoint DELETE para memorias
- No modificar el trigger prevent_memory_delete
- No usar ivfflat con lists=100 sin suficientes datos (usar lists=10 inicialmente)
- No implementar lógica de negocio en SQL (eso va en Python)

GATE: Schema creado, trigger anti-DELETE funciona, checksum se auto-genera, índice pgvector existe, tablas de asociaciones y audit existen, todos los tests pasan.
```
