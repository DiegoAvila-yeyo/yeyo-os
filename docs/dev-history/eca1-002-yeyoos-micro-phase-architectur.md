<overview>
The user (Diego) is designing and planning **YeyoOS**, an AI-native operating system where AI is the center of everything. The system features a "Neural Hub" interface with draggable nodes (image, video, code, automation, etc.), powered by local AI (Ollama). We've been in an extensive conversational planning phase, exploring architecture, security, memory, compositor, package system, hardware, and training strategies. The approach is exploratory conversation first, then documentation, with implementation planned via vibe coding with GitHub Copilot in 1-2 months.
</overview>

<history>
1. Initial exploration of OpenClaw/clawtdbot and AI-native OS concept
   - Created initial UI prototype with draggable neural hub nodes
   - Established project at `/Users/eltitoyeyo/YEYO/yeyo-os/`
   - Created initial 10 documentation files and pushed to private GitHub repo

2. Extensive architecture planning (covered in prior checkpoint)
   - Hexagonal architecture, 5-layer memory, security zones, Linux base
   - Hardware: PC Windows (GTX 1060 3GB + 16GB RAM) primary dev, Mac M1 secondary
   - Decided on Next.js + TypeScript + PixiJS frontend, Python + FastAPI backend

3. Deep-dive topics explored in THIS conversation segment:
   - **ASICs + AI hardware**: ASICs can't run AI models (only hashes), but AI can CONTROL mining ASICs. Discussed AI-specific ASICs (TPU, Groq LPU, etc.)
   - **Multiple hardware backends**: IAHardwareProvider interface to support GPU, NPU, ASIC IA, CPU as fallback. Auto-select best hardware per task.
   - **Smart snapshots/backups**: AI decides when to snapshot (before risky ops, after long work, disk health) and when to backup (important files, no backup in a week, etc.)
   - **"YEYO Obediente"**: Confirmation before acting, strict/normal/free modes, diff preview, scope lock, learning from corrections. BUT the goal is AUTONOMOUS AI that gets so good it doesn't need intervention.
   - **Code training pipeline**: All agents use SAME model (different prompts), pipeline Architect→Backend→Critic→Tester→Performance→Security, GPU and CPU work in parallel
   - **Standardization**: 70% easily standardized (agents, pipelines, security), 30% adapts per user via memory
   - **AMD/Intel GPU support**: Ollama already supports AMD (ROCm), code doesn't change, only installation script detects GPU
   - **Docker Compose**: Only for development. Production uses Podman/containerd managed by YeyoOS Manager via API directly
   - **Repository structure security**: Keep security docs in separate private repo
   - **YEYO-PKG**: 3-layer package system (apt invisible → YEYO-PKG .ypkg → YEYO Store marketplace). Nodes as packages with manifest, container, UI, permissions. Security pipeline for Store uploads. Dynamic node creation by AI.
   - **Wayland Compositor deep dive**: Built with Rust + smithay, custom protocols (yeyo-node-v1, yeyo-ai-v1), scene graph, render pipeline with damage tracking, GLSL shaders (glow, blur, transition, connection lines, accessibility), zero-copy DMA-BUF, each container gets own Wayland socket
   - **GPU optimization strategies**: Time-slicing, model swapping (~2-5s), chunked processing (tiles), CPU offloading (split layers GPU+RAM), adaptive quality (fast preview → final render)
   - **RAG for code**: pgvector with code_examples table, multi-level search (semantic → metadata → project context → ranking), negative examples from user corrections
   - **LoRA/QLoRA training**: Fine-tune 3B models on GTX 1060 using Unsloth, QLoRA (4-bit model + 16-bit adapter), weekly cycle, ~50MB adapter. RAG + LoRA = 95%+ quality
   - **Flash Memory redesign**: Replaced 5-layer memory with ONE unified Flash Memory. No data EVER deleted, only priority changes (HOT/WARM/COLD). Designed for 20+ years. Memories have associations like neural network. Portable JSON format.
   - **20-year memory protection**: 7 layers (checksum, nightly scan, backup 3-2-1, portable format, BTRFS snapshots, anti-ransomware, migration support). Memory is the MOST VALUABLE asset.
   - **Hardware deep dive**: All hardware types (GPU, TPU, NPU, LPU, FPGA, ASICs), IAHardwareProvider interface, HardwareManager auto-detect, GPU Scheduler with P0-P3 priorities
   - **FFmpeg integration**: Already in stack, AI translates natural language to FFmpeg commands, NVENC hardware encoding (separate from AI GPU resources)

