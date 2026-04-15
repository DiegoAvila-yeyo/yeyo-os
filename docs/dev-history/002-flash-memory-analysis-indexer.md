## Tests que deberías hacer con Flash Memory

### Los tests más importantes

**1. Test de corrección** — ¿actualiza cuando te corriges?
```
"Me llamo Diego" → "No, en realidad me llamo Eduardo"
→ recargar → "¿Cómo me llamo?"
→ ¿dice Eduardo o Diego?
```

**2. Test de preferencias** — ¿recuerda gustos?
```
"Me encanta el estilo cyberpunk para imágenes"
→ recargar → "¿Qué estilo me gusta?"
```

**3. Test de recuperación semántica** — ¿encuentra cosas sin mencionar la palabra exacta?
```
Guardas: "Trabajo en una startup de diseño"
→ preguntas: "¿A qué me dedico?" (no usas "trabajo")
→ debería encontrarlo por similitud semántica
```

**4. Test de volumen** — ¿funciona con muchos recuerdos?
```
Dile 10 cosas distintas en una conversación
→ recargar → pide que te resuma lo que sabe de ti
```

---

### ¿Y los otros nodos?

Sí, falta conectarlos, pero hay una diferencia importante:

| Nodo | Qué falta |
|------|-----------|
| Chat | ✅ Conectado — solo falta probar más |
| Imagen | Guardar estilos/prompts que te gustaron |
| Código | Guardar snippets y patrones favoritos |
| Files | Indexar archivos del usuario para búsqueda semántica |
| Video | Guardar composiciones favoritas |

Cada nodo necesita trabajo específico — no es automático como en chat. Hay que decidir **qué guardar** en cada uno y **cuándo** guardarlo.

¿Seguimos con más tests del chat primero o pasamos a conectar otro nodo?

---

<overview>
The user (Diego) is building YeyoOS — an AI-native fullscreen OS shell running on Mac with FastAPI backend + Next.js frontend + PostgreSQL + Ollama (qwen2.5-coder:7b). This session focused on: (1) analyzing whether the 5 Flash Memory layers were correctly implemented, (2) fixing the system prompt so the AI knows its memory is permanent, (3) building a project indexer so the AI can answer questions about the codebase, and (4) discussing what tests to run and what remains to connect Flash Memory to other nodes.
</overview>

<history>
1. User asked to review documentation on 5 memory layers and compare to implementation
   - Analyzed flash_memory.py, cache.py, tier_manager.py, extraction.py, associations.py
   - Found: WARM (PostgreSQL) ✅ and Extraction ✅ work; HOT (Redis), COLD (auto-demotion), Associations ❌ have code but are never wired
   - Found discrepancies: embedding dimension vector(384) vs docs say vector(768), no `importancia` field, relevance formula not implemented

2. User asked if 5 layers per node were needed (for image references, video preferences, etc.)
   - Clarified: Flash Memory is one shared table for all nodes, not separate per node
   - Each node needs to READ and WRITE to flash_memories with different `type`/`metadata` — not separate infrastructure

