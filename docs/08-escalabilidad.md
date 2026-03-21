# 08 — Escalabilidad

## Principio

> **El código no cambia. Solo la infraestructura.**

YeyoOS está diseñado para escalar desde una PC personal hasta un datacenter, sin reescribir código. La clave es Docker: los mismos contenedores que corren en tu PC pueden correr en un servidor o en un cluster.

## Fases de Escalabilidad

### Fase 1 — Ahora (GTX 1060 3GB + 16GB RAM)

```
Una sola PC, todo en docker-compose:

┌─── Tu PC ──────────────────────────┐
│                                    │
│  docker-compose up                 │
│  ├── ollama (modelos pequeños)     │
│  ├── postgresql + pgvector         │
│  ├── redis                         │
│  ├── openclaw                      │
│  ├── celery-worker (1 worker)      │
│  ├── fastapi                       │
│  └── nextjs                        │
│                                    │
│  GPU: Modelos ≤3B en GPU           │
│  RAM: Modelos ≤7B en CPU+RAM       │
│  Velocidad: ~10-20 seg/respuesta   │
└────────────────────────────────────┘
```

**Modelos que funcionan:**
- Phi-3 Mini (3.8B) → GPU
- Gemma 2B → GPU
- Llama 3.1 7B → CPU+RAM (lento pero funcional)
- TinyLlama 1.1B → GPU (rápido, básico)
- nomic-embed-text → GPU (embeddings)

**Limitaciones:**
- Un modelo a la vez en GPU
- Generación de imágenes lenta (SD en CPU)
- No puede correr múltiples agentes en paralelo real

---

### Fase 2 — Upgrade PC (RTX 4090 + 64GB RAM)

```
Misma PC, mismo docker-compose, todo más rápido:

┌─── Tu PC Upgradeada ──────────────┐
│                                    │
│  docker-compose up  (sin cambios)  │
│  ├── ollama (modelos grandes)      │
│  ├── postgresql + pgvector         │
│  ├── redis                         │
│  ├── openclaw                      │
│  ├── celery-worker (4 workers)     │
│  ├── fastapi                       │
│  └── nextjs                        │
│                                    │
│  GPU: 24GB VRAM → Modelos de 70B+  │
│  RAM: 64GB → Múltiples modelos     │
│  Velocidad: ~1-3 seg/respuesta     │
└────────────────────────────────────┘
```

**Lo que cambia:**
- Modelos grandes (Llama 70B, Mixtral) → Respuestas de calidad GPT-4
- Stable Diffusion XL → Imágenes HD en segundos
- Múltiples agentes en paralelo real
- Generación de video más rápida

**Lo que NO cambia:**
- Código
- Estructura de carpetas
- docker-compose.yml (solo se ajusta RAM/GPU limits)
- Interfaz de usuario

---

### Fase 3 — Multi-GPU (2x RTX 4090 o similar)

```
┌─── Tu PC Multi-GPU ───────────────┐
│                                    │
│  GPU 0: Ollama (modelos de texto)  │
│  GPU 1: Stable Diffusion (imágenes)│
│                                    │
│  O alternativa:                    │
│  GPU 0+1: Un modelo enorme split  │
│           (Llama 405B)             │
│                                    │
│  Código: Sin cambios               │
│  Config: Solo variable de entorno  │
│    OLLAMA_GPU_DEVICES=0,1          │
└────────────────────────────────────┘
```

**Ollama distribuye entre GPUs automáticamente.** Solo necesitas decirle cuántas GPUs tiene.

---

### Fase 4 — Servidor(es) / Cloud

```
docker-compose → Kubernetes (o Docker Swarm)

┌──────────┐   ┌──────────┐   ┌──────────┐
│ Server 1 │   │ Server 2 │   │ Server 3 │
│ Ollama   │   │ FastAPI  │   │ Workers  │
│ GPU x4   │   │ Next.js  │   │ Celery   │
│          │   │ Redis    │   │ FFmpeg   │
└──────────┘   └──────────┘   └──────────┘
      │              │              │
      └──────── Red interna ───────┘
                     │
              ┌──────▼──────┐
              │  PostgreSQL  │
              │  (managed)   │
              └─────────────┘
```

**Cambios necesarios:**
- `docker-compose.yml` → `kubernetes.yml` (migración de configuración, no de código)
- Variables de entorno apuntan a IPs de servidores en vez de `localhost`
- Load balancer al frente para múltiples usuarios

**Lo que NO cambia:**
- Todo el código de Python (FastAPI, agentes, lógica)
- Todo el código de Next.js (interfaz)
- Las interfaces/contratos
- La lógica de negocio

---

### Fase 5 — YeyoOS como Servicio (Futuro lejano)

```
┌─── YeyoOS Cloud ────────────────────────────┐
│                                              │
│  Usuario A ──→ ┌────────┐                    │
│  Usuario B ──→ │  Load  │ ──→ Cluster K8s    │
│  Usuario C ──→ │Balancer│     ├── N servers   │
│  ...       ──→ └────────┘     ├── N GPUs      │
│                               └── Auto-scale  │
│                                              │
│  Cada usuario tiene:                          │
│  ├── Su propia memoria (5 capas aisladas)    │
│  ├── Sus propios nodos y configuraciones     │
│  ├── Su propio espacio de archivos           │
│  └── Aislamiento total de otros usuarios     │
│                                              │
└──────────────────────────────────────────────┘
```

## Por Qué Docker es la Clave

```
Desarrollo (tu Mac):
  docker-compose up → Funciona

Producción (PC con GPU):
  docker-compose up → Funciona igual

Servidor:
  kubernetes apply → Los mismos contenedores

Cloud:
  kubernetes scale → Los mismos contenedores × N
```

**Un solo `docker-compose.yml` define todo el sistema:**
```yaml
services:
  ollama:
    image: ollama/ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  postgres:
    image: pgvector/pgvector:pg16

  redis:
    image: redis:7

  backend:
    build: ./backend
    depends_on: [postgres, redis, ollama]

  frontend:
    build: ./frontend
    depends_on: [backend]

  celery:
    build: ./backend
    command: celery -A core worker
    depends_on: [redis, postgres]
```

## Métricas de Rendimiento Esperadas

| Tarea | Fase 1 (1060) | Fase 2 (4090) | Fase 4 (Servidor) |
|-------|---------------|---------------|-------------------|
| Chat (7B) | ~15 seg | ~2 seg | <1 seg |
| Chat (70B) | No viable | ~5 seg | ~2 seg |
| Imagen 512x512 | ~60 seg | ~5 seg | ~2 seg |
| Imagen 1024x1024 | No viable | ~10 seg | ~3 seg |
| Embeddings | ~2 seg | ~0.3 seg | ~0.1 seg |
| Video (10 seg clip) | ~5 min | ~30 seg | ~10 seg |
