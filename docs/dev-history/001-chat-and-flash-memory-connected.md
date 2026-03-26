<overview>
The user (Diego) is building YeyoOS — an AI-native fullscreen shell that runs on top of existing operating systems (Mac/Windows/Linux). The project uses FastAPI backend + Next.js frontend + PostgreSQL + Ollama for local AI. The conversation focused on debugging and fixing the image generation feature, then analyzing the full project state, planning the development roadmap, and finally connecting and fixing the Chat system with Flash Memory persistence. The approach was to fix things that exist but are broken/disconnected rather than building new features.
</overview>

<history>
1. **User asked for server startup commands**
   - Identified backend runs via `python src/api/run.py` (uvicorn on port 8000)
   - Frontend runs via `cd frontend && npm run dev` (Next.js on port 3000)

2. **User reported image generation error (Error 500, showed 20 steps instead of 4)**
   - Found TWO bugs: double fetch (ImageNodeLayout + page.tsx both called backend simultaneously) and `steps: 20` hardcoded in page.tsx
   - Fixed: added `pasos` to `ImageOpciones` interface, made page.tsx skip fetch when source=controls

3. **User showed ECONNRESET errors in console**
   - Root cause: Next.js proxy has ~30s timeout; image generation takes 40-60s → ECONNRESET
   - Second root cause: Two concurrent requests to backend caused MPS race condition ("Already borrowed")
   - Fixed: All image generation moved to `ImageNodeLayout` calling `localhost:8000` directly (no proxy)
   - Fixed: Added `threading.Lock()` to `_load_pipeline` AND `_run_inference` in `image_generator.py`

4. **Image generated but appeared black**
   - Root cause: MPS (Apple Silicon) + float16 produces NaN values during SD inference → black image
   - Fixed: Changed `dtype = torch.float32` (removed float16 for MPS) in `image_generator.py`
   - Added numpy clip fallback as secondary defense

5. **User asked for download button and image display fix**
   - Added `⬇` download anchor button on each gallery card (top-right corner)
   - Made image clickable to open in new tab
   - Added numpy clip fix for NaN pixels in backend

6. **Full project analysis requested**
   - Identified all 8 capas (layers) of prompts and cross-referenced with actual code
   - Found ~77% of backend implemented but most nodes have NO frontend connection
   - Only Image node was fully tested and working end-to-end

7. **Planning session**
   - User goal: complete project properly with solid foundations, then share via YeyoNet with friends
   - Recommended order: Fix existing features → robust+secure → YeyoNet distribution
   - Agreed to start with Chat + Flash Memory

8. **Chat system investigation and fixing**
   - Found chat streaming endpoint returns 200 OK but sends no data (silent hang)
   - Root cause: `ChatService.send_message_stream()` signature mismatch — route calls with `conversation_history` kwarg but method didn't accept it
   - Fixed: Added `conversation_history` and `conversation_id` params to both `send_message` and `send_message_stream` in `ChatService`
   - Fixed: `ChatPanel.tsx` changed to call `http://localhost:8000` directly (bypass Next.js proxy timeout)
   - Found Flash Memory was NEVER being populated — `ContextualChatService` searched but never saved memories
   - Fixed: Connected `MemoryExtractor` to `ContextualChatService` — after each response, extracts memorable facts in background task
   - Installed pgvector for PostgreSQL 14 (had to build from source since brew version was for PG17)
   - Enabled `CREATE EXTENSION vector` in yeyoos database
</history>

<work_done>
Files modified:

**Backend:**
- `src/media/image_generator.py`
  - Changed float16→float32 for MPS (fixes black images)
  - Added `threading.Lock()` (`_pipeline_lock`) protecting both `_load_pipeline` and `_run_inference`
  - Added numpy clip fix for NaN pixels post-inference

- `src/chat/service.py`
  - `send_message()`: Added `conversation_history` and `conversation_id` optional params; now includes history in messages sent to Ollama
  - `send_message_stream()`: Same signature fix; now includes history

- `src/chat/contextual_service.py`
  - Added `import asyncio` and `from src.memory.extraction import MemoryExtractor`
  - Added `self._extractor = MemoryExtractor(ia)` in `__init__`
  - Added `_extract_and_store()` async method that extracts memorable facts and stores in Flash Memory
  - Wired `_extract_and_store` into `send_message` (via `asyncio.create_task`)
  - Wired `_extract_and_store` into `send_message_stream` (accumulates full response then creates task)

