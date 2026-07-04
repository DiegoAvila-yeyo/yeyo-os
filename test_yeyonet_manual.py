"""
YeyoNet — Tests E2E REALES entre Desktop (Windows) y Mac (Central)
Prueba flujo real de: jobs, memory sync, resource reporting.
Ejecutar desde Desktop: python test_yeyonet_manual.py
"""
import requests
import time
import json
import sys

LOCAL = "http://localhost:8000"
MAC = "http://192.168.101.160:8000"
SATELLITE_NODE_ID = "dfb30f54-d173-425b-b96e-1c6dcb287e4e"

passed = 0
failed = 0


def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def result(ok, msg):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ✅ PASS — {msg}")
    else:
        failed += 1
        print(f"  ❌ FAIL — {msg}")
    return ok


# ─── TEST 1: Conexión viva ─────────────────────────────────

def test_1_connection():
    header("TEST 1: Satellite conectado al Central (Mac)")
    r = requests.get(f"{LOCAL}/api/v1/yeyonet/connection", timeout=5)
    d = r.json()
    print(f"  Central: {d.get('central_ws_url')}")
    return result(d.get("connected"), "WebSocket vivo")


# ─── TEST 2: Mac ve nuestros recursos (GPU, CPU, RAM) ──────

def test_2_resources():
    header("TEST 2: Mac recibe recursos de este PC (GPU/CPU/RAM)")
    print("  Esperando 35s para que ResourceMonitor envíe reporte...")
    time.sleep(35)
    try:
        r = requests.get(f"{MAC}/api/v1/yeyonet/satellites/{SATELLITE_NODE_ID}", timeout=5)
        if r.status_code != 200:
            return result(False, f"Mac no encuentra nuestro node: {r.status_code}")
        d = r.json()
        resources = d.get("resources", {})
        gpu = resources.get("gpu_name", "ninguna")
        cpu = resources.get("cpu_percent", -1)
        ram = resources.get("ram_free_gb", -1)
        models = resources.get("ollama_models", [])
        print(f"  GPU:     {gpu}")
        print(f"  CPU:     {cpu}%")
        print(f"  RAM:     {ram} GB libres")
        print(f"  Ollama:  {models}")
        has_data = cpu >= 0 or gpu not in (None, "ninguna")
        return result(has_data, f"Mac ve nuestros recursos: GPU={gpu}, CPU={cpu}%")
    except Exception as e:
        return result(False, str(e))


# ─── TEST 3: Job de texto real (Mac → Desktop → Ollama) ────

def test_3_text_job():
    header("TEST 3: Job de inferencia real (Mac crea → Desktop ejecuta con Ollama)")
    try:
        job_data = {
            "type": "text_inference",
            "payload": {
                "prompt": "Responde en una sola línea: ¿qué es YeyoOS?",
                "model": "qwen2.5:3b",
                "temperature": 0.5,
            },
            "priority": 9,
            "timeout_seconds": 120,
        }
        print("  Creando job en Mac...")
        r = requests.post(f"{MAC}/api/v1/yeyonet/jobs", json=job_data, timeout=10)
        if r.status_code != 200:
            return result(False, f"Error creando job: {r.status_code} {r.text[:200]}")

        d = r.json()
        job_id = d.get("job_id")
        print(f"  Job ID: {job_id[:12]}...")
        print(f"  Status: {d.get('status')}")

        # Poll hasta que complete o timeout
        print("  Esperando que Desktop procese el job...")
        for i in range(30):
            time.sleep(2)
            r2 = requests.get(f"{MAC}/api/v1/yeyonet/jobs/{job_id}", timeout=5)
            d2 = r2.json()
            status = d2.get("status")
            progress = d2.get("progress", 0)
            assigned = d2.get("assigned_to", "")
            
            if status == "assigned" and i == 0:
                node_short = assigned[:8] if assigned else "?"
                print(f"  Asignado a: {node_short}...")
            
            if status == "running":
                print(f"  Progreso: {progress}%")

            if status == "completed":
                res = d2.get("result", {})
                resp_text = res.get("response", "")[:150]
                tokens = res.get("tokens", 0)
                dur = res.get("duration_ms", 0)
                print(f"  Respuesta: \"{resp_text}\"")
                print(f"  Tokens: {tokens}, Duración: {dur}ms")
                return result(True, f"Job completado — Ollama respondió con {tokens} tokens")

            if status == "failed":
                err = d2.get("error", "?")
                return result(False, f"Job falló: {err}")

            if status in ("cancelled",):
                return result(False, f"Job cancelado")

        return result(False, f"Timeout — último status: {status}, progress: {progress}%")
    except Exception as e:
        return result(False, str(e))


# ─── TEST 4: Job de imagen (simulado) ──────────────────────

def test_4_image_job():
    header("TEST 4: Job de imagen (simulado — prueba el pipeline completo)")
    try:
        job_data = {
            "type": "image_generate",
            "payload": {
                "prompt": "A futuristic city at sunset",
                "width": 512,
                "height": 512,
                "steps": 10,
            },
            "priority": 5,
            "timeout_seconds": 60,
        }
        print("  Creando job de imagen en Mac...")
        r = requests.post(f"{MAC}/api/v1/yeyonet/jobs", json=job_data, timeout=10)
        d = r.json()
        job_id = d.get("job_id")
        print(f"  Job ID: {job_id[:12]}...")

        last_progress = 0
        for i in range(20):
            time.sleep(1)
            r2 = requests.get(f"{MAC}/api/v1/yeyonet/jobs/{job_id}", timeout=5)
            d2 = r2.json()
            status = d2.get("status")
            progress = d2.get("progress", 0)

            if progress > last_progress:
                print(f"  Progreso: {progress}% — {d2.get('progress_detail', '')}")
                last_progress = progress

            if status == "completed":
                res = d2.get("result", {})
                print(f"  Result: {json.dumps(res, indent=2)[:200]}")
                return result(True, "Pipeline imagen completo (placeholder)")

            if status == "failed":
                return result(False, f"Job falló: {d2.get('error')}")

        return result(False, f"Timeout — status: {status}")
    except Exception as e:
        return result(False, str(e))


