# 💪 CAPA 3: CUERPO — Prompts de Ejecución
# Total: 16 micro-fases → 17 prompts (15 VSCODE + 1 VSCODE-SIMPLE + 1 MIXTA)
# Flujo: Copiar prompt → Pegar en Copilot (VS Code o CLI) → Ejecutar → Verificar → Siguiente
# ⚠️ Kill Switch (Ctrl+Alt+K) es CRÍTICO — debe funcionar incluso sin UI completamente cargada.

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 3.0 — Hub Canvas Setup | [prompt-3.0-1.md](prompt-3.0-1.md) | VSCODE | Media |
| 3.1 — Central Node | [prompt-3.1-1.md](prompt-3.1-1.md) | VSCODE | Media |
| 3.2 — Satellite Node Base | [prompt-3.2-1.md](prompt-3.2-1.md) | VSCODE | Media |
| 3.3 — Node Layout Engine | [prompt-3.3-1.md](prompt-3.3-1.md) | VSCODE | Media |
| 3.4 — Connection Lines | [prompt-3.4-1.md](prompt-3.4-1.md) | VSCODE | Simple |
| 3.5 — Chat Panel | [prompt-3.5-1.md](prompt-3.5-1.md) | VSCODE | Compleja |
| 3.5 — Chat Panel Tests | [prompt-3.5-2.md](prompt-3.5-2.md) | VSCODE | Compleja |
| 3.6 — MiniChat Overlay | [prompt-3.6-1.md](prompt-3.6-1.md) | VSCODE | Media |
| 3.7 — File Drop Zone | [prompt-3.7-1.md](prompt-3.7-1.md) | VSCODE | Simple |
| 3.8 — Theme System | [prompt-3.8-1.md](prompt-3.8-1.md) | VSCODE | Simple |
| 3.9 — Notification System | [prompt-3.9-1.md](prompt-3.9-1.md) | VSCODE | Simple |
| 3.10 — Keyboard Shortcuts | [prompt-3.10-1.md](prompt-3.10-1.md) | VSCODE | Simple |
| 3.11 — Zustand State Architecture | [prompt-3.11-1.md](prompt-3.11-1.md) | VSCODE | Media |
| 3.12 — WebSocket Client | [prompt-3.12-1.md](prompt-3.12-1.md) | VSCODE | Media |
| 3.13 — API Client | [prompt-3.13-1.md](prompt-3.13-1.md) | VSCODE | Simple |
| 3.14 — Responsive Layout | [prompt-3.14-1.md](prompt-3.14-1.md) | VSCODE | Simple |
| 3.15 — Integration Test Capa 3 | [prompt-3.15-1.md](prompt-3.15-1.md) | MIXTA | Compleja |

---

# 📊 RESUMEN CAPA 3

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 3.0 Hub Canvas Setup | 1 | VSCODE | ⬜ |
| 3.1 Central Node | 1 | VSCODE | ⬜ |
| 3.2 Satellite Node Base | 1 | VSCODE | ⬜ |
| 3.3 Layout Engine | 1 | VSCODE | ⬜ |
| 3.4 Connection Lines | 1 | VSCODE | ⬜ |
| 3.5 Chat Panel | 2 | VSCODE | ⬜ |
| 3.6 MiniChat Overlay | 1 | VSCODE | ⬜ |
| 3.7 File Drop Zone | 1 | VSCODE | ⬜ |
| 3.8 Theme System | 1 | VSCODE | ⬜ |
| 3.9 Notifications | 1 | VSCODE | ⬜ |
| 3.10 Keyboard Shortcuts | 1 | VSCODE | ⬜ |
| 3.11 Zustand Architecture | 1 | VSCODE | ⬜ |
| 3.12 WebSocket Client | 1 | VSCODE | ⬜ |
| 3.13 API Client | 1 | VSCODE | ⬜ |
| 3.14 Responsive Layout | 1 | VSCODE | ⬜ |
| 3.15 Integration Test | 1 | MIXTA | ⬜ |
| **TOTAL** | **17** | **15 VSCODE + 1 SIMPLE + 1 MIXTA** | |

---

## 💪 Filosofía de Capa 3

Capa 3 es el **CUERPO** de YeyoOS. La interfaz Neural Hub donde la IA cobra vida visual.

- **Neural Hub**: Canvas PixiJS 8 con nodo central pulsante (GLSL shader) y nodos satélite orbitando.
- **Chat con Streaming**: Batch flush cada 50ms, no por carácter. Panel lateral + MiniChat flotante.
- **Compositor**: Wayland vía Rust + smithay (Plan B: Chromium kiosk). Para desarrollo, testear en browser.
- **GPU Budget**: GTX 1060 3GB VRAM. El compositor P0 reserva ~200MB siempre. Los shaders deben ser ligeros.
- **Kill Switch**: Ctrl+Alt+K pausa TODA actividad IA. Se registra PRIMERO, antes de cualquier UI.
- **Estado**: Zustand con 4 stores (hub, chat, ui, system) + persistencia en localStorage.
- **WebSocket**: Conexión en tiempo real al backend (Capa 1.7) con auto-reconnect exponential backoff.

**REGLA DE ORO**: El Kill Switch (Ctrl+Alt+K) es SAGRADO. Debe funcionar incluso si la UI está rota. Se registra antes que cualquier componente visual.

## 🔗 Dependencias

- **Requiere**: Capa 0 completada (infraestructura) + Capa 0.5 (scaffold Next.js) + Capa 1 completada (interfaces/skeleton) + Capa 2 completada (cerebro/memoria)
- **Produce**: Cuerpo funcional — Neural Hub visual, chat con streaming, estado reactivo, WebSocket en tiempo real
