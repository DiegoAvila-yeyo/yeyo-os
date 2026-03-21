## ═══════════════════════════════════════
## MICRO-FASE 0.4 — Redis 7
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.4-1 [CLI] — Instalar y configurar Redis

```
Estamos construyendo YeyoOS. Micro-fase 0.4: instalar Redis 7 para caché de Flash Memory (tiers HOT/WARM/COLD).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.3 completadas. PostgreSQL corriendo.

EJECUTAR:
1. Instalar Redis 7:
   sudo apt install -y redis-server

2. Configurar Redis para YeyoOS:
   Editar /etc/redis/redis.conf:
   - maxmemory 512mb
   - maxmemory-policy allkeys-lru
   - save 900 1
   - save 300 10
   - save 60 10000
   - requirepass yeyo_redis_dev_2026
   - bind 127.0.0.1
   - protected-mode yes

3. Iniciar y habilitar:
   sudo systemctl enable --now redis-server

4. Agregar a .env del proyecto (cd ~/yeyo-os):
   Añadir estas líneas al archivo .env existente:
   # Redis
   REDIS_URL=redis://:yeyo_redis_dev_2026@127.0.0.1:6379/0

5. Actualizar .env.example también:
   REDIS_URL=redis://:YOUR_PASSWORD@127.0.0.1:6379/0

VERIFICAR:
- [ ] Redis corriendo: `sudo systemctl status redis-server` → active
- [ ] Versión: `redis-cli --version` → 7.x
- [ ] Conexión con auth: `redis-cli -a yeyo_redis_dev_2026 ping` → PONG
- [ ] Memoria configurada: `redis-cli -a yeyo_redis_dev_2026 CONFIG GET maxmemory` → 536870912 (512MB)
- [ ] Solo localhost: `redis-cli -a yeyo_redis_dev_2026 CONFIG GET bind` → 127.0.0.1

SI FALLA:
- Puerto 6379 ocupado: `sudo ss -tlnp | grep 6379` → matar proceso
- Auth no funciona: verificar que requirepass está sin comentar en redis.conf

NO HACER:
- No exponer Redis a red externa
- No desactivar el password
- No crear keys aún (eso es Capa 2)

GATE: Redis 7 corriendo en localhost, auth con password, maxmemory 512MB, .env actualizado.
```