3. User ran the memory test: told YeyoOS "Me llamo Diego, tengo 20 años" → reloaded → asked it to recall
   - ✅ Flash Memory test PASSED — AI recalled "Diego, 20 años"
   - Problem: AI responded "days to weeks" when asked how long it could remember (it doesn't know about its own permanent architecture)

4. Fixed system prompt to inform the AI about Flash Memory permanence
   - Modified BASE_PROMPT in src/chat/system_prompt.py to state memories are never deleted

5. User asked about making the AI know the whole project codebase
   - Explained RAG over codebase concept — Flash Memory already supports it, just needs indexing
   - TokenBudget and fit_history/fit_memories already handle context window limits
   - conversation_messages saves ALL messages to DB; context window is just the 10 most recent in RAM

6. User asked to implement the project indexer
   - Created src/tools/index_project.py (module version using src.core.config)
   - Created scripts/index_project.py (standalone, no heavy imports)
   - Created scripts/run_indexer.sh (runs 1 file at a time via shell to avoid OOM)
   - Problem: System has only ~71MB free RAM (Ollama + SD model + VS Code consuming everything)
   - OOM killer kills the process when indexing large files (77KB docs/17-modelo-investigador.md)
   - Solution requires stopping uvicorn backend before indexing (frees 2-4GB from SD model)
   - 46 chunks successfully indexed from docs/ before OOM killed the process

7. User asked about Flash Memory tests and connecting other nodes
   - Advised 4 more tests: correction, preferences, semantic retrieval, volume test
   - Confirmed connecting other nodes requires specific per-node design decisions
</history>

<work_done>
Files created:
- `src/tools/__init__.py` — empty init for tools package
- `src/tools/index_project.py` — full indexer using YeyoOS stack (requires src.core.config)
- `scripts/index_project.py` — standalone indexer with --file, --stats, --force flags; uses direct asyncpg without importing src/
- `scripts/run_indexer.sh` — shell script that indexes one file at a time to minimize RAM usage

Files modified:
- `src/chat/system_prompt.py` — Updated BASE_PROMPT to inform AI that Flash Memory is permanent, memories never deleted, never say memory is temporary

Work completed:
- [x] Analyzed all 5 Flash Memory layers vs implementation
- [x] Flash Memory test passed (name + age persisted across reload)
- [x] System prompt fixed to inform AI of permanent memory
- [x] Project indexer created (3 versions: module, standalone, shell)
- [x] 46 doc chunks indexed (docs 01-08 + README)
- [ ] Full project indexation (blocked by OOM — needs backend stopped)
- [ ] Connect HOT tier (Redis/MemoryCache)
- [ ] Start TierManager background task
- [ ] Wire auto_associate() in contextual_service.py
- [ ] Connect Flash Memory to other nodes (Imagen, Código, Files, Video)
</work_done>

<technical_details>
**OOM Issue during indexing:**
- System has only ~71MB free RAM (vm_stat: Pages free: 4334 × 16KB)
- Ollama + SD pipeline in uvicorn + VS Code consume almost all available RAM
- OOM killer (exit code 137) terminates indexer when processing files >30KB
- Solution: Stop uvicorn backend (frees 2-4GB), then run `bash scripts/run_indexer.sh`

**Indexer design:**
- Uses SHA-256 checksum of `{rel_path}:{content}` to detect unchanged files
- Files not changed → skipped (deduplication prevents double-indexing)
- Chunks of 2000 chars (~500 tokens) with 200 char overlap
- Each chunk stored in flash_memories with type='fact', source='docs'/'code'/'prompts'/'schema'
- Metadata includes: file, chunk_index, total_chunks, file_checksum

**Flash Memory layer status:**
- WARM (PostgreSQL): ✅ Working — new memories enter as WARM by default
- Extraction IA: ✅ Working — MemoryExtractor called in contextual_service._extract_and_store()
- HOT (Redis): ❌ MemoryCache class exists but never instantiated in main.py
- COLD auto-demotion: ❌ TierManager exists but evaluate_all() never scheduled
- Associations: ❌ AssociationEngine initialized in main.py as _association_engine but auto_associate() never called after store()

**Embedding dimension mismatch:**
- DB schema: vector(384)
- Docs say: vector(768) for nomic-embed-text
- Actual model: qwen2.5-coder:7b used for embeddings (not nomic-embed-text)
- This inconsistency means semantic search may not work correctly

**Context window solution already exists:**
- TokenBudget splits 4000 tokens: system(300) + memories(1000) + history(1500) + input(500) + response(700)
- fit_history() drops oldest messages when history > 1500 tokens
- fit_memories() drops memories when total > 1000 tokens
- conversation_messages table saves ALL messages to PostgreSQL permanently
- Context window only limits what's in RAM, not what's stored

**System prompt fix:**
- Added to BASE_PROMPT: explanation of Flash Memory permanence
- Model was answering "days to weeks" because it didn't know about YeyoOS architecture
- Fix: explicit instruction "Nunca digas que tu memoria es temporal"
</technical_details>

<important_files>
- `src/chat/system_prompt.py`
  - Modified BASE_PROMPT to inform AI about permanent Flash Memory
  - Key: lines 22-30 (BASE_PROMPT constant)

- `src/chat/contextual_service.py`
  - Core chat service with Flash Memory integration
  - Calls MemoryExtractor after each response via asyncio.create_task
  - Key: _extract_and_store() method, send_message_stream() accumulation logic

- `src/memory/flash_memory.py`
  - Core Flash Memory PostgreSQL implementation
  - store(), recall(), search_semantic(), promote_tier(), demote_tier()
  - _row_to_memory() converter

- `src/memory/cache.py`
  - Redis HOT tier cache — fully implemented but NOT wired in main.py
  - Needs: instantiation in main.py lifespan and integration with FlashMemory.store()

- `src/memory/tier_manager.py`
  - Automatic tier promotion/demotion — fully implemented but NOT scheduled
  - Needs: asyncio background task in main.py that calls evaluate_all() periodically

- `src/memory/associations.py`
  - Neural association engine — fully implemented
  - Needs: auto_associate() called after each memory store in contextual_service._extract_and_store()

- `scripts/index_project.py`
  - Standalone project indexer (no src/ imports needed)
  - Supports --file, --stats, --force flags
  - Key: index_one_file(), chunk_file(), checksum() functions

- `scripts/run_indexer.sh`
  - Shell script that calls scripts/index_project.py one file at a time
  - Required because bulk indexing causes OOM on this machine
</important_files>

<next_steps>
Immediate (before anything else):
- [ ] Stop uvicorn backend → run `bash scripts/run_indexer.sh` → restart backend
- [ ] This completes the project indexation so AI knows the full codebase

Flash Memory improvements (in priority order):
1. Wire auto_associate() in contextual_service._extract_and_store() after memory store (5 lines)
2. Initialize MemoryCache (Redis HOT tier) in main.py lifespan
3. Schedule TierManager.evaluate_all() as background task in main.py

Flash Memory tests to run:
- Correction test: "Me llamo Diego" → "No, me llamo Eduardo" → reload → ask name
- Preference test: tell AI a preference → reload → verify recalled
- Semantic test: store fact with different words, ask in different words
- Volume test: tell 10 facts, verify AI can summarize them all

Connect Flash Memory to other nodes (after tests pass):
- Imagen node: save prompts/styles that worked, recall on next session
- Código node: save snippets and patterns
- Files node: index user's files for semantic search
- Video node: save composition preferences
</next_steps>