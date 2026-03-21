# 🧠 CAPA 2: CEREBRO — Prompts de Ejecución
# Total: 19 micro-fases → 22 prompts (20 VSCODE + 1 CLI + 1 MIXTA)
# Flujo: Copiar prompt → Pegar en Copilot (VS Code o CLI) → Ejecutar → Verificar → Siguiente
# ⚠️ Flash Memory NUNCA borra. NO existe método delete. NO existe endpoint DELETE.

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 2.0 — Flash Memory Schema | [prompt-2.0-1.md](prompt-2.0-1.md) | VSCODE | Media |
| 2.1 — Flash Memory CRUD | [prompt-2.1-1.md](prompt-2.1-1.md) | VSCODE | Media |
| 2.1 — Flash Memory Tests | [prompt-2.1-2.md](prompt-2.1-2.md) | VSCODE | Media |
| 2.2 — Redis Cache Layer | [prompt-2.2-1.md](prompt-2.2-1.md) | VSCODE | Media |
| 2.3 — Embedding Pipeline | [prompt-2.3-1.md](prompt-2.3-1.md) | VSCODE | Media |
| 2.4 — Tier Manager | [prompt-2.4-1.md](prompt-2.4-1.md) | VSCODE | Simple |
| 2.5 — Chat Basic | [prompt-2.5-1.md](prompt-2.5-1.md) | VSCODE | Media |
| 2.6 — Chat Contextual | [prompt-2.6-1.md](prompt-2.6-1.md) | VSCODE | Compleja |
| 2.6 — Chat Contextual Tests | [prompt-2.6-2.md](prompt-2.6-2.md) | VSCODE | Compleja |
| 2.7 — Conversation Manager | [prompt-2.7-1.md](prompt-2.7-1.md) | VSCODE | Media |
| 2.8 — Token Budget Manager | [prompt-2.8-1.md](prompt-2.8-1.md) | VSCODE | Simple |
| 2.9 — Memory Extraction | [prompt-2.9-1.md](prompt-2.9-1.md) | VSCODE | Media |
| 2.10 — Association Engine | [prompt-2.10-1.md](prompt-2.10-1.md) | VSCODE | Media |
| 2.11 — Anti-Hallucination | [prompt-2.11-1.md](prompt-2.11-1.md) | VSCODE | Compleja |
| 2.12 — RAG Pipeline | [prompt-2.12-1.md](prompt-2.12-1.md) | VSCODE | Compleja |
| 2.13 — System Prompt Builder | [prompt-2.13-1.md](prompt-2.13-1.md) | VSCODE | Simple |
| 2.14 — Feedback Loop | [prompt-2.14-1.md](prompt-2.14-1.md) | VSCODE | Media |
| 2.15 — Chat API Endpoints | [prompt-2.15-1.md](prompt-2.15-1.md) | VSCODE | Media |
| 2.16 — Memory API Endpoints | [prompt-2.16-1.md](prompt-2.16-1.md) | VSCODE | Simple |
| 2.17 — Background Tasks | [prompt-2.17-1.md](prompt-2.17-1.md) | VSCODE | Media |
| 2.18 — Integration Test Capa 2 | [prompt-2.18-1.md](prompt-2.18-1.md) | MIXTA | Compleja |

---

# 📊 RESUMEN CAPA 2

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 2.0 Flash Memory Schema | 1 | VSCODE | ⬜ |
| 2.1 Flash Memory CRUD | 2 | VSCODE | ⬜ |
| 2.2 Redis Cache | 1 | VSCODE | ⬜ |
| 2.3 Embeddings | 1 | VSCODE | ⬜ |
| 2.4 Tier Manager | 1 | VSCODE | ⬜ |
| 2.5 Chat Basic | 1 | VSCODE | ⬜ |
| 2.6 Chat Contextual | 2 | VSCODE | ⬜ |
| 2.7 Conversation Manager | 1 | VSCODE | ⬜ |
| 2.8 Token Budget | 1 | VSCODE | ⬜ |
| 2.9 Memory Extraction | 1 | VSCODE | ⬜ |
| 2.10 Associations | 1 | VSCODE | ⬜ |
| 2.11 Anti-Hallucination | 1 | VSCODE | ⬜ |
| 2.12 RAG Pipeline | 1 | VSCODE | ⬜ |
| 2.13 System Prompt | 1 | VSCODE | ⬜ |
| 2.14 Feedback | 1 | VSCODE | ⬜ |
| 2.15 Chat API | 1 | VSCODE | ⬜ |
| 2.16 Memory API | 1 | VSCODE | ⬜ |
| 2.17 Background Tasks | 1 | VSCODE | ⬜ |
| 2.18 Integration | 1 | MIXTA | ⬜ |
| **TOTAL** | **22** | **20 VSCODE + 1 CLI + 1 MIXTA** | |

---

## 🧠 Filosofía de Capa 2

Capa 2 es el **CEREBRO** de YeyoOS. Aquí la IA aprende, recuerda y razona.

- **Flash Memory**: Sistema de memoria persistente con 3 tiers (HOT/WARM/COLD). Las memorias **NUNCA se borran**. Un trigger de PostgreSQL previene físicamente cualquier DELETE.
- **Embeddings en CPU**: sentence-transformers (all-MiniLM-L6-v2, 384 dimensiones) corre en CPU. La GPU es exclusiva para Ollama e imagen.
- **Token Budget**: 4000 tokens máximo distribuidos: system(300) + memories(1000) + history(1500) + input(500) + response(700).
- **Anti-Alucinación**: Verificación automática de respuestas >50 tokens contra hechos conocidos en Flash Memory.
- **RAG Pipeline**: Retrieval-Augmented Generation conectando búsqueda semántica con generación de respuestas.
- **Asociaciones**: Red neuronal-like de conexiones entre memorias, creadas automáticamente por similitud semántica.

**REGLA DE ORO**: Flash Memory es sagrada. NADA se borra, NUNCA. No hay método `delete()`. No hay endpoint `DELETE`. Solo existe `store`, `recall`, `promote` y `demote`.

## 🔗 Dependencias

- **Requiere**: Capa 0 completada (infraestructura) + Capa 1 completada (interfaces/skeleton)
- **Produce**: Cerebro funcional — IA que recuerda, aprende, verifica y razona con contexto
