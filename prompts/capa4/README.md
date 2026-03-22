# 🔌 CAPA 4: SISTEMA NERVIOSO — Prompts de Ejecución
# Total: 24 micro-fases → 26 prompts (23 VSCODE + 1 VSCODE-SIMPLE + 1 MIXTA + 1 extra)
# Flujo: Copiar prompt → Pegar en Copilot (VS Code o CLI) → Ejecutar → Verificar → Siguiente
# ⚠️ Podman SIEMPRE. Docker NUNCA. Socket de Docker JAMÁS montado. Nodos IA SIEMPRE L5.

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 4.0 — YEYO-PKG Manifest Format | [prompt-4.0-1.md](prompt-4.0-1.md) | VSCODE | Media |
| 4.1 — YEYO-PKG Builder | [prompt-4.1-1.md](prompt-4.1-1.md) | VSCODE | Compleja |
| 4.2 — YEYO-PKG Installer | [prompt-4.2-1.md](prompt-4.2-1.md) | VSCODE | Compleja |
| 4.3 — Permission System | [prompt-4.3-1.md](prompt-4.3-1.md) | VSCODE | Compleja |
| 4.4 — Container Security | [prompt-4.4-1.md](prompt-4.4-1.md) | VSCODE | Compleja |
| 4.5 — Privilege Levels | [prompt-4.5-1.md](prompt-4.5-1.md) | VSCODE | Media |
| 4.6 — Node Communication (Drag & Drop) | [prompt-4.6-1.md](prompt-4.6-1.md) | VSCODE | Media |
| 4.7 — Pipeline Engine | [prompt-4.7-1.md](prompt-4.7-1.md) | VSCODE | Compleja |
| 4.7 — Pipeline Tests | [prompt-4.7-2.md](prompt-4.7-2.md) | VSCODE | Compleja |
| 4.8 — Package Database | [prompt-4.8-1.md](prompt-4.8-1.md) | VSCODE | Simple |
| 4.9 — Auto-Update System | [prompt-4.9-1.md](prompt-4.9-1.md) | VSCODE | Media |
| 4.10 — Apt Abstraction | [prompt-4.10-1.md](prompt-4.10-1.md) | VSCODE | Simple |
| 4.11 — Package API Endpoints | [prompt-4.11-1.md](prompt-4.11-1.md) | VSCODE | Media |
| 4.12 — Package Frontend UI | [prompt-4.12-1.md](prompt-4.12-1.md) | VSCODE | Media |
| 4.13 — Integration Test Capa 4 | [prompt-4.13-1.md](prompt-4.13-1.md) | MIXTA | Compleja |
| 4.14 — EstadoGrafo Core | [prompt-4.14-1.md](prompt-4.14-1.md) | VSCODE | Media |
| 4.15 — Nodo Base + Decoradores | [prompt-4.15-1.md](prompt-4.15-1.md) | VSCODE | Compleja |
| 4.16 — Edge + Condiciones | [prompt-4.16-1.md](prompt-4.16-1.md) | VSCODE | Media |
| 4.17 — YeyoGrafo Coordinador | [prompt-4.17-1.md](prompt-4.17-1.md) | VSCODE | Compleja |
| 4.18 — NodoParalelo | [prompt-4.18-1.md](prompt-4.18-1.md) | VSCODE | Media |
| 4.19 — YeyoOrquestador + Ollama Tool Calling | [prompt-4.19-1.md](prompt-4.19-1.md) | VSCODE | Compleja |
| 4.20 — Catálogo de Nodos Base | [prompt-4.20-1.md](prompt-4.20-1.md) | VSCODE | Media |
| 4.21 — Grafos Estáticos Principales | [prompt-4.21-1.md](prompt-4.21-1.md) | VSCODE | Media |
| 4.22 — WebSocket Graph Events (Backend) | [prompt-4.22-1.md](prompt-4.22-1.md) | VSCODE | Media |
| 4.23 — Integration Test Capa 4 (Orquestador) | [prompt-4.23-1.md](prompt-4.23-1.md) | MIXTA | Compleja |

---

