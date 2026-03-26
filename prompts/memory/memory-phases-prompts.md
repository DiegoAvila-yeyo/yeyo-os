# YeyoOS — Memory Architecture: Prompts de Implementación

> Cada prompt es autónomo. Incluye contexto completo, tarea, criterios de aceptación y tests.

---

## FASE 1 — Migración BD: agregar `namespace`

### PROMPT 1.1 — Migración SQL y modelo

```
Eres un ingeniero de software senior trabajando en YeyoOS, un OS AI-nativo.
Stack: Python 3.11, FastAPI, PostgreSQL con pgvector, asyncpg.

CONTEXTO:
La tabla `flash_memories` en PostgreSQL tiene esta estructura actual:
- id (uuid), content (text), type (varchar), tier (varchar)
- embedding (vector(3584)), checksum (varchar), access_count (int)
- metadata (jsonb), source (varchar), created_at, accessed_at, updated_at

El campo `source` solo dice de dónde vino la memoria ('chat_extraction', 'docs').
Necesitamos saber a qué nodo y tipo de memoria pertenece.

TAREA:
1. Crear migración SQL que agregue columna `namespace VARCHAR(50) DEFAULT 'chat:usuario'`
2. Crear índice: `CREATE INDEX idx_memories_namespace ON flash_memories(namespace)`
3. Migrar datos existentes:
   - source='chat_extraction' → namespace='chat:usuario'
   - source='docs' → namespace='sistema:docs'
   - source='prompts' → namespace='sistema:prompts'
4. Actualizar el modelo Pydantic `Memory` en `src/memory/models.py`:
   - Agregar campo: `namespace: str = Field(default='chat:usuario')`
   - El campo NO debe tener restricción de patrón (valores abiertos para extensibilidad)
5. Actualizar `FlashMemory.store()` en `src/memory/flash_memory.py`:
   - Aceptar parámetro opcional `namespace: str = 'chat:usuario'`
   - Guardarlo en la BD

NAMESPACES VÁLIDOS (referencia, no restricción):
chat:usuario, imagen:usuario, imagen:conocimiento,
codigo:usuario, codigo:conocimiento, video:usuario,
video:conocimiento, automatizacion:usuario, automatizacion:conocimiento,
sistema:docs, sistema:prompts, descartado

PRINCIPIOS: SOLID (Single Responsibility), DRY, cambio mínimo.
No romper funcionalidad existente — el campo es opcional con default.

CRITERIOS DE ACEPTACIÓN:
- [ ] Migración SQL ejecuta sin errores
- [ ] Columna namespace existe en la tabla
- [ ] Índice idx_memories_namespace creado
- [ ] Datos existentes migrados correctamente
- [ ] Modelo Memory tiene campo namespace
- [ ] FlashMemory.store() acepta namespace sin romper llamadas existentes
- [ ] Tests unitarios existentes siguen pasando

TESTS DE ACEPTACIÓN:
1. psql: `SELECT COUNT(*) FROM flash_memories WHERE namespace='chat:usuario';` → debe ser > 0
2. psql: `\d flash_memories` → debe mostrar columna namespace
3. psql: `\di flash_memories*` → debe mostrar idx_memories_namespace
4. Python: `memory = Memory(content='test', type='fact')` → `memory.namespace == 'chat:usuario'`
5. pytest: correr `python3.11 -m pytest tests/unit/memory/ --tb=short` → 0 failures
```

---

### PROMPT 1.2 — Verificación y rollback

```
Eres un ingeniero de QA para YeyoOS.

CONTEXTO:
Se acaba de ejecutar una migración SQL que agrega namespace a flash_memories.

TAREA:
Crear script `scripts/verify_migration_namespace.py` que:
1. Se conecta a PostgreSQL (usar DATABASE_URL del env)
2. Verifica que la columna namespace existe
3. Verifica que el índice existe
4. Cuenta memorias por namespace y las imprime
5. Detecta memorias sin namespace (NULL) y las reporta
6. Salida: ✅ o ❌ por cada verificación con mensaje claro

Si alguna verificación falla, imprimir el SQL de rollback:
  `ALTER TABLE flash_memories DROP COLUMN namespace;`

CRITERIOS DE ACEPTACIÓN:
- [ ] Script corre sin errores con `python3.11 scripts/verify_migration_namespace.py`
- [ ] Imprime conteo por namespace
- [ ] Detecta y reporta NULLs
- [ ] Rollback SQL visible si hay error

TESTS DE ACEPTACIÓN:
1. `python3.11 scripts/verify_migration_namespace.py` → todas las líneas con ✅
2. Conteo de 'chat:usuario' > 0
3. Conteo de 'sistema:docs' > 0
4. 0 memorias con namespace NULL
```

