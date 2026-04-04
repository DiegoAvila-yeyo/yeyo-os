-- Migración: vector(384) -> vector(768) para nomic-embed-text
-- Fecha: 2026-04-04

BEGIN;

-- 1. Eliminar el índice ivfflat existente (depende de la dimensión)
DROP INDEX IF EXISTS idx_memories_embedding;

-- 2. Cambiar la columna a vector(768), NULL donde había datos (son incorrectos de todas formas)
ALTER TABLE flash_memories 
  ALTER COLUMN embedding TYPE vector(768) 
  USING NULL;

-- 3. Recrear el índice ivfflat para 768 dimensiones
-- lists=100 es apropiado para hasta ~1M de registros
CREATE INDEX idx_memories_embedding 
  ON flash_memories 
  USING ivfflat (embedding vector_cosine_ops) 
  WITH (lists = 100);

COMMIT;

-- Verificar
SELECT 
  column_name, 
  udt_name,
  character_maximum_length
FROM information_schema.columns 
WHERE table_name = 'flash_memories' AND column_name = 'embedding';
