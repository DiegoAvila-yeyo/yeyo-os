# 09 — Stack Tecnológico

## Resumen

El stack de YeyoOS ya no se organiza alrededor de un "OS con IA encima", sino alrededor de un **kernel de agentes local-first** con memoria, verificación, aprendizaje y cómputo distribuido.

---

## Stack por capa

| Capa | Tecnología | Rol |
|---|---|---|
| UI | Next.js + TypeScript + React | Hub, chats, layouts de nodos, visualización |
| API | FastAPI + WebSocket | Entrada/salida, routing, streaming |
| Kernel de agentes | Python puro (`src/orquestador/`) | Grafos, nodos, edges, checkpoints, eventos |
| Modelos locales | Ollama | Chat, embeddings, tool calling, serving local |
| Memoria | PostgreSQL + pgvector + Redis | Flash Memory HOT/WARM/COLD |
| Investigador | Python + tools propias | Buscar, evaluar, ensamblar, verificar |
| Runtime seguro | Bash/sandbox + permisos | Ejecución real de herramientas y código |
| Calidad | pytest + Jest + Playwright + linters | Verificación, benchmarks, no-slop |
| Aprendizaje | PyTorch + Transformers | YeyoDojo, YeyoHack, LoRA, evaluación |
| Distribución | WebSocket/colas/DB | YeyoNet central-satélite |
| Paquetes | `.ypkg` + manifests | Nodos instalables y exportables |

---

## Stack actual del repo

### Backend / core

- `src/core/config.py`
- `src/core/interfaces.py`
- `src/api/`
- `src/chat/`
- `src/security/`

### Orquestación

- `src/orquestador/`

### Memoria

- `src/memory/flash_memory.py`
- `src/memory/tier_manager.py`
- `src/memory/cache.py`

### IA local

- `src/ia/ollama_provider.py`
- `src/ia/interfaces.py`
- `src/ia/embeddings.py`

### Investigación y calidad

- `src/investigador/`
- `src/quality/`

### Nodos y paquetes

- `src/nodes/`
- `src/pkg/`

---

## Tecnologías núcleo

## 1. Orquestación

**Tecnología:** Python puro con grafos propios.

**Por qué:** control total del runtime, integración nativa con Flash Memory, WebSocket events, checkpointing y exportación futura a `.ypkg`.

**Estado actual:** ya existe en `src/orquestador/`.

**Repos externos que inspiran, no gobiernan:**

- `agiresearch/AIOS`
- `microsoft/JARVIS`
- `langchain-ai/langchain`

## 2. Modelos e inferencia

**Tecnología principal:** Ollama.

**Uso:**

- chat;
- embeddings;
- modelos pequeños locales;
- futuro tool calling estable.

**Estado actual:** `src/ia/ollama_provider.py`.

## 3. Memoria

**Tecnología principal:** PostgreSQL + pgvector + Redis.

**Modelo de memoria:**

- HOT → Redis / caché de acceso inmediato
- WARM/COLD → PostgreSQL + pgvector

**Inspiración complementaria:** `mem0ai/mem0`.

**Estado actual:** ya existe base funcional.

## 4. Investigación y verificación

**Tecnología principal:** pipeline propio en Python + herramientas externas reales.

**Verificación esperada:**

- ejecución real;
- tests;
- lint;
- scoring de calidad;
- coherencia con memoria.

**Estado actual:** parcial en `src/investigador/`.

## 5. Entrenamiento y auto-mejora

**Tecnologías:** PyTorch + Hugging Face Transformers.

**Uso:**

- evaluación offline;
- adapters / LoRA;
- datasets curados;
- entrenamiento de `YeyoDojo` y `YeyoHack`.

**Estado actual:** documentado, no central en runtime diario.

## 6. Distribución

**Tecnologías base previstas:**

- WebSocket para coordinación;
- PostgreSQL/Redis para estado y colas;
- jobs remotos controlados;
- autenticación de satélites.

**Uso:** `YeyoNet`.

**Estado actual:** conceptual en docs.

---

## Dependencias lógicas por área

## Runtime de producto

```text
FastAPI
Redis
PostgreSQL + pgvector
httpx
pydantic
Ollama REST API
```

## Calidad y verificación

```text
pytest
Jest
Playwright
herramientas del ecosistema del lenguaje
```

## Entrenamiento y evaluación

```text
torch
transformers
datasets (cuando aplique)
evaluación propia / benchmarks
```

## Multimedia

```text
FFmpeg
moviepy
Whisper
LLaVA
Stable Diffusion
```

---

## Modelos base recomendados

### Chat / razonamiento local

- `qwen2.5:0.5b` o equivalente para tareas ultraligeras
- `qwen2.5-coder` o equivalente para código
- modelos mayores solo cuando el hardware o `YeyoNet` lo permitan

### Embeddings

- `nomic-embed-text` en Ollama o equivalente compatible

### Visión / audio

- `llava`
- `whisper`

---

## Qué se elimina del stack anterior

Estas decisiones quedan obsoletas como centro del sistema:

- `OpenClaw` como orquestador principal;
- memoria de "5 capas" como arquitectura objetivo;
- prioridad temprana de ISO, kiosk mode y Linux base;
- dependencia conceptual en un framework externo para pensar.

No significa que una integración externa sea imposible. Significa que ya no define el stack.

---

## Stack final esperado

```text
Frontend/UI
  -> Next.js

Entrada y streaming
  -> FastAPI + WebSocket

Kernel
  -> YeyoOrquestador

Memoria
  -> Flash Memory (PostgreSQL + pgvector + Redis)

Inferencia
  -> Ollama

Investigación y quality
  -> Investigador + Quality Kernel

Aprendizaje
  -> YeyoDojo + YeyoHack

Distribución
  -> YeyoNet

Extensibilidad
  -> Nodos + .ypkg
```

---

## Regla práctica

Si una tecnología no mejora alguna de estas seis áreas, no es prioritaria:

1. agentes;
2. memoria;
3. investigación/verificación;
4. aprendizaje;
5. distribución;
6. nodos instalables.