---

## FASE 2 — Clasificador automático

### PROMPT 2.1 — Crear NamespaceClassifier

```
Eres un ingeniero senior en YeyoOS.
Stack: Python 3.11, asyncpg, Ollama como LLM (modelo qwen2.5-coder:7b).

CONTEXTO:
Tenemos `src/memory/extraction.py` con `MemoryExtractor` que usa palabras clave
para decidir si guardar una memoria. Es frágil.

La tabla flash_memories ahora tiene columna `namespace` (Fase 1).

TAREA:
Crear `src/memory/classifier.py` con clase `NamespaceClassifier`:

```python
class NamespaceClassifier:
    def __init__(self, ia_provider: IAProvider): ...
    
    async def classify(self, content: str) -> str:
        """Retorna el namespace correcto para este contenido."""
        ...
    
    async def classify_batch(self, contents: list[str]) -> list[str]:
        """Clasifica múltiples contenidos eficientemente."""
        ...
```

NAMESPACES POSIBLES:
- chat:usuario → preferencias personales, nombre, familia, hobbies
- imagen:usuario → estilos visuales, prompts favoritos del user
- imagen:conocimiento → técnicas de prompt, vocabulario técnico, composición
- codigo:usuario → lenguajes del user, proyectos, stack personal
- codigo:conocimiento → patrones SOLID, snippets, buenas prácticas
- video:usuario → preferencias de edición del user
- video:conocimiento → técnicas narrativas, formatos, transiciones
- automatizacion:usuario → flujos y servicios del user
- automatizacion:conocimiento → patrones de automatización, webhooks
- descartado → saludos, confirmaciones, ruido ("ok", "gracias", "sí")

PROMPT al LLM (incluirlo en el código):
"Clasifica el siguiente texto en exactamente uno de estos namespaces.
Responde SOLO con el namespace, sin explicación.
[lista de namespaces]
Texto: {content}"

REGLAS:
- Si la IA no responde un namespace válido → default 'chat:usuario'
- Timeout de 10s → default 'chat:usuario'
- Nunca lanzar excepciones (degradación graceful)

CRITERIOS DE ACEPTACIÓN:
- [ ] Clase creada y funcional
- [ ] classify() retorna siempre un namespace válido
- [ ] Maneja errores sin crash
- [ ] Tests unitarios con mock del LLM

TESTS DE ACEPTACIÓN:
1. `classify("Prefiero TypeScript")` → 'codigo:usuario'
2. `classify("Hola como estás")` → 'descartado'
3. `classify("La regla de tercios en fotografía")` → 'imagen:conocimiento'
4. `classify("Mi nombre es Diego")` → 'chat:usuario'
5. Con mock que falla → retorna 'chat:usuario' (no crash)
6. `python3.11 -m pytest tests/unit/memory/test_classifier.py` → todos pasan
```

---

### PROMPT 2.2 — Integrar clasificador en el flujo de guardado

```
Eres un ingeniero senior en YeyoOS.

CONTEXTO:
`NamespaceClassifier` ya existe en `src/memory/classifier.py`.
`FlashMemory.store()` ya acepta parámetro `namespace`.
`ContextualChatService` en `src/chat/contextual_service.py` guarda memorias
en el método `_extract_and_store()`.

TAREA:
Modificar `_extract_and_store()` en `src/chat/contextual_service.py`:
1. Después de guardar la memoria, llamar al clasificador de forma async (background)
2. El clasificador actualiza el namespace en BD: `UPDATE flash_memories SET namespace=$1 WHERE id=$2`
3. El flujo principal NO espera al clasificador (usar asyncio.create_task)
4. Si el clasificador falla → namespace queda como 'chat:usuario' (no crash)

NUEVO FLUJO:
mensaje → guardar (namespace='chat:usuario') → create_task(clasificar y actualizar)
                                                      ↓
                                              (2-5 segundos después)
                                              UPDATE namespace = 'codigo:usuario'

CRITERIOS DE ACEPTACIÓN:
- [ ] El chat NO se ralentiza por la clasificación
- [ ] Las memorias eventualmente tienen el namespace correcto
- [ ] Si clasificador falla, memoria existe con namespace default
- [ ] No hay import circular

TESTS DE ACEPTACIÓN:
1. Enviar "Prefiero TypeScript" → respuesta llega normal (< 2s extra)
2. Esperar 10s → `SELECT namespace FROM flash_memories ORDER BY created_at DESC LIMIT 1`
   → debe ser 'codigo:usuario' no 'chat:usuario'
3. Con clasificador fallando (mock) → memoria existe, namespace='chat:usuario'
```

