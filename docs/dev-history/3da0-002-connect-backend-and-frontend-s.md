<overview>
The user (Diego/Yeyo) is building YeyoOS, an AI-native operating system with a layered architecture (Capas 0-7). This session focused on connecting the backend services (PostgreSQL, Redis, Ollama with qwen2.5-coder:7b) to the FastAPI app, then wiring the frontend (Next.js) to the backend. The project lives in two repos: `yeyo-os` (the OS) and `YEYO-IA` (a Rails app for WhatsApp AI). Previous work had formalized Capa 4 (Sistema Nervioso) with bug fixes and 326 tests passing.
</overview>

<history>
1. User asked to connect the backend services
   - Audited all source files: main.py, routes (chat, memory, packages, tts), services (ChatService, ContextualChatService, ConversationManager, FeedbackService, FlashMemory, AssociationEngine, EmbeddingService), factory, health, config
   - Found main.py only registered tts_router; chat/memory/packages routers were not wired
   - Found chat/memory routes used placeholder dependency injection (returning 503)
   - Discovered no .env file existed, no database created

2. User confirmed downloading qwen2.5-coder:7b model themselves
   - Model successfully downloaded (4.7GB, confirmed via `ollama list`)

3. Connected the full backend
   - Installed Python packages: asyncpg, redis, numpy, pydantic-settings, uvicorn
   - Installed pgvector via brew (landed on PG17, but Mac runs PG14 — pgvector incompatible)
   - Created `yeyoos` PostgreSQL database with all 7 tables (without pgvector, using TEXT for embeddings)
   - Created `.env` file with database/redis/ollama config
   - Created `OllamaEmbeddingService` — lightweight embedding adapter using Ollama API instead of sentence-transformers
   - Rewrote `main.py` completely to wire all services with lifespan startup/shutdown
   - Fixed import chain issues: sentence-transformers not installed locally, so made imports lazy/resilient in `__init__.py` files for `src/ia`, `src/memory`, `src/chat`
   - Fixed dependency injection: switched from module-level replacement to FastAPI `dependency_overrides`
   - Added fallback in `FlashMemory.search_semantic` for when pgvector is unavailable
   - Tested all endpoints: health ✅, status ✅, chat ✅, streaming ✅, conversations ✅, memory stats ✅, packages ✅
   - All 297 existing unit tests still passing

4. Connected frontend to backend
   - Added proxy rewrites in `next.config.ts`: `/api/*` → `http://localhost:8000/api/*`
   - Fixed SSE streaming parser in `ChatPanel.tsx` — was reading raw bytes, now properly parses `data: chunk\n\n` format
   - Verified proxy works: requests through `:3000` correctly reach backend at `:8000`

5. Fixed frontend interactivity issues
   - User reported buttons not working in the Hub
   - Found `abrirNodo` function filtered only 4 workspace types (imagen, video, codigo, automacion) — chat and memoria were ignored
   - Added chat/memoria node handlers that open `ChatPanel` via `useChatStore.getState().setPanelOpen(true)`
   - Mounted `ChatPanel` component in `HubPrincipal`
   - Imported `useChatStore` and `ChatPanel` in `page.tsx`

6. User had first conversation with YeyoOS — Mac nearly overheated
   - Added `num_predict: 512` to all three Ollama methods (generate, chat, chat_stream) to limit response length
   - Updated system prompts in both `contextual_service.py` and `service.py` to be concise and honest about capabilities
   - New prompt tells the AI about its real nodos and enforces 3-4 sentence limit
   - Tested: responses now concise and formatted with real node information
</history>

<work_done>
Files created:
- `src/ia/ollama_embeddings.py`: Lightweight embedding service using Ollama /api/embed API (replaces sentence-transformers dependency)
- `.env`: Local development config (DATABASE_URL, REDIS_URL, OLLAMA_HOST, OLLAMA_MODEL=qwen2.5-coder:7b)

