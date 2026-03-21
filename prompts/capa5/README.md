# 🫀 CAPA 5: ÓRGANOS — Prompts de Ejecución
# Total: 22 micro-fases → 24 prompts (20 VSCODE + 2 VSCODE-SIMPLE + 1 MIXTA + 1 extra)
# Flujo: Copiar prompt → Pegar en Copilot (VS Code o CLI) → Ejecutar → Verificar → Siguiente
# ⚠️ GPU NUNCA para minería. FFmpeg SIEMPRE validado. Sandbox: sin red, 30s timeout, container efímero.

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 5.0 — NodeBase Template | [prompt-5.0-1.md](prompt-5.0-1.md) | VSCODE | Media |
| 5.1 — Chat Node | [prompt-5.1-1.md](prompt-5.1-1.md) | VSCODE | Compleja |
| 5.2 — Image Node (Generation) | [prompt-5.2-1.md](prompt-5.2-1.md) | VSCODE | Compleja |
| 5.3 — Image Node (img2img + Analysis) | [prompt-5.3-1.md](prompt-5.3-1.md) | VSCODE | Media |
| 5.4 — Image Node MiniChat v1 | [prompt-5.4-1.md](prompt-5.4-1.md) | VSCODE | Simple |
| 5.5 — Video Node (FFmpeg) | [prompt-5.5-1.md](prompt-5.5-1.md) | VSCODE | Compleja |
| 5.5 — Video Node (FFmpeg Validation) | [prompt-5.5-2.md](prompt-5.5-2.md) | VSCODE | Compleja |
| 5.6 — Video Node (Subtitles + TTS) | [prompt-5.6-1.md](prompt-5.6-1.md) | VSCODE | Media |
| 5.7 — Code Node (Editor) | [prompt-5.7-1.md](prompt-5.7-1.md) | VSCODE | Media |
| 5.8 — Code Node (Sandbox Execution) | [prompt-5.8-1.md](prompt-5.8-1.md) | VSCODE | Compleja |
| 5.9 — Code Node (Git Integration) | [prompt-5.9-1.md](prompt-5.9-1.md) | VSCODE | Media |
| 5.10 — Automation Node (Pipeline Visual) | [prompt-5.10-1.md](prompt-5.10-1.md) | VSCODE | Compleja |
| 5.11 — Automation Node (Social APIs) | [prompt-5.11-1.md](prompt-5.11-1.md) | VSCODE | Media |
| 5.12 — Files Node | [prompt-5.12-1.md](prompt-5.12-1.md) | VSCODE | Media |
| 5.13 — Browser Node | [prompt-5.13-1.md](prompt-5.13-1.md) | VSCODE | Media |
| 5.14 — Config Node | [prompt-5.14-1.md](prompt-5.14-1.md) | VSCODE | Media |
| 5.15 — Mining Node | [prompt-5.15-1.md](prompt-5.15-1.md) | VSCODE | Simple |
| 5.16 — Node Registry | [prompt-5.16-1.md](prompt-5.16-1.md) | VSCODE | Media |
| 5.17 — Node API Endpoints | [prompt-5.17-1.md](prompt-5.17-1.md) | VSCODE | Media |
| 5.18 — MiniChat v2 (Node Context) | [prompt-5.18-1.md](prompt-5.18-1.md) | VSCODE | Media |
| 5.19 — MiniChat v3 (Actions) | [prompt-5.19-1.md](prompt-5.19-1.md) | VSCODE | Media |
| 5.20 — Node Health Monitor | [prompt-5.20-1.md](prompt-5.20-1.md) | VSCODE | Simple |
| 5.21 — Integration Test Capa 5 | [prompt-5.21-1.md](prompt-5.21-1.md) | MIXTA | Compleja |

---

