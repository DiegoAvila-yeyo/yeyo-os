<overview>
Diego is building YeyoOS — an AI-native OS shell running on Mac/Windows/Linux with FastAPI backend + Next.js frontend + PostgreSQL + Ollama. This session focused on analyzing Flash Memory's 5-tier implementation, diagnosing why the chat AI fails to remember context within and between sessions, and fixing the root causes. The core problem discovered: embeddings were stored as Python string representations instead of proper pgvector format, AND the frontend created a new conversation per message (no conversation_id persistence), making context impossible.
</overview>

<history>
1. **User asked to analyze Flash Memory documentation vs implementation**
   - Read `docs/05-memoria.md` and all `src/memory/` files
   - Found 5 layers: WARM ✅, Extraction ✅, HOT Redis ❌, COLD auto-demotion ❌, Associations ❌
   - Identified that `MemoryCache`, `TierManager`, `AssociationEngine.auto_associate()` all exist but are never connected

2. **User asked about whether 5 layers = perfect memory and whether each node needs its own 5 layers**
   - Explained: one shared Flash Memory table for all nodes, organized by `source` field
   - `source='chat'` for personal facts, `source='image_node'` for style prefs, etc.
   - Not 5 layers per node — 1 table with rich types per node

3. **User ran memory test: told name+age, reloaded, asked if remembered**
   - ✅ Test PASSED — AI correctly recalled "Diego, 20 años"
   - But AI said "I remember things for days to weeks" — incorrect for YeyoOS

4. **User asked to fix the AI's self-knowledge about its memory duration**
   - Fixed `BASE_PROMPT` in `src/chat/system_prompt.py` to say memories are NEVER deleted

5. **User asked about context window — is there already an implementation?**
   - Confirmed: `TokenBudget` (4000 token budget), `fit_history()`, `fit_memories()` all exist
   - Real problem: Flash Memory is empty of project knowledge, not the context window itself

6. **User asked to implement the project indexer**
   - Created `src/tools/__init__.py` and `src/tools/index_project.py`
   - Created `scripts/index_project.py` (standalone, no heavy imports)
   - Created `scripts/run_indexer.sh` (runs 1 file at a time to avoid OOM)
   - OOM killer terminated processes — system has only ~71MB free RAM (Ollama + SD model loaded)
   - Partial index: 46 chunks from docs/ got indexed before crash
   - Added `--file` mode and `--stats` mode to standalone script

7. **User ran more memory tests — all failed**
   - "Prefiero modo oscuro" → reloaded → AI didn't remember
   - "Mi nombre no es Juan, es Diego" → AI apologized but next message forgot
   - "Mi color favorito es azul" → next message: "No tengo información sobre tu color"
   - Context not persisting even within same session (no page reload)

