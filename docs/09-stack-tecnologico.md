# 09 — Stack Tecnológico

## Stack Completo de YeyoOS

| Capa | Tecnología | Rol |
|------|-----------|-----|
| **Frontend** | Next.js + TypeScript + PixiJS | Interfaz de nodos, chat, áreas de trabajo |
| **Backend** | Python + FastAPI | Router, interfaces, lógica de nodos |
| **Orquestador IA** | OpenClaw (fork propio) | Decide qué hacer, ejecuta skills |
| **Modelos IA** | Ollama | Servidor de modelos local |
| **Base de datos** | PostgreSQL + pgvector | Datos permanentes + búsqueda semántica |
| **Cache/Colas** | Redis | Memoria de trabajo, sesiones, colas de Celery |
| **Tareas async** | Celery + Redis Broker | Generación de imágenes, video, publicación |
| **IA Texto** | Llama 3.1 (128K context) | Chat, guiones, razonamiento |
| **IA Imágenes** | Stable Diffusion | Generación de imágenes |
| **IA Visión** | LLaVA | Entender imágenes de referencia |
| **IA Voz** | Whisper | Transcripción de audio |
| **IA Voz Sintética** | Bark / XTTS | Generación de voz |
| **IA Embeddings** | nomic-embed-text | Búsqueda semántica |
| **Video** | FFmpeg + moviepy | Edición y procesamiento de video |
| **Testing** | pytest + Playwright + Jest | Backend, E2E, Frontend |
| **CI/CD** | GitHub Actions | Integración y despliegue continuo |
| **Logging** | Loguru + Sentry | Logs estructurados + errores en producción |
| **Seguridad** | AES-256 + bcrypt + JWT | Encriptación, passwords, autenticación |
| **Contenedores** | Docker + Docker Compose | Empaquetado y orquestación |
| **OS Base** | Linux (Alpine o Arch) | Sistema operativo host |
| **Drivers** | NVIDIA CUDA | Aceleración GPU |
| **Filesystem** | BTRFS | Snapshots automáticos |
| **Compositor** | Rust + smithay | Compositor Wayland custom para el hub de nodos |
| **Render** | Vulkan + GLES2 | Renderizado GPU para compositor |
| **Shaders** | GLSL / SPIR-V | Efectos visuales (glow, blur, transiciones) |
| **Paquetería** | YEYO-PKG (.ypkg) | Sistema de paquetes/nodos propio |
| **Containers (producción)** | Podman / containerd | Alternativa ligera a Docker para el OS final |
| **Hardware IA** | Auto-detección | NVIDIA, AMD, Intel, NPU, Coral, Tenstorrent |

## Dependencias por Componente

### Frontend (Next.js)
```json
{
  "next": "latest",
  "react": "latest",
  "typescript": "latest",
  "pixi.js": "latest",
  "@pixi/react": "latest"
}
```

### Backend (FastAPI)
```
fastapi
uvicorn
sqlalchemy
alembic
celery[redis]
redis
psycopg2-binary
pgvector
httpx
python-jose[cryptography]
passlib[bcrypt]
loguru
sentry-sdk
openai (para interfaz Ollama-compatible)
moviepy
```

### Modelos Ollama (Pre-instalados)
```bash
# Texto (elegir según GPU disponible)
ollama pull phi3:mini          # 3.8B - Para GTX 1060
ollama pull llama3.1:7b        # 7B - Para CPU+RAM
ollama pull llama3.1:70b       # 70B - Para upgrade futuro

# Embeddings
ollama pull nomic-embed-text

# Visión
ollama pull llava:7b

# Código
ollama pull codellama:7b
```

### Servicios Docker
```yaml
# docker-compose.yml
services:
  # --- Infraestructura ---
  postgres:
    image: pgvector/pgvector:pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: yeyo_os
      POSTGRES_USER: yeyo
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # --- IA ---
  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # --- Aplicación ---
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    depends_on:
      - postgres
      - redis
      - ollama
    environment:
      - DATABASE_URL=postgresql://yeyo:${DB_PASSWORD}@postgres:5432/yeyo_os
      - REDIS_URL=redis://redis:6379
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - storage_data:/app/storage

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    depends_on:
      - backend
    ports:
      - "3000:3000"

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A core.celery worker --loglevel=info
    depends_on:
      - redis
      - postgres
      - ollama
    volumes:
      - storage_data:/app/storage

volumes:
  postgres_data:
  redis_data:
  ollama_data:
  storage_data:
```

> **Nota:** Docker Compose es para DESARROLLO. En producción (YeyoOS instalado), los contenedores se gestionan directamente vía API de Podman/containerd por el YeyoOS Manager. El usuario nunca ve Docker.

## Interfaces Intercambiables (Contratos)

El sistema usa interfaces genéricas que permiten cambiar cualquier tecnología:

