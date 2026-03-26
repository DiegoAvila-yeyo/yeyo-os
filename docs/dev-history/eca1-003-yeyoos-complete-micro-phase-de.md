<overview>
The user (Diego) is designing **YeyoOS**, an AI-native operating system where AI is the center of everything, featuring a "Neural Hub" interface with draggable nodes (image, video, code, automation, etc.), powered by local AI (Ollama). The project has been in an extensive conversational planning phase, building a detailed "Swiss watch" micro-phase architecture with 120+ micro-phases across 7 layers, each with comprehensive acceptance tests, quality tests, risk tests, precautions, and gates. The approach is: plan conversationally → document → implement via vibe coding with GitHub Copilot in 1-2 months.
</overview>

<history>
1. Initial exploration and prototyping (prior checkpoints)
   - Explored OpenClaw/clawtdbot concept, AI-native OS ideas
   - Created initial UI prototype with draggable neural hub nodes
   - Established 3 repositories: yeyo-os (private, main), yeyo-os-security (private), yeyo-os-public (public marketing)
   - Created 14 documentation files across repos covering architecture, memory, compositor, packages, training, hardware
   - Designed hexagonal architecture with IAProvider, MemoriaProvider, Orquestador interfaces

2. Phase reorganization into 7-layer "Swiss watch" architecture
   - User wanted micro-phases with acceptance tests, ordered by importance
   - Designed 7 layers: Cimientos(0), Esqueleto(1), Cerebro(2), Cuerpo(3), Sistema Nervioso(4), Órganos(5), Sistema Inmune(6), Evolución(7)
   - ~120 micro-phases total with security as "DNA" integrated throughout

3. User requested detailed desglose of ALL phases
   - Provided initial breakdown of all 120 micro-fases with objectives, tasks, and acceptance tests
   - User noticed the detail level was uneven across layers

4. User asked about OpenClaw timing and risks per phase
   - Explained OpenClaw as temporary UI (install at 0.5, remove at Capa 3)
   - Detailed risks and precautions per layer with Top 5 Global Risks
   - VRAM map: 3072MB total, only 1 heavy model at a time, swap ~3-5s

5. User requested re-desglose with ALL details: risks, precautions, quality tests, risk tests, installations, verification
   - This became the main work of this session segment

6. Detailed desglose Capa 0 (Cimientos) - 13 micro-fases
   - Complete with exact install commands, 5+ acceptance tests, 5+ quality tests, 4+ risk tests, precautions, and gate per micro-fase
   - ~115 total tests for Capa 0

7. Detailed desglose Capa 1 (Esqueleto) - 14 micro-fases
   - Every micro-fase with full code examples (interfaces, config, factory, GPU scheduler)
   - ~277 total tests for Capa 1
   - Emphasis: "If interfaces are wrong, EVERYTHING above breaks"

8. Detailed desglose Capa 2 (Cerebro) - 19 micro-fases
   - Flash Memory schema with triggers, checksums, associations
   - Full CRUD, Redis cache tiers (HOT/WARM/COLD), embedding pipeline
   - Chat basic → contextual → multi-agent → anti-hallucination → RAG → feedback loop
   - Token budget: system(300) + memories(1000) + history(1500) + input(500) + response(700) = 4000 max
   - ~391 total tests for Capa 2

9. Detailed desglose Capa 3 (Cuerpo) - 16 micro-fases
   - Next.js 14 + PixiJS 8 + Tailwind + Zustand
   - Hub canvas, central node with GLSL shader, satellite nodes, drag physics, connection lines
   - ChatPanel with streaming (batch flush 50ms), MiniChat, FileDrop
   - Compositor Wayland (smithay/Rust) with Plan B: Chromium kiosk
   - ~308 total tests for Capa 3

10. Detailed desglose Capa 4 (Sistema Nervioso) - 14 micro-fases
    - YEYO-PKG: manifest format (.ypkg), create, build, install, remove lifecycle
    - Container security: seccomp, capabilities drop, non-root, no Docker socket
    - Permission system with dialog (Android/iOS style), 6 privilege levels (L0-L5)
    - Drag&drop between nodes, pipeline engine with cycle detection
    - AI node creation (always L5 sandbox), auto-updates with rollback
    - apt abstraction (invisible to user, inside containers only)
    - ~290 total tests for Capa 4

