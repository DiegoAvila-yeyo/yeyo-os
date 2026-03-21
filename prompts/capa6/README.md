# 🛡️ CAPA 6: SISTEMA INMUNE — Prompts de Ejecución
# Total: 12 micro-fases → 14 prompts (9 VSCODE + 2 CLI + 1 VSCODE+CLI + 1 MIXTA + 1 extra)
# Flujo: Copiar prompt → Pegar en Copilot (VS Code o CLI) → Ejecutar → Verificar → Siguiente
# ⚠️ Kill Switch PAUSA, nunca mata. Flash Memory = lo más valioso, NUNCA se borra. Guardian en RUST obligatorio.

---

## 📋 Índice de Prompts

| Micro-fase | Archivo | Tipo | Complejidad |
|:---|:---|:---:|:---:|
| 6.0 — Guardian Daemon Base | [prompt-6.0-1.md](prompt-6.0-1.md) | VSCODE | Compleja |
| 6.0 — Guardian Daemon Tests | [prompt-6.0-2.md](prompt-6.0-2.md) | VSCODE | Compleja |
| 6.1 — Guardian Anomaly Detection | [prompt-6.1-1.md](prompt-6.1-1.md) | VSCODE | Compleja |
| 6.2 — Guardian Auto-Response | [prompt-6.2-1.md](prompt-6.2-1.md) | VSCODE | Media |
| 6.3 — Kill Switch | [prompt-6.3-1.md](prompt-6.3-1.md) | VSCODE+CLI | Compleja |
| 6.4 — Smart Snapshots | [prompt-6.4-1.md](prompt-6.4-1.md) | VSCODE | Media |
| 6.5 — Backup System (3-2-1) | [prompt-6.5-1.md](prompt-6.5-1.md) | CLI | Compleja |
| 6.6 — Anti-Ransomware | [prompt-6.6-1.md](prompt-6.6-1.md) | VSCODE | Media |
| 6.7 — Honeypots | [prompt-6.7-1.md](prompt-6.7-1.md) | VSCODE | Media |
| 6.8 — Network Firewall Advanced | [prompt-6.8-1.md](prompt-6.8-1.md) | CLI | Media |
| 6.9 — Security Dashboard | [prompt-6.9-1.md](prompt-6.9-1.md) | VSCODE | Media |
| 6.10 — Security Audit System | [prompt-6.10-1.md](prompt-6.10-1.md) | VSCODE | Media |
| 6.11 — Integration Test Capa 6 | [prompt-6.11-1.md](prompt-6.11-1.md) | MIXTA | Compleja |

---

# 📊 RESUMEN CAPA 6

| Micro-fase | Prompts | Tipo | Estado |
|:---:|:---:|:---:|:---:|
| 6.0 Guardian Daemon Base | 2 | VSCODE | ⬜ |
| 6.1 Anomaly Detection | 1 | VSCODE | ⬜ |
| 6.2 Auto-Response | 1 | VSCODE | ⬜ |
| 6.3 Kill Switch | 1 | VSCODE+CLI | ⬜ |
| 6.4 Smart Snapshots | 1 | VSCODE | ⬜ |
| 6.5 Backup 3-2-1 | 1 | CLI | ⬜ |
| 6.6 Anti-Ransomware | 1 | VSCODE | ⬜ |
| 6.7 Honeypots | 1 | VSCODE | ⬜ |
| 6.8 Network Firewall | 1 | CLI | ⬜ |
| 6.9 Security Dashboard | 1 | VSCODE | ⬜ |
| 6.10 Audit System | 1 | VSCODE | ⬜ |
| 6.11 Integration Test | 1 | MIXTA | ⬜ |
| **TOTAL** | **14** | **9 VSCODE + 2 CLI + 1 VSCODE+CLI + 1 MIXTA + 1 extra** | |

---

## 🛡️ Filosofía de Capa 6

Capa 6 es el SISTEMA INMUNE. Guardian protege a YeyoOS como los glóbulos blancos protegen al cuerpo. La Flash Memory es más valiosa que el propio OS.

- **Guardian Daemon**: Daemon en Rust que monitorea TODO el sistema. Corre como servicio systemd, arranca antes que todo.
- **Anomaly Detection**: Detección de anomalías estadística (z-score). Sin ML pesado, eficiente y rápido.
- **Auto-Response**: Respuestas automáticas a eventos de seguridad. NUNCA borra nada automáticamente.
- **Kill Switch**: Ctrl+Alt+K — PAUSA toda la IA. No mata, PAUSA. Funciona incluso sin UI.
- **Smart Snapshots**: Btrfs snapshots disparados por eventos, no solo por tiempo.
- **Backup 3-2-1**: 3 copias, 2 medios diferentes, 1 offsite. Restic cifrado AES-256.
- **Anti-Ransomware**: Detecta cifrado masivo de archivos, pausa inmediata.
- **Honeypots**: Archivos y servicios falsos para detectar intrusiones.
- **Network Firewall**: nftables avanzado, aislamiento por container, rate limiting.
- **Security Dashboard**: Frontend para ver estado de Guardian en tiempo real.
- **Audit System**: Log append-only con cadena SHA-256. NO UPDATE, NO DELETE.

**REGLA DE ORO**: Kill Switch PAUSA, nunca mata. Flash Memory es lo MÁS VALIOSO — se respalda cada hora, nunca se borra automáticamente. Guardian en Rust obligatorio (no Python). Backups cifrados con restic AES-256.

## 🔗 Dependencias

- **Requiere**: Capa 0 (infraestructura) + Capa 1 (esqueleto) + Capa 2 (cerebro) + Capa 3 (cuerpo/UI) + Capa 4 (sistema nervioso) + Capa 5 (órganos)
- **Produce**: Sistema inmune completo — Guardian daemon, anomaly detection, kill switch, backups 3-2-1, anti-ransomware, honeypots, firewall avanzado, dashboard de seguridad, audit trail tamper-proof
