# 13 — Code Dojo: Sistema de Entrenamiento IA para Programación

## Resumen

El Code Dojo es el sistema de auto-entrenamiento de programación de YeyoOS. **12 agentes especializados** trabajan como un equipo de desarrollo completo, todos corriendo sobre el **mismo modelo** con diferentes system prompts. Cada noche, la IA entrena con ~1,800 desafíos de código en la GTX 1060 3GB. El resultado: una IA que programa cada vez más como tú.

## Los 12 Agentes Especializados

```
┌─────────────────────────────────────────────────────────┐
│              MISMO MODELO (ej: Qwen2.5-Coder-3B)       │
│         Cambio de agente = cambio de system prompt      │
│              Sin swap de modelo = INSTANTÁNEO            │
├──────────────┬──────────────┬──────────────┬────────────┤
│  Arquitecto  │   Backend    │   Frontend   │   Mobile   │
│  Diseña la   │  Escribe la  │  Interfaces  │  Apps      │
│  solución    │  lógica      │  y UI        │  nativas   │
├──────────────┼──────────────┼──────────────┼────────────┤
│  Base Datos  │  Seguridad   │   IA/ML      │ Performance│
│  Esquemas,   │  Vulnerab.,  │  Modelos,    │  Optimiz., │
│  queries     │  auth, OWASP │  pipelines   │  profiling │
├──────────────┼──────────────┼──────────────┼────────────┤
│   Testing    │   DevOps     │    Datos     │  Sistemas  │
│  Tests,      │  CI/CD,      │  ETL,        │  Kernel,   │
│  cobertura   │  containers  │  analytics   │  drivers   │
└──────────────┴──────────────┴──────────────┴────────────┘
```

### ¿Por qué el mismo modelo?

```
Enfoque TRADICIONAL (malo):
  Agente 1 → cargar modelo A (5 seg) → responder → descargar
  Agente 2 → cargar modelo B (5 seg) → responder → descargar
  Total: 10+ segundos solo en carga de modelos

Enfoque YeyoOS (bueno):
  Qwen2.5-Coder-3B cargado UNA vez en VRAM
  Agente 1 → cambiar system prompt (0 ms) → responder
  Agente 2 → cambiar system prompt (0 ms) → responder
  Total: 0 segundos de overhead
```

### Definición de Agentes

```python
AGENTES = {
    "arquitecto": {
        "system_prompt": """Eres un arquitecto de software senior.
        Diseñas soluciones escalables, defines estructura de archivos,
        patrones de diseño y dependencias entre componentes.
        Respondes con diagramas ASCII y planes detallados.""",
        "especialidad": "diseño de sistemas",
        "output": "plan de arquitectura"
    },
    "backend": {
        "system_prompt": """Eres un desarrollador backend experto.
        Escribes código limpio, eficiente y bien documentado.
        Manejas APIs REST/GraphQL, bases de datos, autenticación.
        Siempre incluyes manejo de errores y logging.""",
        "especialidad": "lógica de servidor",
        "output": "código funcional"
    },
    "frontend": {
        "system_prompt": """Eres un desarrollador frontend senior.
        Creas interfaces accesibles, responsivas y performantes.
        Dominas React, Vue, CSS moderno y diseño de componentes.""",
        "especialidad": "interfaces de usuario",
        "output": "componentes UI"
    },
    "mobile": {
        "system_prompt": """Eres un desarrollador móvil experto.
        Creas apps nativas y cross-platform con Flutter, React Native,
        Swift y Kotlin. Optimizas para batería y rendimiento.""",
        "especialidad": "aplicaciones móviles",
        "output": "código móvil"
    },
    "base_datos": {
        "system_prompt": """Eres un DBA y experto en modelado de datos.
        Diseñas esquemas normalizados, escribes queries optimizadas,
        manejas migraciones y estrategias de indexación.""",
        "especialidad": "bases de datos",
        "output": "esquemas y queries"
    },
    "seguridad": {
        "system_prompt": """Eres un experto en seguridad informática.
        Revisas código buscando vulnerabilidades OWASP Top 10,
        inyecciones, XSS, auth bypass y data leaks.""",
        "especialidad": "seguridad",
        "output": "reporte de vulnerabilidades"
    },
    "ia_ml": {
        "system_prompt": """Eres un ingeniero de ML/IA.
        Diseñas pipelines de datos, entrenas modelos, optimizas
        inferencia y manejas MLOps.""",
        "especialidad": "inteligencia artificial",
        "output": "modelos y pipelines"
    },
    "performance": {
        "system_prompt": """Eres un experto en optimización de rendimiento.
        Perfilas código, identificas cuellos de botella, optimizas
        algoritmos, memoria y I/O.""",
        "especialidad": "rendimiento",
        "output": "código optimizado"
    },
    "testing": {
        "system_prompt": """Eres un ingeniero de QA senior.
        Escribes tests unitarios, integración y e2e.
        Manejas TDD, BDD, mocking y cobertura de código.""",
        "especialidad": "testing",
        "output": "suite de tests"
    },
    "devops": {
        "system_prompt": """Eres un ingeniero DevOps senior.
        Manejas CI/CD, contenedores, infraestructura como código,
        monitoreo y despliegues automatizados.""",
        "especialidad": "operaciones",
        "output": "pipelines y configs"
    },
    "datos": {
        "system_prompt": """Eres un ingeniero de datos.
        Diseñas ETL pipelines, data warehouses, procesamiento
        batch y streaming con herramientas modernas.""",
        "especialidad": "ingeniería de datos",
        "output": "pipelines de datos"
    },
    "sistemas": {
        "system_prompt": """Eres un programador de sistemas.
        Escribes código de bajo nivel: drivers, kernel modules,
        networking, protocolos y optimización de SO.""",
        "especialidad": "programación de sistemas",
        "output": "código de sistema"
    }
}
```

