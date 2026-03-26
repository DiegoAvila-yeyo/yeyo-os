<overview>
The user (Diego) is designing **YeyoOS**, an AI-native operating system with a "Neural Hub" interface, powered by local AI (Ollama on GTX 1060 3GB). The project has been in an extensive conversational planning phase, building a detailed "Swiss watch" micro-phase architecture with ~125 micro-phases across 8 layers (Capa 0-7), each with comprehensive tests, risks, precautions, and gates. We completed the full desglose of ALL 7+1 layers and then created executable prompts for Capa 0 that can be copy-pasted into Copilot CLI or VS Code to build the system via vibe coding.
</overview>

<history>
1. Initial exploration (prior checkpoints)
   - Explored OpenClaw/clawtdbot, AI-native OS ideas, Ollama integration
   - Created UI prototype with draggable neural hub nodes
   - Established 3 repos: yeyo-os (private), yeyo-os-security (private), yeyo-os-public (public)
   - Created 14+ documentation files across repos
   - Designed hexagonal architecture with IAProvider, MemoriaProvider, Orquestador

2. Phase architecture design (prior checkpoints)
   - Reorganized into 7-layer "Swiss watch" architecture (Capas 0-7)
   - ~125 micro-phases with security as "DNA" integrated throughout
   - Flash Memory redesign (unified HOT/WARM/COLD with pgvector)

3. Detailed desglose of ALL layers (this session + prior)
   - Capa 0 Cimientos: 13 micro-fases, ~115 tests
   - Capa 1 Esqueleto: 14 micro-fases, ~277 tests (interfaces, config, GPU scheduler)
   - Capa 2 Cerebro: 19 micro-fases, ~391 tests (Flash Memory, chat, RAG, anti-hallucination)
   - Capa 3 Cuerpo: 16 micro-fases, ~308 tests (Next.js, PixiJS, compositor)
   - Capa 4 Sistema Nervioso: 14 micro-fases, ~290 tests (YEYO-PKG, permissions, containers)
   - Capa 5 Órganos: 22 micro-fases, ~338 tests (all node types)
   - Capa 6 Sistema Inmune: 12 micro-fases, ~192 tests (Guardian, honeypots, anti-ransomware, kill switch, backups)
   - Capa 7 Evolución: 15 micro-fases, ~275 tests (LoRA training, YEYO Store, ISO builder, multi-user, Swiss Watch Test)

4. User asked about Swiss Watch Test failure complexity
   - Explained that failures are easy to trace due to layered test structure
   - Each phase has its own tests; Swiss Watch Test identifies WHERE, individual tests identify WHY
   - 24h endurance test is the hardest to debug (memory leaks)

5. User asked about prompt format for executing micro-phases
   - Presented 5 format proposals: Military Briefing, Agile User Story, System Prompt+Task (XML), Checklist, Conversational Chain
   - Recommended hybrid of System Prompt (🅲️) + Chain (🅴️)

6. User asked about CLI vs VS Code for prompts
   - Proposed dual-format strategy: CLI for system tasks, VS Code for code tasks
   - Mapped all 125 micro-phases: ~34 CLI, ~65 VS Code, ~26 Mixed
   - Estimated ~309 total prompts across all layers

7. User asked about optimal format specifically for Copilot CLI
   - Designed a hybrid format optimized for Copilot CLI capabilities
   - Structure: EJECUTAR → VERIFICAR → SI FALLA → GATE
   - For complex phases: split into 2-5 sequential prompts

8. User asked to create Capa 0 prompts
   - Generated 18 detailed prompts covering all 13 micro-phases of Capa 0
   - Saved to session files as capa0-prompts.md
   - Each prompt has: install commands, implementation steps, verification checklist, failure handling, restrictions, gate criteria

9. User asked to put prompts inside the yeyo-os repo
   - This was the last request before compaction
   - Need to create the file in the yeyo-os repo directory and commit/push
</history>

<work_done>
Files created:
- `/Users/eltitoyeyo/.copilot/session-state/eca1e636-2cd3-4b63-ace8-a1e9fdd49e49/files/capa0-prompts.md` — Complete Capa 0 prompts (18 prompts, ~46KB)

Work completed:
- [x] Capa 0 detailed desglose (13 micro-fases)
- [x] Capa 1 detailed desglose (14 micro-fases)
- [x] Capa 2 detailed desglose (19 micro-fases)
- [x] Capa 3 detailed desglose (16 micro-fases)
- [x] Capa 4 detailed desglose (14 micro-fases)
- [x] Capa 5 detailed desglose (22 micro-fases)
- [x] Capa 6 detailed desglose (12 micro-fases)
- [x] Capa 7 detailed desglose (15 micro-fases)
- [x] Prompt format design (dual CLI/VS Code strategy)
- [x] Capa 0 prompts generated (18 prompts)
- [ ] Put Capa 0 prompts in yeyo-os repo — USER JUST REQUESTED THIS
- [ ] Generate prompts for Capas 1-7
- [ ] Update docs/10-fases.md with complete 7-layer system
- [ ] Push all documentation to GitHub

