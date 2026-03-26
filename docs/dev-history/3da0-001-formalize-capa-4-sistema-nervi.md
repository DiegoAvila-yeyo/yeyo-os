<overview>
The user (Diego/Yeyo) is building YeyoOS, an AI-native operating system with a layered architecture (Capas 0-7). The project lives in two repos: `yeyo-os` (the OS itself) and `YEYO-IA` (a Rails app for WhatsApp AI). My role has been to pull latest changes, audit the codebase, formalize Capa 4 (Sistema Nervioso) by fixing bugs and connecting services, and advise on AI model selection. The project uses Python/FastAPI backend, Next.js/TypeScript frontend, and Rust stubs for Guardian/Compositor.
</overview>

<history>
1. User asked to pull changes and get up to speed with yeyo-os repo
   - Found repo at `/Users/eltitoyeyo/YEYO/yeyo-os`
   - Fixed git ref lock error (`cannot lock ref 'refs/remotes/origin/main'`) by running `git gc --prune=now && git remote prune origin`
   - Had to `git stash` local changes in `prompts/capa0/prompt-0.11-2.md` to allow merge
   - Successfully pulled 40+ new commits (Capas 0-3 fully implemented)
   - Read all 14 docs, 127+ prompt files across 8 capas, and explored full codebase

2. User asked for current build status assessment
   - Audited all code: ~9,500 LOC Python backend, ~9,800 LOC frontend, ~10,400 LOC tests
   - Found Capas 0-3 complete with tests; Capa 4 code existed but was committed under "Capa 3 completa"
   - Capas 5-7 only exist as prompts; Rust files are `Hello, world!` stubs
   - Identified 2 unit test failures and several issues in Capa 4 code

3. User asked to complete and formalize Capa 4
   - Read all 26 Capa 4 prompts to understand requirements
   - Ran all existing tests: 282 unit passed (2 failed), 29 integration passed
   - Fixed 5 issues (detailed in work_done)
   - All 326 tests passing after fixes
   - Committed, cleaned `__pycache__` from git, pushed to remote

4. User asked about backend connectivity status
   - Discovered `main.py` only registers TTS router; chat/memory/packages routers not wired
   - Chat and Memory endpoints use placeholder dependency injection (return 503)
   - Packages API was using in-memory dicts (fixed to use real services)

5. User asked why services aren't connected / if Mac can run them
   - Checked Mac environment: PostgreSQL 16 ✅, Redis ✅ (PONG), Ollama 0.18 ✅, Docker ✅
   - Everything is available — just never wired together in `main.py`

6. User discussed replacing Ollama with code-specialized AI
   - Recommended **Qwen2.5-Coder** over CodeLlama (128K context, tool calling, modern training)
   - Recommended 7B variant for MacBook Air (~4.7GB)
   - Started background download: `nohup ollama pull qwen2.5-coder:7b > /tmp/ollama-pull.log 2>&1 &` (PID: 46766)
   - Download was still in progress when conversation ended
</history>

<work_done>
Files updated in yeyo-os:
- `src/orquestador/grafo.py`: Fixed retry logic — generic `Exception` now retries instead of breaking (line ~237-239)
- `src/orquestador/grafos/hacer_reel.py`: Moved `_rama_imagenes_mapped` function before its usage (was defined after line 124 where it was called)
- `src/api/routes/packages.py`: Complete rewrite — replaced in-memory dicts with real `PackageInstaller` + `PermissionManager` services, added `init_package_services()` function, proper error handling with specific HTTP codes (403/422/400)
- `tests/unit/pkg/test_installer.py`: Added `permissions: [memory.read, gpu.inference]` to fake ypkg manifest so permission callback actually triggers
- `tests/unit/api/test_packages_api.py`: Updated fixtures to use real `PackageInstaller` in temp dirs and `PermissionManager`, removed old `_installed_packages` dict references
- `.gitignore`: Added `__pycache__/`, `*.pyc`, `*.pyo`, `.pytest_cache/`, `node_modules/`
- Removed 208 `__pycache__` files from git tracking

Commits pushed to origin/main:
1. `da9faba` - feat(capa4): formalizar Sistema Nervioso — 326 tests passing
2. `3f69aa9` - chore: gitignore __pycache__ y limpiar archivos cacheados
3. `38d44ca` - chore: eliminar __pycache__ del tracking de git

Work completed:
- [x] Pull latest changes and resolve git conflicts
- [x] Full codebase audit (all capas)
- [x] Fix 2 failing unit tests (installer permissions, grafo retry)
- [x] Fix hacer_reel.py function ordering bug
- [x] Rewrite packages API to use real services
- [x] Update API tests for new implementation
- [x] Clean __pycache__ from git
- [x] Push all changes to remote
- [ ] Qwen2.5-coder:7b download (in background, PID 46766)
- [ ] Wire backend services (PostgreSQL/Redis/Ollama) to FastAPI main.py
</work_done>

