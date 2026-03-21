# 🔌 CAPA 4: SISTEMA NERVIOSO — Prompts de Ejecución
# Total: 14 micro-fases → 16 prompts (13 VSCODE + 1 VSCODE-SIMPLE + 1 MIXTA + 1 extra)
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
| **TOTAL** | **16** | **13 VSCODE + 1 SIMPLE + 1 MIXTA + 1 extra** | |

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

## 🔗 Dependencias

- **Requiere**: Capa 0 (infraestructura) + Capa 1 (esqueleto) + Capa 2 (cerebro) + Capa 3 (cuerpo/UI)
- **Produce**: Sistema nervioso funcional — paquetes, permisos, containers seguros, pipelines, drag & drop, auto-update
