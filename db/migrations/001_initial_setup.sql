-- YeyoOS Flash Memory - Initial Setup
-- Micro-fase 0.3

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS _yeyo_meta (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO _yeyo_meta (key, value) VALUES 
    ('version', '0.0.1'),
    ('installed_at', NOW()::TEXT),
    ('micro_fase', '0.3');
