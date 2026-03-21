# 02 — Arquitectura del Sistema

## Diagrama General

```
                    ┌─────────────┐
                    │  TÚ (Human) │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    YEYO     │  ← Interfaz visual (Next.js)
                    │  (Frontend) │     La cara del sistema
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │  ← Puente universal (Router)
                    │  (Backend)  │     Traduce UI ↔ Servicios
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
   ┌─────▼─────┐   ┌──────▼──────┐   ┌─────▼─────┐
   │ Interfaz  │   │  Interfaz   │   │ Interfaz  │
   │    IA     │   │ Orquestador │   │  Memoria  │
   └─────┬─────┘   └──────┬──────┘   └─────┬─────┘
         │                │                 │
    ┌────┴────┐     ┌─────┴─────┐     ┌────┴────┐
    │ Ollama  │     │ OpenClaw  │     │PostgreSQL│
    │  (hoy)  │     │   (hoy)   │     │  (hoy)  │
    └─────────┘     └───────────┘     └─────────┘
```

## Principio de Intercambiabilidad

El sistema NUNCA habla directamente con Ollama, OpenClaw o cualquier servicio externo. Todo pasa por **interfaces genéricas** (contratos). Esto permite cambiar cualquier pieza sin reescribir el sistema.

### Interfaces Principales

```python
# Interfaz de IA — Nunca cambia
class IAProvider:
    def chat(self, mensaje, contexto): ...
    def generar_imagen(self, prompt): ...
    def embeddings(self, texto): ...

# Implementación actual
class OllamaProvider(IAProvider): ...

# Implementaciones futuras posibles
class GPT5Provider(IAProvider): ...
class ClaudeProvider(IAProvider): ...
class GroqProvider(IAProvider): ...
```

```python
# Interfaz de Orquestador — Nunca cambia
class Orquestador:
    def ejecutar(self, tarea, contexto): ...
    def listar_skills(self): ...

# Implementación actual
class OpenClawOrquestador(Orquestador): ...

# Implementaciones futuras posibles
class LangChainOrquestador(Orquestador): ...
class CrewAIOrquestador(Orquestador): ...
class MiPropioOrquestador(Orquestador): ...
```

```python
# Interfaz de Memoria — Nunca cambia
class MemoriaProvider:
    def guardar(self, dato, metadata): ...
    def buscar(self, query, tipo): ...
    def buscar_semantico(self, texto): ...

# Implementación actual
class PostgresMemoria(MemoriaProvider): ...

# Implementaciones futuras posibles
class MongoMemoria(MemoriaProvider): ...
class SupabaseMemoria(MemoriaProvider): ...
```

### Cambiar una pieza = Cambiar 1 archivo

```python
# config.py — El ÚNICO lugar donde se elige qué implementación usar
IA_PROVIDER = "ollama"        # Cambiar a "gpt5", "claude", etc.
ORQUESTADOR = "openclaw"      # Cambiar a "langchain", "propio", etc.
MEMORIA = "postgresql"        # Cambiar a "mongodb", "supabase", etc.
```

## Capas del Sistema

### Capa 1: Hardware
```
PC Local:
  ├── GPU NVIDIA (GTX 1060 3GB → Upgrade futuro)
  ├── CPU
  ├── RAM 16GB (→ Upgrade futuro)
  └── Disco (SSD recomendado)
```

### Capa 2: Sistema Operativo Base
```
Linux Minimal:
  ├── Kernel Linux optimizado (sin bloatware)
  ├── Drivers NVIDIA propietarios (CUDA)
  ├── Systemd (init system)
  ├── Docker + Docker Compose
  └── Sin escritorio (ni GNOME, ni KDE)
```

### Capa 3: Servicios (Docker Compose)
```
docker-compose.yml:
  ├── ollama (servidor de modelos IA)
  ├── postgresql (base de datos + pgvector)
  ├── redis (cache, sesiones, colas)
  ├── openclaw (orquestador IA)
  ├── celery-worker (tareas en background)
  ├── fastapi (backend/router)
  └── nextjs (frontend/interfaz)
```