---

## FASE 3 — Guardar todo sin filtros

### PROMPT 3.1 — Refactorizar extracción a guardado directo

```
Eres un ingeniero senior en YeyoOS.

CONTEXTO:
`src/memory/extraction.py` tiene `MemoryExtractor` con `should_extract()`
que usa palabras clave para filtrar. Esto pierde información del usuario.

El nuevo enfoque: guardar SIEMPRE el mensaje del usuario (con su embedding),
dejar que el clasificador (Fase 2) decida el namespace.

TAREA:
Refactorizar `src/memory/extraction.py`:

1. ELIMINAR `should_extract()` completamente
2. ELIMINAR el EXTRACTION_PROMPT que le pedía al LLM resumir en JSON
3. MANTENER la clase `MemoryExtractor` (no romper imports)
4. Nuevo método principal:
```python
async def extract_and_store(
    self,
    user_message: str,
    flash_memory: FlashMemory,
    embedding_service,
    namespace: str = 'chat:usuario'
) -> bool:
    """
    Guarda el mensaje del usuario directamente sin filtros.
    Retorna True si se guardó, False si era ruido puro.
    """
```
5. Ruido puro (no guardar): mensajes < 3 palabras sin contenido
   ("ok", "sí", "no", "gracias", "hola") → no guardar
6. Todo lo demás → guardar con embedding

PRINCIPIOS: cambio mínimo, no romper imports existentes.

CRITERIOS DE ACEPTACIÓN:
- [ ] should_extract() eliminado
- [ ] EXTRACTION_PROMPT eliminado  
- [ ] Clase MemoryExtractor sigue importable
- [ ] Mensajes de ruido no se guardan
- [ ] Todo mensaje con contenido se guarda
- [ ] Tests unitarios pasan

TESTS DE ACEPTACIÓN:
1. `extract_and_store("ok")` → False (no guardado)
2. `extract_and_store("gracias")` → False
3. `extract_and_store("Mi café favorito es el Americano")` → True
4. `extract_and_store("Prefiero TypeScript estricto")` → True
5. psql después del test: `SELECT COUNT(*) FROM flash_memories WHERE content='Mi café favorito es el Americano'` → 1
6. `python3.11 -m pytest tests/unit/memory/ --tb=short` → 0 failures
```

---

## FASE 4 — Búsqueda por namespace

### PROMPT 4.1 — Actualizar search_semantic con namespaces

```
Eres un ingeniero senior en YeyoOS.

CONTEXTO:
`FlashMemory.search_semantic()` en `src/memory/flash_memory.py` ya tiene
parámetro `sources: list[str] | None`. Necesita actualizarse a `namespaces`.

`ContextualChatService._search_relevant_memories()` ya pasa `sources=['chat_extraction']`.
Esto debe cambiar a usar namespaces.

TAREA:
1. En `src/memory/flash_memory.py`:
   - Renombrar parámetro `sources` → `namespaces` en `search_semantic()`
   - SQL: `AND namespace = ANY($4::text[])` (ya implementado como sources, solo renombrar)
   - Mantener backward compatibility: si `namespaces=None` → busca en todos

2. En `src/chat/contextual_service.py`:
   - `_search_relevant_memories()` debe aceptar `namespaces: list[str]`
   - Default: `['chat:usuario']`
   - Pasar namespaces a `search_semantic()`

3. En `src/api/routes/memory.py`:
   - Endpoint `/memory/search` debe aceptar query param `namespace: str | None`
   - Si se pasa → filtrar por ese namespace

CRITERIOS DE ACEPTACIÓN:
- [ ] search_semantic acepta namespaces
- [ ] Búsqueda sin namespace funciona igual que antes
- [ ] Búsqueda con namespace=['chat:usuario'] solo retorna esas memorias
- [ ] Endpoint /memory/search acepta ?namespace=chat:usuario
- [ ] Tests pasan

TESTS DE ACEPTACIÓN:
1. `curl "http://localhost:8000/api/v1/memory/search?q=café&namespace=chat:usuario"`
   → solo memorias de chat:usuario
2. `curl "http://localhost:8000/api/v1/memory/search?q=TypeScript&namespace=codigo:usuario"`
   → solo memorias de codigo:usuario
3. Sin namespace → retorna de todos los namespaces
4. `python3.11 -m pytest tests/unit/memory/ --tb=short` → 0 failures
```

