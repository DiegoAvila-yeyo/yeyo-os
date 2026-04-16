-- 010_lab.sql — Video Generation Lab tables

CREATE TABLE IF NOT EXISTS lab_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storyboard_id UUID REFERENCES storyboards(id),
    name VARCHAR(255) NOT NULL DEFAULT 'Untitled Project',
    status VARCHAR(20) DEFAULT 'idle' CHECK (status IN ('idle', 'generating', 'paused', 'completed', 'error')),
    config JSONB DEFAULT '{"provider": "fal", "quality": "standard", "fps": 24, "resolution": "720p", "transition_default": "fade", "duration_default": 4.0, "consistency": "medium"}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lab_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES lab_projects(id) ON DELETE CASCADE,
    frame_index INT NOT NULL,
    status VARCHAR(20) DEFAULT 'idle' CHECK (status IN ('idle', 'generating', 'completed', 'error')),
    output_url TEXT DEFAULT '',
    duration FLOAT DEFAULT 0.0,
    provider VARCHAR(50) DEFAULT '',
    error_message TEXT DEFAULT '',
    prompt TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_clips_project ON lab_clips(project_id);
CREATE INDEX idx_clips_status ON lab_clips(project_id, status);