# 📊 RESUMEN CAPA 5

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 5.0 NodeBase Template | 1 | VSCODE | ⬜ |
| 5.1 Chat Node | 1 | VSCODE | ⬜ |
| 5.2 Image Gen | 1 | VSCODE | ⬜ |
| 5.3 Image img2img | 1 | VSCODE | ⬜ |
| 5.4 MiniChat v1 | 1 | VSCODE | ⬜ |
| 5.5 Video FFmpeg | 2 | VSCODE | ⬜ |
| 5.6 Video Subtitles+TTS | 1 | VSCODE | ⬜ |
| 5.7 Code Editor | 1 | VSCODE | ⬜ |
| 5.8 Code Sandbox | 1 | VSCODE | ⬜ |
| 5.9 Code Git | 1 | VSCODE | ⬜ |
| 5.10 Automation Visual | 1 | VSCODE | ⬜ |
| 5.11 Automation Social | 1 | VSCODE | ⬜ |
| 5.12 Files Node | 1 | VSCODE | ⬜ |
| 5.13 Browser Node | 1 | VSCODE | ⬜ |
| 5.14 Config Node | 1 | VSCODE | ⬜ |
| 5.15 Mining Node | 1 | VSCODE | ⬜ |
| 5.16 Node Registry | 1 | VSCODE | ⬜ |
| 5.17 Node API | 1 | VSCODE | ⬜ |
| 5.18 MiniChat v2 | 1 | VSCODE | ⬜ |
| 5.19 MiniChat v3 | 1 | VSCODE | ⬜ |
| 5.20 Health Monitor | 1 | VSCODE | ⬜ |
| 5.21 Integration Test | 1 | MIXTA | ⬜ |
| **TOTAL** | **24** | **20 VSCODE + 2 SIMPLE + 1 MIXTA + 1 extra** | |

---

## 🫀 Filosofía de Capa 5

Capa 5 son los ÓRGANOS de YeyoOS. Cada nodo es un órgano especializado que cobra vida dentro del Neural Hub. Cada nodo hereda de NodeBase, corre en un container aislado (Capa 4), tiene permisos, usa el GPU scheduler, y puede comunicarse con otros nodos.

- **NodeBase**: Clase base abstracta. Lifecycle: initialize → render_ui → process → cleanup.
- **Chat Node**: Conversaciones multi-tab, búsqueda, export, streaming.
- **Image Node**: Generación SD 1.5, img2img, análisis LLaVA. GPU scheduler obligatorio.
- **Video Node**: FFmpeg desde lenguaje natural. Comandos SIEMPRE validados antes de ejecutar.
- **Code Node**: Monaco editor + sandbox efímero (sin red, 30s timeout, 256MB RAM).
- **Automation Node**: Pipelines visuales con React Flow + APIs sociales.
- **Files Node**: Explorador + búsqueda semántica por embeddings.
- **Browser Node**: Webview sandboxed + resumen de páginas con IA.
- **Config Node**: Configuración del sistema, monitor GPU, gestión de modelos.
- **Mining Node**: Dashboard ASIC SOLAMENTE. GPU NUNCA para minería.
- **MiniChat**: Evolución v1(básico) → v2(contexto por nodo) → v3(acciones ejecutables).
- **Node Registry**: Registro central de todos los tipos de nodo.
- **Health Monitor**: Monitoreo de salud, auto-restart, máximo 3 intentos.

**REGLA DE ORO**: GPU NUNCA para minería — exclusivamente para IA. FFmpeg SIEMPRE validado antes de ejecutar. Code sandbox: sin red, 30s timeout, container efímero auto-destruido. MiniChat SIEMPRE pide confirmación antes de ejecutar acciones.

## 🔗 Dependencias

- **Requiere**: Capa 0 (infraestructura) + Capa 1 (esqueleto) + Capa 2 (cerebro) + Capa 3 (cuerpo/UI) + Capa 4 (sistema nervioso)
- **Produce**: Todos los nodos funcionales — chat, imagen, video, código, automatización, archivos, browser, config, minería, registro, API, MiniChat contextual con acciones, health monitor
