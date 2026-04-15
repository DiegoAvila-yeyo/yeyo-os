-- ============================================================
-- Cloud Memory Sync Table — Run ONCE in Supabase SQL Editor
-- ============================================================
-- This creates the cloud relay table for YeyoOS memory sync.
-- Each PC keeps its own local PostgreSQL; Supabase acts as
-- the shared cloud relay so memories propagate between nodes.
-- ============================================================

CREATE TABLE cloud_memories (
    id UUID PRIMARY KEY,
    content TEXT NOT NULL,
    type VARCHAR(20) NOT NULL,
    tier VARCHAR(4) NOT NULL DEFAULT 'WARM',
    checksum VARCHAR(64) NOT NULL UNIQUE,
    access_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    source VARCHAR(100) DEFAULT 'user',
    namespace VARCHAR(100) DEFAULT 'general',
    importance FLOAT DEFAULT 0.5,
    tags TEXT[] DEFAULT '{}',
    origin_node_id VARCHAR(100),  -- Which PC created this memory
    created_at TIMESTAMPTZ DEFAULT NOW(),
    accessed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast sync queries
CREATE INDEX idx_cloud_memories_synced ON cloud_memories(synced_at);
CREATE INDEX idx_cloud_memories_checksum ON cloud_memories(checksum);
CREATE INDEX idx_cloud_memories_origin ON cloud_memories(origin_node_id);

-- NOTE: No embedding column (too large for free tier, and each PC generates its own embeddings)
-- NOTE: No delete trigger (cloud follows same sacred rule: memories NEVER deleted)

-- Enable Row Level Security (optional, for multi-user future)
ALTER TABLE cloud_memories ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all for authenticated" ON cloud_memories FOR ALL USING (true);
