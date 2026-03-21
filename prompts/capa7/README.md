# 🚀 CAPA 7: EVOLUCIÓN — Prompts de Ejecución
# Total: 15 micro-fases → 17 prompts (12 VSCODE + 2 CLI + 2 MIXTA + 1 VSCODE/TS)
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
| **TOTAL** | **17** | **12 VSCODE + 2 CLI + 2 MIXTA + 1 VSCODE/TS** | |

---

## 🚀 Filosofía de Capa 7

Capa 7 es la EVOLUCIÓN. YeyoOS aprende, se distribuye, y se prueba como un reloj suizo. El Swiss Watch Test es la prueba final: si pasa, YeyoOS está listo para el mundo.

- **LoRA Training Pipeline**: Fine-tuning con QLoRA 4-bit para 3GB VRAM. SOLO en idle time (P3). Nightly.
- **Training Data Extractor**: Extrae datos de Flash Memory (correcciones, preferencias, skills). Mínimo 100 muestras.
- **LoRA Validation**: Compara modelo base vs LoRA. Auto-rollback si calidad baja >10%.
- **YEYO Store**: Marketplace de paquetes con niveles de confianza (Verified/Trusted/New). Scan de seguridad automático.
- **Store Security**: Análisis automatizado: manifiesto, container, red, firma, malware. Score 0-100.
- **Store Frontend**: UI integrada en Neural Hub. Búsqueda, categorías, reviews, instalación con diálogo de permisos.
- **ISO Builder**: Genera ISO bootable (~2-4GB). UEFI + Legacy BIOS. debootstrap + squashfs + xorriso.
- **Installation Wizard**: Setup de primer boot: idioma, timezone, usuario, Btrfs, Ollama, Flash Memory, Guardian.
- **Multi-User**: Roles (admin/user/guest). Flash Memory aislada por usuario. Login con argon2.
- **Data Migration**: Export/import cifrado AES-256. Merge inteligente (no overwrite).
- **Corporate Deployment**: ISO pre-configurada, políticas, LDAP placeholder, fleet management placeholder.
- **Performance Optimization**: Profiling final. Cache hit rate >80%, DB queries <50ms, frontend <3s.
- **Documentation Generator**: Genera docs HTML desde docstrings + OpenAPI spec.
- **YEYO Observer**: Monitoreo a largo plazo. Tendencias, alertas de degradación, reporte semanal.
- **Swiss Watch Test**: 50 checks, 9 fases, 24h endurance. ≥45/50 = RELEASE. <45 = NO RELEASE.

**REGLA DE ORO**: El Swiss Watch Test es la PRUEBA FINAL. 50 checks cubriendo las 7+2 capas. Test de endurance de 24h: sin memory leaks, sin VRAM leaks, 1000 mensajes de chat continuo. Score ≥45/50 o NO SE PUBLICA. Esta es la ÚLTIMA capa — después de esto, YeyoOS está listo para el mundo.

## 🔗 Dependencias

- **Requiere**: Capa 0 (infraestructura) + Capa 1 (esqueleto) + Capa 2 (cerebro) + Capa 3 (cuerpo/UI) + Capa 4 (sistema nervioso) + Capa 5 (órganos) + Capa 6 (sistema inmune)
- **Produce**: Sistema evolutivo completo — LoRA training, YEYO Store, ISO bootable, wizard de instalación, multi-usuario, migración de datos, deployment corporativo, optimización final, documentación, observer, y el SWISS WATCH TEST que valida TODO
