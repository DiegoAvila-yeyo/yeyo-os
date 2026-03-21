import subprocess, os, httpx, asyncio, asyncpg, redis
from dotenv import load_dotenv
import pytest

load_dotenv()

def test_btrfs_tools():
    assert subprocess.run(['btrfs', '--version'], capture_output=True).returncode == 0

def test_gcc_available():
    assert subprocess.run(['gcc', '--version'], capture_output=True).returncode == 0

def test_make_available():
    assert subprocess.run(['make', '--version'], capture_output=True).returncode == 0

def test_dkms_available():
    assert subprocess.run(['dkms', '--version'], capture_output=True).returncode == 0

def test_systemd_is_pid1():
    r = subprocess.run(['ps', '-p', '1', '-o', 'comm='], capture_output=True, text=True)
    assert 'systemd' in r.stdout.strip()

def test_yeyo_target_exists():
    r = subprocess.run(['systemctl', 'cat', 'yeyo.target'], capture_output=True, text=True)
    assert r.returncode == 0 and 'YeyoOS' in r.stdout

def test_postgresql_running():
    r = subprocess.run(['systemctl', 'is-active', 'postgresql'], capture_output=True, text=True)
    assert r.stdout.strip() == 'active'

def test_postgresql_connection():
    async def _():
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        assert await conn.fetchval('SELECT 1') == 1
        await conn.close()
    asyncio.run(_())

def test_pgvector_loaded():
    async def _():
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        assert await conn.fetchval("SELECT COUNT(*) FROM pg_extension WHERE extname='vector'") == 1
        await conn.close()
    asyncio.run(_())

def test_yeyo_meta_table():
    async def _():
        conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
        assert await conn.fetchval("SELECT value FROM _yeyo_meta WHERE key='micro_fase'") == '0.3'
        await conn.close()
    asyncio.run(_())

def test_redis_running():
    r = subprocess.run(['systemctl', 'is-active', 'redis-server'], capture_output=True, text=True)
    assert r.stdout.strip() == 'active'

def test_redis_connection():
    assert redis.from_url(os.getenv('REDIS_URL')).ping() == True

def test_node_version():
    # Node instalado via nvm para usuario yeyo
    r = subprocess.run(['su', '-', 'yeyo', '-c', 'source ~/.nvm/nvm.sh && node --version'],
                      capture_output=True, text=True)
    assert r.stdout.strip().startswith('v20')

def test_pnpm_available():
    r = subprocess.run(['su', '-', 'yeyo', '-c', 'source ~/.nvm/nvm.sh && pnpm --version'],
                      capture_output=True, text=True)
    assert r.returncode == 0

def test_nextjs_built():
    assert os.path.isdir('/mnt/c/Users/yeyoa/Desktop/yeyo-os/frontend/.next')

def test_python_version():
    import sys
    assert sys.version_info[:2] == (3, 12)

def test_all_imports():
    import asyncpg, redis, aiohttp, pydantic, sentence_transformers

def test_config_loads():
    from src.utils.config import DATABASE_URL, REDIS_URL
    assert DATABASE_URL and REDIS_URL

def test_rust_installed():
    # Rust instalado como yeyo — RUSTUP_HOME vive en ~/.rustup del usuario
    r = subprocess.run(['su', '-', 'yeyo', '-c', 'source ~/.cargo/env && rustc --version'],
                      capture_output=True, text=True)
    assert r.returncode == 0 and 'rustc' in r.stdout

def test_rust_workspace_builds():
    r = subprocess.run(['su', '-', 'yeyo', '-c', 'source ~/.cargo/env && cd /home/yeyo/yeyo-rust && cargo build'],
                      capture_output=True, text=True)
    assert r.returncode == 0

def test_ollama_running():
    r = subprocess.run(['systemctl', 'is-active', 'ollama'], capture_output=True, text=True)
    assert r.stdout.strip() == 'active'

def test_ollama_api():
    assert httpx.get(f"{os.getenv('OLLAMA_HOST')}/api/tags").status_code == 200

def test_ollama_model_available():
    r = httpx.get(f"{os.getenv('OLLAMA_HOST')}/api/tags")
    assert any('qwen2.5' in m['name'] for m in r.json().get('models', []))

def test_ollama_inference():
    r = httpx.post(f"{os.getenv('OLLAMA_HOST')}/api/generate",
                   json={"model": os.getenv('OLLAMA_MODEL'), "prompt": "Say OK", "stream": False},
                   timeout=60)
    assert r.status_code == 200 and len(r.json()["response"]) > 0

def test_podman_installed():
    assert subprocess.run(['podman', '--version'], capture_output=True).returncode == 0

def test_podman_rootless():
    # Debe verificarse como usuario yeyo — rootless es por usuario, no aplica a root
    r = subprocess.run(['su', '-', 'yeyo', '-c', 'podman info --format {{.Host.Security.Rootless}}'],
                      capture_output=True, text=True)
    assert 'true' in r.stdout.strip()

def test_podman_runs_container():
    r = subprocess.run(['podman', 'run', '--rm', 'alpine', 'echo', 'OK'],
                      capture_output=True, text=True)
    assert 'OK' in r.stdout

def test_no_docker_socket():
    assert not os.path.exists('/var/run/docker.sock')

def test_nvidia_smi():
    assert subprocess.run(['nvidia-smi'], capture_output=True).returncode == 0

def test_cuda_available():
    assert subprocess.run(['/usr/local/cuda/bin/nvcc', '--version'], capture_output=True).returncode == 0

def test_gpu_vram_3gb():
    r = subprocess.run(['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader'],
                      capture_output=True, text=True)
    assert '3072' in r.stdout

def test_yeyo_service_user():
    assert subprocess.run(['id', 'yeyo-service'], capture_output=True).returncode == 0

def test_var_lib_yeyo_permissions():
    assert oct(os.stat('/var/lib/yeyo').st_mode)[-3:] == '750'

def test_services_only_localhost():
    r = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
    for line in r.stdout.split('\n')[1:]:
        if any(x in line for x in ['127.0.0.1','::1','*:22','10.255.255.254','127.0.0.53','127.0.0.54']):
            continue
        assert '0.0.0.0' not in line and ':::' not in line, f"Servicio expuesto: {line}"

def test_firewall_active():
    r = subprocess.run(['ufw', 'status'], capture_output=True, text=True)
    assert 'active' in r.stdout.lower()

def test_env_permissions():
    assert oct(os.stat('/mnt/c/Users/yeyoa/Desktop/yeyo-os/.env').st_mode)[-3:] == '600'

@pytest.mark.xfail(reason="auditd bloqueado por Hyper-V en WSL2. Ver docs/wsl2-limitaciones.md. Resolucion: Capa 6 Guardian daemon.")
def test_audit_running():
    r = subprocess.run(['systemctl', 'is-active', 'auditd'], capture_output=True, text=True)
    assert r.stdout.strip() == 'active'