# 📊 RESUMEN CAPA 4

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 4.0 YEYO-PKG Manifest | 1 | VSCODE | ⬜ |
| 4.1 YEYO-PKG Builder | 1 | VSCODE | ⬜ |
| 4.2 YEYO-PKG Installer | 1 | VSCODE | ⬜ |
| 4.3 Permission System | 1 | VSCODE | ⬜ |
| 4.4 Container Security | 1 | VSCODE | ⬜ |
| 4.5 Privilege Levels | 1 | VSCODE | ⬜ |
| 4.6 Node Comm (Drag & Drop) | 1 | VSCODE | ⬜ |
| 4.7 Pipeline Engine | 2 | VSCODE | ⬜ |
| 4.8 Package Database | 1 | VSCODE | ⬜ |
| 4.9 Auto-Update | 1 | VSCODE | ⬜ |
| 4.10 Apt Abstraction | 1 | VSCODE | ⬜ |
| 4.11 Package API | 1 | VSCODE | ⬜ |
| 4.12 Package UI | 1 | VSCODE | ⬜ |
| 4.13 Integration Test | 1 | MIXTA | ⬜ |
| 4.14 EstadoGrafo Core | 1 | VSCODE | ⬜ |
| 4.15 Nodo Base + Decoradores | 1 | VSCODE | ⬜ |
| 4.16 Edge + Condiciones | 1 | VSCODE | ⬜ |
| 4.17 YeyoGrafo Coordinador | 1 | VSCODE | ⬜ |
| 4.18 NodoParalelo | 1 | VSCODE | ⬜ |
| 4.19 YeyoOrquestador + Ollama | 1 | VSCODE | ⬜ |
| 4.20 Catálogo de Nodos Base | 1 | VSCODE | ⬜ |
| 4.21 Grafos Estáticos | 1 | VSCODE | ⬜ |
| 4.22 WebSocket Graph Events | 1 | VSCODE | ⬜ |
| 4.23 Integration Test Orquestador | 1 | MIXTA | ⬜ |
| **TOTAL** | **26** | **23 VSCODE + 1 SIMPLE + 2 MIXTA** | |

---

## 🔌 Filosofía de Capa 4

Capa 4 conecta todo. Los paquetes, los permisos, los containers — es el **sistema nervioso** que permite que los órganos (nodos) funcionen en aislamiento seguro.

- **YEYO-PKG**: Formato .ypkg = tar.gz con manifest.yml + imagen container + bundle UI + assets + firma SHA-256.
- **Ciclo de vida**: create → build → install → use → update → remove.
- **Aislamiento**: Podman (NUNCA Docker), non-root, seccomp, no-new-privileges, capabilities dropped, PID/network namespaces.
- **6 niveles de privilegio**: ROOT(L0) > ADMIN(L1) > USER(L2) > LIMITED(L3) > GUEST(L4) > SANDBOX(L5).
- **Nodos IA**: SIEMPRE L5 (sandbox). Sin escalamiento posible.
- **Permisos**: ALLOWLIST — si no se solicita, no se concede. Diálogo estilo Android/iOS.
- **Docker socket**: JAMÁS montado en ningún container.
- **Pipelines**: Motor de pipelines con detección de ciclos (DAG). Drag & drop entre nodos.
- **Apt**: Invisible para el usuario. Solo dentro de containers.

**REGLA DE ORO**: Podman SIEMPRE. Docker NUNCA. Nodos generados por IA SIEMPRE en sandbox L5. Socket de Docker JAMÁS montado.

### YeyoOrquestador (4.14-4.23)

Las micro-fases 4.14-4.23 implementan el **YeyoOrquestador**, el motor de orquestación nativo de YeyoOS que reemplaza OpenClaw:

- **Diseño híbrido**: código Python puro + capa declarativa encima
- **EstadoGrafo**: objeto central que fluye entre nodos, serializable para checkpoints
- **Nodos**: 3 formas de definición (decorador `@nodo`, herencia, inline `lambda`)
- **Edges**: EdgeDirecto, EdgeCondicional con función sync/async, decorador `@edge`
- **YeyoGrafo**: API fluida con method chaining, sub-grafos, timeouts, retry
- **NodoParalelo**: asyncio.gather, fail_fast / continue_on_error
- **YeyoOrquestador**: integra con Ollama tool calling — Ollama elige qué grafo ejecutar
- **CatalogoNodos**: 5 nodos base registrados (chat, embeddings, memoria, log)
- **WebSocket events**: cada cambio de estado de nodo emite evento en tiempo real

## 🔗 Dependencias

- **Requiere**: Capa 0 (infraestructura) + Capa 1 (esqueleto) + Capa 2 (cerebro) + Capa 3 (cuerpo/UI)
- **Produce**: Sistema nervioso funcional — paquetes, permisos, containers seguros, pipelines, drag & drop, auto-update
