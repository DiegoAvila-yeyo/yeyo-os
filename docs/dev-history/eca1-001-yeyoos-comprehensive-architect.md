<overview>
The user (Diego) is designing **YeyoOS**, an AI-native operating system where the entire user experience revolves around AI (Ollama + OpenClaw). The system features a visual "Neural Hub" interface with draggable nodes representing AI-powered capabilities (image generation, video editing, automation, coding, etc.). We've been extensively planning the architecture, security, memory system, scalability, and novel features like YEYO-HACK (automated red team/blue team security testing) and a Code Dojo (self-training programming agents). The approach is conversational planning first, with documentation captured in a GitHub repo.
</overview>

<history>
1. User asked about OpenClaw/clawtdbot
   - Searched the web and found openclaw.ai — a personal AI assistant by @steipete
   - Confirmed it's an open-source project that runs locally

2. User wanted to start a new project: an AI-native operating system
   - Created initial plan in session state
   - Discussed two UI concepts: floating circles (neural hub) vs videogame-style
   - User chose Option 1: Floating circles/nodes

3. Created UI prototype
   - Built HTML/CSS/JS prototype at `/Users/eltitoyeyo/YEYO/yeyo-os/ui-prototype/index.html`
   - Initially had orbiting animation; user wanted static draggable nodes
   - Rewrote the prototype to be fully static with drag-and-drop functionality
   - Moved project from inside yeyo-ia to `/Users/eltitoyeyo/YEYO/yeyo-os/`

4. Extensive architecture planning through conversation
   - Decided on Linux minimal base (not custom kernel) because Ollama needs GPU drivers
   - Designed node layouts: Image (Chat + Pinboard), Video (Chat + Timeline), Automation (Chat + Pipeline), Code (Chat + Editor/Terminal), Files (Chat + Explorer)
   - Established the "fractal" pattern: nodes within nodes within nodes
   - User shared existing stack: Next.js + TypeScript + PixiJS, Python + FastAPI, PostgreSQL, Redis, Celery, Ollama, FFmpeg

5. Architecture decisions
   - Chose hybrid folder structure (monorepo with organized folders per node)
   - Designed intercambiable interfaces (hexagonal architecture) so Ollama, OpenClaw, PostgreSQL can each be swapped out by changing 1 file
   - User's existing automation station code will plug into the Automatización node

6. 5-Layer Memory System designed
   - Layer 1: Flash (RAM) — current conversation
   - Layer 2: Working (Redis) — session context, 24-48h TTL
   - Layer 3: Episodic (PostgreSQL + pgvector) — all conversations, semantic search
   - Layer 4: Knowledge (PostgreSQL) — extracted facts about user
   - Layer 5: Files (Storage + metadata) — every generated file with tags/versions

7. Security system designed (evolved over multiple exchanges)
   - Started with 6 application-level protections (zones, audit, Ctrl+Alt+K, snapshots, encryption)
   - Added 6 kernel-level protections (namespaces, cgroups, seccomp, AppArmor, isolated network, readonly filesystem)
   - Added anti-hacker protections (firewall, fail2ban, YEYO Guardian AI-powered antivirus, honeypots, zero trust)
   - Added corporate protections (segmented data, distributed guardian, signed updates, VLANs)
   - Identified and solved 10 security breaches (prompt injection, supply chain, memory poisoning, websocket hijacking, Docker escape, etc.)
   - Added Secure Boot, TPM, USBGuard
   - **Total: 31+ security layers**

8. Development environment decided
   - Primary development: **PC Windows (GTX 1060 3GB + 16GB RAM) with WSL2**
   - Secondary: **Mac M1** (code editing, design, backup)
   - Reason: PC has Ollama + OpenClaw + GPU from day 1
   - Phase 12: PC gets formatted and YeyoOS installed

9. Created comprehensive documentation (10 docs + README)
   - Pushed to new GitHub repo: `DiegoAvila-yeyo/yeyo-os` (private)

10. YEYO-HACK concept designed
    - Automated Red Team vs Blue Team using AI
    - Uses uncensored model (dolphin-llama3) in isolated environment
    - Attacks a CLONE of the system, never production
    - Generates patches automatically, validated before applying to real system
    - Runs nightly, system improves security automatically every night
    - Has real pentest tools (nmap, sqlmap, hydra, etc.) inside sandbox