---

## FASE 5 — Seed de conocimiento base

### PROMPT 5.1 — Script de seed para imagen:conocimiento y codigo:conocimiento

```
Eres un ingeniero senior en YeyoOS con conocimiento de IA generativa y código.

CONTEXTO:
Los namespaces `:conocimiento` están vacíos. Necesitan conocimiento base
para que la IA pueda ayudar mejor a los usuarios sin que ellos tengan
que explicar lo básico.

TAREA:
Crear `scripts/seed_knowledge.py` que pueble la BD con conocimiento base:

IMAGEN:CONOCIMIENTO (mínimo 15 entradas):
- Vocabulario de prompts: "photorealistic, 8K, RAW photo, sharp focus, bokeh..."
- Negative prompts por categoría: retratos, paisajes, arquitectura
- Estilos artísticos: anime, oil painting, watercolor, cinematic
- Composición: regla de tercios, simetría, profundidad de campo
- Iluminación: golden hour, studio lighting, dramatic shadows

CODIGO:CONOCIMIENTO (mínimo 15 entradas):
- SOLID principles con ejemplos concisos
- Patrones: Repository, Factory, Observer, Singleton
- TypeScript: tipos estrictos, generics, utility types
- Python: type hints, dataclasses, async/await patterns
- Estructura de proyecto Next.js y FastAPI

VIDEO:CONOCIMIENTO (mínimo 10 entradas):
- Formatos por plataforma: YouTube (16:9), TikTok (9:16), Instagram Reels
- Técnicas de corte: jump cut, L-cut, J-cut
- Narrativa: hook en primeros 3 segundos, regla del 3 actos
- Transiciones y cuándo evitarlas

AUTOMATIZACION:CONOCIMIENTO (mínimo 10 entradas):
- Webhooks: estructura típica de payload
- Rate limiting y retry con exponential backoff
- Patrones: if-this-then-that, filter-transform-output
- APIs comunes: GitHub, Slack, Notion, Gmail estructura de requests

El script debe:
- Conectarse a PostgreSQL (DATABASE_URL del env o default local)
- Generar embeddings para cada entrada usando OllamaEmbeddingService
- Guardar con namespace correcto y source='seed'
- Ser idempotente: no duplicar si ya existe (verificar por checksum)
- Mostrar progreso: "✅ imagen:conocimiento: 15 entradas"

CRITERIOS DE ACEPTACIÓN:
- [ ] Script corre: `python3.11 scripts/seed_knowledge.py`
- [ ] No duplica en segunda ejecución (idempotente)
- [ ] Mínimo 50 entradas totales en la BD
- [ ] Cada entrada tiene embedding no nulo
- [ ] Namespaces correctos asignados

TESTS DE ACEPTACIÓN:
1. `python3.11 scripts/seed_knowledge.py` → "✅ Total: 50+ entradas"
2. Segunda ejecución → "⏭️ Sin cambios (ya existe)"
3. `curl "http://localhost:8000/api/v1/memory/search?q=regla+de+tercios&namespace=imagen:conocimiento"`
   → retorna resultado relevante
4. `curl "http://localhost:8000/api/v1/memory/search?q=SOLID&namespace=codigo:conocimiento"`
   → retorna resultado relevante
```

---

## FASE 6 — Conectar nodos

### PROMPT 6.1 — Conectar Nodo Imagen a memoria

