# 19 — Sistema de Agentes: Catálogo y Arquitectura

> **Principio:** El modelo no necesita ser inteligente. Necesita ser un buen investigador.
> Un modelo de 3B mediocre con el sistema correcto supera a un modelo grande sin estructura.

**Fecha:** 4 de abril de 2026

---

## Por qué los agentes funcionan con un modelo malo

`qwen2.5:3b` en datos reales:
- CRUD básico → incorrecto ~40% del tiempo
- Debug → malo
- Olvida contexto en 8 prompts

La solución no es mejorar el modelo. Es cambiar lo que se le pide:

```
En vez de: "¿puedes escribir esto?"
→         "¿puedes encontrar esto?"
```

Cada agente tiene una tarea pequeña, específica y verificable.
Si falla, hay otro agente que lo atrapa antes de que el output llegue al usuario.

**El modelo nunca falla solo — el sistema lo sostiene:**

```
Modelo genera
  → Crítico puntúa (si < 8.0 → vuelve al Creador)
  → Verificador confirma con fuente real
  → Flash Memory verifica coherencia
  → Solo si pasa todo → llega al usuario
```

---

## Cómo escala con modelos mejores

El sistema no existe solo para compensar un modelo malo.
Cuando el modelo mejore, el sistema le da lo que ningún modelo tiene nativamente:

| Lo que aporta el sistema | Modelo malo | Modelo bueno |
|---|---|---|
| Flash Memory — años de contexto | Compensa olvido | Da contexto que ninguna API externa tiene |
| Gates de calidad | Atrapa basura | Detecta sutilezas que el modelo ignoraría |
| Micro-tareas con DB | Evita overflow de contexto | Permite razonar sin límite real de tokens |
| Patrones aprendidos por nodo | No los tenía | Personaliza al nivel que nunca lograría solo |
| Biblioteca de código curada | Compensa ignorancia | Amplía conocimiento con código testeado |

Cambiar el modelo en el futuro no pierde nada.
La Flash Memory, los patrones, la biblioteca, los errores aprendidos — todo se queda.

---

## Todos los agentes del sistema (~29 en total)

Todos corren sobre el mismo modelo base. Solo cambia el system prompt.
Costo de tener 29 agentes: 0 overhead de VRAM.

---

## GRUPO 1 — Agentes Transversales (todos los nodos los usan)

### Agente Creador
- **Rol:** Genera el output inicial (texto, código, guión, análisis)
- **Input:** Prompt del usuario + contexto de Flash Memory + patrones del nodo
- **Output:** Respuesta sin verificar
- **Cuándo:** Siempre — es el primer paso de cualquier generación
- **Nota:** No llega al usuario. Su output va al Crítico.

### Agente Crítico
- **Rol:** Puntúa el output del Creador de 0 a 10
- **Input:** Output del Creador + criterios de calidad del nodo
- **Output:** Score numérico + razón específica de falla si < 8.0
- **Gate:** Si score < 8.0 → devuelve al Creador con la razón. No avanza.
- **Cuándo:** Después de cada generación de código, guión o análisis
- **NO se activa para:** Tareas creativas puras (imágenes, música) — no son verificables

```python
SYSTEM_PROMPT = """Eres un revisor de calidad estricto.
Evalúas outputs en una escala del 0 al 10.
Criterios: precisión técnica, completitud, claridad, ausencia de errores.
Si el score es menor a 8.0, explica exactamente qué falló en una línea.
Responde solo con: SCORE: X.X | RAZON: <razón si < 8.0>"""
```

### Agente Verificador
- **Rol:** Confirma que el output aprobado por el Crítico es factualmente correcto
- **Input:** Output del Crítico + fuentes disponibles (Flash Memory, APIs, herramientas)
- **Output:** 🟢 VERIFICADO / 🟡 ESTIMACIÓN / 🔴 NO VERIFICADO + fuente
- **Cuándo:** Cuando el output contiene datos verificables (números, fechas, código ejecutable)
- **Herramientas:** Flash Memory, APIs externas, sandbox de ejecución

