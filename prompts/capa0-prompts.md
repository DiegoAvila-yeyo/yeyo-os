# 🏗️ CAPA 0: CIMIENTOS — Prompts de Ejecución
# Total: 13 micro-fases → 22 prompts (20 CLI + 2 VS Code)
# Flujo: Copiar prompt → Pegar en Copilot CLI o VS Code → Ejecutar → Verificar → Siguiente

---

## ═══════════════════════════════════════
## MICRO-FASE 0.0 — Particiones Btrfs
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.0-1 [CLI] — Crear estructura Btrfs con subvolumes

```
Estamos construyendo YeyoOS, un OS AI-nativo. Esta es la micro-fase 0.0: crear la estructura de particiones Btrfs.

Entorno: WSL2 Ubuntu sobre Windows, GTX 1060 3GB, 16GB RAM. Estamos en desarrollo, NO en hardware real aún. Necesitamos simular la estructura Btrfs que usará el OS final.

EJECUTAR:
1. Crear un archivo de imagen de 20GB para simular el disco:
   - `dd if=/dev/zero of=/tmp/yeyo-disk.img bs=1M count=20480`
   - `mkfs.btrfs /tmp/yeyo-disk.img`

2. Montar y crear los 5 subvolumes:
   - `sudo mkdir -p /mnt/yeyo`
   - `sudo mount /tmp/yeyo-disk.img /mnt/yeyo`
   - `sudo btrfs subvolume create /mnt/yeyo/@root`
   - `sudo btrfs subvolume create /mnt/yeyo/@home`
   - `sudo btrfs subvolume create /mnt/yeyo/@yeyo-data`
   - `sudo btrfs subvolume create /mnt/yeyo/@flash-memory`
   - `sudo btrfs subvolume create /mnt/yeyo/@snapshots`

3. Verificar la estructura:
   - `sudo btrfs subvolume list /mnt/yeyo`

4. Crear directorios base dentro de @yeyo-data:
   - `sudo mkdir -p /mnt/yeyo/@yeyo-data/{config,models,packages,logs}`
   - `sudo mkdir -p /mnt/yeyo/@flash-memory/{hot,warm,cold}`

5. Desmontar (lo montaremos cuando sea necesario):
   - `sudo umount /mnt/yeyo`

VERIFICAR:
- [ ] Archivo de imagen existe: `ls -lh /tmp/yeyo-disk.img` → ~20GB
- [ ] 5 subvolumes creados: `sudo mount /tmp/yeyo-disk.img /mnt/yeyo && sudo btrfs subvolume list /mnt/yeyo` → 5 líneas
- [ ] Directorios base existen en @yeyo-data y @flash-memory
- [ ] Btrfs tools instalados: `btrfs --version`

SI FALLA:
- btrfs no instalado: `sudo apt install -y btrfs-progs`
- Espacio insuficiente en /tmp: usar otro path como ~/yeyo-disk.img
- WSL2 no soporta btrfs: verificar kernel con `uname -r`, necesita 5.15+

GATE: 5 subvolumes listados correctamente + directorios internos existen.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.1 — Kernel Headers y Módulos
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.1-1 [CLI] — Instalar kernel headers y verificar módulos

```
Estamos construyendo YeyoOS. Micro-fase 0.1: instalar kernel headers necesarios para compilar drivers y módulos.

Entorno: WSL2 Ubuntu. Micro-fase 0.0 (Btrfs) completada.

EJECUTAR:
1. Instalar kernel headers y herramientas de compilación:
   sudo apt update
   sudo apt install -y linux-headers-$(uname -r) build-essential dkms
   sudo apt install -y pkg-config libssl-dev libffi-dev

2. Verificar módulos cargados necesarios:
   lsmod | grep -E "btrfs|nvidia|overlay"

3. Instalar herramientas de diagnóstico:
   sudo apt install -y htop iotop sysstat curl wget git

VERIFICAR:
- [ ] Headers instalados: `ls /usr/src/linux-headers-$(uname -r)` → directorio existe
- [ ] GCC funciona: `gcc --version` → versión
- [ ] Make funciona: `make --version` → versión
- [ ] DKMS instalado: `dkms status` → sin error
- [ ] Git instalado: `git --version` → versión

SI FALLA:
- Headers no match kernel: `apt search linux-headers` → buscar versión correcta
- En WSL2 los headers pueden ser especiales: `apt install linux-headers-generic`

GATE: gcc + make + dkms funcionando, headers instalados para el kernel actual.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.2 — Systemd Base
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.2-1 [CLI] — Configurar Systemd y servicios base

```
Estamos construyendo YeyoOS. Micro-fase 0.2: configurar systemd como init system y preparar la estructura de servicios.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.1 completadas.

EJECUTAR:
1. Verificar que systemd está activo (WSL2 necesita configuración):
   ps -p 1 -o comm=
   Si NO dice "systemd", configurar:
   - Crear /etc/wsl.conf con:
     [boot]
     systemd=true
   - Reiniciar WSL desde PowerShell: wsl --shutdown

2. Crear directorio para servicios de YeyoOS:
   sudo mkdir -p /etc/systemd/system/yeyo.target.wants

3. Crear target personalizado para YeyoOS:
   Crear archivo /etc/systemd/system/yeyo.target con:
   [Unit]
   Description=YeyoOS Services
   Requires=multi-user.target
   After=multi-user.target

4. Crear template de servicio (usaremos para todos los servicios):
   Crear /etc/systemd/system/yeyo-template@.service con:
   [Unit]
   Description=YeyoOS %i Service
   After=network.target
   PartOf=yeyo.target

   [Service]
   Type=simple
   Restart=always
   RestartSec=3
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=yeyo.target

5. Recargar systemd:
   sudo systemctl daemon-reload

VERIFICAR:
- [ ] Systemd es PID 1: `ps -p 1 -o comm=` → systemd
- [ ] Target creado: `systemctl cat yeyo.target` → muestra contenido
- [ ] Template creado: `systemctl cat yeyo-template@.service` → muestra contenido
- [ ] Journal funciona: `journalctl --no-pager -n 5` → últimas 5 líneas
- [ ] No errores: `systemctl --failed` → 0 failed units (o solo las que ya existían)

SI FALLA:
- WSL2 sin systemd: necesitas Windows 11 + WSL2 actualizado
- Si no puedes usar systemd: Plan B con supervisord (pip install supervisor)

GATE: systemd como PID 1, yeyo.target cargado, journal funcional.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.3 — PostgreSQL 16 + pgvector
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.3-1 [CLI] — Instalar PostgreSQL 16 + pgvector

```
Estamos construyendo YeyoOS. Micro-fase 0.3, Prompt 1 de 2: instalar PostgreSQL 16 con extensión pgvector para Flash Memory.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.2 completadas. Systemd funcional.

