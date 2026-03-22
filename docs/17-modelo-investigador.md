# 17 — El Modelo Investigador

## Paradigma de búsqueda, razonamiento y aprendizaje autónomo

> **Yeyo no genera — busca, verifica y ensambla. El modelo no necesita ser inteligente — necesita ser buen investigador.**

**Fecha:** 21 de marzo de 2026

---

## 1. Cambio de Paradigma: De Generador a Investigador

### El problema

`qwen2.5:3b` tiene 3 billones de parámetros. En pruebas reales:

| Tarea                  | Resultado          |
|------------------------|--------------------|
| CRUD básico            | Incorrecto ~40%    |
| Debug de errores       | Malo               |
| Retención de contexto  | Olvida en 8 prompts|
| Arquitectura compleja  | No confiable       |

El modelo es demasiado pequeño para **GENERAR** soluciones confiables de memoria. Pedirle que invente código complejo desde cero es como pedirle a un junior que diseñe un sistema distribuido sin Google.

### La solución

Cambiar la pregunta. En vez de *"¿puedes escribir esto?"* → *"¿puedes encontrar esto?"*

**Habilidades que un modelo de 3B SÍ tiene:**

- Entender preguntas en español/inglés
- Formular queries de búsqueda relevantes
- Leer y extraer información de documentos
- Comparar soluciones y elegir la mejor
- Seguir un pipeline de pasos definidos
- Adaptar código existente a otro contexto

**Habilidades que ya NO necesita** (porque busca en vez de inventar):

- ~~Escribir sistemas complejos desde cero~~
- ~~Razonar sobre arquitectura abstracta~~
- ~~Debuggear lógica compleja sin referencia~~

El modelo pasa de ser un **generador poco confiable** a ser un **investigador metódico**. La diferencia es enorme: un investigador mediocre con acceso a buenas fuentes supera a un genio sin recursos.

### Pipeline de investigación (6 fases)

```
┌─────────────────────────────────────────────────────────────────────┐
│                   PIPELINE DE INVESTIGACIÓN                         │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────────┐   │
│  │  FASE 1  │──▶│  FASE 2  │──▶│  FASE 3   │──▶│   FASE 4     │   │
│  │ Búsqueda │   │ Búsqueda │   │Evaluación │   │ Ensamblaje   │   │
│  │ interna  │   │ externa  │   │           │   │              │   │
│  └──────────┘   └──────────┘   └───────────┘   └──────┬───────┘   │
│       │                              ▲                  │          │
│       │ hit                          │ falla            ▼          │
│       │                              │          ┌──────────────┐   │
│       ▼                              └──────────│   FASE 5     │   │
│  ┌──────────┐                                   │ Verificación │   │
│  │ Entrega  │◀──────────────────────────────────│   final      │   │
│  │ inmediata│           pasa                    └──────────────┘   │
│  └──────────┘                                          │          │
│       │                                                │ pasa     │
│       │                                                ▼          │
│       │                                        ┌──────────────┐   │
│       └────────────────────────────────────────│   FASE 6     │   │
│                                                │Almacenamiento│   │
│                                                └──────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**FASE 1 — Búsqueda interna** (milisegundos)

```
Redis (caché exacto) → pgvector (similitud semántica) → Flash Memory (histórico)
```

Si la confianza es alta (`score > 0.95`): entrega inmediata. El usuario ni nota que hubo búsqueda.

**FASE 2 — Búsqueda externa** (segundos a minutos)

| Fuente               | Criterio de calidad                |
|-----------------------|------------------------------------|
| GitHub repos          | Estrellas > 100, actividad reciente|
| Stack Overflow         | Respuestas con votos > 10          |
| Documentación oficial | Siempre prioridad máxima           |
| MDN / DevDocs         | Para web y estándares              |

Recolecta **5-10 candidatos** antes de evaluar. Nunca se queda con el primero que encuentra.

**FASE 3 — Evaluación** (minutos)

Cada candidato se evalúa con criterios objetivos:

```python
def evaluar_candidato(candidato: dict) -> float:
    score = 0.0

    if pasa_yeyo_lint(candidato["codigo"]):
        score += 0.25
    if es_compatible_stack(candidato, stack_usuario):
        score += 0.25
    if tiene_tests(candidato):
        score += 0.20
    if candidato["estrellas"] > 100:
        score += 0.15
    if candidato["ultima_actualizacion_dias"] < 180:
        score += 0.15

    return score
