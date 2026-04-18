-- ============================================================
-- YeyoNet Pipeline Ring Pilot
-- Migration 014 — Runs, steps, artifacts y pipeline_step jobs
-- ============================================================

ALTER TABLE yeyonet_jobs DROP CONSTRAINT IF EXISTS yeyonet_jobs_type_check;
ALTER TABLE yeyonet_jobs
    ADD CONSTRAINT yeyonet_jobs_type_check CHECK (type IN (
        'image_generate', 'video_render', 'text_inference', 'training_step',
        'memory_sync', 'custom', 'pipeline_step'
    ));

CREATE TABLE IF NOT EXISTS yeyonet_pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flow_id VARCHAR(100) NOT NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'cancelled'
    )),
    requested_by UUID REFERENCES yeyonet_nodes(id),
    ring_node_ids JSONB NOT NULL DEFAULT '[]',
    current_step_index INTEGER NOT NULL DEFAULT 0,
    next_ring_index INTEGER NOT NULL DEFAULT 0,
    input_payload JSONB NOT NULL DEFAULT '{}',
    output_payload JSONB,
    error TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yeyonet_pipeline_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES yeyonet_pipeline_runs(id) ON DELETE CASCADE,
    step_index INTEGER NOT NULL,
    step_type VARCHAR(50) NOT NULL,
    status VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'assigned', 'running', 'completed', 'failed', 'skipped'
    )),
    assigned_to UUID REFERENCES yeyonet_nodes(id),
    assigned_ring_index INTEGER NOT NULL DEFAULT 0,
    job_id UUID REFERENCES yeyonet_jobs(id),
    input_payload JSONB NOT NULL DEFAULT '{}',
    output_payload JSONB,
    output_artifact_id UUID,
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(run_id, step_index)
);

CREATE TABLE IF NOT EXISTS yeyonet_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES yeyonet_pipeline_runs(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES yeyonet_pipeline_steps(id) ON DELETE CASCADE,
    kind VARCHAR(50) NOT NULL,
    data JSONB NOT NULL DEFAULT '{}',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_name = 'yeyonet_pipeline_steps'
          AND constraint_name = 'yeyonet_pipeline_steps_output_artifact_id_fkey'
    ) THEN
        ALTER TABLE yeyonet_pipeline_steps
            ADD CONSTRAINT yeyonet_pipeline_steps_output_artifact_id_fkey
            FOREIGN KEY (output_artifact_id) REFERENCES yeyonet_artifacts(id);
    END IF;
END $$;

DROP TRIGGER IF EXISTS auto_update_pipeline_runs_timestamp ON yeyonet_pipeline_runs;
CREATE TRIGGER auto_update_pipeline_runs_timestamp
    BEFORE UPDATE ON yeyonet_pipeline_runs
    FOR EACH ROW EXECUTE FUNCTION yeyonet_update_timestamp();

DROP TRIGGER IF EXISTS auto_update_pipeline_steps_timestamp ON yeyonet_pipeline_steps;
CREATE TRIGGER auto_update_pipeline_steps_timestamp
    BEFORE UPDATE ON yeyonet_pipeline_steps
    FOR EACH ROW EXECUTE FUNCTION yeyonet_update_timestamp();

CREATE INDEX IF NOT EXISTS idx_yeyonet_pipeline_runs_status ON yeyonet_pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_yeyonet_pipeline_runs_created_at ON yeyonet_pipeline_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_yeyonet_pipeline_steps_run ON yeyonet_pipeline_steps(run_id, step_index);
CREATE INDEX IF NOT EXISTS idx_yeyonet_pipeline_steps_status ON yeyonet_pipeline_steps(status);
CREATE INDEX IF NOT EXISTS idx_yeyonet_pipeline_steps_job ON yeyonet_pipeline_steps(job_id);
CREATE INDEX IF NOT EXISTS idx_yeyonet_artifacts_run ON yeyonet_artifacts(run_id, created_at);