11. Detailed desglose Capa 5 (Órganos) - 22 micro-fases
    - NodeBase template (all nodes inherit)
    - Chat Node: multi-conversation, search, export
    - Image Node: SD 1.5 generation, img2img, LLaVA, MiniChat versioning (v1→v2→v3)
    - Video Node: FFmpeg from natural language (with command validation), clips+concat, Whisper subtitles, TTS narration
    - Code Node: Monaco editor, code-server (lazy load), sandbox execution (ephemeral container, no network, 30s timeout), Git with AI commit messages
    - Automation Node: React Flow pipeline visual, social media APIs (YouTube, Twitter), scheduling
    - Files Node: explorer + semantic search
    - Browser Node: embedded webview, AI page summary
    - Config Node: models, GPU, preferences, backups
    - Mining Node: ASIC dashboard only (GPU NEVER for mining)
    - ~338 total tests for Capa 5
</history>

<work_done>
**This session's work was entirely conversational planning — no files were created or modified.** All output was detailed micro-phase specifications delivered in chat.

Work completed:
- [x] Capa 0: Cimientos — 13 micro-fases fully detailed (installations, tests, risks, gates)
- [x] Capa 1: Esqueleto — 14 micro-fases fully detailed with code examples
- [x] Capa 2: Cerebro — 19 micro-fases fully detailed with SQL schemas and Python code
- [x] Capa 3: Cuerpo — 16 micro-fases fully detailed with TypeScript/React code
- [x] Capa 4: Sistema Nervioso — 14 micro-fases fully detailed with security configs
- [x] Capa 5: Órganos — 22 micro-fases fully detailed
- [ ] Capa 6: Sistema Inmune — NOT YET DETAILED (12 micro-fases planned)
- [ ] Capa 7: Evolución — NOT YET DETAILED (10 micro-fases planned)
- [ ] Document everything in docs/10-fases.md — NOT YET DONE (waiting for all layers complete)

**Previously completed (prior checkpoints):**
- 3 repos created and pushed to GitHub (yeyo-os, yeyo-os-security, yeyo-os-public)
- 14 docs in yeyo-os, 8 in yeyo-os-security, 3 in yeyo-os-public
- Flash Memory redesign (5-layer → unified HOT/WARM/COLD)
- YEYO Observer concept designed

**Test count summary so far:**

| Capa | Tests |
|------|:-----:|
| 0 Cimientos | ~115 |
| 1 Esqueleto | ~277 |
| 2 Cerebro | ~391 |
| 3 Cuerpo | ~308 |
| 4 Sistema Nervioso | ~290 |
| 5 Órganos | ~338 |
| 6 (pending) | ~90 est |
| 7 (pending) | ~75 est |
| **TOTAL** | **~1,884** |
</work_done>

<technical_details>
**Architecture:**
- Hexagonal architecture: IAProvider, MemoriaProvider, Orquestador interfaces. Changing any component = 1 config line in .env
- Flash Memory: ONE pgvector table, HOT(Redis)/WARM(PG active)/COLD(PG archive), NOTHING ever deleted, checksums SHA-256, associations between memories like neural network
- 7-layer build system (Capa 0-7), each with integration test that verifies ALL previous layers still pass
- Security is DNA (integrated from Capa 0.11), not a separate layer
- Docker Compose for dev ONLY. Production: Podman/containerd via API

**Hardware Constraints (GTX 1060 3GB + 16GB RAM):**
- VRAM budget: Compositor P0 (~200MB always) + IA (~2872MB available)
- Only 1 heavy model at a time: Ollama 3B (~1800MB) OR SD 1.5 (~2500MB) — NEVER both
- Model swap time: ~3-5 seconds
- GPU Scheduler with priorities: P0(compositor) > P1(user request) > P2(background) > P3(idle/nightly)
- NVENC for video encoding uses dedicated hardware (NOT IA VRAM)
- GPU NEVER used for mining — exclusively for AI
- Whisper/TTS on CPU (not GPU) to avoid conflicts
- code-server lazy-loaded (500MB-1GB RAM only when open)

**Token Budget (critical for Capa 2):**
- system_prompt: 300 tokens
- memories: 1000 tokens (top 5, fit to budget)
- history: 1500 tokens (last N messages)
- user_input: 500 tokens
- response: 700 tokens
- TOTAL: 4000 tokens max (qwen2.5:3b context window)
- Anti-hallucination verification only for responses >50 tokens