**Frontend:**
- `frontend/src/components/nodes/ImageNodeLayout.tsx`
  - Added `pasos` to `ImageOpciones` interface
  - `handleGenerar()` now accepts optional `overridePrompt` param
  - `handleChatSend()` now calls `handleGenerar(msg)` directly (chat generates image without going through proxy)
  - Added `onAssistantMessage` prop to notify page.tsx of assistant responses
  - Gallery cards: added download button, image click opens in new tab, added position:relative for overlay

- `frontend/src/components/chat/ChatPanel.tsx`
  - Changed fetch URL from `/api/v1/chat/stream` to `http://localhost:8000/api/v1/chat/stream`

- `frontend/src/app/page.tsx`
  - Removed `generateImage()` function entirely (no longer makes fetch calls)
  - Removed `imageIsGenerating` state (no longer needed)
  - Removed `DEFAULT_IMAGE_OPTIONS`, `parseResolution`, `appendStyle` (dead code)
  - `handleImageGenerate`: now no-op (ImageNodeLayout handles fetch)
  - `handleImageChatSend`: only adds user message to chat store
  - Added `handleImageAssistantMessage`: adds assistant message to chat store
  - `WorkspaceRouter`: removed `isGenerating`/`onImageGenerate` props, added `onAssistantMessage`

**Infrastructure:**
- pgvector built from source and installed for PostgreSQL 14
- `CREATE EXTENSION vector` enabled in yeyoos database

Work completed:
- [x] Image generation working (float32, no proxy, thread-safe)
- [x] Image download button added
- [x] Chat streaming working (signature fix + direct URL)
- [x] Flash Memory extraction connected to chat
- [x] pgvector installed for semantic search
- [ ] User's test: tell name/date → reload → verify memory recalled (pending user action)
- [ ] Restart backend needed to apply all Python changes
</work_done>

<technical_details>
**Image Generation (MPS/Apple Silicon):**
- `float16` on Apple MPS produces NaN tensors during Stable Diffusion inference → all-black images. Must use `float32`
- `torch.float32` is slower (~2x) but produces correct images on M1/M2/M3
- PyTorch MPS does NOT allow concurrent access from multiple threads → "Already borrowed" error
- Solution: single `threading.Lock()` (`_pipeline_lock`) that serializes both model loading AND inference
- The `--reload` flag on uvicorn restarts the server when Python files change, unloading the SD model from memory

**Next.js Proxy Timeout:**
- Next.js `rewrites()` in `next.config.ts` proxies `/api/*` to `localhost:8000`
- This proxy has an internal timeout (~30s) that cannot be configured via rewrites
- Any long-running operation (image generation, chat streaming) MUST call `http://localhost:8000` directly from frontend, NOT via the proxy
- Both `ImageNodeLayout.tsx` and `ChatPanel.tsx` now bypass the proxy

**Double Fetch Bug (resolved):**
- Before fix: `ImageNodeLayout` made fetch AND called `onGenerar` → `page.tsx` made second fetch simultaneously
- Race condition crashed the backend (MPS "Already borrowed")
- Solution: `page.tsx` no longer makes any fetch calls; `ImageNodeLayout` owns all image fetch logic

**Flash Memory Architecture:**
- PostgreSQL tables: `flash_memories`, `conversations`, `conversation_messages`, `feedback`, `memory_associations`
- `flash_memories` has `embedding vector(768)` column — requires pgvector extension
- pgvector was installed for PG17 via brew but server runs PG14 → had to build from source: `PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config make && make install`
- Without pgvector: `search_semantic()` falls back to returning all memories (functional but not semantic)
- `MemoryExtractor` uses Ollama to analyze user+assistant message and extract memorable facts as JSON
- `should_extract()` checks message length before calling Ollama (avoids unnecessary API calls)
- Memory extraction happens via `asyncio.create_task()` — non-blocking, fires after response is yielded

**ChatService vs ContextualChatService:**
- `ChatService` = basic, no memory context. Used as fallback if PostgreSQL unavailable
- `ContextualChatService` = uses Flash Memory for relevant context + saves new memories
- `main.py` lifespan: tries to init `ContextualChatService`; falls back to `ChatService` if flash_memory/embeddings unavailable
- Both services now have compatible `send_message(user_input, conversation_history, conversation_id)` signatures

