## ═══════════════════════════════════════
## MICRO-FASE 0.3 — PostgreSQL 16 + pgvector
## Tipo: CLI | Prompts: 2 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.3-1 [CLI] — Instalar PostgreSQL 16 + pgvector

```
Estamos construyendo YeyoOS. Micro-fase 0.3, Prompt 1 de 2: instalar PostgreSQL 16 con extensión pgvector para Flash Memory.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.2 completadas. Systemd funcional.

EJECUTAR:
1. Añadir repositorio de PostgreSQL 16:
   sudo apt install -y wget gnupg2
   sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
   wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
   sudo apt update

2. Instalar PostgreSQL 16:
   sudo apt install -y postgresql-16 postgresql-16-pgvector

3. Iniciar y habilitar servicio:
   sudo systemctl enable --now postgresql

4. Crear usuario y database para YeyoOS:
   sudo -u postgres psql -c "CREATE USER yeyo WITH PASSWORD 'yeyo_dev_2026';"
   sudo -u postgres psql -c "CREATE DATABASE yeyo_db OWNER yeyo;"
   sudo -u postgres psql -c "CREATE DATABASE yeyo_test_db OWNER yeyo;"

5. Habilitar pgvector:
   sudo -u postgres psql yeyo_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
   sudo -u postgres psql yeyo_test_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

6. Configurar pg_hba.conf para conexión local con password:
   Buscar pg_hba.conf: sudo find /etc/postgresql -name pg_hba.conf
   Agregar línea (antes de las existentes):
   local   yeyo_db     yeyo                                md5
   local   yeyo_test_db yeyo                               md5
   host    yeyo_db     yeyo    127.0.0.1/32                md5
   host    yeyo_test_db yeyo   127.0.0.1/32                md5

7. Optimizar postgresql.conf para desarrollo:
   shared_buffers = 256MB
   work_mem = 64MB
   effective_cache_size = 512MB
   maintenance_work_mem = 128MB

8. Reiniciar para aplicar cambios:
   sudo systemctl restart postgresql

VERIFICAR:
- [ ] PG corriendo: `sudo systemctl status postgresql` → active (running)
- [ ] Versión correcta: `psql --version` → 16.x
- [ ] pgvector activo: `sudo -u postgres psql yeyo_db -c "SELECT extname FROM pg_extension WHERE extname='vector';"` → 1 row
- [ ] Conexión como yeyo: `PGPASSWORD=yeyo_dev_2026 psql -U yeyo -d yeyo_db -h 127.0.0.1 -c "SELECT 1;"` → 1
- [ ] DB de test existe: `PGPASSWORD=yeyo_dev_2026 psql -U yeyo -d yeyo_test_db -h 127.0.0.1 -c "SELECT 1;"` → 1

SI FALLA:
- Puerto 5432 ocupado: `sudo ss -tlnp | grep 5432` → matar proceso
- pgvector no instala: `apt search pgvector` → verificar nombre del paquete
- Auth falla: revisar pg_hba.conf, orden de las líneas importa

NO HACER:
- No crear tablas aún (eso es Capa 2)
- No cambiar el puerto default (5432)
- No usar trust auth (siempre md5/scram)

GATE: PostgreSQL 16 corriendo + pgvector loaded + conexión como usuario yeyo OK.
```