### Capa 4: Aplicación (YeyoOS)
```
Backend (FastAPI):
  ├── Router de nodos
  ├── Interfaces genéricas (IA, Orquestador, Memoria)
  ├── Implementaciones actuales
  ├── Sistema de seguridad (Sandbox)
  └── API REST para el frontend

Frontend (Next.js + PixiJS):
  ├── Hub de nodos flotantes (pantalla principal)
  ├── Componentes compartidos (Chat, Pizarrón, Timeline)
  └── Vistas de cada nodo
```

## Estructura de Carpetas

```
yeyo-os/
│
├── backend/                    # UN solo FastAPI
│   ├── core/                   # Auth, config, gestión de nodos
│   │   ├── config.py           # Qué implementación usar (Ollama, OpenClaw, etc.)
│   │   ├── security.py         # Sandbox, zonas, permisos
│   │   └── interfaces/         # Contratos genéricos
│   │       ├── ia_provider.py
│   │       ├── orquestador.py
│   │       └── memoria.py
│   ├── providers/              # Implementaciones intercambiables
│   │   ├── ollama_provider.py
│   │   ├── openclaw_orquestador.py
│   │   └── postgres_memoria.py
│   ├── nodes/                  # Lógica de cada nodo
│   │   ├── imagen/
│   │   ├── video/
│   │   ├── automatizacion/
│   │   ├── codigo/
│   │   └── archivos/
│   ├── services/               # Servicios compartidos
│   │   ├── ollama.py
│   │   ├── storage.py
│   │   └── ffmpeg.py
│   └── main.py
│
├── frontend/                   # UN solo Next.js
│   ├── components/
│   │   ├── core/               # Hub de nodos, layout principal
│   │   ├── shared/             # Chat, Pizarrón, Timeline (reutilizables)
│   │   └── nodes/
│   │       ├── imagen/
│   │       ├── video/
│   │       ├── automatizacion/
│   │       └── codigo/
│   └── pages/
│       ├── index.tsx           # Pantalla de nodos flotantes (PixiJS)
│       └── node/
│           ├── imagen.tsx
│           ├── video.tsx
│           └── ...
│
├── system/                     # Configuración del OS Linux
│   ├── scripts/                # Scripts de arranque
│   ├── services/               # Systemd services
│   └── iso/                    # Generador de ISO
│
├── docs/                       # Esta documentación
│
├── docker-compose.yml          # Levanta todo
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

## Flujo de una Petición

```
1. Tú haces click en el nodo "Imagen"
2. Next.js carga la vista /node/imagen
3. Escribes "genera un logo cyberpunk"
4. Next.js envía POST /api/nodes/imagen/chat
5. FastAPI recibe → pasa por Seguridad (zona verde ✅)
6. FastAPI llama a Interfaz Orquestador → OpenClaw
7. OpenClaw decide: "necesito generar imagen"
8. OpenClaw llama a Interfaz IA → Ollama (crea el prompt)
9. OpenClaw llama a Stable Diffusion (genera la imagen)
10. El resultado se guarda en Memoria (5 capas)
11. FastAPI responde al frontend con la imagen
12. Next.js la muestra en el Pizarrón
```

## Arquitectura Hexagonal

Este diseño sigue el patrón de **arquitectura hexagonal** (también llamada "ports and adapters"):

- **Puertos (Interfaces):** Lo que el sistema necesita (IA, Orquestador, Memoria)
- **Adaptadores (Providers):** La implementación concreta (Ollama, OpenClaw, PostgreSQL)
- **Core (Lógica de negocio):** Los nodos, la seguridad, el routing — esto NUNCA cambia

Empresas como Netflix, Spotify y Uber usan este patrón para poder cambiar tecnologías sin reescribir sus sistemas.
