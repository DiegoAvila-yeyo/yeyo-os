# 🚀 CAPA 7: EVOLUCIÓN — Prompts de Ejecución
# Total: 28 micro-fases → 30 prompts (23 VSCODE + 4 CLI + 2 MIXTA + 1 VSCODE/TS)
# Flujo: Copiar prompt → Pegar en Copilot (VS Code o CLI) → Ejecutar → Verificar → Siguiente
# ⚠️ Swiss Watch Test: 50 checks, 9 fases, ≥45/50 para release. Si no pasa, NO SE PUBLICA.

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 7.0 — LoRA Training Pipeline | [prompt-7.0-1.md](prompt-7.0-1.md) | VSCODE | Compleja |
| 7.1 — LoRA Validation & Apply | [prompt-7.1-1.md](prompt-7.1-1.md) | VSCODE | Media |
| 7.2 — Training Data Extractor | [prompt-7.2-1.md](prompt-7.2-1.md) | VSCODE | Media |
| 7.3 — YEYO Store Server | [prompt-7.3-1.md](prompt-7.3-1.md) | VSCODE | Compleja |
| 7.4 — YEYO Store Security Pipeline | [prompt-7.4-1.md](prompt-7.4-1.md) | VSCODE | Compleja |
| 7.5 — YEYO Store Frontend | [prompt-7.5-1.md](prompt-7.5-1.md) | VSCODE | Media |
| 7.6 — ISO Builder | [prompt-7.6-1.md](prompt-7.6-1.md) | CLI | Compleja |
| 7.6 — ISO Verification | [prompt-7.6-2.md](prompt-7.6-2.md) | CLI | Compleja |
| 7.7 — Installation Wizard | [prompt-7.7-1.md](prompt-7.7-1.md) | VSCODE | Media |
| 7.8 — Multi-User System | [prompt-7.8-1.md](prompt-7.8-1.md) | VSCODE | Compleja |
| 7.9 — User Data Migration | [prompt-7.9-1.md](prompt-7.9-1.md) | VSCODE | Media |
| 7.10 — Corporate Deployment | [prompt-7.10-1.md](prompt-7.10-1.md) | VSCODE | Media |
| 7.11 — Performance Optimization | [prompt-7.11-1.md](prompt-7.11-1.md) | VSCODE | Media |
| 7.12 — Documentation Generator | [prompt-7.12-1.md](prompt-7.12-1.md) | VSCODE | Simple |
| 7.13 — YEYO Observer | [prompt-7.13-1.md](prompt-7.13-1.md) | VSCODE | Media |
| 7.14 — Swiss Watch Test | [prompt-7.14-1.md](prompt-7.14-1.md) | MIXTA | Compleja |
| 7.15 — YEYO Store: UI Rediseñada + Backend | [prompt-7.15-1.md](prompt-7.15-1.md) | VSCODE | Compleja |
| 7.16 — Node Studio: Crear y Publicar Nodos | [prompt-7.16-1.md](prompt-7.16-1.md) | VSCODE | Compleja |
| 7.17 — YeyoNet Core: Backend Distribuido | [prompt-7.17-1.md](prompt-7.17-1.md) | VSCODE | Compleja |
| 7.18 — YeyoNet UI: Panel de Satélites | [prompt-7.18-1.md](prompt-7.18-1.md) | VSCODE | Compleja |
| 7.19 — Cluster Mode: Celery Workers | [prompt-7.19-1.md](prompt-7.19-1.md) | VSCODE | Compleja |
| 7.20 — Cluster Mode: Distributed GPU Scheduler | [prompt-7.20-1.md](prompt-7.20-1.md) | VSCODE | Compleja |
| 7.21 — Cluster Mode: Federated Learning (Flower) | [prompt-7.21-1.md](prompt-7.21-1.md) | VSCODE | Compleja |
| 7.22 — Cluster Mode: Dashboard UI | [prompt-7.22-1.md](prompt-7.22-1.md) | VSCODE | Compleja |
| 7.23 — YeyoNet: Instalador automático (.sh) | [prompt-7.23-1.md](prompt-7.23-1.md) | CLI | Compleja |
| 7.24 — YeyoNet: ISO Booteable | [prompt-7.24-1.md](prompt-7.24-1.md) | CLI | Compleja |
| 7.25 — Schedule Nocturno Unificado | [prompt-7.25-1.md](prompt-7.25-1.md) | VSCODE | Compleja |
| 7.26 — Autodidacta: Curriculum Dinámico | [prompt-7.26-1.md](prompt-7.26-1.md) | VSCODE | Compleja |
| 7.27 — YeyoPublisher: Deploy Multiplataforma | [prompt-7.27-1.md](prompt-7.27-1.md) | VSCODE | Compleja |

---