EJECUTAR:
1. Añadir repositorio de PostgreSQL 16:
   sudo apt install -y wget gnupg2
   sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
   wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
   sudo apt update

2. Instalar PostgreSQL 16:
   sudo apt install -y postgresql-16 postgresql-16-pgvector

3. Iniciar y habilitar servicio:
   sudo systemctl enable --now postgresql

4. Crear usuario y database para YeyoOS:
   sudo -u postgres psql -c "CREATE USER yeyo WITH PASSWORD 'yeyo_dev_2026';"
   sudo -u postgres psql -c "CREATE DATABASE yeyo_db OWNER yeyo;"
   sudo -u postgres psql -c "CREATE DATABASE yeyo_test_db OWNER yeyo;"

5. Habilitar pgvector:
   sudo -u postgres psql yeyo_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
   sudo -u postgres psql yeyo_test_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

6. Configurar pg_hba.conf para conexión local con password:
   Buscar pg_hba.conf: sudo find /etc/postgresql -name pg_hba.conf
   Agregar línea (antes de las existentes):
   local   yeyo_db     yeyo                                md5
   local   yeyo_test_db yeyo                               md5
   host    yeyo_db     yeyo    127.0.0.1/32                md5
   host    yeyo_test_db yeyo   127.0.0.1/32                md5

7. Optimizar postgresql.conf para desarrollo:
   shared_buffers = 256MB
   work_mem = 64MB
   effective_cache_size = 512MB
   maintenance_work_mem = 128MB

8. Reiniciar para aplicar cambios:
   sudo systemctl restart postgresql

VERIFICAR:
- [ ] PG corriendo: `sudo systemctl status postgresql` → active (running)
- [ ] Versión correcta: `psql --version` → 16.x
- [ ] pgvector activo: `sudo -u postgres psql yeyo_db -c "SELECT extname FROM pg_extension WHERE extname='vector';"` → 1 row
- [ ] Conexión como yeyo: `PGPASSWORD=yeyo_dev_2026 psql -U yeyo -d yeyo_db -h 127.0.0.1 -c "SELECT 1;"` → 1
- [ ] DB de test existe: `PGPASSWORD=yeyo_dev_2026 psql -U yeyo -d yeyo_test_db -h 127.0.0.1 -c "SELECT 1;"` → 1

SI FALLA:
- Puerto 5432 ocupado: `sudo ss -tlnp | grep 5432` → matar proceso
- pgvector no instala: `apt search pgvector` → verificar nombre del paquete
- Auth falla: revisar pg_hba.conf, orden de las líneas importa

NO HACER:
- No crear tablas aún (eso es Capa 2)
- No cambiar el puerto default (5432)
- No usar trust auth (siempre md5/scram)

GATE: PostgreSQL 16 corriendo + pgvector loaded + conexión como usuario yeyo OK.
```

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

---

## ═══════════════════════════════════════
## MICRO-FASE 0.4 — Redis 7
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.4-1 [CLI] — Instalar y configurar Redis

```
Estamos construyendo YeyoOS. Micro-fase 0.4: instalar Redis 7 para caché de Flash Memory (tiers HOT/WARM/COLD).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.3 completadas. PostgreSQL corriendo.

EJECUTAR:
1. Instalar Redis 7:
   sudo apt install -y redis-server

2. Configurar Redis para YeyoOS:
   Editar /etc/redis/redis.conf:
   - maxmemory 512mb
   - maxmemory-policy allkeys-lru
   - save 900 1
   - save 300 10
   - save 60 10000
   - requirepass yeyo_redis_dev_2026
   - bind 127.0.0.1
   - protected-mode yes

3. Iniciar y habilitar:
   sudo systemctl enable --now redis-server

4. Agregar a .env del proyecto (cd ~/yeyo-os):
   Añadir estas líneas al archivo .env existente:
   # Redis
   REDIS_URL=redis://:yeyo_redis_dev_2026@127.0.0.1:6379/0

5. Actualizar .env.example también:
   REDIS_URL=redis://:YOUR_PASSWORD@127.0.0.1:6379/0

VERIFICAR:
- [ ] Redis corriendo: `sudo systemctl status redis-server` → active
- [ ] Versión: `redis-cli --version` → 7.x
- [ ] Conexión con auth: `redis-cli -a yeyo_redis_dev_2026 ping` → PONG
- [ ] Memoria configurada: `redis-cli -a yeyo_redis_dev_2026 CONFIG GET maxmemory` → 536870912 (512MB)
- [ ] Solo localhost: `redis-cli -a yeyo_redis_dev_2026 CONFIG GET bind` → 127.0.0.1

SI FALLA:
- Puerto 6379 ocupado: `sudo ss -tlnp | grep 6379` → matar proceso
- Auth no funciona: verificar que requirepass está sin comentar en redis.conf

NO HACER:
- No exponer Redis a red externa
- No desactivar el password
- No crear keys aún (eso es Capa 2)

GATE: Redis 7 corriendo en localhost, auth con password, maxmemory 512MB, .env actualizado.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.5 — Node.js 20 + Scaffold
## Tipo: MIXTA | Prompts: 2 (1 CLI + 1 VSCODE)
## ═══════════════════════════════════════