```

Rankea candidatos por score. Solo avanza el mejor (o los 2 mejores si están empatados).

**FASE 4 — Ensamblaje** (minutos)

Toma la mejor solución y la adapta al proyecto del usuario:

- Renombra variables al estilo del usuario
- Ajusta la estructura de carpetas
- Conecta con imports existentes
- Aplica convenciones del proyecto (tabs vs spaces, naming, etc.)

**FASE 5 — Verificación final** (minutos)

Pasa por los 5 niveles de validación (ver sección 4). Si falla: vuelve a Fase 3 con el siguiente candidato.

**FASE 6 — Almacenamiento** (milisegundos)

```
Solución verificada → Flash Memory + pgvector + Redis
```

La próxima vez que alguien pregunte algo similar: salto directo desde Fase 1. El conocimiento se acumula.

---

## 2. Micro-Tareas con DB como Pegamento

### El problema del contexto

Una investigación de 15 minutos con múltiples búsquedas, evaluaciones y ensamblajes llenaría la ventana de contexto del modelo. Con `qwen2.5:3b` y ~4096 tokens útiles, esto es un muro infranqueable.

### La solución

> **No es una conversación larga de 15 minutos. Son muchas llamadas de 10 segundos, conectadas por la base de datos.**

```
┌────────────────────────────────────────────────────────────────┐
│                    MICRO-TAREAS CON DB                          │
│                                                                 │
│  Paso 1          Paso 2          Paso 3          Paso N        │
│  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐  │
│  │ LLM     │     │ LLM     │     │ LLM     │     │ LLM     │  │
│  │ ~50 tok │     │~550 tok │     │~300 tok │     │~200 tok │  │
│  └────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘  │
│       │               │               │               │        │
│       ▼               ▼               ▼               ▼        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              PostgreSQL (estado compartido)              │   │
│  │                                                         │   │
│  │  investigacion_pasos | candidatos | evaluaciones         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Cada paso empieza desde CERO.                                  │
│  La DB conecta los pasos, NO el contexto.                       │
└────────────────────────────────────────────────────────────────┘
```

Cada paso es una llamada **independiente** al modelo:

| Paso | Input                      | Tokens | Output             | Acción       |
|------|----------------------------|--------|--------------------|--------------|
| 1    | Instrucción de búsqueda    | ~50    | Query formulado    | Guarda en DB |
| 2    | Instrucción + snippet      | ~550   | Evaluación         | Guarda en DB |
| 3    | Instrucción + 5 resúmenes  | ~300   | Ranking            | Guarda en DB |
| 4    | Instrucción + código mejor | ~800   | Código adaptado    | Guarda en DB |
| 5    | Instrucción + resultado    | ~200   | Verificación       | Guarda en DB |

El modelo **NUNCA** se acerca al límite porque cada paso empieza desde cero. La continuidad vive en la base de datos, no en la ventana de contexto.

### Tabla de tracking de investigación

```sql
CREATE TABLE investigacion_pasos (
    id              SERIAL PRIMARY KEY,
    tarea_id        TEXT NOT NULL,
    paso_numero     INTEGER NOT NULL,
    tipo            TEXT NOT NULL,
        -- 'query', 'busqueda', 'evaluacion', 'ensamblaje', 'verificacion'
    input_resumen   TEXT,
    output_resumen  TEXT,
    tokens_usados   INTEGER,
    duracion_ms     INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Índice para recuperar el estado de una tarea rápidamente
CREATE INDEX idx_inv_tarea ON investigacion_pasos(tarea_id, paso_numero);
```

### Tabla de candidatos por investigación

```sql
CREATE TABLE investigacion_candidatos (
    id              SERIAL PRIMARY KEY,
    tarea_id        TEXT NOT NULL,
    fuente          TEXT NOT NULL,      -- 'github', 'stackoverflow', 'docs'
    url             TEXT,
    codigo          TEXT,
    score           FLOAT DEFAULT 0.0,
    paso_evaluacion INTEGER,            -- en qué paso se evaluó
    seleccionado    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### Ejemplo de flujo completo

```python
async def investigar(tarea: str, tarea_id: str):
    # Paso 1: Formular queries de búsqueda
    queries = await llm_call(
        prompt=f"Formula 3 queries de búsqueda para: {tarea}",
        max_tokens=100
    )
    await db.guardar_paso(tarea_id, paso=1, tipo="query", output=queries)

    # Paso 2: Ejecutar búsquedas (sin LLM, pura herramienta)
    candidatos = await buscar_externo(queries)
    for c in candidatos:
        await db.guardar_candidato(tarea_id, c)

    # Paso 3: Evaluar cada candidato (llamada independiente por cada uno)
    for c in candidatos:
        resumen = await llm_call(
            prompt=f"Evalúa este código para '{tarea}':\n{c.codigo[:500]}",
            max_tokens=150
        )
        await db.actualizar_score(c.id, resumen)
        await db.guardar_paso(tarea_id, paso=3, tipo="evaluacion", output=resumen)

    # Paso 4: Ensamblar el mejor
    mejor = await db.mejor_candidato(tarea_id)
    adaptado = await llm_call(
        prompt=f"Adapta este código al proyecto:\n{mejor.codigo[:800]}",
        max_tokens=500
    )
    await db.guardar_paso(tarea_id, paso=4, tipo="ensamblaje", output=adaptado)

    # Paso 5: Verificar (herramientas externas, sin LLM)
    resultado = await verificar_5_niveles(adaptado)
    await db.guardar_paso(tarea_id, paso=5, tipo="verificacion", output=resultado)

    return adaptado if resultado.ok else await investigar_siguiente(tarea_id)
```

---

## 3. Regla Absoluta: Yeyo NUNCA Se Rinde

> **Si Yeyo no puede resolver algo, no dice "necesito modelo más grande". Busca más profundo, descompone en sub-problemas, tarda horas si es necesario.**

### Estrategia de descomposición

Problema complejo que no puede resolver directamente:

```
"Sistema de pagos con Stripe + webhooks + retry"
```

Yeyo **NO** busca "sistema de pagos completo" — eso no existe como pieza única copiable.

```
┌─────────────────────────────────────────────────────────────┐
│           DESCOMPOSICIÓN DE PROBLEMA COMPLEJO                │
│                                                              │
│  "Sistema de pagos con Stripe + webhooks + retry"            │
│                                                              │
│  ┌───────────────────────────────────────────────────┐       │
│  │              NO buscar esto                       │       │
│  │  "sistema de pagos completo stripe python"        │       │
│  │  → Demasiado amplio, resultados genéricos         │       │
│  └───────────────────────────────────────────────────┘       │
│                          │                                   │
│                          ▼                                   │
│  ┌───────────────────────────────────────────────────┐       │
│  │              SÍ buscar esto (5 sub-problemas)     │       │
│  │                                                   │       │
│  │  1. "stripe checkout session python"        ✅    │       │
│  │  2. "stripe webhook signature verification" ✅    │       │
│  │  3. "fastapi webhook endpoint"              ✅    │       │
│  │  4. "idempotency key stripe"                ✅    │       │
│  │  5. "retry failed webhook python"           ✅    │       │
│  │                                                   │       │
│  │  Cada pieza EXISTE en internet por separado       │       │
│  └───────────────────────────────────────────────────┘       │
│                          │                                   │
│                          ▼                                   │
│              ┌──────────────────────┐                        │
│              │ Ensamblar las piezas │                        │
│              │ Verificar que        │                        │
│              │ funcionen juntas     │                        │
│              └──────────────────────┘                        │
│                          │                                   │
│              ┌───────────┴───────────┐                       │
│              │                       │                       │
│         Primera vez             Próxima vez                  │
│         ⏱ Horas                ⏱ Segundos                   │
│         (investigación)        (ya en DB)                    │
└─────────────────────────────────────────────────────────────┘
```

### Límite de intentos por sub-problema

```python
MAX_PROFUNDIDAD = 5

async def resolver_sub_problema(problema: str, intento: int = 1) -> str:
    estrategias = {
        1: busqueda_general,          # "stripe checkout python"
        2: busqueda_con_error,        # agrega keywords del error específico
        3: busqueda_repos_github,     # repos reales con >100 estrellas
        4: busqueda_docs_oficiales,   # documentación oficial de la librería
        5: descomponer_mas,           # sub-sub-problemas aún más pequeños
    }

    resultado = await estrategias[intento](problema)

    if resultado.verificado:
        return resultado.codigo
    elif intento < MAX_PROFUNDIDAD:
        return await resolver_sub_problema(problema, intento + 1)
    else:
        # Intento 5 siempre descompone — la recursión continúa
        sub_problemas = await descomponer(problema)
        return await ensamblar([
            await resolver_sub_problema(sp) for sp in sub_problemas
        ])
```

No hay intento 6. **Siempre** hay algo que encontrar si descompones lo suficiente. Un problema irresoluble solo significa que no se ha descompuesto en piezas suficientemente pequeñas.

### Tracking de intentos

```sql
CREATE TABLE investigacion_intentos (
    id              SERIAL PRIMARY KEY,
    tarea_id        TEXT NOT NULL,
    sub_problema    TEXT NOT NULL,
    intento_numero  INTEGER NOT NULL,
    estrategia      TEXT NOT NULL,
    exito           BOOLEAN DEFAULT FALSE,
    error_detalle   TEXT,
    duracion_ms     INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 4. Cinco Niveles de Validación

> **El modelo NUNCA se juzga a sí mismo. Herramientas externas validan todo.**

Esta es la diferencia fundamental con otros sistemas de IA. Yeyo no confía en su propia evaluación. Cada nivel usa herramientas **deterministas** que dan respuestas binarias.

```
┌─────────────────────────────────────────────────────────────┐
│                 5 NIVELES DE VALIDACIÓN                      │
│                                                              │
│  Nivel 1 ─── Ejecución binaria ────────── ¿Corre? SÍ/NO   │
│      │                                                       │
│      ▼                                                       │
│  Nivel 2 ─── Tests independientes ──────── ¿Pasa? SÍ/NO    │
│      │                                                       │
│      ▼                                                       │
│  Nivel 3 ─── Herramientas deterministas ── ¿Limpio? SÍ/NO  │
│      │                                                       │
│      ▼                                                       │
│  Nivel 4 ─── Verificación vs fuente ────── ¿Fiel? SÍ/NO    │
│      │                                                       │
│      ▼                                                       │
│  Nivel 5 ─── Stress testing en Docker ──── ¿Aguanta? SÍ/NO │
│                                                              │
│  Score:                                                      │
│    Nivel 1-2 pasado ──── 0.60                                │
│    Nivel 1-3 pasado ──── 0.75                                │
│    Nivel 1-4 pasado ──── 0.90                                │
│    Nivel 1-5 pasado ──── 0.95+                               │
└─────────────────────────────────────────────────────────────┘
```

### Nivel 1: Ejecución binaria

La prueba más básica. ¿El código corre sin explotar?

```python
def validar_nivel_1(codigo: str, lenguaje: str) -> bool:
    comandos = {
        "python": ["python", "-c", f"exec({repr(codigo)})"],
        "javascript": ["node", "-e", codigo],
        "typescript": ["npx", "tsx", "-e", codigo],
    }
    resultado = subprocess.run(
        comandos[lenguaje],
        capture_output=True,
        timeout=30
    )
    return resultado.returncode == 0
```

La computadora dice **SÍ** o **NO**. Sin opinión. Sin matices.

### Nivel 2: Tests de fuentes independientes

El truco: el código viene de una fuente, los tests de **otra**.

```
Código:  GitHub repo A (implementación)
Tests:   GitHub repo B + docs oficiales (verificación)
```

Si el código pasa tests escritos por personas diferentes → la confianza sube. No es un modelo evaluándose a sí mismo.

```python
async def validar_nivel_2(codigo: str, tarea: str) -> bool:
    # Busca tests relevantes de fuentes independientes
    tests = await buscar_tests_independientes(tarea)
    if not tests:
        return True  # No hay tests disponibles, no falla por eso

    resultado = await ejecutar_tests(codigo, tests)
    return resultado.todos_pasaron
```

### Nivel 3: Herramientas deterministas

Reglas matemáticas escritas por expertos. El modelo no participa.

| Herramienta | Lenguaje  | Qué detecta                        |
|-------------|-----------|-------------------------------------|
| `bandit`    | Python    | Vulnerabilidades de seguridad       |
| `semgrep`   | Multi     | Patrones peligrosos configurables   |
| `mypy`      | Python    | Errores de tipos                    |
| `eslint`    | JS/TS     | Errores y malas prácticas           |
| `ruff`      | Python    | Linting rápido                      |
| `shellcheck`| Bash      | Errores en scripts shell            |

```python
HERRAMIENTAS_NIVEL_3 = {
    "python": ["bandit -r {path}", "mypy {path}", "ruff check {path}"],
    "javascript": ["eslint {path}"],
    "typescript": ["eslint {path}", "tsc --noEmit {path}"],
    "bash": ["shellcheck {path}"],
}

async def validar_nivel_3(codigo: str, lenguaje: str) -> dict:
    path = await escribir_temporal(codigo, lenguaje)
    resultados = {}

    for cmd_template in HERRAMIENTAS_NIVEL_3.get(lenguaje, []):
        cmd = cmd_template.format(path=path)
        resultado = await ejecutar(cmd)
        resultados[cmd] = resultado.returncode == 0

    return {
        "pasado": all(resultados.values()),
        "detalle": resultados
    }
```

### Nivel 4: Verificación contra fuente original

Compara lo que Yeyo produjo contra la documentación oficial.

```python
async def validar_nivel_4(codigo: str, tarea: str) -> float:
    docs_oficiales = await buscar_docs_oficiales(tarea)
    if not docs_oficiales:
        return 1.0  # Sin docs para comparar, no penaliza

    similitud = calcular_similitud_semantica(codigo, docs_oficiales)

    # 90%+ similar a docs oficiales → confiable
    return similitud >= 0.90
```

### Nivel 5: Stress testing en sandbox Docker

La prueba definitiva. Todo automático, todo medible.

```python
STRESS_TEST_CONFIG = {
    "requests_normales": 100,
    "requests_datos_malos": 50,
    "requests_simultaneos": 10,
    "sql_injection_tests": 20,
    "uptime_minutos": 5,
}

async def validar_nivel_5(codigo: str, config: dict) -> dict:
    # Levanta container Docker aislado
    container = await docker.run(
        image="yeyo-sandbox:latest",
        code=codigo,
        network="none",  # sin acceso a internet
        memory="512m",
        cpu="1.0"
    )

    resultados = {
        "normales": await enviar_requests(container, config["requests_normales"]),
        "malos": await enviar_requests_malos(container, config["requests_datos_malos"]),
        "concurrentes": await enviar_concurrentes(container, config["requests_simultaneos"]),
        "injection": await probar_injection(container, config["sql_injection_tests"]),
        "uptime": await verificar_uptime(container, config["uptime_minutos"]),
    }

    await container.stop()

    return {
        "pasado": all(r["ok"] for r in resultados.values()),
        "detalle": resultados
    }
```

### Score de confianza compuesto

```python
def calcular_confianza(niveles_pasados: list[int]) -> float:
    scores = {
        (1, 2):       0.60,
        (1, 2, 3):    0.75,
        (1, 2, 3, 4): 0.90,
        (1, 2, 3, 4, 5): 0.95,
    }
    return scores.get(tuple(sorted(niveles_pasados)), 0.0)
```

---

## 5. Razonamiento Extendido

Para problemas que requieren más que búsqueda directa, Yeyo implementa tres técnicas de razonamiento que compensan las limitaciones del modelo.

### Chain of Thought (CoT)

En lugar de respuesta directa, el modelo sigue pasos explícitos:

```
┌───────────────────────────────────────────────────┐
│              CHAIN OF THOUGHT                      │
│                                                    │
│  1. Analiza el problema                            │
│     │                                              │
│     ▼                                              │
│  2. Lista enfoques posibles                        │
│     │                                              │
│     ▼                                              │
│  3. Elige el mejor                                 │
│     │                                              │
│     ▼                                              │
│  4. Implementa                                     │
│     │                                              │
│     ▼                                              │
│  5. Revisa su propia implementación                │
│     │                                              │
│     ▼                                              │
│  6. Corrige y entrega                              │
│                                                    │
│  ⏱ 3-5 min  │  ✅ ~80% correcto                   │
└───────────────────────────────────────────────────┘
```

```python
COT_PROMPT = """
Resuelve paso a paso:

PASO 1 - ANÁLISIS: ¿Qué se pide exactamente?
PASO 2 - ENFOQUES: Lista 3 formas de resolverlo
PASO 3 - ELECCIÓN: ¿Cuál es mejor y por qué?
PASO 4 - IMPLEMENTACIÓN: Escribe el código
PASO 5 - REVISIÓN: Revisa tu código línea por línea
PASO 6 - CORRECCIÓN: Corrige errores encontrados

Problema: {problema}
"""
```

### Tree of Thought (ToT)

Explora múltiples caminos en paralelo en vez de apostar por uno solo:

```
┌───────────────────────────────────────────────────────────┐
│                  TREE OF THOUGHT                           │
│                                                            │
│                    Problema                                │
│                       │                                    │
│              ┌────────┼────────┐                           │
│              ▼        ▼        ▼                           │
│          Camino A  Camino B  Camino C                      │
│              │        │        │                           │
│              ▼        ▼        ▼                           │
│          Sol. A    Sol. B    Sol. C                         │
│              │        │        │                           │
│              └────────┼────────┘                           │
│                       ▼                                    │
│                  Evaluar las 3                              │
│                       │                                    │
│                       ▼                                    │
│                 Elegir mejor                                │
│                       │                                    │
│                       ▼                                    │
│                    Refinar                                  │
│                                                            │
│  ⏱ 10-30 min  │  ✅ ~90% correcto                         │
└───────────────────────────────────────────────────────────┘
```

```python
async def tree_of_thought(problema: str, ramas: int = 3) -> str:
    # Genera N soluciones independientes (cada una es una micro-tarea)
    soluciones = []
    for i in range(ramas):
        sol = await llm_call(
            prompt=f"Enfoque {i+1} de {ramas} para: {problema}\n"
                   f"Usa un enfoque DIFERENTE a los anteriores.",
            temperature=0.7
        )
        soluciones.append(sol)
        await db.guardar_paso(tipo="tot_rama", output=sol)

    # Evalúa cada una (otra micro-tarea)
    evaluaciones = []
    for sol in soluciones:
        ev = await llm_call(
            prompt=f"Evalúa pros y contras de esta solución:\n{sol[:500]}"
        )
        evaluaciones.append(ev)

    # Elige la mejor (otra micro-tarea)
    mejor = await llm_call(
        prompt=f"Dadas estas evaluaciones, ¿cuál es mejor?\n"
               f"{chr(10).join(evaluaciones)}"
    )

    return mejor
```

### Self-Consistency

Genera la misma respuesta múltiples veces y vota:

```
┌───────────────────────────────────────────────────────────┐
│                  SELF-CONSISTENCY                           │
│                                                            │
│  Misma pregunta × 5 (temperatura 0.8)                      │
│                                                            │
│  Run 1: "usa bcrypt"                                       │
│  Run 2: "usa bcrypt"                                       │
│  Run 3: "usa argon2"                                       │
│  Run 4: "usa bcrypt"                                       │
│  Run 5: "usa bcrypt"                                       │
│                                                            │
│  Voto: 4/5 → bcrypt ──── ✅ Alta confianza                │
│                                                            │
│  Si todas difieren → escala a búsqueda más profunda        │
│                                                            │
│  ⏱ 5× más lento  │  Resultado más confiable               │
└───────────────────────────────────────────────────────────┘
```

```python
async def self_consistency(problema: str, runs: int = 5) -> dict:
    respuestas = []
    for _ in range(runs):
        r = await llm_call(prompt=problema, temperature=0.8)
        respuestas.append(r)

    # Agrupa respuestas similares
    grupos = agrupar_por_similitud(respuestas, umbral=0.85)
    grupo_mayor = max(grupos, key=len)

    confianza = len(grupo_mayor) / runs

    if confianza < 0.6:
        # Sin consenso → escala a búsqueda profunda
        return {"resultado": None, "accion": "escalar_busqueda"}

    return {
        "resultado": grupo_mayor[0],
        "confianza": confianza,
        "consenso": f"{len(grupo_mayor)}/{runs}"
    }
```

### Dos modos para el usuario

| Modo       | Icono | Tiempo        | Precisión | Uso                          |
|------------|-------|---------------|-----------|------------------------------|
| **Rápido** | ⚡    | Segundos      | Variable  | Chat casual, preguntas simples|
| **Profundo** | 🧠  | Minutos/horas | Alta      | Código, arquitectura, crítico|

El usuario elige explícitamente, o Yeyo detecta automáticamente por la complejidad de la pregunta.

---

## 6. Caché de Patrones de Razonamiento

### Nivel 1: Caché de soluciones exactas

La forma más rápida. Si alguien ya resolvió exactamente esto, no hay que pensar.

```python
async def cache_nivel_1(consulta: str) -> Optional[str]:
    embedding = await generar_embedding(consulta)
    resultado = await pgvector.buscar(
        embedding=embedding,
        umbral_similitud=0.95  # Solo matches casi exactos
    )

    if resultado:
        # Adapta nombres/estructura al contexto actual
        return await adaptar_solucion(resultado.codigo, contexto_usuario)

    return None  # No hay hit, sigue al pipeline normal
```

### Nivel 2: Caché de caminos de razonamiento

No solo guarda **la solución** — guarda **el camino** que llevó a ella.

```json
{
  "tipo_problema": "autenticación JWT",
  "errores_comunes": [
    "olvidar expiración del token",
    "no sanitizar payload",
    "secret key hardcodeado",
    "no manejar token revocado"
  ],
  "patron_correcto": "jwt.encode + exp claim + refresh token + blacklist",
  "pasos_razonamiento": [
    "definir claims necesarios",
    "implementar firma con RS256",
    "agregar expiración",
    "implementar refresh flow",
    "manejo de errores y revocación"
  ],
  "tiempo_original": "45 min",
  "confianza": 0.94,
  "veces_usado": 12,
  "ultima_verificacion": "2026-03-15"
}
```

Próxima vez que alguien pida JWT: salta directo al patrón probado. **2 min en vez de 45**.

```sql
CREATE TABLE patrones_razonamiento (
    id              SERIAL PRIMARY KEY,
    tipo_problema   TEXT NOT NULL,
    embedding       vector(384),
    errores_comunes JSONB,
    patron_correcto TEXT,
    pasos           JSONB,
    tiempo_original INTEGER,        -- milisegundos
    confianza       FLOAT,
    veces_usado     INTEGER DEFAULT 0,
    ultima_verificacion TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_patrones_embedding
    ON patrones_razonamiento USING ivfflat (embedding vector_cosine_ops);
```

### Nivel 3: Anticipación proactiva

Con 2+ años de historia, Yeyo aprende patrones de **comportamiento** del usuario:

```
┌─────────────────────────────────────────────────────────────┐
│                ANTICIPACIÓN PROACTIVA                         │
│                                                              │
│  Historial detectado:                                        │
│    "Cuando Diego pide API REST,                              │
│     87% de las veces después pide auth"                      │
│                                                              │
│  ┌──────────┐         ┌──────────────┐                       │
│  │ Diego:   │         │   Yeyo:      │                       │
│  │ "hazme   │────────▶│  Genera API  │                       │
│  │  una API │         │      +       │                       │
│  │  REST"   │         │  Pre-computa │                       │
│  └──────────┘         │  auth (bg)   │                       │
│                       └──────┬───────┘                       │
│                              │                               │
│                              ▼                               │
│  ┌──────────┐         ┌──────────────┐                       │
│  │ Diego:   │         │   Yeyo:      │                       │
│  │ "ahora   │────────▶│  "Ya estaba  │                       │
│  │  auth"   │         │   lista 😎"  │                       │
│  └──────────┘         └──────────────┘                       │
│                                                              │
│  Tiempo ahorrado: minutos → instantáneo                      │
└─────────────────────────────────────────────────────────────┘
```

```python
async def anticipar_siguiente_tarea(tarea_actual: str, usuario: str):
    # Busca en historial: ¿qué pidió después de tareas similares?
    historial = await db.query("""
        SELECT t2.descripcion, COUNT(*) as frecuencia
        FROM tareas t1
        JOIN tareas t2 ON t2.created_at > t1.created_at
            AND t2.created_at < t1.created_at + INTERVAL '1 hour'
            AND t2.usuario = t1.usuario
        WHERE t1.descripcion_embedding <-> $1 < 0.3
          AND t1.usuario = $2
        GROUP BY t2.descripcion
        ORDER BY frecuencia DESC
        LIMIT 3
    """, embedding_de(tarea_actual), usuario)

    for prediccion in historial:
        if prediccion.frecuencia / total > 0.7:  # >70% de probabilidad
            # Pre-computa en background
            asyncio.create_task(
                investigar(prediccion.descripcion, generar_tarea_id())
            )
```

---

## 7. Schedule Nocturno Completo (6 Fases)

> **Mientras duermes, Yeyo trabaja. Cuando despiertas, es más inteligente que ayer.**

### Detección de idle

```python
IDLE_THRESHOLD_SECONDS = 600  # 10 min sin mouse/teclado

async def detectar_idle():
    while True:
        ultimo_input = await sistema.ultimo_evento_input()
        if (now() - ultimo_input).seconds > IDLE_THRESHOLD_SECONDS:
            if es_horario_nocturno():  # 22:00 - 06:00
                await iniciar_schedule_nocturno()
        await asyncio.sleep(60)
```

### Línea de tiempo

```
┌─────────────────────────────────────────────────────────────────┐
│                  SCHEDULE NOCTURNO                                │
│                                                                   │
│  22:00 ── Detecta idle (sin input 10 min)                        │
│     │                                                            │
│     ▼                                                            │
│  22:00-00:00 ── FASE 1: INVESTIGACIÓN                            │
│     │  → Toma tareas del día que tardaron más                    │
│     │  → Las investiga a fondo por internet                      │
│     │  → Pre-computa soluciones para mañana                      │
│     │                                                            │
│     ▼                                                            │
│  00:00-02:00 ── FASE 2: FINE-TUNING LOCAL (LoRA)                │
│     │  → Solo con soluciones verificadas del día                 │
│     │  → Dataset limpio (pasó YeyoLint + YeyoQuality)           │
│     │  → Gradiente bajo para no destruir conocimiento previo     │
│     │                                                            │
│     ▼                                                            │
│  02:00-03:00 ── FASE 3: YEYO-HACK                               │
│     │  → Red team vs blue team en Docker aislado                 │
│     │  → Busca vulnerabilidades en código del día                │
│     │  → Reporte listo para la mañana                            │
│     │                                                            │
│     ▼                                                            │
│  03:00-04:00 ── FASE 4: LIMPIEZA DE MEMORIA                     │
│     │  → Consolida duplicados en Flash Memory                    │
│     │  → Degrada memorias obsoletas                              │
│     │  → Resuelve contradicciones detectadas                     │
│     │                                                            │
│     ▼                                                            │
│  04:00-05:00 ── FASE 5: BENCHMARK POST-ENTRENAMIENTO            │
│     │  → Ejecuta suite completa de benchmarks                    │
│     │  → Si degradó: REVIERTE training automáticamente           │
│     │  → Si mejoró: CONFIRMA pesos nuevos                        │
│     │  → El usuario NUNCA encuentra un modelo peor               │
│     │                                                            │
│     ▼                                                            │
│  05:00-06:00 ── FASE 6: SYNC YEYONET                            │
│     │  → Envía aprendizajes al cerebro central                   │
│     │  → Recibe mejoras de otros nodos                           │
│     │  → Actualiza reglas de YeyoLint                            │
│     │                                                            │
│     ▼                                                            │
│  06:00 ── Listo. Yeyo es más inteligente que ayer.               │
└─────────────────────────────────────────────────────────────────┘
```

### Orquestador nocturno

```python
async def schedule_nocturno():
    log.info("🌙 Iniciando schedule nocturno")

    # Fase 1: Investigación (22:00-00:00)
    tareas_lentas = await db.query("""
        SELECT * FROM tareas
        WHERE fecha = CURRENT_DATE
          AND duracion_ms > 600000  -- más de 10 min
        ORDER BY duracion_ms DESC
        LIMIT 10
    """)
    for tarea in tareas_lentas:
        await investigar_profundo(tarea)
        if es_hora_de_parar("00:00"):
            break

    # Fase 2: Fine-tuning (00:00-02:00)
    dataset = await construir_dataset_limpio()
    if len(dataset) > 50:  # mínimo de ejemplos
        await fine_tune_lora(
            modelo="qwen2.5:3b",
            dataset=dataset,
            learning_rate=1e-5,  # conservador
            epochs=3
        )

    # Fase 3: YEYO-HACK (02:00-03:00)
    await ejecutar_yeyo_hack()

    # Fase 4: Limpieza de memoria (03:00-04:00)
    await limpiar_flash_memory()
    await resolver_contradicciones()

    # Fase 5: Benchmark (04:00-05:00)
    score_antes = await cargar_ultimo_benchmark()
    score_despues = await ejecutar_benchmark_completo()
    if score_despues < score_antes:
        log.warning("⚠️ Degradación detectada. Revirtiendo training.")
        await revertir_pesos()
    else:
        log.info(f"✅ Mejora: {score_antes:.2f} → {score_despues:.2f}")
        await confirmar_pesos()

    # Fase 6: Sync YeyoNet (05:00-06:00)
    await yeyonet.sync_aprendizajes()
    await yeyonet.recibir_mejoras()
    await yeyonet.actualizar_lint_rules()

    log.info("☀️ Schedule nocturno completado")
```

---

## 8. Aprendizaje Autodidacta (Extensión de Code Dojo)

### Diferencia con Code Dojo existente

| Aspecto          | Code Dojo (13-code-dojo.md)      | Autodidacta (nuevo)              |
|------------------|----------------------------------|----------------------------------|
| Ejercicios       | 1,800 fijos                      | Generados dinámicamente          |
| Curriculum       | Predefinido                      | Basado en debilidades reales     |
| Fuente           | Curado manualmente               | Detectado por benchmark + uso    |
| Límite           | Se termina                       | Crece indefinidamente            |

Code Dojo es el **piso**. Autodidacta es el **techo que no existe**.

### Generación de curriculum

```python
async def generar_curriculum_nocturno() -> list[dict]:
    ejercicios = []

    # Fuente 1: Benchmark — categorías con score bajo
    debilidades = await db.query("""
        SELECT categoria, score FROM benchmark_resultados
        WHERE score < 0.70
        ORDER BY score ASC
    """)
    for d in debilidades:
        ejercicios.extend(
            await generar_ejercicios(d.categoria, dificultad="progresiva", n=5)
        )

    # Fuente 2: Tareas del día que tardaron demasiado
    tareas_lentas = await db.query("""
        SELECT descripcion, duracion_ms FROM tareas
        WHERE fecha = CURRENT_DATE AND duracion_ms > 600000
    """)
    for t in tareas_lentas:
        ejercicios.append(
            await generar_ejercicio_similar(t.descripcion)
        )

    # Fuente 3: Tecnologías nunca tocadas
    tech_nueva = await detectar_tecnologias_no_vistas()
    for tech in tech_nueva[:3]:  # máximo 3 tecnologías nuevas por noche
        ejercicios.extend(
            await generar_ejercicios_intro(tech, n=3)
        )

    # Fuente 4: Tendencias tecnológicas (búsqueda semanal)
    if es_dia_de_semana("lunes"):
        tendencias = await buscar_tendencias_tech()
        for trend in tendencias[:5]:
            ejercicios.append(
                await generar_ejercicio_tendencia(trend)
            )

    return ejercicios
```

### Ciclo de práctica por ejercicio

```
┌─────────────────────────────────────────────────────────────┐
│              CICLO DE PRÁCTICA POR EJERCICIO                 │
│                                                              │
│  Intento 1: búsqueda general                                │
│     │                                                        │
│     ├── ✅ Pasa verificación → Guarda, siguiente             │
│     │                                                        │
│     └── ❌ Falla                                             │
│              │                                               │
│              ▼                                               │
│  Intento 2: búsqueda específica (keywords del error)         │
│     │                                                        │
│     ├── ✅ Pasa → Guarda                                     │
│     │                                                        │
│     └── ❌ Falla                                             │
│              │                                               │
│              ▼                                               │
│  Intento 3: repos reales de GitHub (>100 ⭐)                 │
│     │                                                        │
│     ├── ✅ Pasa → Guarda                                     │
│     │                                                        │
│     └── ❌ Falla                                             │
│              │                                               │
│              ▼                                               │
│  Intento 4: descompone en sub-problemas                      │
│     │                                                        │
│     └── Resuelve cada pieza por separado                     │
│         (aplica el mismo ciclo recursivamente)               │
│                                                              │
│  NUNCA se rinde — guarda en DB incluso si tardó horas        │
└─────────────────────────────────────────────────────────────┘
```

### Progresión acumulativa

```
┌──────────────────────────────────────────────────────────────┐
│              CURVA DE CONOCIMIENTO ACUMULADO                   │
│                                                               │
│  Ejercicios                                                   │
│  resueltos                                                    │
│     │                                                         │
│ 18K ┤                                              ●·······  │
│     │                                           ··/           │
│ 15K ┤                                        ··/              │
│     │                                     ··/                 │
│ 12K ┤                                  ··/                    │
│     │                               ··/                       │
│  9K ┤                            ··/                          │
│     │                         ··/                             │
│  7K ┤                      ●·/     ← Año 2: avanzado         │
│     │                   ··/                                   │
│  5K ┤                ··/                                      │
│     │             ··/                                         │
│ 3.6K┤          ●·/          ← Año 1: intermedio-avanzado     │
│     │       ··/                                               │
│ 1.8K┤    ●·/               ← Mes 6: intermedio               │
│     │  ·/                                                     │
│  300┤●/                    ← Mes 1: básico                    │
│     └────┬────┬────┬────┬────┬────────────────▶ Tiempo        │
│         M1   M6   Y1   Y2   Y3              Y5               │
└──────────────────────────────────────────────────────────────┘
```

| Período | Ejercicios | Nivel         | Equivalencia            |
|---------|------------|---------------|-------------------------|
| Mes 1   | 300        | Básico        | Junior consciente       |
| Mes 6   | 1,800      | Intermedio    | Mid-level               |
| Año 1   | 3,600      | Avanzado      | Senior en stack principal|
| Año 2   | 7,000+     | Casi todo     | Full-stack senior       |
| Año 5   | 18,000+    | Enciclopédico | ~15 años de experiencia |

---

## 9. Selección Automática de Modelo por Complejidad

No todo necesita el mismo modelo. Tareas simples usan el modelo local rápido. Tareas complejas escalan.

```
┌──────────────────────────────────────────────────────────────┐
│           SELECCIÓN AUTOMÁTICA DE MODELO                      │
│                                                               │
│  Complejidad     Modelo                   Dónde              │
│                                                               │
│  ┌─────────┐     ┌──────────────────┐     ┌──────────┐       │
│  │ < 0.3   │────▶│ qwen2.5:3b       │────▶│ Local    │       │
│  │ Simple  │     │ Rápido, local    │     │ GPU/CPU  │       │
│  └─────────┘     └──────────────────┘     └──────────┘       │
│                                                               │
│  ┌─────────┐     ┌──────────────────┐     ┌──────────┐       │
│  │ 0.3-0.7 │────▶│ qwen2.5-coder:7b │────▶│ Local    │       │
│  │ Medio   │     │ Código, si VRAM  │     │ GPU      │       │
│  └─────────┘     └──────────────────┘     └──────────┘       │
│                                                               │
│  ┌─────────┐     ┌──────────────────┐     ┌──────────┐       │
│  │ > 0.7   │────▶│ YeyoNet nodo     │────▶│ Red P2P  │       │
│  │ Alto    │     │ Mejor GPU disp.  │     │ Remoto   │       │
│  └─────────┘     └──────────────────┘     └──────────┘       │
│                                                               │
│  ┌─────────┐     ┌──────────────────┐     ┌──────────┐       │
│  │ Fallback│────▶│ API externa      │────▶│ Cloud    │       │
│  │         │     │ Claude Haiku     │     │          │       │
│  └─────────┘     └──────────────────┘     └──────────┘       │
└──────────────────────────────────────────────────────────────┘
```

### Estimación de complejidad

```python
def elegir_modelo(tarea: str, complejidad: float) -> str:
    if complejidad < 0.3:
        return "qwen2.5:3b"            # rápido, local
    elif complejidad < 0.7:
        return "qwen2.5-coder:7b"      # código, si hay VRAM
    elif yeyonet.hay_nodo_disponible():
        return yeyonet.mejor_nodo()     # delega a la red
    else:
        return "api_externa"            # Claude Haiku como fallback


def estimar_complejidad(tarea: str) -> float:
    factores = []

    # Factor 1: Longitud del prompt
    tokens = contar_tokens(tarea)
    factores.append(min(tokens / 500, 1.0))

    # Factor 2: Palabras clave técnicas
    keywords_complejas = [
        "distribuido", "concurrencia", "microservicios",
        "autenticación", "pipeline", "websocket", "streaming"
    ]
    matches = sum(1 for k in keywords_complejas if k in tarea.lower())
    factores.append(min(matches / 3, 1.0))

    # Factor 3: Historial — ¿cuánto tardó un problema similar antes?
    similares = buscar_tareas_similares(tarea, limit=5)
    if similares:
        duracion_promedio = mean([t.duracion_ms for t in similares])
        factores.append(min(duracion_promedio / 600000, 1.0))  # 10 min = 1.0

    # Factor 4: Número de sub-problemas estimados
    sub_problemas = estimar_sub_problemas(tarea)
    factores.append(min(sub_problemas / 5, 1.0))

    return mean(factores)
```

### Tabla de decisión rápida

| Tarea                              | Complejidad | Modelo               |
|------------------------------------|-------------|----------------------|
| "¿qué hora es?"                   | 0.05        | `qwen2.5:3b`         |
| "genera un CRUD de usuarios"      | 0.35        | `qwen2.5-coder:7b`   |
| "sistema de pagos con webhooks"   | 0.75        | YeyoNet nodo remoto  |
| "arquitectura de microservicios"  | 0.90        | YeyoNet / API externa|

---

## 10. Detección y Resolución Activa de Contradicciones

> **La memoria no solo crece — se limpia. Un dato contradictorio es peor que ningún dato.**

### Flujo de detección

Cuando llega un dato nuevo, Yeyo busca contradicciones automáticamente:

```
┌─────────────────────────────────────────────────────────────┐
│           DETECCIÓN DE CONTRADICCIONES                       │
│                                                              │
│  Dato nuevo llega                                            │
│     │                                                        │
│     ▼                                                        │
│  Busca memorias semánticamente similares en pgvector          │
│     │                                                        │
│     ├── No hay similares → Guarda normal                     │
│     │                                                        │
│     └── Hay similares → Compara afirmaciones                 │
│              │                                               │
│              ├── Coinciden → Refuerza (sube prioridad)        │
│              │                                               │
│              └── Contradicen → Resuelve                      │
│                       │                                      │
│              ┌────────┼────────┐                             │
│              ▼        ▼        ▼                             │
│          Nueva es  Ambas son  No se puede                    │
│          más       recientes  determinar                     │
│          reciente                                            │
│              │        │        │                             │
│              ▼        ▼        ▼                             │
│          Degrada   Marca     Pregunta                        │
│          vieja,    para      al usuario                      │
│          eleva     revisión  en dashboard                    │
│          nueva     del                                       │
│                    usuario                                   │
└─────────────────────────────────────────────────────────────┘
```

### Implementación

```python
async def verificar_contradiccion(dato_nuevo: str, embedding: list[float]):
    # Busca memorias similares (umbral bajo para capturar candidatos)
    similares = await pgvector.buscar(
        embedding=embedding,
        umbral_similitud=0.75,
        limit=10
    )

    for memoria in similares:
        relacion = await llm_call(
            prompt=f"¿Estas dos afirmaciones se contradicen?\n"
                   f"A: {memoria.contenido}\n"
                   f"B: {dato_nuevo}\n"
                   f"Responde: COINCIDEN, CONTRADICEN, o INDEPENDIENTES",
            max_tokens=20
        )

        if "CONTRADICEN" in relacion:
            await resolver_contradiccion(memoria, dato_nuevo)
        elif "COINCIDEN" in relacion:
            await reforzar_memoria(memoria)


async def resolver_contradiccion(vieja: Memoria, nueva_contenido: str):
    dias_diferencia = (now() - vieja.created_at).days

    if dias_diferencia > 30:
        # La nueva es significativamente más reciente → degrada vieja
        await db.execute("""
            UPDATE flash_memory
            SET prioridad = prioridad * 0.5,
                notas = notas || ' [CONTRADICHO por memoria más reciente]'
            WHERE id = $1
        """, vieja.id)
        log.info(f"Degradada memoria {vieja.id} por contradicción")
    else:
        # Ambas recientes → marca para revisión humana
        await db.execute("""
            INSERT INTO contradicciones_pendientes
                (memoria_vieja_id, contenido_nuevo, detectado_at)
            VALUES ($1, $2, NOW())
        """, vieja.id, nueva_contenido)
        log.info("Contradicción marcada para revisión del usuario")
```

### Dashboard de contradicciones

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️  CONTRADICCIONES DETECTADAS (3 pendientes)               │
│                                                              │
│  1. "bcrypt es suficiente para passwords"                    │
│     vs "argon2 es el estándar recomendado en 2026"           │
│     [Opción A] [Opción B] [Ambas en distintos contextos]     │
│                                                              │
│  2. "usar REST para todo"                                    │
│     vs "usar GraphQL para queries complejas"                 │
│     [Opción A] [Opción B] [Ambas en distintos contextos]     │
│                                                              │
│  3. "Python 3.11 es la versión estable"                      │
│     vs "Python 3.13 es la versión estable actual"            │
│     [Opción A] [Opción B] [Ambas en distintos contextos]     │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Curva de Aceleración Documentada

### Proyección temporal

| Período | Tarea nueva | Tarea repetida | Caché    |
|---------|-------------|----------------|----------|
| Mes 1   | 15 min      | 15 min         | Sin caché|
| Mes 6   | 8 min       | 2 min          | Parcial  |
| Año 2   | 5 min       | 10-30 seg      | Rico     |
| Año 5   | 3 min       | Instantáneo    | Maduro   |

En **año 5**, el 95% de las tareas cotidianas ya tienen solución en caché. Solo lo genuinamente nuevo tarda.

### Factores de aceleración

```
┌──────────────────────────────────────────────────────────────┐
│              FACTORES DE ACELERACIÓN                          │
│                                                               │
│  Factor                           Mejora        Cuándo       │
│  ─────────────────────────────────────────────────────────── │
│  Fine-tuning con tu código        +20-30%       Mes 1+       │
│  Caché de patrones                +500%         Mes 3+       │
│  Red de nodos (mejores GPUs)      +200-400%     Año 1+       │
│  Federated Learning colectivo     +30-50%       Año 2+       │
│  Anticipación proactiva           +∞ (pre-hecho) Año 2+      │
│                                                               │
│  Efecto combinado:                                            │
│                                                               │
│  Velocidad                                                    │
│     │                                                         │
│     │                                           ●·········   │
│     │                                        ··/              │
│     │                                     ··/                 │
│     │                                  ··/                    │
│     │                              ···/                       │
│     │                          ···/                           │
│     │                     ····/                               │
│     │                ····/                                    │
│     │          ·····/                                         │
│     │     ····/                                               │
│     │ ···/                                                    │
│     │·/                                                       │
│     └────────────────────────────────────────────▶ Tiempo     │
│     M1       M6       Y1       Y2       Y3     Y5            │
│                                                               │
│  La curva es exponencial al principio, logarítmica después.   │
│  El caché crece linealmente, la velocidad crece              │
│  exponencialmente hasta estabilizarse.                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 12. Distribución Multiplataforma (Shell de IA)

> **YeyoOS no es un OS — es un Shell de IA fullscreen que corre sobre cualquier sistema operativo.**

### Modelo de distribución

```
┌─────────────────────────────────────────────────────────────┐
│              DISTRIBUCIÓN MULTIPLATAFORMA                     │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Windows  │  │  macOS   │  │  Linux   │  │ISO (opt) │    │
│  │          │  │          │  │          │  │          │    │
│  │ .exe     │  │ .dmg     │  │.AppImage │  │ Bootable │    │
│  │ installer│  │    o     │  │  Snap    │  │ Dedicado │    │
│  │    o     │  │ brew     │  │    o     │  │          │    │
│  │PowerShell│  │ install  │  │ bash     │  │          │    │
│  │ script   │  │          │  │ script   │  │          │    │
│  └─────┬────┘  └────┬─────┘  └─────┬────┘  └─────┬────┘    │
│        │            │              │              │         │
│        └────────────┼──────────────┘              │         │
│                     ▼                             ▼         │
│              ┌──────────────┐           ┌──────────────┐    │
│              │  YeyoOS      │           │  YeyoOS      │    │
│              │  Shell de IA │           │  máquina     │    │
│              │  (sobre OS)  │           │  completa    │    │
│              └──────────────┘           └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Requisitos del usuario

| Requisito       | Versión mínima | Notas                          |
|-----------------|----------------|--------------------------------|
| Python          | 3.11+          | Runtime principal              |
| Ollama          | Última         | Modelos locales                |
| Docker Desktop  | Última         | Sandboxing y aislamiento       |
| Node.js         | 18+            | Frontend (Next.js)             |
| RAM             | 8 GB           | Mínimo funcional               |
| GPU             | Opcional       | Mejora experiencia (~3× speed) |

### Script de instalación (ejemplo Windows)

```powershell
# install-yeyo.ps1
Write-Host "🚀 Instalando YeyoOS..." -ForegroundColor Cyan

# Verificar dependencias
$deps = @{
    "python" = "python --version"
    "ollama" = "ollama --version"
    "docker" = "docker --version"
    "node"   = "node --version"
}

foreach ($dep in $deps.GetEnumerator()) {
    try {
        Invoke-Expression $dep.Value | Out-Null
        Write-Host "  ✅ $($dep.Key) encontrado" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $($dep.Key) no encontrado" -ForegroundColor Red
        Write-Host "     Instala $($dep.Key) primero." -ForegroundColor Yellow
        exit 1
    }
}

# Descargar e instalar
git clone https://github.com/eltitoyeyo/yeyo-os.git
Set-Location yeyo-os
pip install -r requirements.txt
npm install
ollama pull qwen2.5:3b

Write-Host "✅ YeyoOS instalado. Ejecuta 'yeyo start' para comenzar." -ForegroundColor Green
```

---

## 13. YeyoPublisher — Deploy Multiplataforma

> **Un comando, todas las plataformas.**

```
"Yeyo, sube mi app a todas las tiendas"
```

### Plataformas soportadas

```
┌─────────────────────────────────────────────────────────────┐
│                  YEYOPUBLISHER                               │
│                                                              │
│  ┌──────────┐                                                │
│  │ Tu app   │                                                │
│  │ (código) │                                                │
│  └─────┬────┘                                                │
│        │                                                     │
│        ▼                                                     │
│  ┌──────────────────────────────────┐                        │
│  │      YeyoPublisher Pipeline      │                        │
│  │  build → package → sign → upload │                        │
│  └──────┬──────┬──────┬──────┬──────┘                        │
│         │      │      │      │                               │
│         ▼      ▼      ▼      ▼                               │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
│  │ Web  │ │ APK  │ │ IPA  │ │ .exe │ │ .dmg │ │Linux │     │
│  │      │ │ AAB  │ │      │ │      │ │      │ │      │     │
│  ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤ ├──────┤     │
│  │Vercel│ │Google│ │Apple │ │Win   │ │Mac   │ │.App  │     │
│  │Netlif│ │Play  │ │Store │ │Store │ │Store │ │Image │     │
│  │VPS   │ │      │ │      │ │      │ │      │ │Snap  │     │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     │
│                                                              │
│  Requisitos externos:                                        │
│  • Google Play: $25 cuenta dev (una vez)                     │
│  • App Store: $99/año + Mac requerido                        │
│  • Apple notarización: certificado de desarrollador          │
└─────────────────────────────────────────────────────────────┘
```

### Pipeline automatizado

```python
class YeyoPublisher:
    async def publicar_todo(self, app_path: str, config: dict):
        resultados = {}

        # Web
        if "web" in config["plataformas"]:
            resultados["web"] = await self.deploy_web(
                app_path,
                provider=config.get("web_provider", "vercel")
            )

        # Android
        if "android" in config["plataformas"]:
            apk = await self.build_android(app_path)
            signed = await self.sign_android(apk, config["android_keystore"])
            resultados["android"] = await self.upload_play_store(signed)

        # iOS (requiere Mac)
        if "ios" in config["plataformas"]:
            if not self.es_mac():
                resultados["ios"] = {"error": "Requiere Mac para build iOS"}
            else:
                ipa = await self.build_ios(app_path)
                resultados["ios"] = await self.upload_app_store(ipa)

        # Windows
        if "windows" in config["plataformas"]:
            exe = await self.build_electron(app_path, target="win")
            resultados["windows"] = await self.sign_windows(exe)

        # macOS
        if "macos" in config["plataformas"]:
            dmg = await self.build_electron(app_path, target="mac")
            notarized = await self.notarize_apple(dmg)
            resultados["macos"] = notarized

        # Linux
        if "linux" in config["plataformas"]:
            resultados["linux"] = {
                "appimage": await self.build_appimage(app_path),
                "snap": await self.build_snap(app_path),
            }

        return resultados
```

---

## Dependencias entre Conceptos

```
┌─────────────────────────────────────────────────────────────────┐
│              MAPA DE DEPENDENCIAS                                │
│                                                                  │
│  Pipeline Investigador (§1)                                      │
│     │                                                            │
│     ├── REQUIERE → Micro-tareas con DB (§2)                     │
│     ├── REQUIERE → 5 niveles de validación (§4)                 │
│     └── REQUIERE → Caché de patrones (§6)                       │
│                                                                  │
│  Schedule Nocturno (§7)                                          │
│     │                                                            │
│     ├── ORQUESTA → Investigación pre-computada (§1)             │
│     ├── ORQUESTA → Fine-tuning (existente: Code Dojo)           │
│     ├── ORQUESTA → YEYO-HACK (existente: 06-seguridad.md §6.12)│
│     ├── ORQUESTA → Limpieza de memoria (§10)                    │
│     ├── ORQUESTA → Benchmark (existente: §6.15)                 │
│     └── ORQUESTA → Sync YeyoNet (existente: 16-yeyonet.md)     │
│                                                                  │
│  Autodidacta (§8)                                                │
│     │                                                            │
│     ├── EXTIENDE → Code Dojo (13-code-dojo.md)                  │
│     ├── USA     → Pipeline Investigador (§1)                    │
│     └── USA     → Benchmark para detectar debilidades (§6.15)   │
│                                                                  │
│  Selección de Modelo (§9)                                        │
│     │                                                            │
│     ├── REQUIERE → GPU Scheduler (existente: Capa 1.8)          │
│     └── REQUIERE → YeyoNet para delegar (16-yeyonet.md)         │
│                                                                  │
│  Razonamiento Extendido (§5)                                     │
│     │                                                            │
│     ├── USA     → Micro-tareas con DB (§2)                      │
│     └── ALIMENTA → Caché de patrones (§6)                       │
│                                                                  │
│  Contradicciones (§10)                                           │
│     │                                                            │
│     ├── USA     → Flash Memory (05-memoria.md)                  │
│     └── USA     → pgvector (09-stack-tecnologico.md)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Resumen Ejecutivo

Este documento define el **cambio fundamental** en cómo Yeyo opera: de un generador que inventa respuestas a un investigador que busca, verifica y ensambla soluciones probadas.

| Concepto               | Impacto                                              |
|------------------------|------------------------------------------------------|
| Pipeline Investigador  | Soluciones verificadas en vez de alucinadas           |
| Micro-tareas + DB      | Sin límite de contexto, investigaciones de horas      |
| Nunca rendirse         | Todo problema se descompone hasta resolverse          |
| 5 niveles validación   | Confianza medible, no opinión del modelo              |
| Razonamiento extendido | CoT/ToT/Self-Consistency compensan modelo pequeño     |
| Caché de patrones      | Acelera exponencialmente con el uso                   |
| Schedule nocturno      | Mejora continua sin intervención del usuario          |
| Autodidacta            | Curriculum infinito basado en debilidades reales      |
| Selección de modelo    | Recurso correcto para cada tarea                      |
| Contradicciones        | Memoria limpia y consistente                          |
| Distribución           | Corre en cualquier sistema operativo                  |
| YeyoPublisher          | Deploy a todas las plataformas con un comando         |

> **El modelo de 3B no necesita ser genio. Necesita ser el mejor investigador del mundo. Y eso es entrenable.**