# 📊 RESUMEN CAPA 7

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 7.0 LoRA Pipeline | 1 | VSCODE | ⬜ |
| 7.1 LoRA Validation | 1 | VSCODE | ⬜ |
| 7.2 Data Extractor | 1 | VSCODE | ⬜ |
| 7.3 Store Server | 1 | VSCODE | ⬜ |
| 7.4 Store Security | 1 | VSCODE | ⬜ |
| 7.5 Store Frontend | 1 | VSCODE | ⬜ |
| 7.6 ISO Builder | 2 | CLI | ⬜ |
| 7.7 Installation Wizard | 1 | VSCODE | ⬜ |
| 7.8 Multi-User | 1 | VSCODE | ⬜ |
| 7.9 Data Migration | 1 | VSCODE | ⬜ |
| 7.10 Corporate Deploy | 1 | VSCODE | ⬜ |
| 7.11 Performance Opt | 1 | VSCODE | ⬜ |
| 7.12 Docs Generator | 1 | VSCODE | ⬜ |
| 7.13 YEYO Observer | 1 | VSCODE | ⬜ |
| 7.14 Swiss Watch Test | 1 | MIXTA | ⬜ |
| 7.15 YEYO Store Rediseñado | 1 | VSCODE | ⬜ |
| 7.16 Node Studio | 1 | VSCODE | ⬜ |
| 7.17 YeyoNet Core | 1 | VSCODE | ⬜ |
| 7.18 YeyoNet UI | 1 | VSCODE | ⬜ |
| 7.19 Cluster Workers | 1 | VSCODE | ⬜ |
| 7.20 GPU Scheduler | 1 | VSCODE | ⬜ |
| 7.21 Federated Learning | 1 | VSCODE | ⬜ |
| 7.22 Cluster Dashboard | 1 | VSCODE | ⬜ |
| 7.23 Instalador .sh | 1 | CLI | ⬜ |
| 7.24 ISO Booteable | 1 | CLI | ⬜ |
| 7.25 Schedule Nocturno | 1 | VSCODE | ⬜ |
| 7.26 Autodidacta | 1 | VSCODE | ⬜ |
| 7.27 YeyoPublisher | 1 | VSCODE | ⬜ |
| **TOTAL** | **30** | **23 VSCODE + 4 CLI + 2 MIXTA + 1 VSCODE/TS** | |

---

## 🚀 Filosofía de Capa 7

Capa 7 es la EVOLUCIÓN. YeyoOS aprende, se distribuye, y se prueba como un reloj suizo. El Swiss Watch Test es la prueba final: si pasa, YeyoOS está listo para el mundo.

- **LoRA Training Pipeline**: Fine-tuning con QLoRA 4-bit para 3GB VRAM. SOLO en idle time (P3). Nightly.
- **YEYO Store**: Marketplace de paquetes con niveles de confianza (Verified/Trusted/New). Scan de seguridad automático.
- **Store Security**: Análisis automatizado: manifiesto, container, red, firma, malware. Score 0-100.
- **Store Frontend**: UI integrada en Neural Hub. Búsqueda, categorías, reviews, instalación con diálogo de permisos.
- **Instaladores Multiplataforma**: Generadores de .exe (Windows), .dmg (Mac), .deb/.rpm (Linux). Installation wizard: idioma, timezone, usuario, Ollama, Flash Memory, Guardian.
- **Multi-User**: Roles (admin/user/guest). Flash Memory aislada por usuario. Login con argon2.
- **Data Migration**: Export/import cifrado AES-256. Merge inteligente (no overwrite).
- **Corporate Deployment**: Políticas pre-configuradas, LDAP placeholder, fleet management placeholder.
- **Performance Optimization**: Profiling final. Cache hit rate >80%, DB queries <50ms, frontend <3s.
- **Documentation Generator**: Genera docs HTML desde docstrings + OpenAPI spec.
- **YEYO Observer**: Monitoreo a largo plazo. Tendencias, alertas de degradación, reporte semanal.
- **Swiss Watch Test**: 50 checks, 9 fases, 24h endurance. ≥45/50 = RELEASE. <45 = NO RELEASE.
- **YeyoNet Core**: Backend distribuido — relay WebSocket, sync de Flash Memory, invitaciones YEYO-XXXX.
- **YeyoNet UI**: Panel de satélites con estado en tiempo real, invitaciones y niveles de visibilidad.
- **Cluster Workers**: Celery + Redis — generate_image_task, run_graph_task, train_lora_task. IdleDetector reporta satélites idle al Central.
- **GPU Scheduler**: gRPC — GPUPool registra VRAM de cada nodo, allocate_best() elige el nodo con más VRAM libre.
- **Federated Learning**: Flower — FedAvg de mini-LoRAs locales. PrivacyFilter con differential privacy.
- **Cluster Dashboard**: React/TS — nodos, métricas Prometheus en tiempo real, cola de tareas distribuidas.

**REGLA DE ORO**: El Swiss Watch Test es la PRUEBA FINAL. 50 checks cubriendo las 7+2 capas. Test de endurance de 24h: sin memory leaks, sin VRAM leaks, 1000 mensajes de chat continuo. Score ≥45/50 o NO SE PUBLICA. Esta es la ÚLTIMA capa — después de esto, YeyoOS está listo para el mundo.

## 🔗 Dependencias

- **Requiere**: Capa 0 (infraestructura) + Capa 1 (esqueleto) + Capa 2 (cerebro) + Capa 3 (cuerpo/UI) + Capa 4 (sistema nervioso) + Capa 5 (órganos) + Capa 6 (sistema inmune)
- **Produce**: Sistema evolutivo completo — LoRA training, YEYO Store, ISO bootable, wizard de instalación, multi-usuario, migración de datos, deployment corporativo, optimización final, documentación, observer, Swiss Watch Test, YeyoNet Core + UI, Cluster Mode (workers, GPU scheduler, federated learning, dashboard), instalador bash e ISO booteable completa