### PROMPT 0.5-1 [CLI] — Instalar Node.js 20 LTS

```
Estamos construyendo YeyoOS. Micro-fase 0.5, Prompt 1 de 2: instalar Node.js 20 LTS para el frontend (Next.js).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.4 completadas.

EJECUTAR:
1. Instalar Node.js 20 via nvm (más flexible que apt):
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
   export NVM_DIR="$HOME/.nvm"
   [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
   nvm install 20
   nvm use 20
   nvm alias default 20

2. Verificar npm y instalar pnpm (más rápido que npm):
   npm install -g pnpm

3. Agregar a .env:
   # Node.js
   NODE_ENV=development

VERIFICAR:
- [ ] Node version: `node --version` → v20.x.x
- [ ] npm version: `npm --version` → 10.x.x
- [ ] pnpm version: `pnpm --version` → 8.x o 9.x
- [ ] nvm funciona: `nvm list` → v20.x como default

SI FALLA:
- nvm no carga: agregar a ~/.bashrc las líneas de export NVM_DIR
- Permisos: no usar sudo con nvm

GATE: Node.js 20 LTS instalado via nvm, pnpm disponible.
```

### PROMPT 0.5-2 [VSCODE] — Crear scaffold del proyecto Next.js

```
Estamos construyendo YeyoOS. Micro-fase 0.5, Prompt 2 de 2: crear el scaffold base del frontend con Next.js 14.

PREREQUISITO: Node.js 20 + pnpm instalados (Prompt 0.5-1).

Abre el directorio ~/yeyo-os en VS Code.

CREAR:
1. Inicializar Next.js en subdirectorio frontend/:
   cd ~/yeyo-os
   pnpm create next-app frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

2. Entrar al directorio y agregar dependencias base:
   cd frontend
   pnpm add zustand
   pnpm add pixi.js@^8.0.0
   pnpm add socket.io-client
   pnpm add -D @types/node

3. Crear estructura de carpetas:
   mkdir -p src/components/{hub,nodes,chat,common}
   mkdir -p src/lib/{api,store,utils}
   mkdir -p src/hooks
   mkdir -p src/types

4. Crear archivo src/types/index.ts con tipos base:
   // YeyoOS Type Definitions — Micro-fase 0.5
   
   export interface Node {
     id: string;
     type: NodeType;
     position: { x: number; y: number };
     label: string;
     status: 'active' | 'idle' | 'error';
   }
   
   export type NodeType = 
     | 'central' 
     | 'chat' 
     | 'image' 
     | 'video' 
     | 'code' 
     | 'automation' 
     | 'files' 
     | 'browser' 
     | 'config';
   
   export interface Memory {
     id: string;
     content: string;
     type: 'conversation' | 'preference' | 'fact' | 'correction';
     tier: 'HOT' | 'WARM' | 'COLD';
     createdAt: Date;
   }

5. Crear archivo src/lib/store/hub-store.ts:
   // Zustand store base — Micro-fase 0.5
   import { create } from 'zustand';
   import type { Node } from '@/types';
   
   interface HubState {
     nodes: Node[];
     selectedNodeId: string | null;
     addNode: (node: Node) => void;
     selectNode: (id: string | null) => void;
     updateNodePosition: (id: string, x: number, y: number) => void;
   }
   
   export const useHubStore = create<HubState>((set) => ({
     nodes: [],
     selectedNodeId: null,
     addNode: (node) => set((state) => ({ nodes: [...state.nodes, node] })),
     selectNode: (id) => set({ selectedNodeId: id }),
     updateNodePosition: (id, x, y) =>
       set((state) => ({
         nodes: state.nodes.map((n) =>
           n.id === id ? { ...n, position: { x, y } } : n
         ),
       })),
   }));

6. Verificar que compila:
   pnpm build

VERIFICAR:
- [ ] Build exitoso: `cd frontend && pnpm build` → sin errores
- [ ] Estructura existe: `ls src/components/` → hub, nodes, chat, common
- [ ] Tipos creados: `cat src/types/index.ts` → Node, NodeType, Memory
- [ ] Store creado: `cat src/lib/store/hub-store.ts` → useHubStore
- [ ] Dev server arranca: `pnpm dev` → localhost:3000 responde (detener después)

NO HACER:
- No crear componentes UI aún (eso es Capa 3)
- No conectar a PostgreSQL/Redis desde frontend
- No instalar PixiJS en detalle aún (solo el paquete)

GATE: Next.js 14 scaffold compila, estructura de carpetas lista, tipos base definidos, Zustand store base funcional.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.6 — Python 3.11 + Virtual Environment
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.6-1 [CLI] — Instalar Python 3.11 y configurar venv

```
Estamos construyendo YeyoOS. Micro-fase 0.6: Python 3.11 como backend de IA y Flash Memory.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.5 completadas.

EJECUTAR:
1. Instalar Python 3.11:
   sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

2. Crear virtual environment para el proyecto:
   cd ~/yeyo-os
   python3.11 -m venv .venv
   source .venv/bin/activate

3. Instalar dependencias base:
   pip install --upgrade pip
   pip install asyncpg redis aiohttp
   pip install python-dotenv
   pip install pydantic
   pip install sentence-transformers
   pip install pytest pytest-asyncio httpx

4. Crear requirements.txt:
   pip freeze > requirements.txt

5. Crear estructura de carpetas Python:
   mkdir -p src/{memory,ia,api,utils}
   touch src/__init__.py src/memory/__init__.py src/ia/__init__.py src/api/__init__.py src/utils/__init__.py

6. Crear src/utils/config.py:
   # YeyoOS Configuration — Micro-fase 0.6
   from dotenv import load_dotenv
   import os
   
   load_dotenv()
   
   DATABASE_URL = os.getenv("DATABASE_URL")
   TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
   REDIS_URL = os.getenv("REDIS_URL")
   NODE_ENV = os.getenv("NODE_ENV", "development")

