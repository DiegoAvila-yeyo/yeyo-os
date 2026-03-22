-- YeyoOS — Tabla patrones_razonamiento
-- Micro-fase 5.31 — Capa 5: Órganos
-- Almacena patrones de razonamiento reutilizables con búsqueda semántica

CREATE TABLE IF NOT EXISTS patrones_razonamiento (
    id SERIAL PRIMARY KEY,
    tipo_problema TEXT NOT NULL,
    embedding vector(768),
    errores_comunes JSONB,
    patron_correcto TEXT,
    pasos_razonamiento JSONB,
    tiempo_original_ms INTEGER DEFAULT 0,
    confianza FLOAT DEFAULT 0.0,
    veces_reutilizado INTEGER DEFAULT 0,
    aplicable_a TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS patrones_hnsw
ON patrones_razonamiento USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_patrones_tipo
ON patrones_razonamiento(tipo_problema);

CREATE INDEX IF NOT EXISTS idx_patrones_confianza
ON patrones_razonamiento(confianza DESC);