Current state: All planning/desglose is done conversationally. Capa 0 prompts exist in session files but need to be placed in the actual yeyo-os repo.
</work_done>

<technical_details>
**Architecture (125 micro-phases, ~2,186 tests):**
- 8 layers: Capa 0 (Cimientos) → Capa 7 (Evolución)
- Each micro-phase has: acceptance tests, quality tests, risk tests, precautions, gate
- Security is "DNA" — integrated from Capa 0.11, not a separate layer
- Swiss Watch Test (7.14): 50 checks, 9 phases, 24h endurance, score ≥45/50 for release

**Hardware Constraints (GTX 1060 3GB + 16GB RAM):**
- VRAM: Compositor P0 (~200MB) + IA (~2872MB available)
- Only 1 heavy model at a time: Ollama 3B (~1800MB) OR SD 1.5 (~2500MB)
- Model swap: ~3-5s; GPU Scheduler: P0>P1>P2>P3
- Whisper/TTS on CPU; NVENC uses dedicated hardware

**Token Budget (Capa 2):**
- system(300) + memories(1000) + history(1500) + input(500) + response(700) = 4000 max

**Prompt Strategy:**
- Dual format: CLI prompts (system tasks) + VS Code prompts (code tasks)
- ~309 total prompts estimated for all 125 micro-phases
- Simple phases: 1 prompt; Medium: 2-3; Complex: 4-5
- CLI format: EJECUTAR → VERIFICAR (checklist) → SI FALLA → GATE
- VS Code format: CONTEXTO → CREAR ARCHIVOS → RESTRICCIONES → TESTS → GATE

**Key Design Rules:**
- Flash Memory: NEVER deleted, append-only, HOT/WARM/COLD tiers, SHA-256 checksums
- Containers: Podman (not Docker), rootless, no Docker socket EVER
- YEYO-PKG: .ypkg format, 6 privilege levels (L0-L5), IA nodes always L5
- Firewall: DENY ALL default, whitelist only
- Backups: 3-2-1 rule, restic encrypted, Flash Memory = highest priority
- Kill Switch: Ctrl+Alt+K, PAUSES (not kills), works even without UI

**Development Environment:**
- WSL2 Ubuntu (GPU passthrough) on Windows desktop
- Mac M1 secondary
- Testing in QEMU/VM, final install: flash ISO to USB

**Repos:**
- `DiegoAvila-yeyo/yeyo-os` (private) — main OS repo, 14+ docs
- `DiegoAvila-yeyo/yeyo-os-security` (private) — 8 security docs
- `DiegoAvila-yeyo/yeyo-os-public` (public) — 3 marketing files
- `DiegoAvila-yeyo/YEYO-IA` (current workspace) — Rails app

**User Preferences:**
- Speaks Spanish informally
- Plans 1-2 month timeline via vibe coding with GitHub Copilot
- Wants "Swiss watch" precision — everything must fit perfectly
- Never used Copilot CLI for programming before (explained how it works)
</technical_details>

<important_files>
- `/Users/eltitoyeyo/.copilot/session-state/eca1e636-2cd3-4b63-ace8-a1e9fdd49e49/files/capa0-prompts.md`
   - Complete Capa 0 prompts (18 prompts for 13 micro-phases)
   - ~46KB, needs to be copied to yeyo-os repo
   - Contains all CLI/VS Code prompts with verification checklists

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/10-fases.md`
   - Current phases document — has OLD flat 17-phase plan
   - WILL BE REPLACED with the 7-layer micro-phase system

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/05-memoria.md`
   - Flash Memory design (unified HOT/WARM/COLD)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/11-compositor.md` — Wayland compositor spec
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/12-yeyo-pkg.md` — Package system spec
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/13-code-dojo.md` — Self-training system
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/14-hardware.md` — Hardware compatibility

- `/Users/eltitoyeyo/.copilot/session-state/eca1e636-2cd3-4b63-ace8-a1e9fdd49e49/plan.md`
   - Session plan tracking (outdated, needs update)
</important_files>

<next_steps>
Immediate (user's last request):
1. **Copy Capa 0 prompts into the yeyo-os repo** — User said "pon los prompts dentro del repo". Need to create the file at something like `~/YEYO/yeyo-os/prompts/capa0-prompts.md` or similar directory structure, then commit and push.

Remaining work:
2. Generate prompts for Capas 1-7 (~291 more prompts)
3. Update `docs/10-fases.md` with complete 7-layer micro-phase system
4. Push all documentation to yeyo-os GitHub repo
5. Potentially create a master index/table of contents for all prompts

Open questions:
- Exact directory structure for prompts in repo (e.g., `prompts/capa0/`, or `prompts/capa0-prompts.md`)
- Whether to also put the detailed desglose (non-prompt docs) in the repo
- User may want prompts as separate files per micro-phase vs one big file per capa
</next_steps>