7. Crear test básico tests/test_config.py:
   mkdir -p tests
   touch tests/__init__.py
   # test que verifica que config carga las variables

8. Agregar .venv a .gitignore:
   echo ".venv" >> .gitignore

VERIFICAR:
- [ ] Python version: `python --version` → 3.11.x (dentro del venv)
- [ ] Venv activo: `which python` → ~/yeyo-os/.venv/bin/python
- [ ] asyncpg importa: `python -c "import asyncpg; print('OK')"` → OK
- [ ] sentence-transformers importa: `python -c "from sentence_transformers import SentenceTransformer; print('OK')"` → OK
- [ ] Config carga .env: `python -c "from src.utils.config import DATABASE_URL; print(DATABASE_URL)"` → postgresql://...
- [ ] pytest funciona: `pytest tests/ -v` → pass
- [ ] .venv en .gitignore: `grep '.venv' .gitignore` → match

SI FALLA:
- Python 3.11 no disponible: `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update`
- sentence-transformers falla: verificar que hay 2GB+ de RAM libre (descarga modelo)
- CUDA warning en sentence-transformers: ignorar, usamos CPU para embeddings

NO HACER:
- No instalar torch con CUDA aún (eso es 0.10 + Capa 7 para training)
- No crear lógica de negocio aún
- No hardcodear passwords (todo desde .env)

GATE: Python 3.11 en venv, todas las dependencias base instaladas, config.py carga .env correctamente, pytest funciona.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.7 — Rust Toolchain
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.7-1 [CLI] — Instalar Rust y crear proyecto Guardian

```
Estamos construyendo YeyoOS. Micro-fase 0.7: instalar Rust toolchain para el compositor Wayland (Capa 3) y Guardian daemon (Capa 6).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.6 completadas.

EJECUTAR:
1. Instalar Rust via rustup:
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
   source $HOME/.cargo/env

2. Instalar componentes adicionales:
   rustup component add clippy rustfmt
   rustup target add x86_64-unknown-linux-gnu

3. Instalar dependencias de sistema para compilación:
   sudo apt install -y cmake libwayland-dev libxkbcommon-dev libudev-dev libinput-dev libgbm-dev libdrm-dev

4. Crear workspace Rust dentro del proyecto:
   cd ~/yeyo-os
   mkdir -p rust/
   cd rust/
   
   Crear Cargo.toml de workspace:
   [workspace]
   members = ["guardian", "compositor"]
   resolver = "2"

5. Crear proyecto Guardian (scaffold):
   cargo init guardian --name yeyo-guardian
   cd guardian
   cargo add tokio --features full
   cargo add serde serde_json --features derive
   cargo add chrono --features serde
   cd ..

6. Crear proyecto Compositor (scaffold vacío):
   cargo init compositor --name yeyo-compositor
   cd ..

7. Verificar que compila:
   cd rust && cargo build

VERIFICAR:
- [ ] Rust version: `rustc --version` → 1.7x.x+
- [ ] Cargo version: `cargo --version`
- [ ] Clippy funciona: `cd ~/yeyo-os/rust && cargo clippy` → sin errores
- [ ] Guardian compila: `cargo build -p yeyo-guardian` → OK
- [ ] Compositor compila: `cargo build -p yeyo-compositor` → OK
- [ ] Workspace build: `cargo build` → ambos compilan

SI FALLA:
- Rustup no en PATH: `source $HOME/.cargo/env` o agregar a ~/.bashrc
- Dependencias de sistema faltantes: instalar lo que pida el error de compilación
- WSL2 sin wayland libs: las instalamos para compilar, no para ejecutar aún

NO HACER:
- No implementar lógica en Guardian aún (Capa 6)
- No implementar compositor aún (Capa 3)
- Solo scaffold + verificar que compila

GATE: Rust + cargo funcionando, workspace con 2 proyectos (guardian + compositor), ambos compilan.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.8 — Ollama
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.8-1 [CLI] — Instalar Ollama

```
Estamos construyendo YeyoOS. Micro-fase 0.8, Prompt 1 de 2: instalar Ollama para inferencia de IA local.

Entorno: WSL2 Ubuntu, GTX 1060 3GB VRAM. Micro-fases 0.0-0.7 completadas.

IMPORTANTE: Ollama necesita GPU drivers (que instalaremos en 0.10). Por ahora instalar y verificar que corre en CPU. La aceleración GPU vendrá después.

EJECUTAR:
1. Instalar Ollama:
   curl -fsSL https://ollama.ai/install.sh | sh

2. Verificar que el servicio está corriendo:
   systemctl status ollama
   Si no está corriendo:
   sudo systemctl enable --now ollama

3. Esperar 5 segundos y verificar el API:
   curl http://localhost:11434/api/tags

4. Descargar modelo ligero para verificación:
   ollama pull qwen2.5:0.5b
   (Este es el más pequeño, solo para test. El 3b lo usaremos después.)

5. Agregar a .env:
   # Ollama
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen2.5:0.5b

6. Actualizar .env.example:
   OLLAMA_HOST=http://localhost:11434
   OLLAMA_MODEL=qwen2.5:0.5b

VERIFICAR:
- [ ] Ollama corriendo: `systemctl status ollama` → active
- [ ] API responde: `curl -s http://localhost:11434/api/tags | head` → JSON con models
- [ ] Modelo descargado: `ollama list` → qwen2.5:0.5b listado
- [ ] Puerto 11434: `ss -tlnp | grep 11434` → ollama

SI FALLA:
- Install script falla: descargar binario manualmente de github.com/ollama/ollama
- Puerto ocupado: verificar con ss y matar proceso
- Sin GPU: Ollama corre en CPU (más lento pero funcional)

NO HACER:
- No descargar modelos grandes aún (3b necesita GPU configurada)
- No configurar GPU aún (eso es 0.10)
- No exponer Ollama a red externa

GATE: Ollama corriendo en localhost:11434, modelo 0.5b descargado y listado.
```

### PROMPT 0.8-2 [CLI] — Verificar inferencia de Ollama

```
Estamos construyendo YeyoOS. Micro-fase 0.8, Prompt 2 de 2: verificar que Ollama puede hacer inferencia correctamente.