8. **Analysis and fixes**
   - Found Bug 1: Frontend sends NO `conversation_id` — each message creates new conversation (confirmed in DB: 8 different conv IDs for 8 messages)
   - Found Bug 2: Embeddings stored as `str([0.1, 0.2,...])` Python string — invalid for pgvector — search_semantic finds nothing — falls back to random memories — AI hallucinates
   - Found Bug 3: Threshold inconsistency (contextual_service uses 0.5, flash_memory.py hardcoded 0.7)
   - Applied 6 fixes (see Work Done)
   - User tested again — still same failures (backend wasn't restarted, or X-Conversation-Id CORS issue)

9. **User described correct design for conversation management**
   - One conversation per app session (from open to reload/close)
   - All messages share same conversation_id
   - Flash Memory extracts important facts in background
   - New session on reload, but Flash Memory persists knowledge across sessions

10. **User asked about source-based memory organization per node**
    - Confirmed: `source` field already exists in schema
    - Each node reads/writes only its own `source` carril
    - No revoltijo: `source='chat'`, `source='image_node'`, `source='code_node'` etc.

11. **User asked what other implemented-but-never-used solutions exist**
    - Full audit revealed: `BackgroundTaskManager`, `SystemPromptBuilder`, `AntiHallucination`, `RAGPipeline`, `TierManager`, `MemoryCache`, `AssociationEngine.auto_associate()` — all written, none connected in `main.py`
</history>

<work_done>
Files modified:

- `src/chat/system_prompt.py`
  - Added to `BASE_PROMPT`: "Tienes acceso a Flash Memory... NUNCA se borran... Nunca digas que tu memoria es temporal"

- `src/memory/flash_memory.py`
  - **Bug fix**: `store()` now formats embedding as `"[x,y,z]"` with `::vector` cast instead of `str(embedding)`
  - **Bug fix**: `search_semantic()` threshold changed from hardcoded 0.7 → 0.5, same vector format fix
  - **Bug fix**: `search_semantic()` SQL now filters `AND (metadata->>'invalid') IS NULL`
  - **Bug fix**: `recall()` fallback also filters `AND (metadata->>'invalid') IS NULL`

- `src/api/routes/chat.py`
  - Added `"X-Conversation-Id": conv_id` to StreamingResponse headers

- `frontend/src/lib/store/chat-store.ts`
  - Added `conversationId: string | null` to state
  - Added `setConversationId: (id: string) => void` action
  - `clearMessages()` now also resets `conversationId: null`

- `frontend/src/components/chat/ChatPanel.tsx`
  - Destructures `conversationId` and `setConversationId` from store
  - fetch body now includes `conversation_id: conversationId || undefined`
  - Reads `X-Conversation-Id` response header and calls `setConversationId(newConvId)`
  - Updated `useCallback` deps array

Files created:

- `src/tools/__init__.py` (empty)
- `src/tools/index_project.py` (full indexer using src/ config system)
- `scripts/index_project.py` (standalone indexer, no heavy imports, supports `--file`, `--stats`, `--force`)
- `scripts/run_indexer.sh` (shell script, indexes 1 file at a time to avoid OOM)

Database changes:

- Cleaned 18 corrupted embeddings (set to NULL): `UPDATE flash_memories SET embedding = NULL WHERE source = 'chat_extraction'`
- Marked 2 hallucinated memories as invalid: `UPDATE flash_memories SET metadata = metadata || '{"invalid": true}'::jsonb WHERE content ILIKE '%Juan%'`

Current state:
- [x] System prompt fix applied
- [x] Embedding format bug fixed in code
- [x] conversation_id wired in frontend store and ChatPanel
- [x] Backend returns X-Conversation-Id header
- [x] Hallucinated data cleaned from DB
- [ ] Backend not restarted to apply Python fixes (user needs to do this)
- [ ] X-Conversation-Id header may be blocked by CORS (untested)
- [ ] Project indexer only ran partially (46 docs chunks) — needs RAM freed to complete
- [ ] Conversation_id fix may still fail if CORS blocks custom headers — need alternative approach (send conv_id in SSE body instead of header)
</work_done>

<technical_details>
**Root cause of all memory failures:**
1. `str([0.1, 0.2, ...])` produces `"[0.1, 0.2, ...]"` — asyncpg passes this as TEXT to PostgreSQL, not as a vector. pgvector `<=>` operator requires proper vector format `"[0.1,0.2]"` with `::vector` cast. All embeddings in `chat_extraction` rows were NULL or invalid text — `search_semantic` returned nothing, fell back to `recall()` which returned random recent memories — AI received irrelevant context and hallucinated.

2. **Frontend conversation_id**: Each `fetch()` call sends `{}` with no `conversation_id` → backend creates new conversation every time → `get_history()` returns empty list → model has no conversation context.

**CORS risk with X-Conversation-Id header**: Custom response headers from streaming endpoints may be blocked by browser CORS unless `expose_headers` is configured in FastAPI's CORSMiddleware. If this is the issue, the fix is to send conversation_id as the FIRST SSE event: `data: {"type":"conversation_id","value":"..."}` instead of a header.

**OOM killer (macOS)**: System has ~71MB free RAM. Ollama (loaded model) + SD pipeline + VS Code + Next.js + PostgreSQL consume nearly all RAM. Any Python process that tries to import heavy modules gets killed. Solution: `scripts/index_project.py` is standalone (no pydantic_settings, no torch, etc.) and uses `asyncpg.connect()` (not pool) + `gc.collect()` between files. Still crashes on large files (77KB docs). Must stop backend before running indexer.

**pgvector format**: Correct: `"[" + ",".join(str(x) for x in embedding) + "]"` with SQL `$1::vector`. Wrong: `str(embedding)` which Python formats as `"[0.1, 0.2, ...]"` with spaces after commas (may also fail pgvector parsing).

**BackgroundTaskManager** also has the embedding bug — `_generate_missing_embeddings` uses `str(embedding)` at line ~150 of `background.py`. Would need fixing before connecting.

**Conversation architecture decision**: One conversation per browser session (created on first message, stored in Zustand store, lost on page reload). Flash Memory persists facts across sessions. This is the correct design — not one conversation forever.

**All these modules exist but are NEVER instantiated in main.py**: BackgroundTaskManager, SystemPromptBuilder, AntiHallucination, RAGPipeline, TierManager, MemoryCache, AssociationEngine.auto_associate(). The app runs only with: FlashMemory, ConversationManager, ContextualChatService (with basic memory search), OllamaProvider, OllamaEmbeddingService.

**Embedding model**: Config says `nomic-embed-text` but `.env` uses `qwen2.5-coder:7b` for both chat AND embeddings. DB schema has `vector(384)` but docs say `vector(768)`. These are inconsistent and need alignment when embeddings are fixed.
</technical_details>

<important_files>
- `src/memory/flash_memory.py`
  - Core Flash Memory implementation
  - Fixed: embedding format bug (str→vector), threshold 0.7→0.5, invalid memory filter
  - Key methods: `store()` (~line 42), `search_semantic()` (~line 163), `recall()` (~line 90)

- `src/chat/contextual_service.py`
  - Main chat service with memory injection
  - Contains `_extract_and_store()` — fires after every response to save facts
  - `build_context()` calls `_search_relevant_memories()` — this is where embeddings matter
  - Has its own token budget implementation (duplicates TokenBudget class)

- `frontend/src/lib/store/chat-store.ts`
  - Zustand store for chat state
  - Modified: added `conversationId` field and `setConversationId` action
  - Critical for conversation persistence within a session

- `frontend/src/components/chat/ChatPanel.tsx`
  - Main chat UI component
  - Modified: now sends `conversation_id` in fetch body, reads `X-Conversation-Id` from response headers
  - Key section: `sendMessage()` function (~line 107)

- `src/api/routes/chat.py`
  - Chat API endpoints
  - Modified: `send_message_stream()` now returns `X-Conversation-Id` in StreamingResponse headers
  - Key: `/stream` endpoint (~line 144)

- `src/chat/system_prompt.py`
  - Builds system prompt for IA
  - Modified: `BASE_PROMPT` now tells model its memory is permanent
  - `SystemPromptBuilder` class exists but is NEVER used — direct string used instead

- `scripts/index_project.py`
  - Standalone project indexer (no heavy imports)
  - Supports: `--file <path>`, `--stats`, `--force`
  - Must be run with backend stopped (OOM risk)

- `scripts/run_indexer.sh`
  - Shell script that indexes project 1 file at a time
  - Run: `bash scripts/run_indexer.sh` from project root

- `src/core/background.py`
  - `BackgroundTaskManager` — fully implemented, never started
  - Would handle: tier evaluation, cache warming, embedding generation
  - Has the same embedding bug (`str(embedding)`) — needs fix before connecting
</important_files>

<next_steps>
Immediate (blocking everything else):

1. **Fix conversation_id delivery** — The X-Conversation-Id header approach may be blocked by CORS. Better approach: send conv_id as first SSE event:
   ```
   yield f"data: {{\"type\":\"conv_id\",\"value\":\"{conv_id}\"}}\n\n"
   ```
   Then frontend parses it before rendering text chunks.

2. **Restart backend** to apply Python fixes (embedding format, threshold, invalid filter)

3. **Verify CORS exposes the header** — check `CORSMiddleware` config in `main.py` for `expose_headers=["X-Conversation-Id"]`

After conversation_id is fixed:

4. **Re-run memory tests** — name/age recall, color preference, correction handling

5. **Fix `_generate_missing_embeddings`** in `BackgroundTaskManager` — same `str(embedding)` bug

6. **Connect BackgroundTaskManager in main.py** — instantiate TierManager, MemoryCache, start background tasks

7. **Run project indexer** (stop backend first): `bash scripts/run_indexer.sh`

8. **Consider SSE-based conv_id** as the robust solution if CORS header approach fails

Planned architecture for conversation_id (robust approach):
- Backend: first SSE event = `data: {"type":"meta","conversation_id":"xxx"}\n\n`
- Frontend: parse first event type, call `setConversationId()`, then render subsequent text events normally
</next_steps>