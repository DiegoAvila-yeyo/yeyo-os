## ═══════════════════════════════════════
## MICRO-FASE 0.2 — Systemd Base
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.2-1 [CLI] — Configurar Systemd y servicios base

```
Estamos construyendo YeyoOS. Micro-fase 0.2: configurar systemd como init system y preparar la estructura de servicios.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.1 completadas.

EJECUTAR:
1. Verificar que systemd está activo (WSL2 necesita configuración):
   ps -p 1 -o comm=
   Si NO dice "systemd", configurar:
   - Crear /etc/wsl.conf con:
     [boot]
     systemd=true
   - Reiniciar WSL desde PowerShell: wsl --shutdown

2. Crear directorio para servicios de YeyoOS:
   sudo mkdir -p /etc/systemd/system/yeyo.target.wants

3. Crear target personalizado para YeyoOS:
   Crear archivo /etc/systemd/system/yeyo.target con:
   [Unit]
   Description=YeyoOS Services
   Requires=multi-user.target
   After=multi-user.target

4. Crear template de servicio (usaremos para todos los servicios):
   Crear /etc/systemd/system/yeyo-template@.service con:
   [Unit]
   Description=YeyoOS %i Service
   After=network.target
   PartOf=yeyo.target

   [Service]
   Type=simple
   Restart=always
   RestartSec=3
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=yeyo.target

5. Recargar systemd:
   sudo systemctl daemon-reload

VERIFICAR:
- [ ] Systemd es PID 1: `ps -p 1 -o comm=` → systemd
- [ ] Target creado: `systemctl cat yeyo.target` → muestra contenido
- [ ] Template creado: `systemctl cat yeyo-template@.service` → muestra contenido
- [ ] Journal funciona: `journalctl --no-pager -n 5` → últimas 5 líneas
- [ ] No errores: `systemctl --failed` → 0 failed units (o solo las que ya existían)

SI FALLA:
- WSL2 sin systemd: necesitas Windows 11 + WSL2 actualizado
- Si no puedes usar systemd: Plan B con supervisord (pip install supervisor)

GATE: systemd como PID 1, yeyo.target cargado, journal funcional.
```
