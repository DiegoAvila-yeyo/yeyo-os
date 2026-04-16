-- 011_observatory.sql — Observatory Town tables

CREATE TABLE IF NOT EXISTS observatory_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'error')),
    result_output TEXT DEFAULT '',
    result_files TEXT[] DEFAULT '{}',
    result_memories INT DEFAULT 0,
    duration_ms INT DEFAULT 0,
    error_message TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS observatory_crews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    agent_sequence TEXT[] NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'error')),
    current_agent_index INT DEFAULT 0,
    results JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_observatory_tasks_agent ON observatory_tasks(agent_name);
CREATE INDEX idx_observatory_tasks_status ON observatory_tasks(status);