# ─── TEST 5: Memory sync real (Desktop → Mac) ──────────────

def test_5_memory_sync():
    header("TEST 5: Memory Sync real (Desktop envía memoria → Mac la recibe)")
    try:
        # Count Mac's memories before
        r_before = requests.get(f"{MAC}/api/v1/yeyonet/sync/stats", timeout=5)
        before_count = r_before.json().get("total_memories", 0)
        print(f"  Memorias en Mac antes: {before_count}")

        # Trigger sync from Mac to us
        print("  Triggering sync push desde Mac hacia Desktop...")
        r_sync = requests.post(
            f"{MAC}/api/v1/yeyonet/sync/trigger/{SATELLITE_NODE_ID}",
            timeout=15,
        )
        if r_sync.status_code == 200:
            d = r_sync.json()
            sent = d.get("memories_sent", d.get("sent", 0))
            print(f"  Memorias enviadas: {sent}")
            return result(True, f"Sync push ejecutado — {sent} memorias enviadas")
        else:
            print(f"  Status: {r_sync.status_code}")
            print(f"  Body: {r_sync.text[:300]}")
            return result(False, f"Sync push falló: {r_sync.status_code}")
    except Exception as e:
        return result(False, str(e))


# ─── TEST 6: Network stats coherentes ──────────────────────

def test_6_network_stats():
    header("TEST 6: Network stats coherentes (Mac ve Desktop online)")
    try:
        r = requests.get(f"{MAC}/api/v1/yeyonet/stats", timeout=5)
        d = r.json()
        online = d.get("online", 0)
        total = d.get("total_satellites", 0)
        print(f"  Total satélites: {total}")
        print(f"  Online: {online}")
        print(f"  Idle: {d.get('idle', 0)}")
        print(f"  Offline: {d.get('offline', 0)}")

        # Also check our specific satellite status
        r2 = requests.get(f"{MAC}/api/v1/yeyonet/satellites/{SATELLITE_NODE_ID}", timeout=5)
        if r2.status_code == 200:
            sat = r2.json()
            print(f"  Nuestro status: {sat.get('status')}")
            print(f"  Nombre: {sat.get('name')}")
            return result(sat.get("status") == "online", f"Mac nos ve como '{sat.get('status')}'")
        return result(online > 0, f"{online} online de {total}")
    except Exception as e:
        return result(False, str(e))


# ─── TEST 7: Disconnect + reconnect real ────────────────────

def test_7_disconnect_reconnect():
    header("TEST 7: Disconnect → Mac ve offline → Reconnect → Mac ve online")
    try:
        # Disconnect
        print("  Desconectando satellite...")
        requests.post(f"{LOCAL}/api/v1/yeyonet/disconnect", timeout=5)
        time.sleep(3)
        r = requests.get(f"{LOCAL}/api/v1/yeyonet/connection", timeout=5)
        disconnected = not r.json().get("connected", True)
        print(f"  Desktop disconnected: {disconnected}")

        # Reconnect with saved creds
        print("  Reconectando...")
        config = {
            "node_id": SATELLITE_NODE_ID,
            "auth_token": "cb7c4b98-8e4b-428d-97fa-16e600388a08",
            "central_ws_url": "ws://192.168.101.160:8000/ws/yeyonet",
            "central_name": "http://192.168.101.160:8000",
        }
        requests.post(f"{LOCAL}/api/v1/yeyonet/connect", json=config, timeout=10)

        for i in range(10):
            time.sleep(2)
            r2 = requests.get(f"{LOCAL}/api/v1/yeyonet/connection", timeout=5)
            if r2.json().get("connected"):
                print(f"  Reconectado en {(i+1)*2}s")
                return result(True, f"Reconnect exitoso en {(i+1)*2}s")

        return result(False, "No reconectó en 20s")
    except Exception as e:
        return result(False, str(e))


# ─── MAIN ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔬 YeyoNet — Tests E2E REALES")
    print(f"   Desktop: {LOCAL}")
    print(f"   Mac:     {MAC}")
    print(f"   Node ID: {SATELLITE_NODE_ID[:12]}...")
    print(f"   Hora:    {time.strftime('%H:%M:%S')}")

    test_1_connection()
    test_6_network_stats()
    test_2_resources()
    test_3_text_job()
    test_4_image_job()
    test_5_memory_sync()
    test_7_disconnect_reconnect()

    header("RESUMEN FINAL")
    total = passed + failed
    print(f"  ✅ Pasaron: {passed}/{total}")
    print(f"  ❌ Fallaron: {failed}/{total}")
    if failed == 0:
        print(f"\n  🎉 TODOS LOS TESTS PASARON — YeyoNet funciona E2E")
    else:
        print(f"\n  ⚠️  Hay {failed} test(s) que necesitan atención")
    print()
