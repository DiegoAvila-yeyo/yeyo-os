## ═══════════════════════════════════════
## MICRO-FASE 0.3 — PostgreSQL 16 + pgvector
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.3-2 [CLI] — Crear schema base y archivo .env

```
Estamos construyendo YeyoOS. Micro-fase 0.3, Prompt 2 de 2: crear schema inicial y archivo de configuración.

PREREQUISITO: Prompt 0.3-1 completado (PG16 + pgvector corriendo).

EJECUTAR:
1. Ir al directorio del proyecto:
   cd ~/yeyo-os  (o donde esté el repo clonado)

2. Crear directorio de database:
   mkdir -p db/migrations

3. Crear archivo db/migrations/001_initial_setup.sql con:
   -- YeyoOS Flash Memory - Initial Setup
   -- Micro-fase 0.3
   
   CREATE EXTENSION IF NOT EXISTS vector;
   CREATE EXTENSION IF NOT EXISTS pgcrypto;
   
   -- Tabla de verificación de instalación
   CREATE TABLE IF NOT EXISTS _yeyo_meta (
       key VARCHAR(100) PRIMARY KEY,
       value TEXT NOT NULL,
       created_at TIMESTAMPTZ DEFAULT NOW()
   );
   
   INSERT INTO _yeyo_meta (key, value) VALUES 
       ('version', '0.0.1'),
       ('installed_at', NOW()::TEXT),
       ('micro_fase', '0.3');

4. Ejecutar migration:
   PGPASSWORD=yeyo_dev_2026 psql -U yeyo -d yeyo_db -h 127.0.0.1 -f db/migrations/001_initial_setup.sql

5. Crear archivo .env en la raíz del proyecto:
   # YeyoOS Environment Configuration
   # Micro-fase 0.3
   
   # PostgreSQL
   DATABASE_URL=postgresql://yeyo:yeyo_dev_2026@127.0.0.1:5432/yeyo_db
   TEST_DATABASE_URL=postgresql://yeyo:yeyo_dev_2026@127.0.0.1:5432/yeyo_test_db
   
   # (Más variables se agregarán en micro-fases posteriores)

6. Asegurar que .env está en .gitignore:
   echo ".env" >> .gitignore (si no existe ya)

7. Crear .env.example (para el repo, sin secrets):
   # YeyoOS Environment Configuration
   DATABASE_URL=postgresql://yeyo:YOUR_PASSWORD@127.0.0.1:5432/yeyo_db
   TEST_DATABASE_URL=postgresql://yeyo:YOUR_PASSWORD@127.0.0.1:5432/yeyo_test_db

VERIFICAR:
- [ ] Migration ejecutada: `PGPASSWORD=yeyo_dev_2026 psql -U yeyo -d yeyo_db -h 127.0.0.1 -c "SELECT * FROM _yeyo_meta;"` → 3 rows
- [ ] .env existe: `cat .env` → muestra DATABASE_URL
- [ ] .env en .gitignore: `grep '.env' .gitignore` → match
- [ ] .env.example en repo: `cat .env.example` → sin passwords reales
- [ ] Extensiones: `PGPASSWORD=yeyo_dev_2026 psql -U yeyo -d yeyo_db -h 127.0.0.1 -c "SELECT extname FROM pg_extension;"` → vector + pgcrypto

GATE: Schema base creado, .env configurado, .gitignore protege secrets, migration exitosa.
```
