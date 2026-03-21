# 🦴 CAPA 1: ESQUELETO — Prompts de Ejecución
# Total: 14 micro-fases → 18 prompts (16 VSCODE + 1 CLI + 1 MIXTA)
# Flujo: Copiar prompt → Pegar en Copilot (VS Code o CLI) → Ejecutar → Verificar → Siguiente
# ⚠️ Si las interfaces están mal, TODO lo de arriba se rompe

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 1.0 — IAProvider Interface | [prompt-1.0-1.md](prompt-1.0-1.md) | VSCODE | Simple |
| 1.1 — OllamaProvider Implementación | [prompt-1.1-1.md](prompt-1.1-1.md) | VSCODE | Media |
| 1.1 — OllamaProvider Tests | [prompt-1.1-2.md](prompt-1.1-2.md) | VSCODE | Media |
| 1.2 — MemoriaProvider Interface | [prompt-1.2-1.md](prompt-1.2-1.md) | VSCODE | Simple |
| 1.3 — Orquestador Interface | [prompt-1.3-1.md](prompt-1.3-1.md) | VSCODE | Simple |
| 1.4 — Config System | [prompt-1.4-1.md](prompt-1.4-1.md) | VSCODE | Media |
| 1.5 — Factory Pattern | [prompt-1.5-1.md](prompt-1.5-1.md) | VSCODE | Media |
| 1.6 — API Base FastAPI | [prompt-1.6-1.md](prompt-1.6-1.md) | VSCODE | Media |
| 1.6 — API Tests | [prompt-1.6-2.md](prompt-1.6-2.md) | VSCODE | Media |
| 1.7 — WebSocket Server | [prompt-1.7-1.md](prompt-1.7-1.md) | VSCODE | Media |
| 1.8 — GPU Scheduler | [prompt-1.8-1.md](prompt-1.8-1.md) | VSCODE | Compleja |
| 1.8 — GPU Scheduler Tests | [prompt-1.8-2.md](prompt-1.8-2.md) | VSCODE | Compleja |
| 1.9 — Event Bus | [prompt-1.9-1.md](prompt-1.9-1.md) | VSCODE | Media |
| 1.10 — Error Handling | [prompt-1.10-1.md](prompt-1.10-1.md) | VSCODE | Simple |
| 1.11 — Logging System | [prompt-1.11-1.md](prompt-1.11-1.md) | VSCODE | Simple |
| 1.12 — Health Check System | [prompt-1.12-1.md](prompt-1.12-1.md) | VSCODE | Media |
| 1.13 — Integration Test Capa 1 | [prompt-1.13-1.md](prompt-1.13-1.md) | MIXTA | Media |

---

# 📊 RESUMEN CAPA 1

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 1.0 IAProvider | 1 | VSCODE | ⬜ |
| 1.1 OllamaProvider | 2 | VSCODE | ⬜ |
| 1.2 MemoriaProvider | 1 | VSCODE | ⬜ |
| 1.3 Orquestador | 1 | VSCODE | ⬜ |
| 1.4 Config | 1 | VSCODE | ⬜ |
| 1.5 Factory | 1 | VSCODE | ⬜ |
| 1.6 API Base | 2 | VSCODE | ⬜ |
| 1.7 WebSocket | 1 | VSCODE | ⬜ |
| 1.8 GPU Scheduler | 2 | VSCODE | ⬜ |
| 1.9 Event Bus | 1 | VSCODE | ⬜ |
| 1.10 Errors | 1 | VSCODE | ⬜ |
| 1.11 Logging | 1 | VSCODE | ⬜ |
| 1.12 Health Check | 1 | VSCODE | ⬜ |
| 1.13 Integration | 1 | MIXTA | ⬜ |
| **TOTAL** | **18** | **16 VSCODE + 1 CLI + 1 MIXTA** | |

---

## 🧠 Filosofía de Capa 1

Capa 1 crea el **ESQUELETO** de YeyoOS. Aquí definimos:
- **Interfaces abstractas** (puertos hexagonales) que permiten intercambiar componentes
- **Configuración centralizada** con validación y defaults
- **Patrones fundamentales**: Factory, Event Bus, Singleton
- **Skeleton de API** con FastAPI + WebSocket
- **GPU Scheduler** con prioridades para 3GB VRAM
- **Sistema de errores y logging** estructurado

**REGLA DE ORO**: Si las interfaces de Capa 1 están mal, TODAS las capas superiores se rompen. Cada interfaz debe ser pensada como un contrato irrompible.

## 🔗 Dependencias

- **Requiere**: Capa 0 completada (todos los 25 tests pasando)
- **Produce**: Skeleton listo para implementaciones concretas en Capa 2