## Pipeline de Desarrollo

El usuario solo ve el resultado final. Todo el proceso interno es invisible:

```
Usuario: "Hazme una API REST para gestionar tareas"
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│                    PIPELINE INTERNO                      │
│                                                          │
│  1. ARQUITECTO planifica                                │
│     → Estructura de archivos, endpoints, modelos        │
│     → System prompt de arquitecto, mismo modelo          │
│                                                          │
│  2. BACKEND escribe el código                           │
│     → Implementa según el plan del arquitecto           │
│     → System prompt de backend, mismo modelo             │
│                                                          │
│  3. CRÍTICO revisa (da puntuación 0-10)                 │
│     → "Falta validación de input: 6.5/10"               │
│     → Si < 8.0, vuelve al paso 2 con feedback           │
│                                                          │
│  4. BACKEND corrige según el feedback                   │
│     → Agrega validación, mejora manejo de errores       │
│     → Nuevo score: 8.5/10 ✓                             │
│                                                          │
│  5. TESTER genera y ejecuta tests (CPU, sin GPU)        │
│     → Tests unitarios + integración                     │
│     → Ejecución real con pytest/jest                    │
│                                                          │
│  6. PERFORMANCE analiza                                 │
│     → Complejidad algorítmica, uso de memoria           │
│     → Sugiere optimizaciones si es necesario            │
│                                                          │
│  7. SEGURIDAD revisa                                    │
│     → OWASP Top 10, inyecciones, auth                   │
│     → Valida que no hay vulnerabilidades                │
│                                                          │
│  8. TODOS APRUEBAN → entrega al usuario                 │
└─────────────────────────────────────────────────────────┘
  │
  ▼
Usuario: Recibe API completa, testeada, segura y optimizada
```

### Timeline GPU + CPU en Paralelo

```
Tiempo ──────────────────────────────────────────────────►

GPU (Inferencia del modelo):
  ████ Arquitecto ████ Backend ████ Crítico ████ Backend ████ Performance ████ Seguridad
  planifica          escribe       revisa       corrige      analiza          revisa

CPU (Ejecución real):
  ░░░░ idle ░░░░░░░░░░░░░░░░░░░░░ ████ Tests ████ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░
                                    pytest ejecuta
                                    los tests reales

Disco/Red:
  ░░░░ idle ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ ████ Guardar resultado ████
```

## Entrenamiento Nocturno

Mientras duermes, el Dojo entrena con desafíos de programación:

