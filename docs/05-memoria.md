# 05 — Flash Memory: Memoria Unificada

## Principio

> **Una sola tabla. Nada se borra jamás. Solo cambia la prioridad.**

YeyoOS reemplaza las 5 capas anteriores con **Flash Memory**: una única tabla PostgreSQL con pgvector que almacena TODO — conversaciones, hechos, preferencias, archivos, decisiones. Los recuerdos no se eliminan nunca; solo cambian de temperatura según su relevancia.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                     FLASH MEMORY                            │
│                                                             │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  🔴 HOT     │  │  🟡 WARM         │  │  🔵 COLD      │  │
│  │  RAM/Redis  │  │  PostgreSQL      │  │  PostgreSQL   │  │
│  │  ~50MB      │  │  activo          │  │  archivo      │  │
│  │  Top 1000   │  │  últimos 6 meses │  │  desde día 1  │  │
│  │  <1ms       │  │  10-50ms         │  │  50-200ms     │  │
│  └──────┬──────┘  └────────┬─────────┘  └───────┬───────┘  │
│         │                  │                     │          │
│         └──────────────────┴─────────────────────┘          │
│                    UNA SOLA TABLA                            │
│                PostgreSQL + pgvector                         │
└─────────────────────────────────────────────────────────────┘
```

## Regla de Oro

**Nada se borra. NUNCA.**

- Un recuerdo de hace 5 años sigue ahí → solo es COLD
- Si lo mencionas de nuevo → sube a WARM o HOT
- Como las neuronas: se refuerzan con el uso

## Tiers de Temperatura

| Tier | Ubicación | Capacidad | Latencia | Criterio |
|------|-----------|-----------|----------|----------|
| 🔴 HOT | RAM + Redis | ~50MB, top 1000 | <1ms | Lo más relevante ahora mismo |
| 🟡 WARM | PostgreSQL activo | Últimos 6 meses | 10-50ms | Accedido recientemente |
| 🔵 COLD | PostgreSQL archivo | Todo desde día 1 | 50-200ms | Sin acceso reciente |

## Fórmula de Relevancia

```
relevancia = (similaridad_semántica × 0.4)
           + (importancia × 0.3)
           + (frecuencia_acceso × 0.2)
           + (recencia × 0.1)
```

- **Similaridad semántica:** qué tan parecido es al contexto actual (pgvector cosine)
- **Importancia:** peso asignado (hechos personales = alta, chat casual = baja)
- **Frecuencia de acceso:** cuántas veces se ha consultado este recuerdo
- **Recencia:** qué tan reciente es el último acceso

## Refuerzo Neuronal

Cada vez que un recuerdo se accede, se refuerza:

```
Tú: "¿Cómo se llamaba el logo que hicimos en febrero?"

→ Flash Memory busca → encuentra recuerdo #4523
→ access_count += 1
→ last_accessed = ahora
→ Si estaba COLD → sube a WARM
→ Si relevancia > umbral_hot → sube a HOT
```

Igual que las neuronas: las conexiones usadas se fortalecen, las ignoradas se debilitan (pero NUNCA desaparecen).

## Esquema real de memoria

Conceptualmente sigue siendo "una sola memoria", pero operativamente conviene usar:

- **una tabla central canónica**;
- **tablas auxiliares** para asociaciones, auditoría, feedback, calidad, entrenamiento y sincronización.

Así todo el sistema se conecta a la misma memoria sin convertir una sola fila en un monstruo imposible de mantener.

## Tabla central canónica

La tabla central debe alinearse con el adaptador actual de `src/memory/flash_memory.py`, que ya usa `flash_memories`, `source`, `namespace` y `memory_audit_log`.

```sql
CREATE TABLE flash_memories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Contenido base
    content         TEXT NOT NULL,
    summary         TEXT,
    type            VARCHAR(50) NOT NULL,
        -- conversation | preference | fact | correction | skill
        -- decision | file | research_result | benchmark | pattern
        -- training_example | tool_trace | node_output

    -- Organización lógica
    source          VARCHAR(100) NOT NULL DEFAULT 'user',
    namespace       VARCHAR(200) NOT NULL DEFAULT 'chat:usuario',

    -- Contexto y payload
    metadata        JSONB NOT NULL DEFAULT '{}',
    checksum        CHAR(64) NOT NULL,

    -- Vector semántico
    embedding       vector(768),

    -- Relevancia y temperatura
    importance      FLOAT NOT NULL DEFAULT 0.5,
    access_count    INTEGER NOT NULL DEFAULT 0,
    tier            VARCHAR(10) NOT NULL DEFAULT 'WARM',
    pinned          BOOLEAN NOT NULL DEFAULT FALSE,
    invalid         BOOLEAN NOT NULL DEFAULT FALSE,

    -- Trazabilidad temporal
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    accessed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Versionado lógico
    version         INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_flash_embedding
    ON flash_memories USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_flash_tier ON flash_memories (tier);