### IAProvider
```python
# backend/core/interfaces/ia_provider.py
from abc import ABC, abstractmethod

class IAProvider(ABC):
    @abstractmethod
    def chat(self, mensaje: str, contexto: list) -> str: ...

    @abstractmethod
    def generar_imagen(self, prompt: str, referencias: list = None) -> bytes: ...

    @abstractmethod
    def embeddings(self, texto: str) -> list[float]: ...

    @abstractmethod
    def transcribir_audio(self, audio: bytes) -> str: ...

    @abstractmethod
    def generar_voz(self, texto: str) -> bytes: ...
```

### Orquestador
```python
# backend/core/interfaces/orquestador.py
from abc import ABC, abstractmethod

class Orquestador(ABC):
    @abstractmethod
    def ejecutar(self, tarea: str, contexto: dict) -> dict: ...

    @abstractmethod
    def listar_skills(self) -> list[str]: ...

    @abstractmethod
    def agregar_skill(self, nombre: str, config: dict) -> bool: ...
```

### MemoriaProvider
```python
# backend/core/interfaces/memoria.py
from abc import ABC, abstractmethod

class MemoriaProvider(ABC):
    @abstractmethod
    def guardar(self, dato: dict, metadata: dict) -> str: ...

    @abstractmethod
    def buscar(self, query: str, tipo: str = None) -> list[dict]: ...

    @abstractmethod
    def buscar_semantico(self, texto: str, limit: int = 10) -> list[dict]: ...

    @abstractmethod
    def guardar_hecho(self, categoria: str, hecho: str, fuente: str) -> None: ...

    @abstractmethod
    def obtener_conocimiento(self, categoria: str = None) -> list[dict]: ...
```

### Configuración Central
```python
# backend/core/config.py

# Cambiar cualquiera de estos = cambiar la implementación
# El resto del código NO se toca

IA_PROVIDER = "ollama"          # Opciones: "ollama", "openai", "claude", "groq"
ORQUESTADOR = "openclaw"        # Opciones: "openclaw", "langchain", "crewai", "propio"
MEMORIA = "postgresql"          # Opciones: "postgresql", "mongodb", "supabase"

# Modelos por defecto
MODELO_CHAT = "llama3.1:7b"
MODELO_CODIGO = "codellama:7b"
MODELO_VISION = "llava:7b"
MODELO_EMBEDDINGS = "nomic-embed-text"
MODELO_IMAGEN = "stable-diffusion"
```

## Herramientas de Desarrollo

| Herramienta | Uso |
|-------------|-----|
| Git | Control de versiones |
| GitHub | Repositorio remoto + Actions |
| Docker | Contenedores |
| Docker Compose | Orquestación local |
| pytest | Tests de backend |
| Playwright | Tests E2E |
| Jest | Tests de frontend |
| Loguru | Logging estructurado |
| Sentry | Monitoreo de errores |
| QEMU | Virtualización para probar el OS |

## Entorno de Desarrollo

### Máquina Principal: PC Windows (GTX 1060 3GB + 16GB RAM)
Todo el desarrollo se hace aquí porque:
- Ollama corre con GPU real desde el día 1
- OpenClaw funciona nativamente
- Es la misma máquina que se convertirá en YeyoOS (Fase 12)
- WSL2 (Ubuntu dentro de Windows) permite desarrollar en Linux sin formatear

### Máquina Secundaria: Mac M1
- Editar código (VS Code + Git)
- Diseñar interfaz (Next.js corre perfecto en M1)
- Documentación
- Backup permanente del repositorio
- OpenClaw NO es compatible con Mac actualmente

### Setup en la PC Windows
```
Windows 11
├── WSL2 (Ubuntu 22.04)
│   ├── Docker Desktop (backend WSL2)
│   ├── Git
│   ├── Node.js (Next.js)
│   └── Python (FastAPI)
├── Ollama para Windows (acceso directo a GPU)
├── OpenClaw
├── VS Code (conectado a WSL2 vía Remote Extension)
└── GPU: GTX 1060 3GB (drivers NVIDIA + CUDA)
```

### Flujo de Trabajo
```
DESARROLLO (Fases 0-11):
  PC Windows + WSL2
  ├── docker-compose up → Levanta todo
  ├── Ollama con GPU
  ├── OpenClaw funcionando
  ├── Código en VS Code → WSL2
  └── Push a GitHub → Mac M1 tiene backup

INSTALACIÓN (Fase 12):
  PC Windows → Se formatea
  ├── Se genera ISO de Linux con todo integrado
  ├── Se flashea USB
  ├── Se instala YeyoOS
  └── Windows desaparece, YeyoOS toma su lugar

POST-INSTALACIÓN (Fases 13-14):
  Desarrollo desde:
  ├── El propio YeyoOS (Nodo Código)
  ├── Mac M1 (push via Git)
  └── Cualquier máquina con acceso al repo
```

### Upgrade Futuro
La PC recibirá upgrade de CPU, GPU y RAM de última generación. La arquitectura escala automáticamente sin cambiar código (ver doc 08-escalabilidad.md).