4. Documentation update session
   - User requested: create security repo (private), public marketing repo, update main docs
   - Created `yeyo-os-security` repo with 8 security docs
   - Created `yeyo-os-public` repo with 3 marketing files (minimal info to prevent idea theft)
   - Updated main `yeyo-os` repo: new docs 11-14, updated docs 04, 05, 06, 09, 10, README
   - All 3 repos pushed to GitHub

5. Phase reorganization discussion
   - User wants to build like a "Swiss watch" — micro-phases with acceptance tests
   - Designed 7-layer architecture replacing the flat 17-phase plan:
     - Capa 0: Cimientos (12 micro-fases) — Linux, Docker, PostgreSQL, Redis, Ollama, GPU
     - Capa 1: Esqueleto (14) — FastAPI, interfaces, GPU scheduler, audit, CI/CD
     - Capa 2: Cerebro (18) — Flash Memory, chat, anti-hallucination, RAG
     - Capa 3: Cuerpo (16) — Wayland compositor, hub, shaders, WebSocket
     - Capa 4: Sistema Nervioso (14) — YEYO-PKG, drag&drop, privileges, dynamic nodes
     - Capa 5: Órganos (22) — All nodes (Image, Video, Code, etc.), Code Dojo
     - Capa 6: Sistema Inmune (12) — Guardian, YEYO-HACK, backups, smart protection
     - Capa 7: Evolución (10) — LoRA, Store, ISO, multi-user, corporate, hardware expansion
   - Total: 118 micro-phases with acceptance tests
   - Security is DNA (integrated into every micro-phase), not a separate layer

6. Training strategy discussion
   - User plans to build in 1-2 months via vibe coding with GitHub Copilot
   - Designed **YEYO Observer**: background service that watches while user codes with Copilot
   - Observer watches: git commits, file changes, test results, Copilot accept/reject patterns
   - Before Flash Memory exists (weeks 1-2): saves to JSON locally
   - After Flash Memory (week 3+): migrates JSON → Flash Memory, direct indexing
   - Added micro-phases: 0.13 (Observer v1) and 2.18b (Migration to Flash Memory)

7. Development environment confirmed
   - Development: PC Windows + WSL2 (GPU passthrough works), compositor in window mode
   - Testing: QEMU/VM with generated ISO, compositor fullscreen
   - Installation: Flash ISO to USB → format Windows → install YeyoOS
   - Data migration: export Flash Memory + LoRA + RAG to portable format → reimport after install
</history>

<work_done>
Files created/updated across 3 repositories:

**yeyo-os (private, main repo) — Updated:**
- `README.md` — Added docs 11-14 to table, security note, updated memory description
- `docs/04-nodos.md` — Added Mining Node + YEYO-PKG reference
- `docs/05-memoria.md` — REPLACED: 5-layer → unified Flash Memory (no deletion, HOT/WARM/COLD, 20-year design, associations, Python code examples)
- `docs/06-seguridad.md` — REPLACED: full doc → short pointer to security repo
- `docs/09-stack-tecnologico.md` — Added compositor, render, shaders, YEYO-PKG, Podman, hardware rows + Docker dev note
- `docs/10-fases.md` — Added phases 15 (YEYO-PKG), 16 (Enterprise), 17 (Hardware) + "EXPANSIÓN" priority
- `docs/11-compositor.md` — NEW: Wayland compositor (Rust+smithay, protocols, shaders, render pipeline, integration)
- `docs/12-yeyo-pkg.md` — NEW: Package system (.ypkg format, Store, security pipeline, trust levels, dynamic creation)
- `docs/13-code-dojo.md` — NEW: Code training (12 agents, RAG, LoRA/QLoRA, nightly training)
- `docs/14-hardware.md` — NEW: Hardware compatibility (GPU/NPU/ASIC, scheduler, optimization strategies)

