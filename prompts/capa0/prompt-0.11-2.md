## ═══════════════════════════════════════
## MICRO-FASE 0.11 — Security Base
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.11-2 [CLI] — Audit logging y firewall básico

```
Estamos construyendo YeyoOS. Micro-fase 0.11, Prompt 2 de 2: configurar audit logging y firewall básico.

PREREQUISITO: Prompt 0.11-1 completado (usuarios y permisos).

EJECUTAR:
1. Instalar y configurar auditd:
   sudo apt install -y auditd
   sudo systemctl enable --now auditd

2. Crear reglas de auditoría para YeyoOS:
   Crear /etc/audit/rules.d/yeyo.rules:
   # Monitorear cambios en configuración de YeyoOS
   -w /var/lib/yeyo/config/ -p wa -k yeyo-config
   -w /etc/systemd/system/yeyo.target -p wa -k yeyo-systemd
   
   # Monitorear accesos a archivos sensibles
   -w /etc/passwd -p wa -k auth-change
   -w /etc/shadow -p wa -k auth-change
   -w /etc/sudoers -p wa -k sudo-change
   
   # Monitorear ejecución de comandos privilegiados
   -a always,exit -F arch=b64 -S execve -F euid=0 -k root-commands

3. Recargar reglas:
   sudo auditctl -R /etc/audit/rules.d/yeyo.rules

4. Configurar firewall básico con ufw:
   sudo apt install -y ufw
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow from 127.0.0.1
   sudo ufw --force enable

5. Crear directorio de logs estructurados de YeyoOS:
   sudo mkdir -p /var/log/yeyo/{guardian,api,memory,security}
   sudo chown -R yeyo-service:yeyo-users /var/log/yeyo/
   sudo chmod -R 750 /var/log/yeyo/

6. Configurar logrotate para YeyoOS:
   Crear /etc/logrotate.d/yeyo:
   /var/log/yeyo/*/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
       create 640 yeyo-service yeyo-users
   }

7. Crear test de seguridad básico:
   cd ~/yeyo-os
   source .venv/bin/activate
   
   Crear tests/test_security.py:
   import subprocess
   import os
   
   def test_env_not_world_readable():
       mode = oct(os.stat('.env').st_mode)[-3:]
       assert mode == '600', f".env permisos: {mode}, esperado: 600"
   
   def test_services_only_localhost():
       result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
       lines = result.stdout.strip().split('\n')[1:]  # skip header
       for line in lines:
           if '127.0.0.1' not in line and '::1' not in line and '*:22' not in line:
               if '0.0.0.0' in line or ':::' in line:
                   assert False, f"Servicio expuesto: {line}"
   
   def test_audit_running():
       result = subprocess.run(['systemctl', 'is-active', 'auditd'], capture_output=True, text=True)
       assert result.stdout.strip() == 'active'

8. Ejecutar tests:
   pytest tests/test_security.py -v

VERIFICAR:
- [ ] Auditd corriendo: `systemctl status auditd` → active
- [ ] Reglas cargadas: `sudo auditctl -l` → muestra reglas yeyo
- [ ] Firewall activo: `sudo ufw status` → active, default deny incoming
- [ ] Log dirs existen: `ls /var/log/yeyo/` → guardian, api, memory, security
- [ ] Logrotate configurado: `cat /etc/logrotate.d/yeyo` → existe
- [ ] Security tests pasan: `pytest tests/test_security.py -v` → 3 passed

SI FALLA:
- ufw bloquea WSL: `sudo ufw allow from 172.16.0.0/12` (rango WSL)
- auditd no arranca: verificar que no hay otra instancia

NO HACER:
- No configurar firewall complejo aún (Capa 6.9)
- No bloquear SSH si lo necesitas para desarrollo

GATE: Auditd corriendo con reglas YeyoOS, firewall deny incoming activo, logs rotativos configurados, 3 security tests pasan.
```