```
Eres un ingeniero senior en YeyoOS.

CONTEXTO:
Stack: FastAPI backend, Next.js frontend.
El nodo Imagen tiene un endpoint en el backend que recibe el prompt
y llama a la IA para generar la imagen.
Flash Memory ya tiene imagen:usuario e imagen:conocimiento poblados.

TAREA:
1. En el backend (endpoint de generación de imagen):
   - Antes de llamar al generador, buscar en Flash Memory:
     - namespaces=['imagen:usuario', 'imagen:conocimiento']
     - query = el prompt del usuario
     - limit=5, threshold=0.3
   - Inyectar las memorias relevantes en el prompt:
     ```
     Prompt original: "un paisaje al atardecer"
     Prompt enriquecido: "un paisaje al atardecer, [preferencias: estilo realista,
     colores fríos] [técnicas: golden hour, wide angle, cinematic, 8K]"
     ```
   - Guardar el prompt del usuario en imagen:usuario (async, no bloquea)

2. El enriquecimiento es aditivo — nunca reemplaza el prompt del usuario,
   solo agrega contexto al final.

3. Si Flash Memory falla → usar prompt original sin crash.

CRITERIOS DE ACEPTACIÓN:
- [ ] Endpoint de imagen busca en memoria antes de generar
- [ ] Prompt se enriquece con preferencias y conocimiento
- [ ] Fallo de memoria no rompe la generación
- [ ] Prompt del usuario se guarda en imagen:usuario

TESTS DE ACEPTACIÓN:
1. Primera generación "un paisaje" → prompt enriquecido con imagen:conocimiento
2. Decir "prefiero colores cálidos" → próxima generación incluye ese contexto
3. Con Flash Memory caída (mock) → imagen se genera igual con prompt original
4. psql: prompts del user aparecen en imagen:usuario después de generar
```

---

### PROMPT 6.2 — Conectar Nodo Código a memoria

```
Eres un ingeniero senior en YeyoOS.

CONTEXTO:
El nodo Código tiene un endpoint que recibe descripción del usuario
y genera código usando la IA.
Flash Memory tiene codigo:usuario y codigo:conocimiento.

TAREA:
1. En el backend (endpoint de generación de código):
   - Buscar en Flash Memory antes de generar:
     - namespaces=['codigo:usuario', 'codigo:conocimiento']
   - Construir system prompt enriquecido:
     ```
     "Genera código siguiendo estas preferencias del usuario: [memoria usuario]
     Aplica estas buenas prácticas: [memoria conocimiento]
     Solicitud: {descripción del usuario}"
     ```
   - Guardar la solicitud en codigo:usuario (async)

2. Si el usuario nunca ha definido preferencias → usar solo codigo:conocimiento.

CRITERIOS DE ACEPTACIÓN:
- [ ] Código generado respeta el stack del usuario si está en memoria
- [ ] Aplica buenas prácticas del conocimiento base
- [ ] Fallo de memoria → genera código sin contexto (no crash)
- [ ] Solicitudes guardadas en codigo:usuario

TESTS DE ACEPTACIÓN:
1. Sin memoria previa → genera código con buenas prácticas base
2. Con "prefiero TypeScript" en memoria → genera TypeScript aunque no lo pida explícitamente
3. "crea función de validación" → aplica patrones de codigo:conocimiento
4. psql: solicitud guardada en codigo:usuario después de generar
```

---

## Checklist general de aceptación del sistema completo

```
MEMORIA BÁSICA (Fases 1-3):
- [ ] Todo mensaje del usuario se guarda en flash_memories
- [ ] Namespace asignado en < 10 segundos tras guardar
- [ ] Mensajes de ruido (< 3 palabras sin contenido) no se guardan

RECUPERACIÓN (Fase 4):
- [ ] Búsqueda por namespace retorna solo memorias del namespace correcto
- [ ] Búsqueda semántica funciona sin pgvector errors en logs
- [ ] Threshold 0.3 retorna resultados relevantes sin ruido

CONOCIMIENTO BASE (Fase 5):
- [ ] 50+ entradas de conocimiento en la BD
- [ ] Búsqueda "regla de tercios" → imagen:conocimiento ✅
- [ ] Búsqueda "SOLID" → codigo:conocimiento ✅

NODOS CONECTADOS (Fase 6):
- [ ] Nodo Imagen enriquece prompts automáticamente
- [ ] Nodo Código respeta stack del usuario
- [ ] Todos los nodos: fallo de memoria no rompe funcionalidad

TEST FINAL DE INTEGRACIÓN:
1. "Mi estilo favorito para imágenes es anime con colores vibrantes"
   → namespace='imagen:usuario' en BD
2. Generar imagen "un samurai" → prompt incluye "anime, colores vibrantes"
3. "Uso TypeScript con Zod para validaciones"
   → namespace='codigo:usuario' en BD
4. Generar "función de login" → código TypeScript con Zod
5. Recargar página → preferencias siguen disponibles (persistencia real)
```
