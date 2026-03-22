# 🏗️ CAPA 0: CIMIENTOS — Prompts de Ejecución
# Total: 9 micro-fases → 14 prompts (12 CLI + 1 VSCODE + 1 MIXTA)
# Flujo: Copiar prompt → Pegar en Copilot CLI o VS Code → Ejecutar → Verificar → Siguiente

> **⚠️ Nota:** Capa 0 prepara el ENTORNO DE DESARROLLO. Para ISO/distribución completa, ver Capa 7.

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 0.3 — PostgreSQL Install | [prompt-0.3-1.md](prompt-0.3-1.md) | CLI | Media |
| 0.3 — PostgreSQL Schema | [prompt-0.3-2.md](prompt-0.3-2.md) | CLI | Media |
| 0.4 — Redis 7 | [prompt-0.4-1.md](prompt-0.4-1.md) | CLI | Simple |
| 0.5 — Node.js 20 LTS | [prompt-0.5-1.md](prompt-0.5-1.md) | CLI | MIXTA |
| 0.5 — Next.js Scaffold | [prompt-0.5-2.md](prompt-0.5-2.md) | VSCODE | MIXTA |
| 0.6 — Python 3.11 | [prompt-0.6-1.md](prompt-0.6-1.md) | CLI | Simple |
| 0.8 — Ollama Install | [prompt-0.8-1.md](prompt-0.8-1.md) | CLI | Media |
| 0.8 — Ollama Verify | [prompt-0.8-2.md](prompt-0.8-2.md) | CLI | Media |
| 0.9 — Podman | [prompt-0.9-1.md](prompt-0.9-1.md) | CLI | Simple |
| 0.10 — GPU Drivers | [prompt-0.10-1.md](prompt-0.10-1.md) | CLI | Media |
| 0.10 — GPU Model + Container | [prompt-0.10-2.md](prompt-0.10-2.md) | CLI | Media |
| 0.11 — Security Users | [prompt-0.11-1.md](prompt-0.11-1.md) | CLI | Media |
| 0.11 — Security Audit | [prompt-0.11-2.md](prompt-0.11-2.md) | CLI | Media |
| 0.12 — Integration Test | [prompt-0.12-1.md](prompt-0.12-1.md) | CLI | Media |

---

# 📊 RESUMEN CAPA 0

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 0.3 PostgreSQL | 2 | CLI | ⬜ |
| 0.4 Redis | 1 | CLI | ⬜ |
| 0.5 Node.js | 2 | CLI+VSCODE | ⬜ |
| 0.6 Python | 1 | CLI | ⬜ |
| 0.8 Ollama | 2 | CLI | ⬜ |
| 0.9 Podman | 1 | CLI | ⬜ |
| 0.10 GPU | 2 | CLI | ⬜ |
| 0.11 Security | 2 | CLI | ⬜ |
| 0.12 Integration | 1 | CLI | ⬜ |
| **TOTAL** | **14** | **12 CLI + 1 VSCODE + 1 MIXTA** | |

---

## 🗑️ Prompts Removidos (Obsoletos — Arquitectura Anterior)

> YeyoOS es ahora un **Shell de IA fullscreen** que corre sobre Windows/Mac/Linux, no un custom Linux OS.
> Los siguientes prompts fueron diseñados para el plan anterior y ya no son necesarios:

- ~~0.0 — Particiones Btrfs~~ (Only for OS-level setup)
- ~~0.1 — Kernel Headers y Módulos~~ (Only for kernel module compilation)
- ~~0.2 — Systemd Base~~ (Only for OS init system)
- ~~0.7 — Rust Toolchain~~ (Was for Wayland compositor, now using browser-based approach)