**yeyo-os-security (private, NEW repo):**
- `README.md` — Index with 8 docs, design principles, classification notice
- `01-seguridad-base.md` — Application security (sandbox, zones, users, audit, kill switch, BTRFS, encryption)
- `02-seguridad-kernel.md` — Kernel protections (namespaces, cgroups, seccomp, AppArmor, Secure Boot, TPM, USBGuard)
- `03-yeyo-hack.md` — Automated red team/blue team with uncensored model in isolated environment
- `04-yeyo-guardian.md` — AI-powered security monitoring, honeypots, anomaly detection, Zero Trust
- `05-brechas-y-soluciones.md` — 10 security breaches analyzed with solutions
- `06-privilegios.md` — 6-level privilege system (Root→Visitor) + corporate mode
- `07-seguridad-corporativa.md` — Enterprise: isolated islands, VLANs, distributed Guardian
- `08-seguridad-memoria.md` — 7-layer memory protection for 20+ years

**yeyo-os-public (public, NEW repo):**
- `README.md` — Marketing landing page (minimal info, no technical details, social media links)
- `VISION.md` — Inspirational philosophy document
- `FEATURES.md` — Teaser feature list with emojis

All pushed to GitHub:
- `https://github.com/DiegoAvila-yeyo/yeyo-os` (private) — 14 docs
- `https://github.com/DiegoAvila-yeyo/yeyo-os-security` (private) — 8 security docs
- `https://github.com/DiegoAvila-yeyo/yeyo-os-public` (public) — 3 marketing files

Work completed:
- [x] All documentation created and pushed
- [x] 7-layer micro-phase architecture designed (118 micro-phases)
- [x] YEYO Observer concept designed
- [x] Development → Testing → Installation pipeline confirmed
- [ ] Detailed desglose of all 118 micro-phases with acceptance tests (user was about to approve)
</work_done>

<technical_details>
**Architecture Decisions:**
- Hexagonal architecture: IAProvider, MemoriaProvider, Orquestador interfaces. Changing any component = 1 config line
- Flash Memory replaces 5-layer system: ONE pgvector table, HOT (Redis)/WARM (PG active)/COLD (PG archive), NOTHING ever deleted
- Compositor built in Rust + smithay (not wlroots C) for memory safety. COSMIC desktop validates this approach.
- YEYO-PKG: apt invisible below, .ypkg format, YEYO Store marketplace. Nodes = packages.
- Security is DNA integrated in every micro-phase, not a separate layer
- Docker Compose for dev ONLY. Production: Podman/containerd via API.

**Hardware Strategy:**
- GTX 1060 3GB: models ≤3B on GPU, ≤7B with CPU offloading (60% GPU + 40% RAM)
- GPU Scheduler: P0=compositor (always), P1=user request, P2=background, P3=idle/nightly
- Strategies: time-slicing, model swapping (2-5s), tile-based chunking (~700MB per tile), adaptive quality (512px preview 3s → 1024px final 25s)
- All agents use SAME model (different prompts) = zero swap time between agents
- NVENC for video encoding uses dedicated hardware (NOT AI VRAM)
- GPU is NEVER used for mining — exclusively for AI
- Future: NPU (Intel/AMD), Coral USB, Tenstorrent, Groq via IAHardwareProvider interface

**Training/Learning:**
- RAG: pgvector code_examples table, multi-level search, negative examples from corrections
- LoRA: QLoRA on 3B models fits in 3GB VRAM (4-bit model + 16-bit adapter, ~50MB output)
- Weekly LoRA cycle: collect data → train (4-6h) → validate → deploy if better
- RAG + LoRA combined = 95%+ quality
- Code Dojo: ~1,800 challenges per night on GTX 1060 (16s per challenge)
- YEYO Observer: watches git commits, file changes, test results while user codes with Copilot