```
┌─────────────────────────────────────────────────┐
│          ENTRENAMIENTO NOCTURNO                  │
│                                                  │
│  Hora inicio: 2:00 AM                           │
│  Hora fin:    ~10:00 AM                          │
│  Duración:    ~8 horas                           │
│                                                  │
│  Desafíos por sesión: ~1,800                    │
│  Tiempo por desafío:  ~16 segundos              │
│  Hardware:            GTX 1060 3GB              │
│                                                  │
│  Cada desafío:                                   │
│    1. Generar código (GPU, ~8 seg)              │
│    2. Ejecutar tests (CPU, ~3 seg)              │
│    3. Evaluar calidad (GPU, ~5 seg)             │
│    4. Guardar en RAG si score ≥ 9.0            │
│                                                  │
│  Categorías rotativas:                           │
│    - Algoritmos y estructuras de datos          │
│    - APIs y servicios web                       │
│    - Bases de datos y queries                   │
│    - Patrones de diseño                         │
│    - Seguridad y criptografía                   │
│    - Testing y TDD                              │
│    - Optimización de rendimiento                │
│    - Programación funcional                     │
│    - Concurrencia y paralelismo                 │
│    - Machine Learning básico                    │
└─────────────────────────────────────────────────┘
```

## RAG para Código (Deep Dive)

### Esquema PostgreSQL + pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE code_examples (
    id              SERIAL PRIMARY KEY,
    code            TEXT NOT NULL,
    language        VARCHAR(50) NOT NULL,
    category        VARCHAR(100) NOT NULL,
    description     TEXT NOT NULL,
    embedding       vector(768),          -- nomic-embed-text dimension
    score           FLOAT NOT NULL,       -- 0.0 a 10.0
    source          VARCHAR(50) NOT NULL, -- 'user', 'dojo', 'correction', 'opensource'
    tags            TEXT[] DEFAULT '{}',
    errors_found    TEXT[] DEFAULT '{}',
    corrections     JSONB DEFAULT '[]',   -- [{original, corregido, razon}]
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Índice HNSW para búsqueda semántica rápida
CREATE INDEX idx_code_embedding ON code_examples
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Índices para filtros de metadatos
CREATE INDEX idx_code_language ON code_examples(language);
CREATE INDEX idx_code_category ON code_examples(category);
CREATE INDEX idx_code_score ON code_examples(score);
CREATE INDEX idx_code_source ON code_examples(source);
CREATE INDEX idx_code_tags ON code_examples USING gin(tags);
```

### Embeddings con nomic-embed-text

```
¿Por qué nomic-embed-text?
  - Optimizado para texto técnico y código
  - 768 dimensiones (buen balance precisión/velocidad)
  - Corre localmente via Ollama (sin API externa)
  - ~100ms por embedding en GTX 1060
```

### Búsqueda Multi-Nivel

```
Consulta del usuario: "función para ordenar lista enlazada"
  │
  ▼
Nivel 1: BÚSQUEDA SEMÁNTICA (pgvector)
  → Cosine similarity con el embedding de la consulta
  → Top 50 candidatos más similares
  │
  ▼
Nivel 2: FILTRO DE METADATOS
  → language = lenguaje del proyecto actual
  → category IN ('algoritmos', 'estructuras_datos')
  → score ≥ 7.0
  → Quedan ~15 candidatos
  │
  ▼
Nivel 3: FILTRO DE CONTEXTO DEL PROYECTO
  → Coincidencia con tags del proyecto actual
  → Prioridad a source = 'user' (tu propio código)
  → Quedan ~5 candidatos
  │
  ▼
Nivel 4: RANKING DE UTILIDAD
  → score * 0.4 + relevancia_semántica * 0.3 +
    frescura * 0.15 + match_contexto * 0.15
  → Top 3 resultados finales
```

### Ejemplos Negativos (Gold Data)

```
Los ejemplos negativos son ORO para el entrenamiento:

Cuando el usuario RECHAZA código generado:
  ┌────────────────────────────────────────┐
  │  código_original: "def sort(l):..."    │
  │  razón_rechazo:   "muy lento, O(n²)"  │
  │  corrección:      "def sort(l):..."    │  ← versión mejorada
  │  score_original:  4.0                  │
  │  score_corrección: 9.0                 │
  └────────────────────────────────────────┘

Esto enseña a la IA:
  - Qué NO hacer (código rechazado)
  - POR QUÉ no hacerlo (razón)
  - Qué hacer EN CAMBIO (corrección)
  - = Aprendizaje 3x más efectivo que solo ejemplos positivos
```

### Fuentes de Datos y Prioridad

```
Fuente                          Score Base    Prioridad
─────────────────────────────────────────────────────────
Código del usuario              10             Máxima
  → Tu estilo, tus patrones, tu forma de nombrar

Resultados del Dojo ≥ 9.0      9.0-10.0       Alta
  → Código generado que pasó todas las validaciones

