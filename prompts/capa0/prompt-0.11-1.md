## ═══════════════════════════════════════
## MICRO-FASE 0.11 — Security Base
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.11-1 [CLI] — Usuarios, permisos y estructura de seguridad

```
Estamos construyendo YeyoOS. Micro-fase 0.11, Prompt 1 de 2: configurar la base de seguridad del sistema.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.10 completadas. Todo instalado.

EJECUTAR:
1. Crear usuario de sistema para servicios de YeyoOS (no login):
   sudo useradd -r -s /usr/sbin/nologin -d /var/lib/yeyo yeyo-service

2. Crear grupo para acceso a recursos de YeyoOS:
   sudo groupadd yeyo-users

3. Agregar tu usuario al grupo:
   sudo usermod -aG yeyo-users $USER

4. Configurar permisos de directorios:
   sudo mkdir -p /var/lib/yeyo/{config,models,packages,logs,run}
   sudo mkdir -p /var/log/yeyo
   sudo chown -R yeyo-service:yeyo-users /var/lib/yeyo
   sudo chown -R yeyo-service:yeyo-users /var/log/yeyo
   sudo chmod -R 750 /var/lib/yeyo
   sudo chmod -R 750 /var/log/yeyo

5. Proteger archivos sensibles:
   chmod 600 ~/yeyo-os/.env
   
6. Configurar ulimits para servicios:
   Crear /etc/security/limits.d/yeyo.conf:
   yeyo-service soft nofile 65536
   yeyo-service hard nofile 65536
   yeyo-service soft nproc 4096
   yeyo-service hard nproc 4096

7. Verificar que no hay servicios escuchando en interfaces públicas:
   ss -tlnp | grep -v "127.0.0.1\|::1\|\*:22"
   → Solo debe haber servicios en localhost

VERIFICAR:
- [ ] Usuario yeyo-service existe: `id yeyo-service` → uid sin login shell
- [ ] Grupo yeyo-users existe: `getent group yeyo-users` → muestra grupo
- [ ] Permisos correctos: `ls -la /var/lib/yeyo/` → yeyo-service:yeyo-users, 750
- [ ] .env protegido: `stat -c %a ~/yeyo-os/.env` → 600
- [ ] Solo localhost: `ss -tlnp` → PG, Redis, Ollama solo en 127.0.0.1
- [ ] ulimits configurados: `cat /etc/security/limits.d/yeyo.conf` → existe

SI FALLA:
- Permiso denegado: usar sudo
- Grupo no aplica hasta re-login: `newgrp yeyo-users` o logout/login

GATE: Usuario de servicio creado, permisos restrictivos, servicios solo en localhost, .env protegido.
```