PREREQUISITO: Prompt 0.8-1 completado (Ollama instalado + modelo 0.5b).

EJECUTAR:
1. Test de inferencia básico:
   curl http://localhost:11434/api/generate -d '{
     "model": "qwen2.5:0.5b",
     "prompt": "Say hello in one word",
     "stream": false
   }'
   → Debe devolver JSON con "response" que contiene texto

2. Test de inferencia con streaming:
   curl http://localhost:11434/api/generate -d '{
     "model": "qwen2.5:0.5b",
     "prompt": "Count from 1 to 5",
     "stream": true
   }'
   → Debe devolver múltiples líneas JSON (streaming)

3. Test de chat API:
   curl http://localhost:11434/api/chat -d '{
     "model": "qwen2.5:0.5b",
     "messages": [{"role": "user", "content": "What is 2+2?"}],
     "stream": false
   }'
   → Debe responder con el resultado correcto

4. Crear script de test en Python:
   cd ~/yeyo-os
   source .venv/bin/activate
   
   Crear tests/test_ollama.py:
   import httpx
   import os
   from dotenv import load_dotenv
   
   load_dotenv()
   
   def test_ollama_api_reachable():
       r = httpx.get(f"{os.getenv('OLLAMA_HOST')}/api/tags")
       assert r.status_code == 200
   
   def test_ollama_generate():
       r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/generate", json={
           "model": os.getenv('OLLAMA_MODEL'),
           "prompt": "Say OK",
           "stream": False
       })
       assert r.status_code == 200
       assert "response" in r.json()
       assert len(r.json()["response"]) > 0
   
   def test_ollama_chat():
       r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/chat", json={
           "model": os.getenv('OLLAMA_MODEL'),
           "messages": [{"role": "user", "content": "Say hello"}],
           "stream": False
       })
       assert r.status_code == 200
       assert "message" in r.json()

5. Ejecutar tests:
   pytest tests/test_ollama.py -v

VERIFICAR:
- [ ] Generate (no stream) devuelve texto: response no vacío
- [ ] Generate (stream) devuelve múltiples chunks
- [ ] Chat API funciona: message con content
- [ ] 3 pytest tests pasan: `pytest tests/test_ollama.py -v` → 3 passed
- [ ] Latencia <30s en CPU: (0.5b es rápido incluso en CPU)

GATE: Ollama hace inferencia correctamente, 3 tests Python pasan, API generate + chat funcionan.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.9 — Podman (Containers)
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.9-1 [CLI] — Instalar Podman para containers de nodos

```
Estamos construyendo YeyoOS. Micro-fase 0.9: instalar Podman como runtime de containers (reemplazo de Docker, más seguro).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.8 completadas.

IMPORTANTE: Usamos Podman, NO Docker. Podman es rootless por defecto (más seguro) y compatible con Docker CLI.

EJECUTAR:
1. Instalar Podman:
   sudo apt install -y podman

2. Configurar Podman rootless:
   podman system migrate

3. Verificar que funciona:
   podman run --rm alpine echo "YeyoOS container OK"

4. Configurar registries:
   mkdir -p ~/.config/containers
   Crear ~/.config/containers/registries.conf:
   [registries.search]
   registries = ['docker.io']

5. Crear un container de test para verificar aislamiento:
   podman run --rm -it --security-opt=no-new-privileges:true \
     --cap-drop=ALL \
     alpine sh -c "whoami && id && echo 'Isolated OK'"
   → Debe mostrar usuario non-root

6. Verificar que Podman no expone socket peligroso:
   ls /var/run/docker.sock 2>/dev/null && echo "PELIGRO: Docker socket existe" || echo "OK: No docker socket"

VERIFICAR:
- [ ] Podman version: `podman --version` → 3.x o 4.x
- [ ] Rootless funciona: `podman info | grep rootless` → true
- [ ] Container corre: `podman run --rm alpine echo test` → "test"
- [ ] No Docker socket: `ls /var/run/docker.sock 2>/dev/null` → no existe
- [ ] Capabilities dropped: `podman run --rm --cap-drop=ALL alpine cat /proc/1/status | grep Cap` → CapEff: 0

SI FALLA:
- Podman no instala: `sudo apt update && sudo apt install -y podman`
- Rootless falla: `podman system reset` y reintentar
- cgroup v2 necesario: verificar `cat /sys/fs/cgroup/cgroup.controllers`

NO HACER:
- NO instalar Docker (usamos Podman)
- NO montar /var/run/docker.sock en ningún container JAMÁS
- NO correr containers como root

GATE: Podman rootless funcionando, containers corren sin root, no hay Docker socket.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.10 — GPU Drivers + NVIDIA Container
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.10-1 [CLI] — Instalar NVIDIA drivers en WSL2

```
Estamos construyendo YeyoOS. Micro-fase 0.10, Prompt 1 de 2: configurar GPU NVIDIA en WSL2 para Ollama y IA.

Entorno: WSL2 Ubuntu, GTX 1060 3GB. Micro-fases 0.0-0.9 completadas.

IMPORTANTE PARA WSL2: Los drivers NVIDIA se instalan en WINDOWS, no en WSL2. WSL2 usa el driver de Windows via GPU paravirtualization. Solo necesitamos las CUDA libraries dentro de WSL2.

EJECUTAR:
1. Verificar que GPU es visible desde WSL2:
   nvidia-smi
   Si funciona → ya tienes el driver de Windows. Continuar.
   Si NO funciona → necesitas instalar NVIDIA drivers en Windows primero.

2. Instalar CUDA toolkit para WSL2:
   wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
   sudo dpkg -i cuda-keyring_1.1-1_all.deb
   sudo apt update
   sudo apt install -y cuda-toolkit-12-4

3. Agregar CUDA al PATH:
   echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
   echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
   source ~/.bashrc