**YEYO-PKG System (Capa 4):**
- Format: .ypkg = tar.gz with manifest.yml + Docker image + UI + assets + signature
- Lifecycle: create → build → install → use → update → remove
- Container isolation: non-root, seccomp, no-new-privileges, capabilities dropped, PID/network namespaces
- 6 privilege levels: ROOT(L0) > ADMIN(L1) > USER(L2) > LIMITED(L3) > GUEST(L4) > SANDBOX(L5)
- IA-generated nodes ALWAYS L5 (sandbox)
- Permissions are ALLOWLIST (if not requested, not granted)
- Docker socket NEVER mounted in any node container

**Compositor (Capa 3.15):**
- Built with Rust + smithay (not wlroots)
- Plan B: Chromium kiosk mode if smithay too complex
- This is the HARDEST micro-phase of the entire project

**Development Environment:**
- PC Windows + WSL2 (GPU passthrough), compositor in window mode
- Mac M1 secondary
- Testing: QEMU/VM with generated ISO
- Installation: Flash ISO to USB → format Windows → install YeyoOS

**Key Design Rules:**
- No micro-fase advances until acceptance test passes 100%
- Integration test at end of each layer (regression: all previous layers must still pass)
- Files ALWAYS generated to temp → verify → move to final (never in-place)
- Audit log: append-only, no UPDATE/DELETE, every action logged
- Flash Memory is the MOST VALUABLE asset — more protected than the OS itself

**User Preferences:**
- Speaks Spanish informally
- Wants conversational planning before documentation
- Plans aggressive 1-2 month timeline via vibe coding with GitHub Copilot
- Wants to prevent idea theft (minimal public info)
- Thinks like "Swiss watch" — milimetric precision, everything must fit perfectly
</technical_details>

<important_files>
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/10-fases.md`
   - Current development phases document — WILL BE REPLACED with the 7-layer micro-phase system once all layers are detailed and user approves
   - Currently has old flat 17-phase plan (phases 0-17)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/05-memoria.md`
   - Flash Memory design (unified HOT/WARM/COLD, no deletion, 20-year design)
   - Already updated in prior checkpoint

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/11-compositor.md`
   - Wayland compositor spec (Rust+smithay)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/12-yeyo-pkg.md`
   - Package system spec (.ypkg format, Store, security)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/13-code-dojo.md`
   - Self-training system (agents, RAG, LoRA)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/14-hardware.md`
   - Hardware compatibility and optimization

- `/Users/eltitoyeyo/YEYO/yeyo-os-security/` (8 docs)
   - Complete security architecture in separate private repo

- `/Users/eltitoyeyo/YEYO/yeyo-os-public/` (3 files)
   - Marketing repo, minimal info

- `/Users/eltitoyeyo/.copilot/session-state/eca1e636-2cd3-4b63-ace8-a1e9fdd49e49/plan.md`
   - Session plan tracking

**Repos on GitHub:**
- `https://github.com/DiegoAvila-yeyo/yeyo-os` (private) — 14 docs
- `https://github.com/DiegoAvila-yeyo/yeyo-os-security` (private) — 8 security docs
- `https://github.com/DiegoAvila-yeyo/yeyo-os-public` (public) — 3 marketing files
</important_files>

<next_steps>
Remaining work:
1. **Capa 6: Sistema Inmune** — Detailed desglose needed (12 micro-fases):
   - Guardian baseline + anomaly detection + auto-response
   - YEYO-HACK: isolated red team/blue team
   - Kill Switch (Ctrl+Alt+K)
   - Smart Snapshots, Backup 3-2-1, Anti-ransomware
   - Honeypots
   - Integration test

2. **Capa 7: Evolución** — Detailed desglose needed (10 micro-fases):
   - LoRA/QLoRA training pipeline + validation
   - YEYO Store (server, security pipeline, trust levels)
   - ISO generation + Installation wizard
   - Multi-user system
   - Corporate deployment
   - Final "Swiss Watch Test"

3. **Document everything** — Replace `docs/10-fases.md` with the complete 7-layer micro-phase system (~120 micro-fases with all tests, risks, precautions, gates)

4. **Push documentation** to yeyo-os GitHub repo

Immediate next action:
- User said "capa 5" and I delivered it. They were progressing layer by layer. Next they will likely ask for **Capa 6** (Sistema Inmune).
</next_steps>