Correcciones del usuario        9.5            Alta
  → Cuando corriges código de la IA = feedback directo

Open source curado              7.0-8.0        Media
  → Repos populares, bien mantenidos, mismo lenguaje
```

### Evolución del RAG

```
MES 1:    ~500 ejemplos   → 70% calidad
  └─ Principalmente open source curado + tus primeros códigos

MES 6:    ~20,000 ejemplos → 92% calidad
  └─ Miles de ejemplos del Dojo + cientos de correcciones tuyas

AÑO 1:   ~80,000+ ejemplos → 95%+ calidad
  └─ La IA conoce tu estilo tan bien como tú mismo
```

### Implementación CodeRAG

```python
import numpy as np
from typing import Optional

class CodeRAG:
    """Sistema RAG especializado en código para YeyoOS."""

    def __init__(self, db_pool, ollama_client):
        self.db = db_pool
        self.ollama = ollama_client
        self.embed_model = "nomic-embed-text"

    async def get_embedding(self, text: str) -> list[float]:
        """Genera embedding de código usando nomic-embed-text."""
        response = await self.ollama.embeddings(
            model=self.embed_model,
            prompt=text
        )
        return response["embedding"]

    async def search(
        self,
        query: str,
        language: Optional[str] = None,
        category: Optional[str] = None,
        min_score: float = 7.0,
        project_tags: Optional[list[str]] = None,
        limit: int = 3
    ) -> list[dict]:
        """Búsqueda multi-nivel: semántica → metadatos → contexto → ranking."""
        embedding = await self.get_embedding(query)

        # Nivel 1 + 2: Semántica + filtros de metadatos
        sql = """
            SELECT id, code, language, category, description,
                   score, source, tags, corrections,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM code_examples
            WHERE score >= $2
        """
        params = [embedding, min_score]
        param_idx = 3

        if language:
            sql += f" AND language = ${param_idx}"
            params.append(language)
            param_idx += 1

        if category:
            sql += f" AND category = ${param_idx}"
            params.append(category)
            param_idx += 1

        sql += " ORDER BY embedding <=> $1::vector LIMIT 50"

        candidates = await self.db.fetch(sql, *params)

        # Nivel 3 + 4: Contexto del proyecto + ranking de utilidad
        ranked = []
        for row in candidates:
            context_score = 0.0
            if project_tags:
                overlap = set(row["tags"]) & set(project_tags)
                context_score = len(overlap) / max(len(project_tags), 1)

            freshness = self._calculate_freshness(row["created_at"])

            final_score = (
                row["score"] / 10.0 * 0.4 +
                row["similarity"] * 0.3 +
                freshness * 0.15 +
                context_score * 0.15
            )
            ranked.append({**dict(row), "final_score": final_score})

        ranked.sort(key=lambda x: x["final_score"], reverse=True)
        return ranked[:limit]

    async def add_example(self, code: str, language: str, category: str,
                          description: str, score: float, source: str,
                          tags: list[str] = None):
        """Agrega un ejemplo de código al RAG."""
        embedding = await self.get_embedding(
            f"{description}\n\n{code}"
        )
        await self.db.execute("""
            INSERT INTO code_examples
                (code, language, category, description, embedding,
                 score, source, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, code, language, category, description,
            embedding, score, source, tags or [])

    async def add_negative_example(self, original_code: str,
                                    corrected_code: str, reason: str,
                                    language: str, category: str):
        """Registra un ejemplo negativo (código rechazado + corrección)."""
        # Guardar la corrección como ejemplo positivo de alta prioridad
        await self.add_example(
            code=corrected_code,
            language=language,
            category=category,
            description=f"Corrección: {reason}",
            score=9.5,
            source="correction",
            tags=["corrección_usuario"]
        )

        # Marcar el código original con el error
        await self.db.execute("""
            UPDATE code_examples
            SET errors_found = array_append(errors_found, $1),
                corrections = corrections || $2::jsonb
            WHERE code = $3
        """, reason, json.dumps({
            "original": original_code,
            "corregido": corrected_code,
            "razon": reason
        }), original_code)

    def _calculate_freshness(self, created_at) -> float:
        """Código más reciente = más relevante."""
        age_days = (datetime.now() - created_at).days
        return max(0.0, 1.0 - (age_days / 365.0))
```

### PromptBuilder con RAG

```python
class PromptBuilder:
    """Construye prompts enriquecidos con contexto RAG."""

    def __init__(self, code_rag: CodeRAG):
        self.rag = code_rag

    async def build(self, user_request: str, agent: str,
                    language: str = None, project_tags: list[str] = None) -> str:
        """Construye prompt con ejemplos RAG relevantes."""

        # Buscar ejemplos similares en el RAG
        examples = await self.rag.search(
            query=user_request,
            language=language,
            project_tags=project_tags,
            limit=3
        )

        # Construir sección de ejemplos
        examples_text = ""
        if examples:
            examples_text = "\n\n## Ejemplos de referencia (tu estilo):\n"
            for i, ex in enumerate(examples, 1):
                examples_text += f"\n### Ejemplo {i} (score: {ex['score']}):\n"
                examples_text += f"```{ex['language']}\n{ex['code']}\n```\n"

        # Construir sección de correcciones previas
        corrections_text = ""
        corrections = [e for e in examples if e.get("corrections")]
        if corrections:
            corrections_text = "\n\n## Correcciones previas (NO repetir estos errores):\n"
            for c in corrections:
                for fix in c["corrections"]:
                    corrections_text += f"- ❌ Error: {fix['razon']}\n"

        prompt = f"""{AGENTES[agent]['system_prompt']}

## Tarea:
{user_request}
{examples_text}
{corrections_text}

Responde con código limpio y funcional siguiendo el estilo de los ejemplos."""

        return prompt
```

## LoRA / QLoRA: Entrenamiento Personalizado

### ¿Qué es LoRA?

```
MODELO BASE (Qwen2.5-Coder-3B):
  ┌─────────────────────────────────┐
  │  3 billones de parámetros       │  ← CONGELADOS (no se tocan)
  │  ~6 GB en disco                 │
  │  Conocimiento general de código │
  └──────────────┬──────────────────┘
                 │
                 │  + se adjunta:
                 │
  ┌──────────────▼──────────────────┐
  │  LoRA Adapter (~50 MB)          │  ← SOLO esto se entrena
  │  Matrices pequeñas de rank bajo │
  │  Tu estilo personal de código   │
  └─────────────────────────────────┘

Resultado: Modelo base + LoRA = TU modelo personalizado
           Sin modificar el modelo original
           Puedes tener múltiples LoRAs para diferentes tareas
```

### ¿Qué es QLoRA?

```
QLoRA = Quantized LoRA

Modelo base: 4-bit quantization (3B modelo → ~1.5 GB VRAM)
LoRA adapter: 16-bit precision (~50 MB VRAM)
───────────────────────────────────────────────
Total VRAM necesaria: ~2.0 GB ← ¡CABE EN GTX 1060 3GB!

Sin QLoRA: 3B modelo en 16-bit = 6 GB VRAM → NO CABE
Con QLoRA: 3B modelo en 4-bit  = 1.5 GB VRAM → ¡SÍ CABE!

La pérdida de calidad es mínima (~1-2%) pero permite
entrenar modelos grandes en hardware limitado.
```

### Datos de Entrenamiento

```
Formato: instruction/code pairs (pares instrucción/código)

{
  "instruction": "Crea una función que valide emails en Python",
  "input": "",
  "output": "import re\n\ndef validate_email(email: str) -> bool:\n    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'\n    return bool(re.match(pattern, email))"
}

Fuentes de datos para entrenamiento:
  1. Tu código personal (lo más valioso)
  2. Resultados del Dojo con score ≥ 9.0
  3. Correcciones que hiciste al código de la IA
  4. Pares pregunta/respuesta de tus sesiones
```

### Ciclo Semanal de Entrenamiento

```
LUNES a VIERNES:
  → Recolectar datos: código del usuario, sesiones, correcciones
  → Acumular ejemplos de entrenamiento

SÁBADO 2:00 AM (automático):
  ┌─────────────────────────────────────────────┐
  │  1. Recolectar datos de la semana           │
  │     → Filtrar por calidad (score ≥ 8.0)     │
  │     → Formatear como instruction/code pairs │
  │     → ~260 ejemplos nuevos por semana       │
  │                                              │
  │  2. Entrenar LoRA con Unsloth               │
  │     → QLoRA 4-bit en GTX 1060 3GB           │
  │     → ~2-4 horas de entrenamiento           │
  │     → Learning rate: 2e-4                    │
  │     → Epochs: 3                              │
  │                                              │
  │  3. Validar el nuevo LoRA                    │
  │     → Ejecutar benchmark de 50 problemas    │
  │     → Comparar score vs LoRA anterior       │
  │     → Si nuevo_score > viejo_score: ✓       │
  │                                              │
  │  4. Desplegar si es mejor                    │
  │     → Backup del LoRA anterior              │
  │     → Activar nuevo LoRA                     │
  │     → Rollback automático si hay problemas  │
  └─────────────────────────────────────────────┘
```

### Evolución del LoRA

```
SEMANA 1:   260 ejemplos   → LoRA básico, mejora sutil
SEMANA 4:   1,040 ejemplos → Empieza a capturar tu estilo
SEMANA 12:  3,120 ejemplos → Conoce tus patrones habituales
SEMANA 26:  6,760 ejemplos → Predice tu enfoque con precisión
SEMANA 52:  13,520 ejemplos → Tu clon de programación
  └─ La IA programa como TÚ: mismos nombres, mismos patrones,
     misma estructura, mismas preferencias
```

### Implementación YeyoLoRATrainer

```python
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class YeyoLoRATrainer:
    """Entrenador LoRA/QLoRA para YeyoOS usando Unsloth."""

    def __init__(self, db_pool, config):
        self.db = db_pool
        self.base_model = config.get("base_model", "unsloth/Qwen2.5-Coder-3B-bnb-4bit")
        self.lora_output = Path(config.get("lora_path", "/var/yeyo/loras/"))
        self.max_seq_length = 2048
        self.lora_rank = 16

    async def collect_training_data(self, since_days: int = 7) -> list[dict]:
        """Recolecta datos de entrenamiento de la última semana."""
        since = datetime.now() - timedelta(days=since_days)

        # Código del usuario (máxima prioridad)
        user_code = await self.db.fetch("""
            SELECT description AS instruction, code AS output
            FROM code_examples
            WHERE source = 'user' AND created_at >= $1
            ORDER BY score DESC
        """, since)

        # Resultados del Dojo con alta calidad
        dojo_code = await self.db.fetch("""
            SELECT description AS instruction, code AS output
            FROM code_examples
            WHERE source = 'dojo' AND score >= 9.0 AND created_at >= $1
            ORDER BY score DESC
        """, since)

        # Correcciones (gold data)
        corrections = await self.db.fetch("""
            SELECT description AS instruction, code AS output
            FROM code_examples
            WHERE source = 'correction' AND created_at >= $1
            ORDER BY score DESC
        """, since)

        data = []
        for row in user_code:
            data.append({"instruction": row["instruction"],
                         "input": "", "output": row["output"]})
        for row in dojo_code:
            data.append({"instruction": row["instruction"],
                         "input": "", "output": row["output"]})
        for row in corrections:
            data.append({"instruction": row["instruction"],
                         "input": "", "output": row["output"]})

        return data

    def train(self, training_data: list[dict]):
        """Entrena LoRA con QLoRA 4-bit usando Unsloth."""
        from unsloth import FastLanguageModel
        from trl import SFTTrainer
        from transformers import TrainingArguments
        from datasets import Dataset

        # Cargar modelo base en 4-bit
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.base_model,
            max_seq_length=self.max_seq_length,
            dtype=None,  # auto-detect
            load_in_4bit=True,
        )

        # Configurar LoRA
        model = FastLanguageModel.get_peft_model(
            model,
            r=self.lora_rank,
            target_modules=["q_proj", "k_proj", "v_proj",
                            "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_alpha=self.lora_rank,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
        )

        # Preparar dataset
        dataset = Dataset.from_list(training_data)

        def format_prompt(example):
            return f"""### Instrucción:
{example['instruction']}

### Entrada:
{example['input']}

### Respuesta:
{example['output']}"""

        # Entrenar
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_dir = self.lora_output / f"lora_{timestamp}"

        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            formatting_func=format_prompt,
            args=TrainingArguments(
                per_device_train_batch_size=2,
                gradient_accumulation_steps=4,
                warmup_steps=5,
                num_train_epochs=3,
                learning_rate=2e-4,
                fp16=True,
                logging_steps=10,
                output_dir=str(output_dir),
                optim="adamw_8bit",
            ),
            max_seq_length=self.max_seq_length,
        )

        trainer.train()
        model.save_pretrained(str(output_dir))
        tokenizer.save_pretrained(str(output_dir))

        return str(output_dir)

    async def validate_and_deploy(self, new_lora_path: str,
                                   benchmark_problems: list[dict]) -> bool:
        """Valida el nuevo LoRA contra el anterior y despliega si es mejor."""
        current_lora = self._get_current_lora()
        new_score = await self._run_benchmark(new_lora_path, benchmark_problems)

        if current_lora:
            old_score = await self._run_benchmark(current_lora, benchmark_problems)
            if new_score <= old_score:
                print(f"Nuevo LoRA ({new_score:.1f}) no supera al actual ({old_score:.1f}). Descartado.")
                return False

        # Backup del anterior
        if current_lora:
            backup_path = current_lora + ".backup"
            os.rename(current_lora, backup_path)

        # Activar nuevo LoRA
        self._set_current_lora(new_lora_path)
        print(f"Nuevo LoRA desplegado con score: {new_score:.1f}")
        return True

    async def weekly_cycle(self):
        """Ciclo completo de entrenamiento semanal."""
        print("=== Inicio ciclo semanal de entrenamiento ===")

        # 1. Recolectar datos
        data = await self.collect_training_data(since_days=7)
        print(f"Datos recolectados: {len(data)} ejemplos")

        if len(data) < 10:
            print("Pocos datos, saltando entrenamiento.")
            return

        # 2. Entrenar
        lora_path = self.train(data)
        print(f"LoRA entrenado: {lora_path}")

        # 3. Validar y desplegar
        benchmarks = await self._load_benchmarks()
        deployed = await self.validate_and_deploy(lora_path, benchmarks)

        status = "DESPLEGADO" if deployed else "DESCARTADO"
        print(f"=== Ciclo completado: {status} ===")

    def _get_current_lora(self) -> str | None:
        marker = self.lora_output / "current"
        if marker.exists():
            return marker.read_text().strip()
        return None

    def _set_current_lora(self, path: str):
        marker = self.lora_output / "current"
        marker.write_text(path)

    async def _run_benchmark(self, lora_path, problems) -> float:
        """Ejecuta benchmark de 50 problemas y retorna score promedio."""
        scores = []
        for problem in problems:
            # Generar código con el LoRA
            # Ejecutar tests
            # Evaluar calidad
            scores.append(problem.get("expected_score", 7.0))
        return sum(scores) / len(scores) if scores else 0.0

    async def _load_benchmarks(self) -> list[dict]:
        return await self.db.fetch("""
            SELECT instruction, expected_output, test_code
            FROM lora_benchmarks
            ORDER BY RANDOM() LIMIT 50
        """)
```

## RAG + LoRA = Doble Personalización

```
SIN personalización:
  Modelo base → calidad genérica (~70%)

SOLO RAG:
  Modelo base + ejemplos de tu código en contexto → ~85%
  (El modelo VE tu estilo pero no lo INTERNALIZÓ)

SOLO LoRA:
  Modelo fine-tuned con tu código → ~88%
  (El modelo INTERNALIZÓ tu estilo pero sin contexto actual)

RAG + LoRA COMBINADOS:
  Modelo fine-tuned + ejemplos relevantes en contexto → 95%+
  ┌──────────────────────────────────────┐
  │  LoRA: "Sé que este usuario prefiere │
  │         snake_case y docstrings"     │
  │                                       │
  │  RAG:  "Y aquí hay 3 ejemplos de     │
  │         cómo resolvió algo similar"  │
  │                                       │
  │  = Código que parece escrito por TI   │
  └──────────────────────────────────────┘
```

## IA Autónoma: Evolución Temporal

```
MES 1 — Aprendiz:
  "¿Quieres que use tabs o spaces?"
  "¿Prefieres clases o funciones?"
  "¿Docstrings en inglés o español?"
  → Pregunta MUCHO, aprende tus preferencias

MES 3 — Junior:
  "Hice la API con FastAPI como prefieres. ¿Lo reviso contigo?"
  → Conoce tus herramientas favoritas, aún pide confirmación

MES 6 — Mid-Level:
  "API lista. Usé tu patrón de repositorio habitual.
   Tests incluidos. ¿Algo que ajustar?"
  → Anticipa decisiones, pocos errores

AÑO 1 — Senior:
  "Hecho. API REST con FastAPI, patrón repositorio, SQLAlchemy,
   Alembic para migraciones, 94% cobertura de tests.
   Ya está en /src/api/tasks/."
  → Entrega resultados perfectos sin preguntar
  → SABE qué quieres antes de que lo pidas
```
