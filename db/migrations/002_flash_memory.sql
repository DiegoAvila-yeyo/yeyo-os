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

DROP TRIGGER IF EXISTS no_delete_memories ON flash_memories;
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

DROP TRIGGER IF EXISTS auto_checksum ON flash_memories;
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

DROP TRIGGER IF EXISTS auto_update_timestamp ON flash_memories;
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
-- ivfflat: lists=10 inicialmente (recrear con lists=100 cuando haya >1000 filas)
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