Files modified:
- `src/api/main.py`: Complete rewrite — connects PostgreSQL, Ollama, Redis; registers all routers (chat, memory, packages, tts); lifespan startup/shutdown; real health checks; dependency_overrides for DI; WebSocket connected to chat service
- `src/ia/ollama_provider.py`: Added `num_predict: 512` to generate(), chat(), and chat_stream() options
- `src/ia/__init__.py`: Made imports of EmbeddingService, AntiHallucination, RAGPipeline lazy with try/except (sentence-transformers optional)
- `src/memory/__init__.py`: Made AssociationEngine import lazy with try/except
- `src/memory/flash_memory.py`: Added try/except fallback in `search_semantic()` for when pgvector is unavailable
- `src/chat/__init__.py`: Made ContextualChatService import lazy with try/except
- `src/chat/contextual_service.py`: Removed hard dependency on `EmbeddingService` type hint; updated system prompt with real node info and conciseness rules
- `src/chat/service.py`: Updated DEFAULT_SYSTEM_PROMPT with real node info and conciseness
- `frontend/next.config.ts`: Added rewrites proxy `/api/*` → `http://localhost:8000/api/*`
- `frontend/src/components/chat/ChatPanel.tsx`: Fixed SSE streaming parser to handle `data: chunk\n\n` format
- `frontend/src/app/page.tsx`: Added ChatPanel mount, imported useChatStore, wired chat/memoria nodes to open ChatPanel

Database created:
- PostgreSQL database `yeyoos` with 7 tables: flash_memories, memory_associations, memory_audit_log, conversations, conversation_messages, feedback, _yeyo_meta
- All triggers working (prevent_memory_delete, auto_checksum, auto_update_timestamp, update_conversation_on_message)

Commits pushed to origin/main:
1. `cd6d948` - feat: conectar backend — PostgreSQL + Ollama (qwen2.5-coder:7b) + Redis
2. `5fe633e` - feat: conectar frontend con backend — proxy + SSE streaming
3. `f623d4f` - feat: conectar nodos Chat y Memoria al ChatPanel
4. `d5e2ff6` - perf: limitar tokens y mejorar system prompt

Current state:
- Backend fully operational on :8000 (PostgreSQL ✅, Ollama ✅, Redis ✅)
- Frontend on :3000 proxying to backend ✅
- Chat working end-to-end with streaming SSE ✅
- Conversations persisted in PostgreSQL ✅
- 297 unit tests passing ✅
- 3 pre-existing frontend test failures (jsdom scrollIntoView issue, unrelated to our changes)
</work_done>

<technical_details>
### Architecture
- YeyoOS uses hexagonal architecture with generic interfaces (IAProvider, MemoriaProvider)
- 8 layers (Capas 0-7): Cimientos → Esqueleto → Cerebro → Cuerpo → Sistema Nervioso → Órganos → Sistema Inmune → Evolución
- Flash Memory NEVER deletes — only changes temperature (HOT/WARM/COLD)
- Kill Switch Ctrl+Alt+K is sacred

### Python Environment
- System Python is 3.9.6 — TOO OLD. Always use `python3.11` (`/opt/homebrew/opt/python@3.11/bin/python3.11`)
- Installed via pip3.11: pytest, pytest-asyncio, pydantic, pydantic-settings, aiosqlite, PyYAML, fastapi, httpx, python-multipart, asyncpg, redis, numpy, uvicorn
- `sentence-transformers` is NOT installed — all imports made resilient with try/except
- `asyncpg` IS now installed (was missing before)
- No virtual environment — packages installed globally for python3.11

### PostgreSQL
- Running PG14 on Mac (`/opt/homebrew/opt/postgresql@14`)
- `psql` points to PG16 client (`/opt/homebrew/opt/postgresql@16/bin/psql`) but connects to PG14 server
- pgvector installed via brew but only for PG17/PG18 — NOT compatible with running PG14
- Workaround: embedding column is TEXT instead of vector(384); `search_semantic()` has fallback that returns recent memories when pgvector query fails
- Database `yeyoos` owned by user `eltitoyeyo` (no password needed for local connections)
- Connection URL: `postgresql://eltitoyeyo@localhost:5432/yeyoos`

### Ollama
- Model: `qwen2.5-coder:7b` (4.7GB) — heavy on MacBook Air, causes CPU spike
- `num_predict: 512` added to all methods to limit response tokens
- Embedding model also set to `qwen2.5-coder:7b` (same model for both chat and embeddings)
- Host: `http://localhost:11434`

### FastAPI Dependency Injection
- Initial attempt to inject by replacing module-level functions (chat_mod.get_chat_service = ...) FAILED — FastAPI captures original function references at import time
- Solution: use `app.dependency_overrides[original_function] = replacement_function` — this is the correct FastAPI pattern

### Frontend
- Next.js 16.2.1 with Turbopack on port 3000
- Proxy via `rewrites()` in next.config.ts routes `/api/*` to backend at `:8000`
- ChatPanel uses streaming SSE — reads `data: chunk\n\n` format from FastAPI StreamingResponse
- Chat opens via sidebar click or Ctrl+Space (MiniChat)
- Onboarding uses `speechSynthesis` browser API for TTS (not the /api/tts endpoint)
- Pre-existing test failures: ChatPanel (scrollIntoView jsdom), AppLayout, OnboardingScreen — NOT caused by our changes