CREATE INDEX idx_flash_type ON flash_memories (type);
CREATE INDEX idx_flash_namespace ON flash_memories (namespace);
CREATE INDEX idx_flash_source ON flash_memories (source);
CREATE INDEX idx_flash_accessed_at ON flash_memories (accessed_at DESC);
CREATE INDEX idx_flash_importance ON flash_memories (importance DESC);
CREATE INDEX idx_flash_metadata_gin ON flash_memories USING gin (metadata);
```

> **Nota de unificación:** la versión vieja del doc usaba `flash_memory` en singular.  
> La forma canónica debe ser `flash_memories`, porque coincide con el código real del adaptador.

## Tablas auxiliares

### 1. Asociaciones entre recuerdos

```sql
CREATE TABLE memory_links (
    id                  BIGSERIAL PRIMARY KEY,
    from_memory_id      UUID NOT NULL REFERENCES flash_memories(id),
    to_memory_id        UUID NOT NULL REFERENCES flash_memories(id),
    relation_type       VARCHAR(50) NOT NULL,
        -- related | caused_by | corrects | derived_from | example_of
        -- used_in | produced_by | verified_by | preferred_with
    weight              FLOAT NOT NULL DEFAULT 0.5,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (from_memory_id, to_memory_id, relation_type)
);

CREATE INDEX idx_memory_links_from ON memory_links (from_memory_id);
CREATE INDEX idx_memory_links_to ON memory_links (to_memory_id);
```

### 2. Auditoría inmutable

```sql
CREATE TABLE memory_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    memory_id       UUID NOT NULL REFERENCES flash_memories(id),
    action          VARCHAR(50) NOT NULL,
        -- CREATE | UPDATE | ACCESS | PROMOTE | DEMOTE | INVALIDATE | LINK
    details         JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_audit_memory_id ON memory_audit_log (memory_id);