11. Code Dojo concept designed
    - 12 specialized programming agents (Architect, Backend, Frontend, Mobile, DB, Security, AI/ML, Performance, Testing, DevOps, Data, Systems)
    - Automatic training through challenges of increasing difficulty
    - Agents critique each other (creator → critic → tester → performance → security)
    - Learn from user's corrections and real production errors

12. Privilege system designed
    - 6 levels: Root → Owner → Admin → User → AI Agent → Visitor
    - Each level has specific permissions, inherits from below
    - AI agents have individual profiles (Image agent can't access video storage, etc.)
    - Corporate mode adds departmental hierarchy

13. Mining node concept discussed
    - ASICs connect to YeyoOS via local network
    - AI optimizes which crypto to mine based on price/difficulty/electricity
    - GPU is NEVER used for mining — exclusively for AI
    - ASICs on separate VLAN, can't access YeyoOS (one-way control)
    - User explicitly said: ignore GPU mining idea, GPU is 100% for AI

14. User said they'll tell us when to update documentation — wants to keep exploring ideas first
</history>

<work_done>
Files created:
- `/Users/eltitoyeyo/YEYO/yeyo-os/README.md` — Project overview with hardware info and doc index
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/01-vision.md` — Philosophy, snowball effect, design principles
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/02-arquitectura.md` — Full architecture, interfaces, folder structure, request flow
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/03-interfaz.md` — Node hub design, layouts per module, fractal concept
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/04-nodos.md` — Detail of each node (Image, Video, Code, Automation, Files, Web, Config)
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/05-memoria.md` — 5 memory layers with examples and flow
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/06-seguridad.md` — Original security doc (zones, audit, Ctrl+Alt+K, snapshots)
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/07-anti-alucinacion.md` — Multi-agent verification, confidence levels
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/08-escalabilidad.md` — PC → Multi-GPU → Server → Cloud scaling path
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/09-stack-tecnologico.md` — Full stack, docker-compose, interfaces in Python, dev environment
- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/10-fases.md` — 14 development phases with checkboxes
- `/Users/eltitoyeyo/YEYO/yeyo-os/ui-prototype/index.html` — Static draggable neural hub prototype

GitHub repo created and pushed:
- `https://github.com/DiegoAvila-yeyo/yeyo-os` (private)

Work completed:
- [x] Initial project vision and concept
- [x] Full architecture design with intercambiable interfaces
- [x] UI concept and HTML prototype (static, draggable nodes)
- [x] 5-layer memory system design
- [x] Security system (31+ layers documented in conversation)
- [x] Anti-hallucination system design
- [x] Scalability roadmap
- [x] Stack technology definition
- [x] 14-phase development plan
- [x] Documentation pushed to GitHub

NOT yet in documentation (discussed in conversation only):
- [ ] Expanded security: kernel-level protections (namespaces, cgroups, seccomp, AppArmor, etc.)
- [ ] YEYO Guardian (AI-powered antivirus)
- [ ] YEYO-HACK (automated red team/blue team)
- [ ] Code Dojo (self-training programming agents)
- [ ] 10 security breaches analysis and solutions
- [ ] Privilege system (6 levels)
- [ ] Corporate/enterprise architecture
- [ ] Mining node concept
- [ ] Anti-hacker protections (firewall, fail2ban, honeypots, etc.)
- [ ] Secure Boot, TPM, USBGuard
</work_done>

<technical_details>
**Hardware:**
- PC: Windows, GTX 1060 3GB, 16GB RAM — primary dev machine, future YeyoOS host
- Mac M1 — secondary dev, backup, OpenClaw NOT compatible with Mac
- GTX 1060 3GB limits: models ≤3B on GPU, ≤7B on CPU+RAM (slow ~10-20s)
- GPU is exclusively for AI, NEVER for mining
- Future upgrade planned: high-end CPU, GPU, RAM

**Architecture Decisions:**
- Hexagonal architecture with interfaces (IAProvider, Orquestador, MemoriaProvider)
- Changing any component (Ollama→GPT5, OpenClaw→LangChain, Postgres→MongoDB) = change 1 config file
- Single FastAPI backend + single Next.js frontend (not microservices)
- Nodes organized by folders within the monorepo
- Docker Compose for local dev → Kubernetes for server scaling
- BTRFS filesystem for native snapshots

**OpenClaw Strategy:**
- Fork OpenClaw repo for custom improvements
- OpenClaw is the initial orchestrator but can be replaced
- Runs in sandbox with AppArmor/Seccomp like everything else
- Uses uncensored model (dolphin-llama3) ONLY for YEYO-HACK in isolated network

**Key Security Architecture:**
- 31+ security layers total
- Kill switch: Ctrl+Alt+K — implemented as C daemon at kernel level, independent of all apps
- YEYO-HACK uses a CLONE of the system, never attacks production
- Uncensored model (ollama-hack) on separate port (11435), separate network, off by default
- Corporate mode: each PC is independent island, communicates only via API
- Zero Trust: every service verifies every request even within internal network

**Memory/Anti-Hallucination:**
- pgvector for semantic search in PostgreSQL
- nomic-embed-text model for embeddings (lightweight, runs on GPU)
- RAG pattern: search memory → build context → send to Ollama
- Multi-agent verification: Creator → Critic → Verifier
- Confidence indicators: 🟢 verified, 🟡 estimated, 🔴 unverified

**Development Strategy:**
- Develop on Windows PC with WSL2 (Ubuntu)
- Phase 12: format Windows, install YeyoOS Linux
- Mac M1 always has backup of code via GitHub
- Can develop from within YeyoOS itself after installation (Node Código)

**User Communication Style:**
- User prefers conversational planning before documentation
- User will explicitly say when to update docs ("yo te diré cuando acabemos")
- User types in Spanish with informal style
- User thinks big — wants enterprise/corporate potential, crypto mining, self-improving AI
</technical_details>

<important_files>
- `/Users/eltitoyeyo/YEYO/yeyo-os/README.md`
   - Main project overview, hardware specs, doc index
   - Updated with dev environment (Windows WSL2 primary, Mac M1 secondary)

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/01-vision.md`
   - Core philosophy, snowball effect, design principles, use cases

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/02-arquitectura.md`
   - Full architecture diagram, interfaces in Python code, folder structure, request flow

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/03-interfaz.md`
   - UI design: neural hub, node layouts (Image, Video, Automation, Code, Files), fractal concept

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/04-nodos.md`
   - Detailed spec for each node including tools, flows, dynamic node creation

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/05-memoria.md`
   - 5-layer memory system with code examples and search flow

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/06-seguridad.md`
   - Original security doc — NEEDS MAJOR UPDATE with kernel-level protections, YEYO-HACK, YEYO Guardian, breach analysis, privilege system, corporate security

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/09-stack-tecnologico.md`
   - Full stack table, docker-compose.yml, Python interfaces, dev environment setup

- `/Users/eltitoyeyo/YEYO/yeyo-os/docs/10-fases.md`
   - 14 development phases with checkboxes — may need Phase 15 for corporate/enterprise

- `/Users/eltitoyeyo/YEYO/yeyo-os/ui-prototype/index.html`
   - Working HTML prototype of draggable neural hub interface
</important_files>

<next_steps>
Remaining documentation updates (user said to wait until they say so):
- Massively expand 06-seguridad.md with all 31+ layers, kernel protections, breach analysis
- Create new doc: YEYO-HACK (automated red team/blue team)
- Create new doc: YEYO Guardian (AI-powered security monitoring)
- Create new doc: Code Dojo (self-training programming agents)
- Create new doc: Privilege System (6 levels)
- Create new doc: Corporate/Enterprise Architecture
- Create new doc: Mining Node
- Update 04-nodos.md with Mining node
- Update 10-fases.md with Phase 15 (Enterprise)
- Push all updates to GitHub

User's mode: Still in exploratory conversation phase, asking to explore more ideas before committing to documentation. Wait for explicit signal to update docs.

When user is ready to implement:
- Start with Phase 0 on PC Windows with WSL2
- Install Docker, Ollama, PostgreSQL, Redis
- Set up the project structure
</next_steps>