### Agente Curador
- **Rol:** Evalúa archivos antes de que entren a cualquier biblioteca
- **Input:** Archivo subido (código, video, imagen, texto)
- **Output:** Score 0-10 + decisión (✅ entra / ⚠️ entra con advertencia / ❌ rechazado)
- **Cuándo:** Cada vez que el usuario sube contenido al nodo Código

**Sistema de puntuación para código:**
```
¿Tiene tests?              → +2 puntos
¿Tiene type hints?         → +1 punto
¿Maneja errores?           → +2 puntos
¿Nombres descriptivos?     → +1 punto
¿Vulnerabilidades OWASP?   → -5 puntos
¿Complejidad excesiva?     → -2 puntos

≥ 8.0 → entra a biblioteca ✅
5-7.9 → entra con advertencia ⚠️
< 5.0 → rechazado con explicación ❌
```

---

## GRUPO 2 — El Investigador (pipeline de 6 fases)

No son 6 agentes distintos. Es 1 agente que sigue un pipeline con la DB como pegamento.

**Por qué la DB como pegamento:**
Una investigación de 15 minutos llenaría la ventana de contexto del modelo.
Con 4096 tokens útiles, es un muro infranqueable.

```
NO es una conversación larga de 15 minutos.
Son muchas llamadas de 10 segundos, conectadas por PostgreSQL.
```

| Paso | Tokens usados | Qué hace | Guarda en DB |
|------|--------------|----------|-------------|
| 1 | ~50 | Formula queries de búsqueda | investigacion_pasos |
| 2 | ~550 | Evalúa un candidato por llamada | investigacion_candidatos |
| 3 | ~300 | Rankea 5 resúmenes | scores actualizados |
| 4 | ~800 | Adapta el mejor candidato al proyecto | resultado_ensamblado |
| 5 | ~200 | Verifica el resultado final | verificacion_resultado |

Cada llamada empieza desde cero. El contexto vive en la DB, no en el modelo.

**Pipeline completo:**

```
FASE 1 — Búsqueda interna (milisegundos)
  Redis (caché exacto) → pgvector (similitud) → Flash Memory
  Si score > 0.95: entrega inmediata. Ni llega a Fase 2.

FASE 2 — Búsqueda externa (segundos)
  GitHub (estrellas > 100, actividad reciente)
  Stack Overflow (votos > 10)
  Documentación oficial (siempre prioridad máxima)
  MDN / DevDocs (para web y estándares)
  Recolecta 5-10 candidatos antes de evaluar.

FASE 3 — Evaluación
  Cada candidato recibe un score objetivo:
  - pasa_lint: +0.25
  - compatible_con_stack: +0.25
  - tiene_tests: +0.20
  - estrellas > 100: +0.15
  - actualizado hace < 180 días: +0.15
  Solo avanza el mejor (o los 2 si empatan).

FASE 4 — Ensamblaje
  Adapta la mejor solución al proyecto del usuario:
  - Renombra variables al estilo del usuario
  - Ajusta estructura de carpetas
  - Conecta imports existentes
  - Aplica convenciones del proyecto

FASE 5 — Verificación final
  Pasa por Agente Crítico + Agente Verificador.
  Si falla: vuelve a Fase 3 con el siguiente candidato.

FASE 6 — Almacenamiento
  Solución verificada → Flash Memory + pgvector + Redis
  La próxima vez: salto directo desde Fase 1.
```

