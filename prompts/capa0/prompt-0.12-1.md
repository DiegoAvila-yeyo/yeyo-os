## ═══════════════════════════════════════
## MICRO-FASE 0.12 — Integration Test Capa 0
## Tipo: CLI | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 0.12-1 [CLI] — Test de integración completo de Capa 0

```
Estamos construyendo YeyoOS. Micro-fase 0.12: INTEGRATION TEST de toda la Capa 0. Esta es la verificación final antes de pasar a Capa 1.

TODAS las micro-fases 0.0-0.11 deben estar completadas.

EJECUTAR:
1. Ir al proyecto:
   cd ~/yeyo-os
   source .venv/bin/activate

2. Crear tests/test_capa0_integration.py con TODOS estos tests:

   import subprocess
   import os
   import httpx
   import asyncio
   import asyncpg
   import redis
   from dotenv import load_dotenv
   
   load_dotenv()
   
   # === BTRFS (0.0) ===
   def test_btrfs_tools():
       r = subprocess.run(['btrfs', '--version'], capture_output=True)
       assert r.returncode == 0
   
   # === KERNEL (0.1) ===
   def test_gcc_available():
       r = subprocess.run(['gcc', '--version'], capture_output=True)
       assert r.returncode == 0
   
   # === SYSTEMD (0.2) ===
   def test_systemd_is_pid1():
       r = subprocess.run(['ps', '-p', '1', '-o', 'comm='], capture_output=True, text=True)
       assert 'systemd' in r.stdout.strip()
   
   # === POSTGRESQL (0.3) ===
   def test_postgresql_running():
       r = subprocess.run(['systemctl', 'is-active', 'postgresql'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_postgresql_connection():
       async def _test():
           conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
           result = await conn.fetchval('SELECT 1')
           await conn.close()
           assert result == 1
       asyncio.run(_test())
   
   def test_pgvector_loaded():
       async def _test():
           conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
           result = await conn.fetchval("SELECT COUNT(*) FROM pg_extension WHERE extname='vector'")
           await conn.close()
           assert result == 1
       asyncio.run(_test())
   
   # === REDIS (0.4) ===
   def test_redis_running():
       r = subprocess.run(['systemctl', 'is-active', 'redis-server'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_redis_connection():
       url = os.getenv('REDIS_URL')
       r = redis.from_url(url)
       assert r.ping() == True
   
   # === NODE.JS (0.5) ===
   def test_node_version():
       r = subprocess.run(['node', '--version'], capture_output=True, text=True)
       assert r.stdout.strip().startswith('v20')
   
   def test_nextjs_builds():
       r = subprocess.run(['pnpm', 'build'], capture_output=True, cwd='frontend')
       assert r.returncode == 0
   
   # === PYTHON (0.6) ===
   def test_python_version():
       import sys
       assert sys.version_info[:2] == (3, 11)
   
   def test_all_imports():
       import asyncpg, redis, aiohttp, pydantic, sentence_transformers
       assert True
   
   # === RUST (0.7) ===
   def test_rust_installed():
       r = subprocess.run(['rustc', '--version'], capture_output=True)
       assert r.returncode == 0
   
   def test_rust_workspace_builds():
       r = subprocess.run(['cargo', 'build'], capture_output=True, cwd='rust')
       assert r.returncode == 0
   
   # === OLLAMA (0.8) ===
   def test_ollama_running():
       r = subprocess.run(['systemctl', 'is-active', 'ollama'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_ollama_api():
       r = httpx.get(f"{os.getenv('OLLAMA_HOST')}/api/tags")
       assert r.status_code == 200
   
   def test_ollama_inference():
       r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/generate", json={
           "model": os.getenv('OLLAMA_MODEL'),
           "prompt": "Say OK",
           "stream": False
       }, timeout=60)
       assert r.status_code == 200
       assert len(r.json()["response"]) > 0
   
   # === PODMAN (0.9) ===
   def test_podman_installed():
       r = subprocess.run(['podman', '--version'], capture_output=True)
       assert r.returncode == 0
   
   def test_podman_runs_container():
       r = subprocess.run(['podman', 'run', '--rm', 'alpine', 'echo', 'OK'], capture_output=True, text=True)
       assert 'OK' in r.stdout
   
   # === GPU (0.10) ===
   def test_nvidia_smi():
       r = subprocess.run(['nvidia-smi'], capture_output=True)
       assert r.returncode == 0
   
   def test_cuda_available():
       r = subprocess.run(['nvcc', '--version'], capture_output=True)
       assert r.returncode == 0
   
   # === SECURITY (0.11) ===
   def test_env_protected():
       mode = oct(os.stat('.env').st_mode)[-3:]
       assert mode == '600'
   
   def test_auditd_running():
       r = subprocess.run(['systemctl', 'is-active', 'auditd'], capture_output=True, text=True)
       assert r.stdout.strip() == 'active'
   
   def test_firewall_active():
       r = subprocess.run(['sudo', 'ufw', 'status'], capture_output=True, text=True)
       assert 'active' in r.stdout.lower()

3. Ejecutar TODA la suite:
   pytest tests/test_capa0_integration.py -v --tb=short

4. Si algún test falla, diagnosticar y corregir ANTES de avanzar.

VERIFICAR:
- [ ] TODOS los tests pasan: pytest output muestra 0 failed
- [ ] Total tests: 25 tests
- [ ] Ningún servicio crasheó durante la ejecución
- [ ] Tiempo total <2 minutos

RESULTADO ESPERADO:
tests/test_capa0_integration.py::test_btrfs_tools PASSED
tests/test_capa0_integration.py::test_gcc_available PASSED
tests/test_capa0_integration.py::test_systemd_is_pid1 PASSED
tests/test_capa0_integration.py::test_postgresql_running PASSED
tests/test_capa0_integration.py::test_postgresql_connection PASSED
tests/test_capa0_integration.py::test_pgvector_loaded PASSED
tests/test_capa0_integration.py::test_redis_running PASSED
tests/test_capa0_integration.py::test_redis_connection PASSED
tests/test_capa0_integration.py::test_node_version PASSED
tests/test_capa0_integration.py::test_nextjs_builds PASSED
tests/test_capa0_integration.py::test_python_version PASSED
tests/test_capa0_integration.py::test_all_imports PASSED
tests/test_capa0_integration.py::test_rust_installed PASSED
tests/test_capa0_integration.py::test_rust_workspace_builds PASSED
tests/test_capa0_integration.py::test_ollama_running PASSED
tests/test_capa0_integration.py::test_ollama_api PASSED
tests/test_capa0_integration.py::test_ollama_inference PASSED
tests/test_capa0_integration.py::test_podman_installed PASSED
tests/test_capa0_integration.py::test_podman_runs_container PASSED
tests/test_capa0_integration.py::test_nvidia_smi PASSED
tests/test_capa0_integration.py::test_cuda_available PASSED
tests/test_capa0_integration.py::test_env_protected PASSED
tests/test_capa0_integration.py::test_auditd_running PASSED
tests/test_capa0_integration.py::test_firewall_active PASSED

========================= 25 passed in Xs =========================

🚪 GATE FINAL CAPA 0: 25/25 tests passing. Todos los cimientos instalados y funcionando. LISTO PARA CAPA 1.
```