**Development Plan:**
- Build in 1-2 months via vibe coding with GitHub Copilot
- Dev: PC Windows + WSL2 (GPU passthrough works)
- Test: QEMU/VM with ISO
- Install: format Windows → install YeyoOS from USB
- Data migration: export Flash Memory + LoRA + RAG → reimport after install

**Key Design Principles:**
- "Swiss watch" — 118 micro-phases, each with acceptance test, no advancing if test fails
- Integration test at end of each layer (7 total)
- Security integrated from micro-phase 0.11 (not bolted on later)
- Flash Memory is the MOST VALUABLE asset — more protected than the OS itself
- The AI learns from day 1 via Observer, not just when "ready"

**User Preferences (communication):**
- Speaks Spanish informally
- Wants conversational planning before documentation
- Will say "yo te diré cuando acabemos" when ready to document
- Thinks big: enterprise potential, crypto mining, self-improving AI
- Plans aggressive 1-2 month timeline via vibe coding
- Wants to prevent idea theft (minimal public info)
</technical_details>

<important_files>
- `/Users/eltitoyeyo/YEYO/yeyo-os/README.md`
   - Main project overview, doc index, hardware specs
   - Updated: added docs 11-14, security repo note, memory description change

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/05-memoria.md`
   - CRITICAL: Flash Memory design (replaces old 5-layer)
   - Completely rewritten: unified memory, HOT/WARM/COLD, no deletion, Python code examples

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/11-compositor.md`
   - NEW: Full Wayland compositor spec (Rust+smithay, protocols, shaders, render pipeline)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/12-yeyo-pkg.md`
   - NEW: Package system (.ypkg format, Store, security, dynamic node creation)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/13-code-dojo.md`
   - NEW: Self-training system (12 agents, RAG, LoRA, nightly training)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/14-hardware.md`
   - NEW: Hardware compatibility and optimization strategies

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/10-fases.md`
   - Development phases — NOW BEING REPLACED by 7-layer micro-phase system (not yet documented)
   - Updated: added phases 15-17 but the entire structure is changing

- `/Users/eltitoyeyo/YEYO/yeyo-os-security/` (all 8 docs)
   - Complete security architecture, separate private repo
   - 31+ security layers documented

- `/Users/eltitoyeyo/YEYO/yeyo-os-public/` (3 files)
   - Marketing repo, minimal info, for social media

- Session plan: `/Users/eltitoyeyo/.copilot/session-state/eca1e636-2cd3-4b63-ace8-a1e9fdd49e49/plan.md`
   - Current task tracking
</important_files>

<next_steps>
The user was about to approve the 7-layer micro-phase design for detailed breakdown.

Immediate next steps:
1. **Desglose detallado de las 118 micro-fases** — Each micro-phase needs:
   - Clear objective (1-3 tasks max)
   - Acceptance test that must pass
   - Dependencies on previous micro-phases
   - This should be done conversationally first, then documented

2. **Document the new phase structure** — Replace `docs/10-fases.md` with the 7-layer system:
   - 118 micro-phases with acceptance tests
   - Integration tests between layers
   - YEYO Observer micro-phases (0.13 and 2.18b)

3. **YEYO Observer implementation spec** — Needs its own doc or section:
   - Simple Python script for Capa 0 (JSON mode)
   - Migration to Flash Memory in Capa 2
   - Git hooks, file watcher, test watcher specs

Remaining topics the user may want to explore:
- The user said "quiero seguir pensando en más cosas para implementar"
- May have more features/ideas to discuss before finalizing micro-phases
- The user is in an exploratory phase and will signal when ready to start coding

Key decision pending:
- User needs to confirm the 7-layer structure before detailed breakdown begins
- The last message was confirming the dev→test→install pipeline
</next_steps>