4. Verificar CUDA:
   nvcc --version
   nvidia-smi

5. Reiniciar Ollama para que detecte GPU:
   sudo systemctl restart ollama
   Esperar 5 segundos.

6. Verificar que Ollama usa GPU:
   curl -s http://localhost:11434/api/tags
   ollama run qwen2.5:0.5b "Say GPU test" --verbose 2>&1 | grep -i gpu

VERIFICAR:
- [ ] nvidia-smi funciona: muestra GTX 1060 con 3GB
- [ ] CUDA version: `nvcc --version` → 12.x
- [ ] VRAM visible: `nvidia-smi --query-gpu=memory.total --format=csv` → ~3072 MiB
- [ ] Ollama detecta GPU: logs muestran CUDA/GPU
- [ ] Inferencia más rápida: comparar tiempo vs CPU

SI FALLA:
- nvidia-smi no funciona: instalar driver NVIDIA en Windows, reiniciar WSL
- CUDA no instala: verificar que el repo de NVIDIA WSL está configurado
- Ollama no detecta GPU: `OLLAMA_GPU_LAYER=99 ollama serve` para forzar

NO HACER:
- NO instalar drivers NVIDIA Linux (usamos los de Windows en WSL2)
- NO instalar nvidia-docker (usamos Podman)

GATE: nvidia-smi muestra GTX 1060 3GB, CUDA toolkit funcional, Ollama usa GPU.
```

### PROMPT 0.10-2 [CLI] — Descargar modelo real y NVIDIA container toolkit

```
Estamos construyendo YeyoOS. Micro-fase 0.10, Prompt 2 de 2: descargar modelo de IA real y configurar GPU para containers.

PREREQUISITO: Prompt 0.10-1 completado (GPU visible + CUDA instalado).

EJECUTAR:
1. Descargar el modelo real que usaremos (qwen2.5:3b):
   ollama pull qwen2.5:3b
   (Esto tarda 2-5 minutos, ~2GB de descarga)

2. Verificar VRAM usage con el modelo real:
   En una terminal: watch -n 1 nvidia-smi
   En otra terminal: ollama run qwen2.5:3b "Explain what is AI in 2 sentences"
   → nvidia-smi debe mostrar VRAM usage ~1800MB durante inferencia

3. Instalar NVIDIA Container Toolkit para Podman:
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
     sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt update
   sudo apt install -y nvidia-container-toolkit
   sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml

4. Verificar GPU en container:
   podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi

5. Actualizar .env con modelo real:
   Cambiar OLLAMA_MODEL en .env:
   OLLAMA_MODEL=qwen2.5:3b

6. Actualizar test de Ollama para usar modelo real:
   Editar tests/test_ollama.py y correr:
   pytest tests/test_ollama.py -v

VERIFICAR:
- [ ] Modelo 3b descargado: `ollama list` → qwen2.5:3b
- [ ] VRAM ~1800MB durante uso: nvidia-smi muestra uso
- [ ] VRAM vuelve a ~0 cuando idle: nvidia-smi post-inferencia
- [ ] GPU en container: `podman run --rm --device nvidia.com/gpu=all ubuntu nvidia-smi` → muestra GPU
- [ ] Tests pasan con modelo real: `pytest tests/test_ollama.py -v` → 3 passed

SI FALLA:
- OOM con 3b: usar qwen2.5:1.5b como fallback
- NVIDIA container toolkit no instala: verificar repos, usar --no-install-recommends
- GPU no visible en container: revisar CDI config, regenerar yaml

GATE: qwen2.5:3b funciona con GPU, VRAM <2GB durante uso, GPU accesible desde containers Podman.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.11 — Security Base
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.11-1 [CLI] — Usuarios, permisos y estructura de seguridad

```
Estamos construyendo YeyoOS. Micro-fase 0.11, Prompt 1 de 2: configurar la base de seguridad del sistema.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.10 completadas. Todo instalado.

EJECUTAR:
1. Crear usuario de sistema para servicios de YeyoOS (no login):
   sudo useradd -r -s /usr/sbin/nologin -d /var/lib/yeyo yeyo-service

2. Crear grupo para acceso a recursos de YeyoOS:
   sudo groupadd yeyo-users

3. Agregar tu usuario al grupo:
   sudo usermod -aG yeyo-users $USER

4. Configurar permisos de directorios:
   sudo mkdir -p /var/lib/yeyo/{config,models,packages,logs,run}
   sudo mkdir -p /var/log/yeyo
   sudo chown -R yeyo-service:yeyo-users /var/lib/yeyo
   sudo chown -R yeyo-service:yeyo-users /var/log/yeyo
   sudo chmod -R 750 /var/lib/yeyo
   sudo chmod -R 750 /var/log/yeyo

5. Proteger archivos sensibles:
   chmod 600 ~/yeyo-os/.env
   
6. Configurar ulimits para servicios:
   Crear /etc/security/limits.d/yeyo.conf:
   yeyo-service soft nofile 65536
   yeyo-service hard nofile 65536
   yeyo-service soft nproc 4096
   yeyo-service hard nproc 4096

7. Verificar que no hay servicios escuchando en interfaces públicas:
   ss -tlnp | grep -v "127.0.0.1\|::1\|\*:22"
   → Solo debe haber servicios en localhost

VERIFICAR:
- [ ] Usuario yeyo-service existe: `id yeyo-service` → uid sin login shell
- [ ] Grupo yeyo-users existe: `getent group yeyo-users` → muestra grupo
- [ ] Permisos correctos: `ls -la /var/lib/yeyo/` → yeyo-service:yeyo-users, 750
- [ ] .env protegido: `stat -c %a ~/yeyo-os/.env` → 600
- [ ] Solo localhost: `ss -tlnp` → PG, Redis, Ollama solo en 127.0.0.1
- [ ] ulimits configurados: `cat /etc/security/limits.d/yeyo.conf` → existe

SI FALLA:
- Permiso denegado: usar sudo
- Grupo no aplica hasta re-login: `newgrp yeyo-users` o logout/login

GATE: Usuario de servicio creado, permisos restrictivos, servicios solo en localhost, .env protegido.
```

