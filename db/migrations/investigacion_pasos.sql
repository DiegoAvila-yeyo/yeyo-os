-- YeyoOS — Tabla investigacion_pasos
-- Micro-fase 5.28 — Capa 5: Órganos
-- Tracking detallado de cada paso del Pipeline Investigador

CREATE TABLE IF NOT EXISTS investigacion_pasos (
    id SERIAL PRIMARY KEY,
    tarea_id TEXT NOT NULL,
    paso_numero INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    input_resumen TEXT,
    output_resumen TEXT,
    tokens_usados INTEGER DEFAULT 0,
    duracion_ms INTEGER DEFAULT 0,
    confianza FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_investigacion_tarea ON investigacion_pasos(tarea_id);
CREATE INDEX IF NOT EXISTS idx_investigacion_tipo ON investigacion_pasos(tipo);