CREATE INDEX idx_memory_audit_action ON memory_audit_log (action);
```

### 3. Feedback del usuario

```sql
CREATE TABLE memory_feedback (
    id                  BIGSERIAL PRIMARY KEY,
    memory_id           UUID NOT NULL REFERENCES flash_memories(id),
    feedback_type       VARCHAR(30) NOT NULL,
        -- positive | negative | correction | favorite | reject
    score               FLOAT,
    comment             TEXT,
    source              VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 4. Señales de calidad y verificación

```sql
CREATE TABLE memory_quality_signals (
    id                      BIGSERIAL PRIMARY KEY,
    memory_id               UUID NOT NULL REFERENCES flash_memories(id),
    correctness_score       FLOAT,
    security_score          FLOAT,
    compatibility_score     FLOAT,
    confidence_score        FLOAT,
    verification_status     VARCHAR(30) NOT NULL DEFAULT 'unverified',
        -- unverified | partial | verified | rejected
    benchmark_name          VARCHAR(100),
    benchmark_result        JSONB DEFAULT '{}',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 5. Corpus de entrenamiento del Dojo / Hack

```sql
CREATE TABLE memory_training_corpus (
    id                      BIGSERIAL PRIMARY KEY,
    memory_id               UUID NOT NULL REFERENCES flash_memories(id),
    corpus_type             VARCHAR(50) NOT NULL,
        -- code_example | correction_pair | preference_pair | tool_trace
        -- benchmark_case | refusal_example | reasoning_example
    split                   VARCHAR(20) NOT NULL DEFAULT 'train',
        -- train | valid | test
    promoted                BOOLEAN NOT NULL DEFAULT FALSE,
    promoted_by             VARCHAR(50) NOT NULL DEFAULT 'dojo',
    notes                   JSONB NOT NULL DEFAULT '{}',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 6. Sincronización de YeyoNet

```sql
CREATE TABLE memory_sync_queue (
    id                  BIGSERIAL PRIMARY KEY,
    memory_id           UUID NOT NULL REFERENCES flash_memories(id),
    target_node         VARCHAR(100) NOT NULL,
    sync_status         VARCHAR(30) NOT NULL DEFAULT 'pending',
        -- pending | sent | applied | failed | skipped
    sync_reason         VARCHAR(50) NOT NULL,
        -- hot_context | promoted_lora | benchmark_result | user_preference
        -- verified_solution | node_dataset
    payload             JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    synced_at           TIMESTAMPTZ
);
```

## Cómo se conecta todo en la memoria

### Chat

Guarda:

- conversaciones útiles;
- preferencias;
- decisiones;
- correcciones del usuario.

Namespaces típicos:

- `chat:usuario`
- `chat:sistema`
- `preferencias:usuario`

### Investigador

Guarda:

- soluciones verificadas;
- fuentes útiles;
- candidatos ganadores;
- ensamblajes exitosos;
- errores descartados.

Namespaces típicos:

- `investigador:consultas`
- `investigador:soluciones`
- `investigador:fuentes`

### Quality Kernel

No necesita crear siempre nuevos recuerdos; muchas veces enriquece recuerdos existentes con:

- `memory_quality_signals`
- `memory_audit_log`

Namespaces típicos:

- `quality:benchmarks`
- `quality:verification`

### YeyoDojo / YeyoHack

Usan memoria como:

- biblioteca de ejemplos buenos;
- historial de errores;
- dataset curado;
- base para adapters/LoRAs promovidos.

Namespaces típicos:

- `dojo:dataset`
- `dojo:errores`
- `hack:redteam`
- `hack:blueteam`

### Nodos

Cada nodo escribe en la misma memoria, pero con su namespace propio:

- `node:imagen`
- `node:video`
- `node:codigo`
- `node:archivos`

### YeyoNet

No sincroniza todo el cerebro. Sincroniza selectivamente:

- preferencias estables;
- soluciones verificadas;
- adapters/LoRAs promovidos;
- datasets aprobados;
- benchmark results relevantes.

Eso se gobierna con `memory_sync_queue`.

## Flujo real

```text
Usuario / nodo / agente
    -> genera evento o resultado
    -> YeyoOrquestador decide si vale la pena recordarlo
    -> Flash Memory guarda en flash_memories
    -> links / feedback / quality / training flags se agregan en tablas auxiliares
    -> retrieval futuro usa:
         1. tier
         2. embedding
         3. namespace
         4. quality_signals
         5. links asociados
    -> si una memoria es útil para otras máquinas:
         memory_sync_queue -> YeyoNet
```

## Regla de oro de escritura

No todo se guarda como fila nueva. Solo existen tres movimientos válidos:

1. **crear memoria nueva**;
2. **reforzar memoria existente**;
3. **enriquecer memoria existente** con links, feedback, quality o training flags.

Así la memoria deja de ser historial bruto y se vuelve una red viva de hechos, decisiones, errores, soluciones y patrones.

## Implementación Python

```python
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import psycopg2
import redis


class FlashMemory:
    """
    Memoria unificada de YeyoOS.
    Una tabla. Nada se borra. Solo cambia la prioridad.
    """

    HOT_LIMIT = 1000
    WARM_MONTHS = 6
    RELEVANCE_WEIGHTS = {
        "similaridad": 0.4,
        "importancia": 0.3,
        "frecuencia": 0.2,
        "recencia": 0.1,
    }

    def __init__(self, pg_dsn: str, redis_url: str = "redis://localhost:6379"):
        self.pg = psycopg2.connect(pg_dsn)
        self.redis = redis.from_url(redis_url)

    # ── Almacenar ────────────────────────────────────────────

    def store(
        self,
        tipo: str,
        contenido: str,
        embedding: list[float],
        importancia: float = 0.5,
        metadata: Optional[dict] = None,
        resumen: Optional[str] = None,
    ) -> str:
        """Almacena un recuerdo nuevo. Nunca se borra."""
        memory_id = str(uuid.uuid4())
        with self.pg.cursor() as cur:
            cur.execute(
                """
                INSERT INTO flash_memory
                    (id, tipo, contenido, resumen, metadata, embedding, importancia, tier)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'WARM')
                """,
                (
                    memory_id,
                    tipo,
                    contenido,
                    resumen,
                    json.dumps(metadata or {}),
                    embedding,
                    importancia,
                ),
            )
        self.pg.commit()
        self._maybe_promote_to_hot(memory_id, importancia)
        return memory_id

    def store_with_associations(
        self,
        tipo: str,
        contenido: str,
        embedding: list[float],
        asociar_con: list[str],
        importancia: float = 0.5,
        metadata: Optional[dict] = None,
        resumen: Optional[str] = None,
    ) -> str:
        """Almacena un recuerdo y lo conecta bidireccionalmente con otros."""
        memory_id = self.store(tipo, contenido, embedding, importancia, metadata, resumen)

        with self.pg.cursor() as cur:
            # Agregar asociaciones al nuevo recuerdo
            cur.execute(
                "UPDATE flash_memory SET asociaciones = %s WHERE id = %s",
                (asociar_con, memory_id),
            )
            # Agregar asociación bidireccional en los recuerdos existentes
            for assoc_id in asociar_con:
                cur.execute(
                    """
                    UPDATE flash_memory
                    SET asociaciones = array_append(asociaciones, %s::uuid)
                    WHERE id = %s AND NOT (%s::uuid = ANY(asociaciones))
                    """,
                    (memory_id, assoc_id, memory_id),
                )
        self.pg.commit()
        return memory_id

    # ── Recordar ─────────────────────────────────────────────

    def recall(
        self,
        query_embedding: list[float],
        limit: int = 10,
        tipo: Optional[str] = None,
        include_associations: bool = True,
    ) -> list[dict]:
        """
        Busca recuerdos por similaridad semántica.
        Primero HOT (Redis), luego WARM/COLD (PostgreSQL).
        Refuerza cada recuerdo accedido.
        """
        # 1. Buscar en HOT (Redis) primero
        hot_results = self._search_hot(query_embedding, limit)

        # 2. Completar con PostgreSQL si hace falta
        if len(hot_results) < limit:
            remaining = limit - len(hot_results)
            hot_ids = [r["id"] for r in hot_results]
            pg_results = self._search_pg(query_embedding, remaining, tipo, exclude_ids=hot_ids)
        else:
            pg_results = []

        results = hot_results + pg_results

        # 3. Reforzar cada recuerdo accedido
        for memory in results:
            self._reinforce(memory["id"])

        # 4. Cargar asociaciones si se piden
        if include_associations:
            for memory in results:
                memory["asociados"] = self._load_associations(memory["id"])

        return results

    # ── Refuerzo neuronal ────────────────────────────────────

    def _reinforce(self, memory_id: str):
        """Refuerza un recuerdo: incrementa accesos, actualiza timestamp, evalúa promoción."""
        with self.pg.cursor() as cur:
            cur.execute(
                """
                UPDATE flash_memory
                SET access_count = access_count + 1,
                    last_accessed = NOW()
                WHERE id = %s
                RETURNING importancia, access_count, tier
                """,
                (memory_id,),
            )
            row = cur.fetchone()
            if row:
                importancia, access_count, current_tier = row
                new_relevance = self._calculate_relevance(importancia, access_count)
                if current_tier == "COLD" and new_relevance > 0.3:
                    cur.execute(
                        "UPDATE flash_memory SET tier = 'WARM' WHERE id = %s",
                        (memory_id,),
                    )
                if current_tier in ("COLD", "WARM") and new_relevance > 0.7:
                    self._maybe_promote_to_hot(memory_id, new_relevance)
        self.pg.commit()

    def _calculate_relevance(
        self,
        importancia: float,
        access_count: int,
        similarity: float = 0.5,
        days_since_access: float = 0.0,
    ) -> float:
        """Calcula relevancia combinada."""
        w = self.RELEVANCE_WEIGHTS
        recencia = max(0, 1.0 - (days_since_access / 180))
        frecuencia = min(1.0, access_count / 100)
        return (
            similarity * w["similaridad"]
            + importancia * w["importancia"]
            + frecuencia * w["frecuencia"]
            + recencia * w["recencia"]
        )

    # ── Tiers ────────────────────────────────────────────────

    def _maybe_promote_to_hot(self, memory_id: str, relevance: float):
        """Promueve a HOT si la relevancia es suficiente."""
        hot_count = self.redis.scard("flash:hot_ids")
        if hot_count < self.HOT_LIMIT or relevance > 0.7:
            with self.pg.cursor() as cur:
                cur.execute(
                    "SELECT contenido, resumen, metadata, tipo FROM flash_memory WHERE id = %s",
                    (memory_id,),
                )
                row = cur.fetchone()
                if row:
                    self.redis.hset(f"flash:hot:{memory_id}", mapping={
                        "contenido": row[0],
                        "resumen": row[1] or "",
                        "metadata": row[2],
                        "tipo": row[3],
                    })
                    self.redis.sadd("flash:hot_ids", memory_id)
                    cur.execute(
                        "UPDATE flash_memory SET tier = 'HOT' WHERE id = %s",
                        (memory_id,),
                    )
            self.pg.commit()

    def rebalance_tiers(self):
        """Proceso periódico: degrada recuerdos sin acceso reciente."""
        with self.pg.cursor() as cur:
            # HOT → WARM: sin acceso en 7 días
            cur.execute(
                """
                UPDATE flash_memory SET tier = 'WARM'
                WHERE tier = 'HOT' AND last_accessed < NOW() - INTERVAL '7 days'
                RETURNING id
                """,
            )
            for (mid,) in cur.fetchall():
                self.redis.delete(f"flash:hot:{mid}")
                self.redis.srem("flash:hot_ids", str(mid))

            # WARM → COLD: sin acceso en 6 meses
            cur.execute(
                """
                UPDATE flash_memory SET tier = 'COLD'
                WHERE tier = 'WARM' AND last_accessed < NOW() - INTERVAL '6 months'
                """,
            )
        self.pg.commit()

    # ── Búsqueda interna ─────────────────────────────────────

    def _search_hot(self, query_embedding: list[float], limit: int) -> list[dict]:
        """Busca en cache HOT de Redis."""
        # Simplificado: en producción usar un índice vectorial en Redis
        hot_ids = self.redis.smembers("flash:hot_ids")
        results = []
        for mid in hot_ids:
            data = self.redis.hgetall(f"flash:hot:{mid.decode()}")
            if data:
                results.append({"id": mid.decode(), **{k.decode(): v.decode() for k, v in data.items()}})
        return results[:limit]

    def _search_pg(
        self,
        query_embedding: list[float],
        limit: int,
        tipo: Optional[str] = None,
        exclude_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """Búsqueda semántica en PostgreSQL con pgvector."""
        exclude_ids = exclude_ids or []
        with self.pg.cursor() as cur:
            tipo_filter = "AND tipo = %s" if tipo else ""
            exclude_filter = "AND id != ALL(%s)" if exclude_ids else ""
            params = [str(query_embedding)]
            if tipo:
                params.append(tipo)
            if exclude_ids:
                params.append(exclude_ids)
            params.append(limit)

            cur.execute(
                f"""
                SELECT id, tipo, contenido, resumen, metadata, importancia,
                       access_count, tier, created_at, last_accessed,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM flash_memory
                WHERE embedding IS NOT NULL {tipo_filter} {exclude_filter}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (*params, str(query_embedding)),
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    def _load_associations(self, memory_id: str, depth: int = 1) -> list[dict]:
        """Carga recuerdos asociados (1 nivel de profundidad por defecto)."""
        if depth <= 0:
            return []
        with self.pg.cursor() as cur:
            cur.execute(
                """
                SELECT m.id, m.tipo, m.resumen, m.importancia
                FROM flash_memory m
                WHERE m.id = ANY(
                    SELECT unnest(asociaciones) FROM flash_memory WHERE id = %s
                )
                """,
                (memory_id,),
            )
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]

    # ── Portabilidad ─────────────────────────────────────────

    def export_portable(self, filepath: str):
        """Exporta TODA la memoria en JSON portable."""
        with self.pg.cursor() as cur:
            cur.execute(
                """
                SELECT id, tipo, contenido, resumen, metadata, importancia,
                       access_count, tier, asociaciones, created_at, last_accessed
                FROM flash_memory
                ORDER BY created_at
                """
            )
            columns = [desc[0] for desc in cur.description]
            memories = []
            for row in cur.fetchall():
                record = dict(zip(columns, row))
                record["created_at"] = record["created_at"].isoformat()
                record["last_accessed"] = record["last_accessed"].isoformat()
                record["asociaciones"] = [str(a) for a in (record["asociaciones"] or [])]
                memories.append(record)

        export = {
            "format": "yeyo-flash-memory-v1",
            "exported_at": datetime.utcnow().isoformat(),
            "total_memories": len(memories),
            "memories": memories,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2)

    def import_portable(self, filepath: str):
        """Importa memoria desde JSON portable. No sobreescribe duplicados."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for mem in data["memories"]:
            with self.pg.cursor() as cur:
                cur.execute("SELECT 1 FROM flash_memory WHERE id = %s", (mem["id"],))
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO flash_memory
                            (id, tipo, contenido, resumen, metadata, importancia,
                             access_count, tier, asociaciones, created_at, last_accessed)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            mem["id"], mem["tipo"], mem["contenido"], mem.get("resumen"),
                            json.dumps(mem.get("metadata", {})), mem["importancia"],
                            mem["access_count"], mem.get("tier", "COLD"),
                            mem.get("asociaciones", []),
                            mem["created_at"], mem["last_accessed"],
                        ),
                    )
            self.pg.commit()
```

## Flujo Completo: Una Sola Búsqueda

```
Tú dices: "Modifica el logo que hicimos ayer"

1. Se genera embedding de tu mensaje
2. flash.recall(embedding, limit=10) busca:
   → HOT (Redis): ¿está en los top 1000? → Sí/No
   → WARM (PostgreSQL): busca por similaridad semántica
   → COLD: si no hay suficientes resultados, busca en archivo
3. Encuentra recuerdo #4523 (logo cyberpunk)
4. Carga asociaciones:
   → [Preferencia cyberpunk] + [Canal YouTube] + [Archivo img_0847.png]
5. Refuerza el recuerdo (access_count += 1, sube tier si aplica)
6. Construye contexto para Ollama con todo
7. Ollama responde con contexto completo
```

## Proyección a 20+ Años

| Período | Recuerdos estimados | Tamaño PostgreSQL | Tier HOT | Tier WARM | Tier COLD |
|---------|--------------------:|------------------:|---------:|----------:|----------:|
| Año 1   | 500K               | ~5 GB             | 1,000    | 400K      | 99K       |
| Año 5   | 1.2M               | ~15 GB            | 1,000    | 300K      | 899K      |
| Año 10  | 2M                 | ~30 GB            | 1,000    | 250K      | 1.75M     |
| Año 20  | 10M+               | ~120 GB           | 1,000    | 200K      | 9.8M+     |

**¿Por qué funciona?** Porque HOT siempre es 1,000 recuerdos. Da igual que tengas 500K o 10M — lo que importa siempre cabe en RAM. El resto está en PostgreSQL, que maneja millones de filas sin problemas.

## Formato Portable

```json
{
  "format": "yeyo-flash-memory-v1",
  "exported_at": "2046-03-18T00:00:00",
  "total_memories": 10482331,
  "memories": [
    {
      "id": "a1b2c3d4-...",
      "tipo": "hecho",
      "contenido": "El usuario prefiere estilo cyberpunk oscuro",
      "resumen": "Preferencia visual: cyberpunk",
      "importancia": 0.95,
      "access_count": 847,
      "tier": "HOT",
      "asociaciones": ["e5f6g7h8-...", "i9j0k1l2-..."],
      "created_at": "2026-03-18T06:00:00",
      "last_accessed": "2046-03-17T23:45:00"
    }
  ]
}
```

Este formato JSON sobrevive cambios de tecnología. Si en 2040 PostgreSQL ya no existe, importas el JSON a lo que sea que exista.

## Modelo de Embeddings

- **Modelo:** `nomic-embed-text` (corre en Ollama, ligero, 768 dimensiones)
- **Función:** Convierte texto en vectores para búsqueda por significado
- **Ejemplo:** "logo oscuro" encuentra "imagen cyberpunk con tonos nocturnos"

## Backups

- Backup incremental cada 6 horas
- Backup completo diario
- Retención de 30 días
- Export portable JSON semanal (por si todo falla)