<technical_details>
### Architecture
- YeyoOS uses **hexagonal architecture** with generic interfaces (`IAProvider`, `MemoriaProvider`, `Orquestador`) — swap any provider by changing config
- 8 layers (Capas 0-7): Cimientos → Esqueleto → Cerebro → Cuerpo → Sistema Nervioso → Órganos → Sistema Inmune → Evolución
- Flash Memory **NEVER deletes** — only changes temperature (HOT/WARM/COLD)
- Kill Switch `Ctrl+Alt+K` is sacred — must work even if UI is broken
- **Podman ALWAYS, Docker NEVER** (per security docs, though Docker is what's installed on the Mac)

### Python Environment
- System Python is 3.9.6 (`/usr/bin/python3`) — too old, many imports fail
- **Use `python3.11`** (`/opt/homebrew/opt/python@3.11/bin/python3.11`) for all test runs
- Installed via pip for python3.11: pytest, pytest-asyncio, pydantic, aiosqlite, PyYAML, fastapi, httpx, python-multipart
- `asyncpg` is NOT installed — Capa 0-2 tests that depend on it will fail with import errors (not our problem)
- `requirements.txt` lists torch, CUDA bindings, etc. — these are for the Linux target, not Mac dev

### Test Running
- Capa 4 tests: `python3.11 -m pytest tests/unit/pkg/ tests/unit/security/ tests/unit/pipeline/ tests/unit/orquestador/ tests/unit/api/test_packages_api.py tests/integration/test_capa4_integration.py tests/integration/test_capa4_orquestador_integration.py`
- Running ALL unit tests fails because Capa 0-2 tests import `asyncpg` which isn't installed locally — scope test runs to relevant capas only

### Key Bug Fixes
- `grafo.py` retry: The `except Exception` block was doing `break` which meant generic errors (like `ValueError`) would NOT retry even with `max_intentos=3`. Changed to continue the loop with backoff.
- `hacer_reel.py`: Python function `_rama_imagenes_mapped` was defined AFTER being referenced in the `YeyoGrafo` builder chain. Moved to top of file.
- `test_installer.py`: The fake ypkg manifest had no `permissions` field, so `_check_permissions()` returned early without calling the deny callback, making the "permission denied" test always pass incorrectly.

### Backend Wiring Status
- `src/api/main.py` only registers `tts_router` — chat, memory, and packages routers are NOT included
- Chat/Memory routes use FastAPI `Depends()` with placeholder functions that raise 503
- Packages route now has `init_package_services()` that accepts real services

### Mac Environment
- PostgreSQL 16: running on port 5432 (accepting connections)
- Redis: running (responds PONG)
- Ollama 0.18: running on localhost:11434
- Docker 29.2.1: available (note: docs say "Podman ALWAYS" but Mac has Docker)
- No virtual environment set up in the project

### Git Stash
- There's a stashed change: `prompts/capa0/prompt-0.11-2.md` — user's local edit. Recoverable with `git stash pop`.

### Model Decision
- User chose **Qwen2.5-Coder:7b** over CodeLlama for code generation
- Reasons: 128K context, native tool calling, modern training data, better reasoning
- Download in progress to `/tmp/ollama-pull.log`
</technical_details>

<important_files>
- `/Users/eltitoyeyo/YEYO/yeyo-os/src/api/main.py`
   - FastAPI app entry point — NEEDS WIRING to connect all routers and services
   - Currently only registers tts_router; chat/memory/packages routers missing
   - Lines 82-87: where routers are imported/registered

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/api/routes/packages.py`
   - Package management REST API — REWRITTEN to use real services
   - `init_package_services()` function (line ~33) for dependency injection
   - Uses `PackageInstaller`, `PermissionManager` from src/pkg and src/security

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/orquestador/grafo.py`
   - YeyoGrafo graph executor — FIXED retry logic at lines ~237-239
   - Core of the orchestration system

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/orquestador/grafos/hacer_reel.py`
   - Multi-node graph example — FIXED function ordering
   - `_rama_imagenes_mapped` moved to top of file

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/ia/interfaces.py`
   - `IAProvider` abstract class — the interface that allows swapping AI providers
   - Methods: `generate()`, `chat()`, `chat_stream()`

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/ia/ollama_provider.py`
   - Current Ollama implementation of IAProvider
   - Will need config update for qwen2.5-coder:7b model

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/core/config.py`
   - Central configuration — where model name and service URLs are defined

- `/Users/eltitoyeyo/YEYO/yeyo-os/prompts/capa4/README.md`
   - Capa 4 prompt index — 26 prompts across 24 micro-phases, all implemented

- `/Users/eltitoyeyo/YEYO/yeyo-os/.gitignore`
   - Updated to exclude __pycache__, .pyc, .pytest_cache, node_modules
</important_files>

<next_steps>
Remaining work:
- Qwen2.5-coder:7b download completing in background (check: `cat /tmp/ollama-pull.log` or `ollama list`)
- Wire backend services in `main.py`: register all routers (chat, memory, packages), initialize real services (PostgreSQL, Redis, Ollama) with dependency injection
- Configure OllamaProvider to use `qwen2.5-coder:7b` model
- Potentially set up a Python virtual environment for the project
- Capa 5 (Órganos) — specialized node implementations (next major layer)

Immediate next steps:
1. Check if `ollama pull qwen2.5-coder:7b` completed (PID 46766, log at `/tmp/ollama-pull.log`)
2. Connect backend: update `main.py` to register chat, memory, packages routers and wire real services
3. Test the full backend with `uvicorn` running against real PostgreSQL/Redis/Ollama
4. User may want to proceed with Capa 5 or continue backend wiring

Open questions:
- Does the user want a Python venv set up for the project?
- The docs say "Podman ALWAYS, Docker NEVER" but Mac has Docker — is this acceptable for dev?
- Git stash with `prompts/capa0/prompt-0.11-2.md` changes still pending
</next_steps>