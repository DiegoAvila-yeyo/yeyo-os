# YeyoOS Setup Guide

Complete setup guide for the new YeyoOS features: **Workflow Orchestrator**, **Observatory**, and **Arena**.

---

## 1. Environment Variables

All required environment variables with descriptions and where to obtain API keys:

| Variable | Description | Where to get |
|----------|-------------|--------------|
| `REPLICATE_API_TOKEN` | Replicate API for video generation | https://replicate.com/account/api-tokens |
| `FAL_KEY` | Fal.ai API for image generation | https://fal.ai/dashboard/keys |
| `SUPABASE_URL` | Supabase project URL | https://supabase.com/dashboard/project/_/settings/api |
| `SUPABASE_KEY` | Supabase anon/service key | Same as above |
| `OLLAMA_HOST` | Ollama server URL (default `localhost:11434`) | Install from https://ollama.ai |
| `DATABASE_URL` | PostgreSQL connection string | Local: `postgres://user:pass@localhost:5432/yeyoos` |
| `REDIS_URL` | Redis connection string | Local: `redis://localhost:6379` |

### Example `.env`

```env
REPLICATE_API_TOKEN=r8_xxxxx
FAL_KEY=xxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=xxxxx
OLLAMA_HOST=http://localhost:11434
DATABASE_URL=postgres://yeyo:yeyo@localhost:5432/yeyoos
REDIS_URL=redis://localhost:6379
```

Copy the example above into a `.env` file at the repository root and fill in your actual values.

---

## 2. Quick Start Commands

### Backend

```bash
cd /path/to/yeyo-os
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migration
psql $DATABASE_URL < scripts/workflow_migration.sql

# Start backend
uvicorn src.api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

The frontend runs on `http://localhost:3000` and the backend on `http://localhost:8000`.

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 3. New Dependencies

### Python (pip)

| Package | Purpose | Status |
|---------|---------|--------|
| `httpx` | Async HTTP client for workflow handlers | Already in `requirements.txt` |
| `uvicorn` | ASGI server | Already in `requirements.txt` |
| `fastapi` | API framework | Already in `requirements.txt` |
| `redis` | Redis client for job queue | Already in `requirements.txt` |
| `psycopg2-binary` | PostgreSQL driver | Already in `requirements.txt` |

No new pip packages are required — all dependencies are already in `requirements.txt`.

### Node.js (pnpm)

No new npm packages are required — all frontend dependencies are already installed.

---

## 4. Sprite Structure

The sprite assets are organized under `frontend/public/sprites/`:

```
frontend/public/sprites/
├── characters/         # 10 character sprite sets
│   ├── miner/         # Each has: Walk.png, Idle.png, Attack.png, Dead.png, etc.
│   ├── scientist/
│   ├── tester/
│   ├── writer/
│   ├── optimizer/
│   ├── guard/
│   ├── sage/
│   ├── yeyohack/
│   ├── guardian/
│   └── robot/
├── tiles/             # 134 individual tiles + tilemap sheets
├── effects/           # Battle effects (slash, shield, spark, etc.)
└── ui/                # 30 emote PNGs (emote1.png - emote30.png)
```

### Sprite Format Details

| File | Dimensions | Layout | Frame Size |
|------|-----------|--------|------------|
| `Walk.png` | 64×64 px | 4 columns (frames) × 4 rows (down/left/right/up) | 16×16 px per frame |
| `Idle.png` | 64×16 px | 4 frames horizontal | 16×16 px per frame |
| `Attack.png` | 64×64 px | 4 columns × 4 rows | 16×16 px per frame |
| `Dead.png` | 64×16 px | 4 frames horizontal | 16×16 px per frame |

**Walk.png row order**: Row 0 = facing down, Row 1 = facing left, Row 2 = facing right, Row 3 = facing up.

---

## 5. API Endpoints Reference

### Workflow Orchestrator

