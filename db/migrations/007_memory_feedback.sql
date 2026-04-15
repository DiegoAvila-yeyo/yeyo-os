-- ============================================
-- YeyoOS — Memory Feedback, Quality & Training
-- Micro-fase 3.30 — Capa 3: Cuerpo
-- Extiende Flash Memory con señales de calidad
-- y corpus de entrenamiento para fine-tuning
-- ============================================

-- ─── Extensiones a flash_memories ───────────────────────────────────────────────
ALTER TABLE flash_memories ADD COLUMN IF NOT EXISTS importance FLOAT DEFAULT 0.5;
ALTER TABLE flash_memories ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_memories_importance ON flash_memories (importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_tags ON flash_memories USING gin(tags);

-- ─── Tabla: feedback del usuario sobre memorias ────────────────────────────────
-- El usuario puede aprobar, rechazar o corregir memorias individuales.
-- Nunca se modifica la memoria original — el feedback es un registro aparte.
CREATE TABLE IF NOT EXISTS memory_feedback (
    id BIGSERIAL PRIMARY KEY,
    memory_id UUID NOT NULL REFERENCES flash_memories(id),
    feedback_type VARCHAR(30) NOT NULL CHECK (
        feedback_type IN ('positive', 'negative', 'correction', 'favorite', 'reject', 'training_approved')
    ),
    score FLOAT CHECK (score IS NULL OR (score >= 0.0 AND score <= 1.0)),
    comment TEXT DEFAULT '',
    source VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_memory ON memory_feedback(memory_id);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON memory_feedback(feedback_type);
CREATE INDEX IF NOT EXISTS idx_feedback_created ON memory_feedback(created_at DESC);

-- ─── Tabla: señales de calidad por memoria ─────────────────────────────────────
-- Acumula métricas de calidad, verificación y confianza.
CREATE TABLE IF NOT EXISTS memory_quality_signals (
    id BIGSERIAL PRIMARY KEY,
    memory_id UUID NOT NULL REFERENCES flash_memories(id),
    correctness_score FLOAT DEFAULT 0.0,
    security_score FLOAT DEFAULT 0.0,
    compatibility_score FLOAT DEFAULT 0.0,
    confidence_score FLOAT DEFAULT 0.0,
    verification_status VARCHAR(30) DEFAULT 'unverified' CHECK (
        verification_status IN ('unverified', 'partial', 'verified', 'rejected')
    ),
    benchmark_name VARCHAR(100),
    benchmark_result JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_memory ON memory_quality_signals(memory_id);
CREATE INDEX IF NOT EXISTS idx_quality_status ON memory_quality_signals(verification_status);

-- ─── Tabla: corpus de entrenamiento para fine-tuning ──────────────────────────
-- Memorias promovidas a corpus de entrenamiento para YeyoDojo / YeyoHack.
-- El usuario marca ⭐ y la memoria se añade con split train/valid/test.
CREATE TABLE IF NOT EXISTS memory_training_corpus (
    id BIGSERIAL PRIMARY KEY,
    memory_id UUID NOT NULL REFERENCES flash_memories(id),
    corpus_type VARCHAR(50) NOT NULL CHECK (
        corpus_type IN (
            'code_example', 'correction_pair', 'preference_pair',
            'tool_trace', 'benchmark_case', 'refusal_example',
            'reasoning_example', 'action_reference', 'prompt_example'
        )
    ),
    split VARCHAR(10) NOT NULL DEFAULT 'train' CHECK (split IN ('train', 'valid', 'test')),
    promoted BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_corpus_memory ON memory_training_corpus(memory_id);
CREATE INDEX IF NOT EXISTS idx_corpus_type ON memory_training_corpus(corpus_type);
CREATE INDEX IF NOT EXISTS idx_corpus_split ON memory_training_corpus(split);
CREATE INDEX IF NOT EXISTS idx_corpus_promoted ON memory_training_corpus(promoted) WHERE promoted = TRUE;