**Tablas DB requeridas:**
```sql
CREATE TABLE investigacion_pasos (
    id              SERIAL PRIMARY KEY,
    tarea_id        TEXT NOT NULL,
    paso_numero     INTEGER NOT NULL,
    tipo            TEXT NOT NULL,  -- 'query','busqueda','evaluacion','ensamblaje','verificacion'
    input_resumen   TEXT,
    output_resumen  TEXT,
    tokens_usados   INTEGER,
    duracion_ms     INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE investigacion_candidatos (
    id              SERIAL PRIMARY KEY,
    tarea_id        TEXT NOT NULL,
    fuente          TEXT NOT NULL,  -- 'github','stackoverflow','docs','memoria_interna'
    url             TEXT,
    codigo          TEXT,
    score           FLOAT DEFAULT 0.0,
    seleccionado    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## GRUPO 3 — Los 12 Agentes del Code Dojo

Todos usan el mismo modelo base. Solo cambia el system prompt. 0ms de overhead.

| # | Agente | Especialidad | Output |
|---|--------|-------------|--------|
| 1 | **Arquitecto** | Diseña soluciones, diagramas ASCII, estructura de archivos | Plan de arquitectura |
| 2 | **Backend** | APIs REST/GraphQL, auth, DB, logging, manejo de errores | Código funcional |
| 3 | **Frontend** | React/Vue, accesible, responsivo, componentes | Componentes UI |
| 4 | **Mobile** | Flutter, React Native, Swift, Kotlin | Código móvil |
| 5 | **Base de Datos** | Schemas normalizados, queries optimizadas, migraciones | SQL optimizado |
| 6 | **Seguridad** | OWASP Top 10, XSS, injection, auth bypass, data leaks | Reporte de vulnerabilidades |
| 7 | **IA/ML** | Pipelines ML, entrenamiento, inferencia, MLOps | Modelos y pipelines |
| 8 | **Performance** | Profiling, cuellos de botella, algoritmos, I/O | Código optimizado |
| 9 | **Testing** | Tests unitarios/integración/e2e, TDD, BDD, cobertura | Suite de tests |
| 10 | **DevOps** | CI/CD, contenedores, IaC, monitoreo, deploys | Pipelines y configs |
| 11 | **Datos** | ETL pipelines, data warehouses, batch/streaming | Pipelines de datos |
| 12 | **Sistemas** | Drivers, kernel modules, networking, bajo nivel | Código de sistema |

**Pipeline del Code Dojo:**
```
Usuario pide código
  → ARQUITECTO planifica la estructura
  → BACKEND escribe el código
  → CRÍTICO puntúa (si < 8.0 → vuelve a BACKEND con razón)
  → TESTING genera y ejecuta tests REALES (pytest/jest)
  → Si tests fallan → BACKEND corrige
  → PERFORMANCE analiza complejidad algorítmica
  → SEGURIDAD revisa OWASP Top 10
  → Todos aprueban → usuario recibe código + reporte