### Git
- Stashed change still exists: `prompts/capa0/prompt-0.11-2.md` (user's local edit, recoverable with `git stash pop`)

### Running the System
```bash
# Terminal 1 — Backend
cd ~/YEYO/yeyo-os && python3.11 -m uvicorn src.api.main:app --port 8000

# Terminal 2 — Frontend
cd ~/YEYO/yeyo-os/frontend && npm run dev
```
- Backend may already be running as detached process; check with `lsof -ti:8000`
- Frontend may also be detached; check with `lsof -ti:3000`
</technical_details>

<important_files>
- `/Users/eltitoyeyo/YEYO/yeyo-os/src/api/main.py`
   - Central FastAPI app — COMPLETELY REWRITTEN to wire all services
   - Lifespan connects PostgreSQL, Ollama, Redis; initializes all services
   - `_wire_dependencies()` uses `app.dependency_overrides` for DI
   - Registers 4 routers: tts, chat, memory, packages
   - WebSocket endpoint connected to chat service
   - Real health check in `/api/v1/status`

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/ia/ollama_provider.py`
   - Ollama adapter implementing IAProvider interface
   - Added `num_predict: 512` to all three methods (generate, chat, chat_stream)
   - Uses httpx async client

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/ia/ollama_embeddings.py`
   - NEW FILE — lightweight embedding service using Ollama /api/embed
   - Drop-in replacement for EmbeddingService (duck typing compatible)
   - Uses synchronous httpx client
   - Auto-detects embedding dimension on first call

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/chat/contextual_service.py`
   - Chat with memory context — builds enriched prompts with Flash Memory
   - Removed hard `EmbeddingService` type import; accepts any embeddings duck type
   - Updated DEFAULT_SYSTEM_PROMPT with real nodo info and conciseness rules (line ~34)

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/chat/service.py`
   - Basic chat service (fallback when ContextualChatService unavailable)
   - Updated DEFAULT_SYSTEM_PROMPT (line ~16)

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/memory/flash_memory.py`
   - Flash Memory implementation with PostgreSQL
   - `search_semantic()` has try/except fallback for missing pgvector (line ~161)

- `/Users/eltitoyeyo/YEYO/yeyo-os/.env`
   - Local dev config — DATABASE_URL, REDIS_URL, OLLAMA_HOST, OLLAMA_MODEL=qwen2.5-coder:7b
   - In .gitignore (not committed)

- `/Users/eltitoyeyo/YEYO/yeyo-os/frontend/next.config.ts`
   - Added proxy rewrites for `/api/*` and `/health` to backend at :8000

- `/Users/eltitoyeyo/YEYO/yeyo-os/frontend/src/components/chat/ChatPanel.tsx`
   - Fixed SSE streaming parser (lines ~149-170) to parse `data: chunk\n\n` format

- `/Users/eltitoyeyo/YEYO/yeyo-os/frontend/src/app/page.tsx`
   - Main page — added ChatPanel mount, chat/memoria node handlers
   - Imported useChatStore and ChatPanel
   - `abrirNodo` now handles 'chat' and 'memoria' nodeIds (lines ~92-100)

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/ia/__init__.py`
   - Made all heavy imports lazy (EmbeddingService, AntiHallucination, RAGPipeline)

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/memory/__init__.py`
   - Made AssociationEngine import lazy

- `/Users/eltitoyeyo/YEYO/yeyo-os/src/chat/__init__.py`
   - Made ContextualChatService import lazy
</important_files>

<next_steps>
Remaining work:
- Install pgvector for PG14 (or upgrade to PG17) for real semantic search — currently using fallback
- Install sentence-transformers for proper CPU embeddings (currently using Ollama for embeddings which is heavier)
- Connect WebSocket in frontend components (configured in websocket.ts but not instantiated)
- Build Memory UI (currently memoria node just opens ChatPanel as placeholder)
- Capa 5 (Órganos) — specialized node implementations
- Capa 6 (Sistema Inmune) — security hardening
- Capa 7 (Evolución) — LoRA, Store, ISO

Open questions:
- User may want to explore connecting the frontend more (Memory dashboard, etc.)
- Podman vs Docker: docs say "Podman ALWAYS" but Mac has Docker — acceptable for dev?
- Git stash with `prompts/capa0/prompt-0.11-2.md` still pending

Detached processes that may still be running:
- Backend uvicorn on :8000 (check: `lsof -ti:8000`)
- Frontend next dev on :3000 (check: `lsof -ti:3000`)
</next_steps>