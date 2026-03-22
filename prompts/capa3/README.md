# 💪 CAPA 3: CUERPO — Prompts de Ejecución
# Total: 23 micro-fases → 24 prompts (22 VSCODE + 1 VSCODE-SIMPLE + 1 MIXTA)
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
| 3.16 — GraphExecutionView | [prompt-3.16-1.md](prompt-3.16-1.md) | VSCODE | Compleja |
| 3.17 — NodeExpandedWithGraph | [prompt-3.17-1.md](prompt-3.17-1.md) | VSCODE | Media |
| 3.18 — Double Grid Background + Onboarding | [prompt-3.18-1.md](prompt-3.18-1.md) | VSCODE | Compleja |
| 3.19 — Hub Activo: Nodos Libres + Energía | [prompt-3.19-1.md](prompt-3.19-1.md) | VSCODE | Compleja |
| 3.20 — Node App Layout: Topbar + Sidebar + Layouts | [prompt-3.20-1.md](prompt-3.20-1.md) | VSCODE | Compleja |
| 3.21 — Seguridad Visual: Permission Alerts + Kill Switch + Dashboard | [prompt-3.21-1.md](prompt-3.21-1.md) | VSCODE | Compleja |
| 3.22 — Primera Tarea: Materialización + Scan | [prompt-3.22-1.md](prompt-3.22-1.md) | VSCODE | Compleja |

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
| 3.16 GraphExecutionView | 1 | VSCODE | ⬜ |
| 3.17 NodeExpandedWithGraph | 1 | VSCODE | ⬜ |
| 3.18 Double Grid + Onboarding | 1 | VSCODE | ⬜ |
| 3.19 Hub Activo: Nodos Libres + Energía | 1 | VSCODE | ⬜ |
| 3.20 Node App Layout | 1 | VSCODE | ⬜ |
| 3.21 Seguridad Visual | 1 | VSCODE | ⬜ |
| 3.22 Primera Tarea Visual | 1 | VSCODE | ⬜ |
| **TOTAL** | **24** | **22 VSCODE + 1 SIMPLE + 1 MIXTA** | |

---

## 💪 Filosofía de Capa 3

Capa 3 es el **CUERPO** de YeyoOS. La interfaz Neural Hub donde la IA cobra vida visual.

- **Neural Hub**: Canvas PixiJS 8 con nodo central pulsante (GLSL shader) y nodos satélite orbitando.
- **Chat con Streaming**: Batch flush cada 50ms, no por carácter. Panel lateral + MiniChat flotante.
- **UI Rendering**: Browser-based (Next.js para desarrollo) → Chromium kiosk fullscreen para producción (cross-platform). No requiere compositor custom.
- **GPU Budget**: GTX 1060 3GB VRAM. La UI P0 reserva ~200MB siempre. Los shaders deben ser ligeros.
- **Kill Switch**: Ctrl+Alt+K pausa TODA actividad IA. Se registra PRIMERO, antes de cualquier UI.
- **Estado**: Zustand con 4 stores (hub, chat, ui, system) + persistencia en localStorage.
- **WebSocket**: Conexión en tiempo real al backend (Capa 1.7) con auto-reconnect exponential backoff.

**REGLA DE ORO**: El Kill Switch (Ctrl+Alt+K) es SAGRADO. Debe funcionar incluso si la UI está rota. Se registra antes que cualquier componente visual.

### Mini-grafo de Ejecución (3.16-3.17)

Las micro-fases 3.16 y 3.17 añaden visualización en tiempo real de los grafos del YeyoOrquestador dentro del Hub:
- **GraphExecutionView**: componente que renderiza el mini-grafo animado con estados por nodo (pendiente/activo/completado/error/saltado)
- **NodeExpandedWithGraph**: integración del mini-grafo como overlay semitransparente en el SatelliteNode expandido
- **graphStore**: store Zustand que consume eventos WebSocket `{type: "graph_event"}` del backend
- Estas micro-fases son **UI pura** — pueden mockearse independientemente del backend (Capa 4)

## 🔗 Dependencias

- **Requiere**: Capa 0 completada (infraestructura) + Capa 0.5 (scaffold Next.js) + Capa 1 completada (interfaces/skeleton) + Capa 2 completada (cerebro/memoria)
- **Produce**: Cuerpo funcional — Neural Hub visual, chat con streaming, estado reactivo, WebSocket en tiempo real