**OllamaEmbeddingService:**
- The embeddings service is `src/ia/ollama_embeddings.py` — uses `OllamaEmbeddingService`
- Embeddings are generated synchronously via `.generate()` method (not async)
- `_search_relevant_memories` in contextual service wraps this in try/except and returns [] on failure

**pgvector on macOS PG14:**
- Brew pgvector 0.8.2 installs for PG17/PG18, not PG14
- Must clone pgvector repo and build manually: `git clone https://github.com/pgvector/pgvector.git && PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config make && make install`
- Then: `psql -d yeyoos -c "CREATE EXTENSION IF NOT EXISTS vector;"`

**Project Layer Status (capas):**
- Capas 0-4: Fully implemented in backend
- Capa 5: Backend nodes all exist but only Image node has working frontend connection
- Capa 6: Most security modules exist but Guardian Daemon missing, no kill switch backend endpoint
- Capa 7: 0% implemented (LoRA, YEYO Store, ISO, YeyoNet, multi-user)
- Only working E2E tested feature before this session: image generation
</technical_details>

<important_files>
- `src/media/image_generator.py`
  - Core SD image generation service with MPS thread safety and float32 fix
  - Key: `_pipeline_lock = threading.Lock()`, `dtype = torch.float32`, numpy clip fix
  - Lines ~79-175

- `src/chat/service.py`
  - Basic chat service (fallback when PostgreSQL unavailable)
  - Fixed: `send_message()` and `send_message_stream()` now accept `conversation_history` and `conversation_id`
  - Lines 38-95

- `src/chat/contextual_service.py`
  - Full chat service with Flash Memory context + extraction
  - Added: `MemoryExtractor` import, `_extractor` init, `_extract_and_store()` method
  - Fixed: streaming now accumulates full response before extraction
  - Lines 71-225

- `src/api/routes/chat.py`
  - Chat API endpoints — streaming SSE handler
  - No changes needed; it was correct; the bug was in the service layer
  - Key: `/stream` endpoint at line ~144

- `src/api/routes/media.py`
  - Image + video API endpoints
  - No recent changes; serves as reference for image generation flow

- `frontend/src/components/nodes/ImageNodeLayout.tsx`
  - Complete image generation UI — controls, gallery, chat panel
  - All generation logic lives here; calls `http://localhost:8000` directly
  - Key: `handleGenerar()`, `handleChatSend()`, `onAssistantMessage` prop
  - Lines 94-160 (generation logic), 401-450 (gallery with download button)

- `frontend/src/components/chat/ChatPanel.tsx`
  - Main chat sliding panel
  - Fixed: now calls `http://localhost:8000/api/v1/chat/stream` directly
  - Lines 107-193 (sendMessage function)

- `frontend/src/app/page.tsx`
  - Main app component — hub, workspace router, state management
  - Simplified: removed generateImage fetch logic; now just manages display state
  - Key: `WorkspaceRouter` (lines ~79-104), `HubPrincipal` (lines ~106+)

- `frontend/next.config.ts`
  - Next.js proxy config — routes `/api/*` to `:8000`
  - Important: proxy has timeout limitation; long operations must bypass it
</important_files>

<next_steps>
Remaining work from current session:
- [ ] User needs to restart backend (uvicorn) to pick up Python changes
- [ ] User should do the memory test: tell name + date → reload → ask YeyoOS to recall it
- [ ] Verify pgvector semantic search works after extension install (no more "fallback" warning in logs)

Planned next features (agreed in planning session, in priority order):
1. **Nodo Código** — connect `CodeNodeLayout.tsx` to `/api/v1/nodes/codigo/process` for code execution in sandbox
2. **Nodo Video** — connect `VideoNodeLayout.tsx` to `/api/v1/media/video/compose` (requires ffmpeg installed)
3. **Nodo Files** — connect `FilesNode.tsx` to semantic search backend
4. **Kill Switch backend** — add `/api/v1/security/kill-switch` endpoint that actually pauses AI activity
5. **Guardian Daemon** — implement `src/security/guardian.py` (anomaly detection)
6. **YeyoNet** — capa 7 feature for sharing with friends (prompts 7.17-7.20, 7.23)

Immediate next action when resuming:
- Restart uvicorn backend
- Test chat memory: `"Me llamo Diego"` → reload → `"¿Cómo me llamo?"`
- If memory works, proceed to Nodo Código connection
</next_steps>