-- ============================================================
-- YeyoNet: Red privada de cómputo distribuido
-- Migration 008 — Tablas de identidad, invitaciones, jobs
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Nodos de la red ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS yeyonet_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    role VARCHAR(10) NOT NULL DEFAULT 'satellite' CHECK (role IN ('central', 'satellite')),
    mode VARCHAR(10) NOT NULL DEFAULT 'completo' CHECK (mode IN ('completo', 'ligero', 'minimo')),
    status VARCHAR(10) NOT NULL DEFAULT 'offline' CHECK (status IN ('online', 'idle', 'offline')),

    -- Auth
    auth_token VARCHAR(256) NOT NULL UNIQUE,

    -- Permisos del satélite (otorgados por el Central)
    permissions JSONB NOT NULL DEFAULT '["chat"]',
    -- Array de: "chat", "grafos", "memoria", "control"

    -- Nivel de visibilidad (1-4)
    visibility_level INTEGER NOT NULL DEFAULT 1 CHECK (visibility_level BETWEEN 1 AND 4),
    -- 1=solo resultados, 2=actividad, 3=memoria completa, 4=control total

    -- Recursos reportados por ResourceMonitor
    resources JSONB DEFAULT '{}',
    -- {cpu_percent, ram_free_gb, gpu_name, gpu_vram_mb, gpu_usage_percent, ollama_models[], active_jobs}

    -- Metadata
    ollama_host VARCHAR(200),
    ip_address VARCHAR(45),
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Invitaciones (códigos YEYO-XXXX-XXXX-XXXX) ────────────
CREATE TABLE IF NOT EXISTS yeyonet_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(19) NOT NULL UNIQUE,
    -- Formato: YEYO-XXXX-XXXX-XXXX

    -- Config de la invitación
    satellite_name VARCHAR(100) NOT NULL,
    permissions JSONB NOT NULL DEFAULT '["chat"]',
    visibility_level INTEGER NOT NULL DEFAULT 1 CHECK (visibility_level BETWEEN 1 AND 4),

    -- Estado
    used BOOLEAN NOT NULL DEFAULT FALSE,
    used_by_node_id UUID REFERENCES yeyonet_nodes(id),
    used_at TIMESTAMPTZ,

    -- Expiración
    expires_at TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Jobs distribuidos ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS yeyonet_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Tipo de trabajo
    type VARCHAR(30) NOT NULL CHECK (type IN (
        'image_generate', 'video_render', 'text_inference', 'training_step',
        'memory_sync', 'custom'
    )),

    -- Estado del job
    status VARCHAR(15) NOT NULL DEFAULT 'queued' CHECK (status IN (
        'queued', 'assigned', 'running', 'completed', 'failed', 'cancelled'
    )),

    -- Asignación
    requested_by UUID REFERENCES yeyonet_nodes(id),
    assigned_to UUID REFERENCES yeyonet_nodes(id),

    -- Payload y resultado
    payload JSONB NOT NULL DEFAULT '{}',
    -- image_generate: {prompt, negative_prompt, width, height, steps, count}
    -- video_render: {input_url, effects, chunk_start_s, chunk_end_s, output_format}
    -- text_inference: {prompt, system, model, temperature, max_tokens}
    -- training_step: {corpus_id, base_model, lora_config}

    result JSONB,
    -- {output_url, tokens_used, duration_ms, error}

    -- Progreso (0-100)
    progress INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    progress_detail VARCHAR(200),

    -- Prioridad (mayor = más urgente)
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),

    -- Retry
    attempt INTEGER DEFAULT 1,
    max_attempts INTEGER DEFAULT 3,

    -- Tiempos
    timeout_seconds INTEGER DEFAULT 600,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Resultados por nodo (para jobs distribuidos multi-nodo) ─
CREATE TABLE IF NOT EXISTS yeyonet_job_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES yeyonet_jobs(id),
    node_id UUID NOT NULL REFERENCES yeyonet_nodes(id),

    -- Chunk info (para video render distribuido)
    chunk_index INTEGER,
    chunk_total INTEGER,

    -- Resultado
    status VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed'
    )),
    data JSONB DEFAULT '{}',
    error TEXT,

    -- Métricas
    duration_ms INTEGER,
    cpu_used_percent FLOAT,
    gpu_used_percent FLOAT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(job_id, node_id, chunk_index)
);

-- ─── Triggers ───────────────────────────────────────────────

-- Auto-update timestamps
CREATE OR REPLACE FUNCTION yeyonet_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auto_update_nodes_timestamp
    BEFORE UPDATE ON yeyonet_nodes
    FOR EACH ROW EXECUTE FUNCTION yeyonet_update_timestamp();

CREATE TRIGGER auto_update_jobs_timestamp
    BEFORE UPDATE ON yeyonet_jobs
    FOR EACH ROW EXECUTE FUNCTION yeyonet_update_timestamp();

-- ─── Indexes ────────────────────────────────────────────────

-- Nodes
CREATE INDEX IF NOT EXISTS idx_yeyonet_nodes_status ON yeyonet_nodes(status);
CREATE INDEX IF NOT EXISTS idx_yeyonet_nodes_role ON yeyonet_nodes(role);
CREATE INDEX IF NOT EXISTS idx_yeyonet_nodes_last_seen ON yeyonet_nodes(last_seen_at DESC);

-- Invitations
CREATE INDEX IF NOT EXISTS idx_yeyonet_invitations_code ON yeyonet_invitations(code);
CREATE INDEX IF NOT EXISTS idx_yeyonet_invitations_used ON yeyonet_invitations(used) WHERE NOT used;

-- Jobs
CREATE INDEX IF NOT EXISTS idx_yeyonet_jobs_status ON yeyonet_jobs(status);
CREATE INDEX IF NOT EXISTS idx_yeyonet_jobs_type ON yeyonet_jobs(type);
CREATE INDEX IF NOT EXISTS idx_yeyonet_jobs_assigned ON yeyonet_jobs(assigned_to);
CREATE INDEX IF NOT EXISTS idx_yeyonet_jobs_queued ON yeyonet_jobs(priority DESC, created_at ASC)
    WHERE status = 'queued';

-- Job Results
CREATE INDEX IF NOT EXISTS idx_yeyonet_results_job ON yeyonet_job_results(job_id);
CREATE INDEX IF NOT EXISTS idx_yeyonet_results_node ON yeyonet_job_results(node_id);