Prefix: `/api/v1/yeyonet`  
Core service: `JobOrchestrator` (`src/yeyonet/job_orchestrator.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/yeyonet/jobs` | Create a new job. Types: `image_generate`, `video_render`, `text_inference`, `training_step`, `memory_sync`, `custom` |
| POST | `/api/v1/yeyonet/jobs/distributed` | Create a distributed job with multiple items (render farm style) |
| GET | `/api/v1/yeyonet/jobs` | List jobs with optional filters (`?status=queued&type=image_generate&limit=50`) |
| GET | `/api/v1/yeyonet/jobs/stats` | Get queue statistics (total, by status, by type, processing time) |
| GET | `/api/v1/yeyonet/jobs/{job_id}` | Get detailed status and result of a specific job |
| GET | `/api/v1/yeyonet/jobs/{job_id}/results` | Get sub-results of a distributed job |
| DELETE | `/api/v1/yeyonet/jobs/{job_id}` | Cancel a job if not yet completed |
| POST | `/api/v1/yeyonet/invite` | Create invitation code for satellite node |
| GET | `/api/v1/yeyonet/invitations` | List active invitations |
| DELETE | `/api/v1/yeyonet/invitations/{invitation_id}` | Delete an invitation |
| POST | `/api/v1/yeyonet/register` | Register satellite node |
| GET | `/api/v1/yeyonet/satellites` | List satellite nodes |
| GET | `/api/v1/yeyonet/satellites/{node_id}` | Get satellite details |
| PUT | `/api/v1/yeyonet/satellites/{node_id}` | Update satellite configuration |
| DELETE | `/api/v1/yeyonet/satellites/{node_id}` | Remove satellite |
| GET | `/api/v1/yeyonet/identity` | Get node identity |
| POST | `/api/v1/yeyonet/sync/trigger/{node_id}` | Force memory sync to satellite |
| POST | `/api/v1/yeyonet/sync/training-corpus/{node_id}` | Share training data with satellite |
| POST | `/api/v1/yeyonet/connect` | Connect as satellite to Central |
| POST | `/api/v1/yeyonet/disconnect` | Disconnect from Central |
| GET | `/api/v1/yeyonet/connection` | Get connection status |
| WebSocket | `/ws/yeyonet` | Real-time satellite/central communication relay |

**Job states**: `queued` → `assigned` → `processing` → `completed` / `failed`  
**Priority**: 1–10 (default 5)  
**Timeout**: Default 600 seconds

### Observatory

Monitoring, health, and real-time system visibility.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check (`{status, version, uptime_seconds}`) |
| GET | `/api/v1/status` | Detailed status with real service verification (API, PostgreSQL, Ollama, Redis, GPU) |
| GET | `/api/v1/yeyonet/stats` | Network statistics (satellites, node count, resources) |
| GET | `/api/v1/yeyonet/sync/stats` | Synchronization statistics (push/pull counts, last sync) |
| GET | `/api/v1/cloud-sync/status` | Cloud sync configuration & running status (Supabase) |
| GET | `/api/v1/cloud-sync/stats` | Detailed sync statistics (synced, failed, retry counts) |
| POST | `/api/v1/cloud-sync/force` | Trigger manual full sync cycle (push + pull) |
| GET | `/api/v1/memory/stats` | Memory statistics: total, by tier, by type, associations |
| GET | `/api/v1/memory/map/distribution` | Memory distribution across tiers |
| GET | `/api/v1/memory/map/pipeline` | Pipeline event memory mapping |
| GET | `/api/v1/memory/debug/hot` | Debug: hot tier memories (recently accessed) |
| GET | `/api/v1/memory/debug/recent` | Debug: recently accessed memories |
| GET | `/api/v1/memory/debug/context` | Debug: context memories |
| GET | `/api/v1/memory/debug/audit` | Debug: audit log of memory operations |
| GET | `/api/v1/nodes/{node_id}/status` | Get status of a specific node |
| GET | `/api/v1/media/image/status` | Image generation model status (loaded, device, model) |
| GET | `/api/v1/media/image/progress` | Real-time image generation progress (active, step, percent) |
| WebSocket | `/ws/pipeline` | Real-time pipeline events stream |

**Status response levels**: `healthy` / `degraded` / `unhealthy`

### Arena

Red vs Blue security testing system.

| Method | Endpoint | Description |
|--------|----------|-------------|
| WebSocket | `/ws/security` | Real-time permission request/response system |

**WebSocket message types**:

| Direction | Type | Payload |
|-----------|------|---------|
| Frontend → Backend | `permission_response` | `{type, request_id, allowed, remember}` |
| Frontend → Backend | `ping` | Keep-alive |
| Backend → Frontend | `permission_request` | `{type: "permission_request", ...request_details}` |
| Backend → Frontend | `pong` | Keep-alive response |

**Docker Arena** (`src/security/hack/arena.py`):

| Property | Value |
|----------|-------|
| Container name | `yeyo-hack-arena` |
| Network name | `yeyo-hack-net` |
| Backend port | 8001 |
| Redis port | 6380 |
| Timeout | 60 minutes |
| Max rounds | 10 |

The `DockerArena` class provides: `create()`, `destroy()`, `is_running()`, `get_status()`.

### WebSocket Endpoints Summary

| Endpoint | Purpose |
|----------|---------|
| `/ws` | Main chat — real-time chat communication with context |
| `/ws/pipeline` | Pipeline events — real-time pipeline event broadcasting |
| `/ws/yeyonet` | YeyoNet relay — satellite/central communication |
| `/ws/security` | Security events — permission requests/responses (Arena) |
| `/ws/voice` | Voice state — microphone state broadcasting |

---

## 6. Architecture Overview

### How the New Systems Fit Together

```
┌─────────────────────────────────────────────────────┐
│                    YeyoOS Frontend                   │
│              (Next.js @ localhost:3000)               │
│                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │  Workflow UI  │ │  Observatory │ │   Arena UI   │ │
│  │  (pipelines)  │ │  (2D world)  │ │ (red vs blue)│ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
└─────────┼────────────────┼────────────────┼─────────┘
          │ REST + WS      │ REST + WS      │ WS
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────┐
│               YeyoOS Backend (FastAPI)               │
│               (uvicorn @ localhost:8000)              │
│                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │  Workflow     │ │  Resource    │ │  Docker      │ │
│  │  Orchestrator │ │  Monitor     │ │  Arena       │ │
│  │  (job queue)  │ │  (health)    │ │  (sandbox)   │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
└─────────┼────────────────┼────────────────┼─────────┘
          │                │                │
          ▼                ▼                ▼
   ┌────────────┐  ┌────────────┐   ┌────────────┐
   │ PostgreSQL  │  │   Redis    │   │   Docker   │
   │ (jobs, mem) │  │  (queue)   │   │ (isolation)│
   └────────────┘  └────────────┘   └────────────┘
```

- **Workflow Orchestrator**: Internal n8n-like system for chaining YeyoOS nodes. Manages a job queue with priority, resource requirements, and distributed processing across satellite nodes. Job types include image generation, video rendering, text inference, training steps, and memory sync.

- **Observatory**: Real-time 2D visualization of agent activities. Provides health monitoring (API, PostgreSQL, Ollama, Redis, GPU), queue statistics, memory tier distribution, sync metrics, and pipeline event streaming via WebSocket. The frontend renders agents as sprites moving in a 2D world.

- **Arena**: Red vs Blue security testing system. Uses Docker-isolated sandboxes for adversarial testing. A WebSocket-based permission system gates dangerous operations. The `DockerArena` class spins up isolated containers with their own backend and Redis instances.

---

## 7. Troubleshooting

| Problem | Solution |
|---------|----------|
| **"Cannot connect to PostgreSQL"** | Check `DATABASE_URL` is correct. Ensure PostgreSQL is running: `pg_isready` or `brew services start postgresql` |
| **"Ollama not responding"** | Ensure Ollama is running: `ollama serve`. Verify with `curl http://localhost:11434/api/tags` |
| **"Sprites not loading"** | Check `frontend/public/sprites/` directory exists and contains the character/tile/effect assets |
| **"WebSocket connection failed"** | Ensure backend is running on port 8000. Check browser console for CORS errors |
| **"CORS errors"** | Backend has CORS enabled for `http://localhost:3000` by default. If using a different port, update `src/api/main.py` |
| **"No module named 'src.workflows'"** | Run from the repo root directory, not from `src/`. Ensure your virtualenv is activated |
| **"Arena sandbox timeout"** | Increase timeout in `src/arena/sandbox.py` (default 30s). For Docker Arena, default is 60 minutes |
| **"Redis connection refused"** | Start Redis: `redis-server` or `brew services start redis`. Verify with `redis-cli ping` |
| **"GPU not detected"** | Observatory checks `nvidia-smi`. On macOS, MPS (Apple Silicon) is used instead — this is normal |
| **"Job stuck in 'assigned' state"** | Check if the processing node is still alive. Cancel with `DELETE /api/v1/yeyonet/jobs/{job_id}` and re-submit |
| **"Supabase sync failing"** | Verify `SUPABASE_URL` and `SUPABASE_KEY`. Force a sync with `POST /api/v1/cloud-sync/force` |
| **"pnpm: command not found"** | Install pnpm: `npm install -g pnpm` |

### Useful Debug Commands

```bash
# Check all service health at once
curl http://localhost:8000/api/v1/status | python -m json.tool

# Check job queue stats
curl http://localhost:8000/api/v1/yeyonet/jobs/stats | python -m json.tool

# Test WebSocket connection
websocat ws://localhost:8000/ws

# Check Ollama models
curl http://localhost:11434/api/tags

# View memory statistics
curl http://localhost:8000/api/v1/memory/stats | python -m json.tool

# Force cloud sync
curl -X POST http://localhost:8000/api/v1/cloud-sync/force
```
