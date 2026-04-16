-- 012_workshop.sql — Workshop: 16 Anti-Slop Gates pipeline

CREATE TABLE IF NOT EXISTS workshop_missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    origin VARCHAR(50) DEFAULT 'user',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'spec_review', 'designing', 'coding', 'testing', 'completed', 'error')),
    spec JSONB DEFAULT '{}',
    code_files JSONB DEFAULT '[]',
    test_results JSONB DEFAULT '{}',
    security_report JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workshop_gates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES workshop_missions(id) ON DELETE CASCADE,
    gate_number INT NOT NULL,
    gate_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'passed', 'failed', 'skipped', 'waiting_approval')),
    output TEXT DEFAULT '',
    duration_ms INT DEFAULT 0,
    attempts INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_workshop_gates ON workshop_gates(mission_id, gate_number);
