-- 009_storyboard.sql — Storyboard "Disney Studio" tables

CREATE TABLE IF NOT EXISTS storyboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS storyboard_frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    storyboard_id UUID NOT NULL REFERENCES storyboards(id) ON DELETE CASCADE,
    image_url TEXT DEFAULT '',
    description TEXT DEFAULT '',
    movement VARCHAR(50) DEFAULT 'static',
    duration FLOAT DEFAULT 4.0,
    camera VARCHAR(50) DEFAULT 'static',
    emotion VARCHAR(50) DEFAULT 'neutral',
    transition VARCHAR(50) DEFAULT 'cut',
    audio_text TEXT DEFAULT '',
    prompt_extra TEXT DEFAULT '',
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_frames_storyboard ON storyboard_frames(storyboard_id);
CREATE INDEX IF NOT EXISTS idx_frames_order ON storyboard_frames(storyboard_id, sort_order);
