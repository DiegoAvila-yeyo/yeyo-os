#!/usr/bin/env python3
"""
YeyoNet Local Simulation — Simula satélites en la misma máquina.

Uso:
  python scripts/yeyonet_simulate.py [--satellites N] [--duration SECONDS]

Pasos:
  1. Crea N invitaciones via API
  2. Registra N satélites
  3. Conecta N WebSocket clients
  4. Envía heartbeats y resource reports periódicos
  5. Central crea jobs, simulated satellites execute them
  6. Muestra stats en consola cada 10s
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import signal
import sys
import time
import uuid
from datetime import datetime
from typing import Any

try:
    import httpx
except ImportError:
    sys.exit("httpx is required: pip install httpx")

try:
    import websockets
    import websockets.asyncio.client as ws_client
except ImportError:
    websockets = None  # type: ignore[assignment]


BASE_URL = "http://localhost:8000/api/v1/yeyonet"
WS_URL = "ws://localhost:8000/ws/yeyonet"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("yeyonet-sim")


# ── Data structures ──────────────────────────────────────────

class SimSatellite:
    """Simulated satellite node."""

    def __init__(self, index: int, node_id: str, token: str, name: str):
        self.index = index
        self.node_id = node_id
        self.token = token
        self.name = name
        self.ws: Any = None
        self.connected = False
        self.heartbeats_sent = 0
        self.reports_sent = 0

    def fake_resources(self) -> dict:
        return {
            "cpu_percent": round(random.uniform(5.0, 85.0), 1),
            "ram_free_gb": round(random.uniform(1.0, 16.0), 1),
            "gpu_name": random.choice(["RTX 4090", "RTX 3080", "M1 Ultra", None]),
            "gpu_vram_mb": random.choice([0, 8192, 16384, 24576]),
            "gpu_usage_percent": round(random.uniform(0.0, 100.0), 1),
            "ollama_models": random.sample(
                ["llama3", "mistral", "phi3", "codellama", "gemma"],
                k=random.randint(0, 3),
            ),
            "active_jobs": random.randint(0, 2),
        }


# ── API helpers ──────────────────────────────────────────────

async def create_invitation(client: httpx.AsyncClient, name: str) -> str:
    r = await client.post(
        f"{BASE_URL}/invite",
        json={
            "satellite_name": name,
            "permissions": ["chat", "memoria", "grafos"],
            "visibility_level": 2,
            "expires_in_days": 1,
        },
    )
    r.raise_for_status()
    return r.json()["code"]


async def register_satellite(
    client: httpx.AsyncClient, code: str, name: str
) -> tuple[str, str]:
    r = await client.post(
        f"{BASE_URL}/register",
        json={"code": code, "node_name": name, "mode": "completo"},
    )
    r.raise_for_status()
    data = r.json()
    return data["node_id"], data["auth_token"]


async def remove_satellite(client: httpx.AsyncClient, node_id: str) -> None:
    await client.delete(f"{BASE_URL}/satellites/{node_id}")


async def create_test_job(client: httpx.AsyncClient) -> str | None:
    job_types = ["text_inference", "image_generate", "custom"]
    try:
        r = await client.post(
            f"{BASE_URL}/jobs",
            json={
                "type": random.choice(job_types),
                "payload": {"prompt": f"sim-job-{uuid.uuid4().hex[:6]}"},
                "priority": random.randint(1, 10),
                "timeout_seconds": 120,
            },
        )
        if r.status_code == 200:
            return r.json()["job_id"]
    except Exception as e:
        log.warning("Failed to create job: %s", e)
    return None


async def fetch_stats(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get(f"{BASE_URL}/stats")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


async def fetch_job_stats(client: httpx.AsyncClient) -> dict:
    try:
        r = await client.get(f"{BASE_URL}/jobs/stats")
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


# ── WebSocket loop ───────────────────────────────────────────

def _make_message(msg_type: str, from_node: str, payload: dict | None = None) -> str:
    return json.dumps({
        "msg_id": str(uuid.uuid4()),
        "type": msg_type,
        "from_node": from_node,
        "to_node": "",
        "payload": payload or {},
        "timestamp": time.time(),
        "reply_to": None,
    })


async def satellite_ws_loop(sat: SimSatellite, stop: asyncio.Event) -> None:
    """Manages the WebSocket lifecycle for one simulated satellite."""
    if websockets is None:
        log.warning("websockets not installed — skipping WS for %s", sat.name)
        return

    retry_delay = 2.0
    while not stop.is_set():
        try:
            async with ws_client.connect(WS_URL) as ws:
                sat.ws = ws
                sat.connected = True
                log.info("✅ %s connected via WebSocket", sat.name)

                # AUTH
                auth_msg = _make_message("auth", sat.node_id, {"token": sat.token})
                await ws.send(auth_msg)

                # Read AUTH_OK / AUTH_FAIL
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    resp = json.loads(raw)
                    if resp.get("type") in ("auth_fail", "AUTH_FAIL"):
                        log.error("❌ %s auth rejected", sat.name)
                        return
                    log.info("🔑 %s authenticated", sat.name)
                except asyncio.TimeoutError:
                    log.warning("⏱ %s auth timeout, continuing anyway", sat.name)

                # Main loop: send heartbeats + resource reports
                while not stop.is_set():
                    # Heartbeat
                    hb = _make_message("heartbeat", sat.node_id)
                    await ws.send(hb)
                    sat.heartbeats_sent += 1

                    # Resource report every other cycle
                    if sat.heartbeats_sent % 2 == 0:
                        rr = _make_message(
                            "resource_report", sat.node_id, sat.fake_resources()
                        )
                        await ws.send(rr)
                        sat.reports_sent += 1

                    # Read any incoming messages (non-blocking)
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                        msg = json.loads(raw)
                        mtype = msg.get("type", "").lower()
                        if mtype == "job_assign":
                            job_id = msg.get("payload", {}).get("job_id", "?")
                            log.info(
                                "📦 %s received job %s — accepting",
                                sat.name,
                                job_id,
                            )
                            accept = _make_message(
                                "job_accept",
                                sat.node_id,
                                {"job_id": job_id},
                            )
                            await ws.send(accept)
                    except asyncio.TimeoutError:
                        pass

                    await asyncio.sleep(15)

        except Exception as e:
            sat.connected = False
            if stop.is_set():
                break
            log.warning("🔄 %s WS error: %s — retrying in %.0fs", sat.name, e, retry_delay)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 1.5, 30.0)

    sat.connected = False


# ── Stats printer ────────────────────────────────────────────

async def stats_printer(
    client: httpx.AsyncClient,
    satellites: list[SimSatellite],
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        await asyncio.sleep(10)
        if stop.is_set():
            break

        net = await fetch_stats(client)
        jobs = await fetch_job_stats(client)
        connected = sum(1 for s in satellites if s.connected)
        total_hb = sum(s.heartbeats_sent for s in satellites)
        total_rr = sum(s.reports_sent for s in satellites)

        print(
            f"\n{'─' * 60}\n"
            f"  ⏰ {datetime.now().strftime('%H:%M:%S')}  |  "
            f"Satellites: {connected}/{len(satellites)} connected\n"
            f"  Heartbeats sent: {total_hb}  |  "
            f"Resource reports: {total_rr}\n"
            f"  Network: {json.dumps(net, default=str)}\n"
            f"  Jobs:    {json.dumps(jobs, default=str)}\n"
            f"{'─' * 60}"
        )


# ── Main ─────────────────────────────────────────────────────

async def main(num_satellites: int, duration: int) -> None:
    stop = asyncio.Event()

    # Handle Ctrl+C
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    satellites: list[SimSatellite] = []
    job_ids: list[str] = []

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        # 1. Verify backend is reachable
        try:
            r = await client.get(f"{BASE_URL}/identity")
            r.raise_for_status()
            identity = r.json()
            log.info(
                "🏠 Central node: %s (%s)",
                identity.get("name", "?"),
                identity.get("node_id", "?")[:8],
            )
        except Exception as e:
            log.error("Cannot reach backend at %s: %s", BASE_URL, e)
            return

        # 2. Create invitations + register satellites
        log.info("📨 Creating %d invitations...", num_satellites)
        for i in range(num_satellites):
            name = f"sim-satellite-{i}"
            try:
                code = await create_invitation(client, name)
                node_id, token = await register_satellite(client, code, name)
                sat = SimSatellite(i, node_id, token, name)
                satellites.append(sat)
                log.info("  ✅ %s registered (id=%s…)", name, node_id[:8])
            except Exception as e:
                log.error("  ❌ Failed to register %s: %s", name, e)

        if not satellites:
            log.error("No satellites registered — aborting")
            return

        # 3. Launch WebSocket loops + stats printer
        tasks: list[asyncio.Task] = []
        for sat in satellites:
            tasks.append(asyncio.create_task(satellite_ws_loop(sat, stop)))
        tasks.append(asyncio.create_task(stats_printer(client, satellites, stop)))

        # 4. Create a few test jobs periodically
        async def job_creator() -> None:
            await asyncio.sleep(5)  # let satellites connect first
            while not stop.is_set():
                jid = await create_test_job(client)
                if jid:
                    job_ids.append(jid)
                    log.info("🎯 Created job %s…", jid[:8])
                await asyncio.sleep(15)

        tasks.append(asyncio.create_task(job_creator()))

        # 5. Wait for duration or Ctrl+C
        log.info(
            "🚀 Simulation running for %ds with %d satellites (Ctrl+C to stop)",
            duration,
            len(satellites),
        )
        try:
            await asyncio.wait_for(stop.wait(), timeout=duration)
        except asyncio.TimeoutError:
            log.info("⏰ Duration reached (%ds)", duration)
            stop.set()

        # 6. Cleanup
        log.info("🧹 Cleaning up...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        # Cancel test jobs
        for jid in job_ids:
            try:
                await client.delete(f"{BASE_URL}/jobs/{jid}")
            except Exception:
                pass

        # Remove simulated satellites
        for sat in satellites:
            try:
                await remove_satellite(client, sat.node_id)
                log.info("  🗑 Removed %s", sat.name)
            except Exception:
                pass

    log.info("✅ Simulation complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="YeyoNet Local Simulation — simulate satellites on this machine"
    )
    parser.add_argument(
        "--satellites",
        type=int,
        default=2,
        help="Number of simulated satellites (default: 2)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (default: 60)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.satellites, args.duration))
