-- Agrega columna namespace a flash_memories para separar memorias por nodo/contexto
-- chat:usuario  → memorias del nodo Chat
-- codigo:usuario → memorias del nodo Código
-- personal       → info personal (nombre, preferencias)
-- preferencias   → configuraciones del usuario

ALTER TABLE flash_memories
    ADD COLUMN IF NOT EXISTS namespace VARCHAR(100) DEFAULT 'chat:usuario';

CREATE INDEX IF NOT EXISTS idx_flash_memories_namespace
    ON flash_memories (namespace);

-- Marcar memorias existentes como chat:usuario (su origen real)
UPDATE flash_memories SET namespace = 'chat:usuario' WHERE namespace IS NULL;