```

**Entrenamiento nocturno (~1,800 desafíos en GTX 1060):**
- Genera desafíos de código por categoría
- Resuelve con el pipeline completo
- Evalúa resultados
- Guarda patrones de errores en Flash Memory
- Usa Unsloth para LoRA/QLoRA si el modelo necesita mejora específica

---

## GRUPO 4 — Agentes del Nodo Video

### Analizador de Patrones Virales
- **Rol:** Dado un video TikTok/Reel, extrae patrones de engagement automáticamente
- **Input:** Video subido por el usuario + metadata (likes/vistas opcionales)
- **Output:** Registro estructurado en `video_viral_patrones`
- **Extrae:**
  - Velocidad de cortes (cortes/segundo)
  - Gancho inicial (primeras 3 palabras + tipo: pregunta/shock/humor/afirmación)
  - Segundo exacto donde aparece texto en pantalla
  - Tipo de transición principal
  - Sincronización audio-video
  - Score de engagement calculado de likes/vistas

### Director Creativo
- **Rol:** Convierte descripción del usuario en guión estructurado con timing exacto
- **Input:** Descripción del video + patrones aprendidos (Capa 2) + duración objetivo
- **Output:** Guión con timestamps, indicaciones de corte, tipo de transición, texto en pantalla

### Generador de Narración
- **Herramienta:** Bark/XTTS (no Ollama — generación de audio real)
- **Input:** Texto del guión + voz seleccionada
- **Output:** Archivo de audio .wav

### Transcriptor
- **Herramienta:** Whisper (no Ollama — reconocimiento de audio real)
- **Input:** Video con audio
- **Output:** Subtítulos .srt + timestamps

---

## GRUPO 5 — Agentes del Nodo Imagen

### Mejorador de Prompts
- **Rol:** Convierte descripción casual del usuario en prompt optimizado para Stable Diffusion
- **Input:** Descripción del usuario + estilo deseado + patrones aprendidos (Capa 5)
- **Output:** Prompt técnico optimizado

```python
SYSTEM_PROMPT = """Eres un experto en prompts para Stable Diffusion.
Conviertes descripciones casuales en prompts técnicos optimizados.
Incluyes: estilo artístico, iluminación, composición, calidad técnica.
Formato: [sujeto], [estilo], [iluminación], [composición], [calidad]
Nunca inventas — trabajas con lo que el usuario describe."""
```

### Analista Visual (LLaVA)
- **Herramienta:** LLaVA (modelo de visión — no Ollama chat)
- **Rol:** Lee imágenes de referencia que sube el usuario
- **Input:** Imagen de referencia + instrucción ("hazla como esta pero más oscura")
- **Output:** Descripción técnica de la imagen → alimenta al Mejorador de Prompts

### Extractor de Patrones de Estilo
- **Rol:** Aprende qué prompts del usuario siempre resultan aceptados
- **Input:** Historial de generaciones + feedback del usuario (Capa 4)
- **Output:** Reglas guardadas en `imagen_patrones`
- **Ejemplo aprendido:** "Cuando añades 'dramatic lighting' este usuario siempre acepta la imagen"

---

## GRUPO 6 — Agentes del Nodo Automatización

### Detector de Tendencias
- **Rol:** Analiza APIs de redes sociales y detecta qué está viral ahora
- **Input:** Credenciales de YouTube/TikTok/Instagram + categorías de interés
- **Output:** Lista de tendencias con score de viralidad + tipo de contenido sugerido
- **Herramientas:** YouTube Data API v3, TikTok API, Instagram Graph API

### Generador de Guiones
- **Rol:** Crea guión optimizado para cada plataforma considerando tendencias activas
- **Input:** Tendencias detectadas + estilo aprendido del usuario (Capa 6) + plataforma objetivo
- **Output:** Guión con instrucciones específicas por plataforma (vertical TikTok vs horizontal YouTube)

### Optimizador de Publicación
- **Rol:** Genera metadata y elige el mejor momento para publicar
- **Input:** Video listo + plataforma + historial de engagement (Capa 4)
- **Output:** Título, descripción, hashtags optimizados + horario de publicación

### Analizador de Resultados
- **Rol:** Lee métricas post-publicación y actualiza el aprendizaje del nodo
- **Input:** Métricas reales de APIs (views, likes, retention, CTR)
- **Output:** Patrones actualizados en Capa 6 (Estrategia Evolutiva)
- **Aprendizaje:** "Los martes a las 7pm es tu mejor horario" — basado en datos reales, no intuición

---

## GRUPO 7 — Agente Orquestador

### YeyoOrquestador (decide el flujo)
- **Rol:** Dado el estado actual del grafo (EstadoGrafo), decide qué nodo ejecutar siguiente
- **Cuándo:** En edges tipo "IA decide" — cuando la lógica de routing no es determinística
- **Herramienta:** Ollama tool calling
- **Input:** EstadoGrafo con historial de ejecución + nodos disponibles
- **Output:** ID del siguiente nodo a ejecutar

No genera contenido. Solo decide el flujo.

---

## Resumen total

| Grupo | Agentes | Estado |
|-------|---------|--------|
| Transversales (Creador/Crítico/Verificador/Curador) | 4 | 🔴 Por construir |
| Investigador (pipeline 6 fases) | 1 pipeline | 🔶 Fase 1 lista (Flash Memory) |
| Code Dojo | 12 | 🔴 Por construir |
| Nodo Video | 4 | 🔴 Por construir |
| Nodo Imagen | 3 | 🔴 Por construir |
| Nodo Automatización | 4 | 🔴 Por construir |
| Orquestador | 1 | 🔶 Parcial (EstadoGrafo existe) |
| **Total** | **~29** | **~45% del sistema** |

---

## Dependencias entre agentes

```
Flash Memory (base de todo)
  └── Investigador Fase 1 (búsqueda interna)
        └── Investigador Fases 2-6 (necesita Crítico + Verificador)
              └── Code Dojo (necesita Investigador + Crítico + Verificador + Curador)
                    └── Nodos (necesitan Code Dojo para código + Investigador para contexto)

YeyoOrquestador (runtime de todo)
  └── Corre todos los pipelines anteriores como grafos
```

La Flash Memory es la base. El Investigador es el segundo bloque.
Sin esos dos, los demás agentes no tienen dónde buscar ni cómo verificar.