### PROMPT 0.11-2 [CLI] — Audit logging y firewall básico

```
Estamos construyendo YeyoOS. Micro-fase 0.11, Prompt 2 de 2: configurar audit logging y firewall básico.

PREREQUISITO: Prompt 0.11-1 completado (usuarios y permisos).

EJECUTAR:
1. Instalar y configurar auditd:
   sudo apt install -y auditd
   sudo systemctl enable --now auditd

2. Crear reglas de auditoría para YeyoOS:
   Crear /etc/audit/rules.d/yeyo.rules:
   # Monitorear cambios en configuración de YeyoOS
   -w /var/lib/yeyo/config/ -p wa -k yeyo-config
   -w /etc/systemd/system/yeyo.target -p wa -k yeyo-systemd
   
   # Monitorear accesos a archivos sensibles
   -w /etc/passwd -p wa -k auth-change
   -w /etc/shadow -p wa -k auth-change
   -w /etc/sudoers -p wa -k sudo-change
   
   # Monitorear ejecución de comandos privilegiados
   -a always,exit -F arch=b64 -S execve -F euid=0 -k root-commands

3. Recargar reglas:
   sudo auditctl -R /etc/audit/rules.d/yeyo.rules

4. Configurar firewall básico con ufw:
   sudo apt install -y ufw
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow from 127.0.0.1
   sudo ufw --force enable

5. Crear directorio de logs estructurados de YeyoOS:
   sudo mkdir -p /var/log/yeyo/{guardian,api,memory,security}
   sudo chown -R yeyo-service:yeyo-users /var/log/yeyo/
   sudo chmod -R 750 /var/log/yeyo/

6. Configurar logrotate para YeyoOS:
   Crear /etc/logrotate.d/yeyo:
   /var/log/yeyo/*/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
       create 640 yeyo-service yeyo-users
   }

7. Crear test de seguridad básico:
   cd ~/yeyo-os
   source .venv/bin/activate
   
   Crear tests/test_security.py:
   import subprocess
   import os
   
   def test_env_not_world_readable():
       mode = oct(os.stat('.env').st_mode)[-3:]
       assert mode == '600', f".env permisos: {mode}, esperado: 600"
   
   def test_services_only_localhost():
       result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
       lines = result.stdout.strip().split('\n')[1:]  # skip header
       for line in lines:
           if '127.0.0.1' not in line and '::1' not in line and '*:22' not in line:
               if '0.0.0.0' in line or ':::' in line:
                   assert False, f"Servicio expuesto: {line}"
   
   def test_audit_running():
       result = subprocess.run(['systemctl', 'is-active', 'auditd'], capture_output=True, text=True)
       assert result.stdout.strip() == 'active'

8. Ejecutar tests:
   pytest tests/test_security.py -v

VERIFICAR:
- [ ] Auditd corriendo: `systemctl status auditd` → active
- [ ] Reglas cargadas: `sudo auditctl -l` → muestra reglas yeyo
- [ ] Firewall activo: `sudo ufw status` → active, default deny incoming
- [ ] Log dirs existen: `ls /var/log/yeyo/` → guardian, api, memory, security
- [ ] Logrotate configurado: `cat /etc/logrotate.d/yeyo` → existe
- [ ] Security tests pasan: `pytest tests/test_security.py -v` → 3 passed

SI FALLA:
- ufw bloquea WSL: `sudo ufw allow from 172.16.0.0/12` (rango WSL)
- auditd no arranca: verificar que no hay otra instancia

NO HACER:
- No configurar firewall complejo aún (Capa 6.9)
- No bloquear SSH si lo necesitas para desarrollo

GATE: Auditd corriendo con reglas YeyoOS, firewall deny incoming activo, logs rotativos configurados, 3 security tests pasan.
```

---

## ═══════════════════════════════════════
## MICRO-FASE 0.12 — Integration Test Capa 0
## Tipo: CLI | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.12-1 [CLI] — Test de integración completo de Capa 0

```
Estamos construyendo YeyoOS. Micro-fase 0.12: INTEGRATION TEST de toda la Capa 0. Esta es la verificación final antes de pasar a Capa 1.

TODAS las micro-fases 0.0-0.11 deben estar completadas.

EJECUTAR:
1. Ir al proyecto:
   cd ~/yeyo-os
   source .venv/bin/activate

2. Crear tests/test_capa0_integration.py con TODOS estos tests:

   import subprocess
   import os
   import httpx
   import asyncio
   import asyncpg
   import redis
   from dotenv import load_dotenv
   
   load_dotenv()
   
   # === BTRFS (0.0) ===
   def test_btrfs_tools():
       r = subprocess.run(['btrfs', '--version'], capture_output=True)
       assert r.returncode == 0
   
   # === KERNEL (0.1) ===
   def test_gcc_available():
       r = subprocess.run(['gcc', '--version'], capture_output=True)
       assert r.returncode == 0
   
   # === SYSTEMD (0.2) ===
   def test_systemd_is_pid1():
       r = subprocess.run(['ps', '-p', '1', '-o', 'comm='], capture_output=True, text=True)
       assert 'systemd' in r.stdout.strip()
   
   # === POSTGRESQL (0.3) ===
   def test_postgresql_running():
       r = subprocess.run(['systemctl', 'is-active', 'postgresql'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_postgresql_connection():
       async def _test():
           conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
           result = await conn.fetchval('SELECT 1')
           await conn.close()
           assert result == 1
       asyncio.run(_test())
   
   def test_pgvector_loaded():
       async def _test():
           conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
           result = await conn.fetchval("SELECT COUNT(*) FROM pg_extension WHERE extname='vector'")
           await conn.close()
           assert result == 1
       asyncio.run(_test())
   
   # === REDIS (0.4) ===
   def test_redis_running():
       r = subprocess.run(['systemctl', 'is-active', 'redis-server'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_redis_connection():
       url = os.getenv('REDIS_URL')
       r = redis.from_url(url)
       assert r.ping() == True
   
   # === NODE.JS (0.5) ===
   def test_node_version():
       r = subprocess.run(['node', '--version'], capture_output=True, text=True)
       assert r.stdout.strip().startswith('v20')
   
   def test_nextjs_builds():
       r = subprocess.run(['pnpm', 'build'], capture_output=True, cwd='frontend')
       assert r.returncode == 0
   
   # === PYTHON (0.6) ===
   def test_python_version():
       import sys
       assert sys.version_info[:2] == (3, 11)
   
   def test_all_imports():
       import asyncpg, redis, aiohttp, pydantic, sentence_transformers
       assert True
   
   # === RUST (0.7) ===
   def test_rust_installed():
       r = subprocess.run(['rustc', '--version'], capture_output=True)
       assert r.returncode == 0
   
   def test_rust_workspace_builds():
       r = subprocess.run(['cargo', 'build'], capture_output=True, cwd='rust')
       assert r.returncode == 0
   
   # === OLLAMA (0.8) ===
   def test_ollama_running():
       r = subprocess.run(['systemctl', 'is-active', 'ollama'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_ollama_api():
       r = httpx.get(f"{os.getenv('OLLAMA_HOST')}/api/tags")
       assert r.status_code == 200
   
   def test_ollama_inference():
       r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/generate", json={
           "model": os.getenv('OLLAMA_MODEL'),
           "prompt": "Say OK",
           "stream": False
       }, timeout=60)
       assert r.status_code == 200
       assert len(r.json()["response"]) > 0
   
   # === PODMAN (0.9) ===
   def test_podman_installed():
       r = subprocess.run(['podman', '--version'], capture_output=True)
       assert r.returncode == 0
   
   def test_podman_runs_container():
       r = subprocess.run(['podman', 'run', '--rm', 'alpine', 'echo', 'OK'], capture_output=True, text=True)
       assert 'OK' in r.stdout
   
   # === GPU (0.10) ===
   def test_nvidia_smi():
       r = subprocess.run(['nvidia-smi'], capture_output=True)
       assert r.returncode == 0
   
   def test_cuda_available():
       r = subprocess.run(['nvcc', '--version'], capture_output=True)
       assert r.returncode == 0
   
   # === SECURITY (0.11) ===
   def test_env_protected():
       mode = oct(os.stat('.env').st_mode)[-3:]
       assert mode == '600'
   
   def test_auditd_running():
       r = subprocess.run(['systemctl', 'is-active', 'auditd'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_firewall_active():
       r = subprocess.run(['sudo', 'ufw', 'status'], capture_output=True, text=True)
       assert 'active' in r.stdout.lower()

3. Ejecutar TODA la suite:
   pytest tests/test_capa0_integration.py -v --tb=short

4. Si algún test falla, diagnosticar y corregir ANTES de avanzar.

VERIFICAR:
- [ ] TODOS los tests pasan: pytest output muestra 0 failed
- [ ] Total tests: 25 tests
- [ ] Ningún servicio crasheó durante la ejecución
- [ ] Tiempo total <2 minutos

RESULTADO ESPERADO:
tests/test_capa0_integration.py::test_btrfs_tools PASSED
tests/test_capa0_integration.py::test_gcc_available PASSED
tests/test_capa0_integration.py::test_systemd_is_pid1 PASSED
tests/test_capa0_integration.py::test_postgresql_running PASSED
tests/test_capa0_integration.py::test_postgresql_connection PASSED
tests/test_capa0_integration.py::test_pgvector_loaded PASSED
tests/test_capa0_integration.py::test_redis_running PASSED
tests/test_capa0_integration.py::test_redis_connection PASSED
tests/test_capa0_integration.py::test_node_version PASSED
tests/test_capa0_integration.py::test_nextjs_builds PASSED
tests/test_capa0_integration.py::test_python_version PASSED
tests/test_capa0_integration.py::test_all_imports PASSED
tests/test_capa0_integration.py::test_rust_installed PASSED
tests/test_capa0_integration.py::test_rust_workspace_builds PASSED
tests/test_capa0_integration.py::test_ollama_running PASSED
tests/test_capa0_integration.py::test_ollama_api PASSED
tests/test_capa0_integration.py::test_ollama_inference PASSED
tests/test_capa0_integration.py::test_podman_installed PASSED
tests/test_capa0_integration.py::test_podman_runs_container PASSED
tests/test_capa0_integration.py::test_nvidia_smi PASSED
tests/test_capa0_integration.py::test_cuda_available PASSED
tests/test_capa0_integration.py::test_env_protected PASSED
tests/test_capa0_integration.py::test_auditd_running PASSED
tests/test_capa0_integration.py::test_firewall_active PASSED

========================= 25 passed in Xs =========================

🚪 GATE FINAL CAPA 0: 25/25 tests passing. Todos los cimientos instalados y funcionando. LISTO PARA CAPA 1.
```

---

# 📊 RESUMEN CAPA 0

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 0.0 Btrfs | 1 | CLI | ⬜ |
| 0.1 Kernel | 1 | CLI | ⬜ |
| 0.2 Systemd | 1 | CLI | ⬜ |
| 0.3 PostgreSQL | 2 | CLI | ⬜ |
| 0.4 Redis | 1 | CLI | ⬜ |
| 0.5 Node.js | 2 | CLI+VSCODE | ⬜ |
| 0.6 Python | 1 | CLI | ⬜ |
| 0.7 Rust | 1 | CLI | ⬜ |
| 0.8 Ollama | 2 | CLI | ⬜ |
| 0.9 Podman | 1 | CLI | ⬜ |
| 0.10 GPU | 2 | CLI | ⬜ |
| 0.11 Security | 2 | CLI | ⬜ |
| 0.12 Integration | 1 | CLI | ⬜ |
| **TOTAL** | **18** | **16 CLI + 1 VSCODE + 1 MIXTA** | |
