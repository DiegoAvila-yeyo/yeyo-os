"""
YeyoNet Integration Tests — Full Flow
Requires: PostgreSQL, Backend running on :8000
Run with: pytest -m integration tests/integration/yeyonet/ -v
"""
from __future__ import annotations

import pytest
import httpx

BASE = "http://localhost:8000/api/v1/yeyonet"


@pytest.mark.integration
class TestYeyoNetFlow:
    """End-to-end lifecycle test for YeyoNet: invite → register → jobs → cleanup."""

    _invite_code: str = ""
    _satellite_id: str = ""
    _satellite_token: str = ""
    _job_id: str = ""

    # ── 01  Identity ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_01_identity(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE}/identity")
            assert r.status_code == 200
            data = r.json()
            assert data["role"] == "central"
            assert "node_id" in data
            assert "name" in data

    # ── 02  Create Invitation ────────────────────────────────

    @pytest.mark.asyncio
    async def test_02_create_invitation(self):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE}/invite",
                json={
                    "satellite_name": "test-sat-flow",
                    "permissions": ["chat", "memoria"],
                    "visibility_level": 2,
                    "expires_in_days": 1,
                },
            )
            assert r.status_code == 200
            data = r.json()
            assert data["code"].startswith("YEYO-")
            assert len(data["code"]) == 19
            TestYeyoNetFlow._invite_code = data["code"]

    # ── 03  Register Satellite ───────────────────────────────

    @pytest.mark.asyncio
    async def test_03_register_satellite(self):
        assert TestYeyoNetFlow._invite_code, "Invite code not set (test_02 failed?)"
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE}/register",
                json={
                    "code": TestYeyoNetFlow._invite_code,
                    "node_name": "integration-satellite",
                    "mode": "completo",
                },
            )
            assert r.status_code == 200
            data = r.json()
            assert "node_id" in data
            assert "auth_token" in data
            assert data["central_ws_url"] == "ws://localhost:8000/ws/yeyonet"
            assert "chat" in data["permissions"]
            TestYeyoNetFlow._satellite_id = data["node_id"]
            TestYeyoNetFlow._satellite_token = data["auth_token"]

    # ── 04  Satellite appears in list ────────────────────────

    @pytest.mark.asyncio
    async def test_04_satellite_appears_in_list(self):
        assert TestYeyoNetFlow._satellite_id, "Satellite ID not set"
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE}/satellites", params={"include_offline": True})
            assert r.status_code == 200
            satellites = r.json()
            ids = [s["id"] for s in satellites]
            assert TestYeyoNetFlow._satellite_id in ids

    # ── 05  Update satellite permissions ─────────────────────

    @pytest.mark.asyncio
    async def test_05_update_satellite_permissions(self):
        sid = TestYeyoNetFlow._satellite_id
        assert sid, "Satellite ID not set"
        async with httpx.AsyncClient() as client:
            r = await client.put(
                f"{BASE}/satellites/{sid}",
                json={
                    "name": "integration-satellite-updated",
                    "permissions": ["chat", "memoria", "grafos"],
                    "visibility_level": 3,
                },
            )
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "updated"

            # Verify
            r2 = await client.get(f"{BASE}/satellites/{sid}")
            assert r2.status_code == 200
            detail = r2.json()
            assert detail["name"] == "integration-satellite-updated"
            assert "grafos" in detail["permissions"]
            assert detail["visibility_level"] == 3

    # ── 06  Network stats ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_06_network_stats(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE}/stats")
            assert r.status_code == 200
            data = r.json()
            assert "central_node_id" in data
            assert data["role"] == "central"
            assert "total_satellites" in data

    # ── 07  Create job ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_07_create_job(self):
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE}/jobs",
                json={
                    "type": "text_inference",
                    "payload": {"prompt": "integration test", "model": "llama3"},
                    "priority": 7,
                    "timeout_seconds": 120,
                },
            )
            assert r.status_code == 200
            data = r.json()
            assert "job_id" in data
            assert data["type"] == "text_inference"
            assert data["status"] == "queued"
            TestYeyoNetFlow._job_id = data["job_id"]

    # ── 08  List jobs ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_08_list_jobs(self):
        assert TestYeyoNetFlow._job_id, "Job ID not set"
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE}/jobs", params={"limit": 50})
            assert r.status_code == 200
            jobs = r.json()
            assert isinstance(jobs, list)
            job_ids = [j["id"] if isinstance(j, dict) else j for j in jobs]
            # Verify our job shows up (may be nested)
            found = any(
                (isinstance(j, dict) and j.get("id") == TestYeyoNetFlow._job_id)
                for j in jobs
            )
            assert found, f"Job {TestYeyoNetFlow._job_id} not found in job list"

    # ── 09  Job stats ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_09_job_stats(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE}/jobs/stats")
            assert r.status_code == 200
            data = r.json()
            assert isinstance(data, dict)

    # ── 10  Get single job ───────────────────────────────────

    @pytest.mark.asyncio
    async def test_10_get_job(self):
        jid = TestYeyoNetFlow._job_id
        assert jid, "Job ID not set"
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE}/jobs/{jid}")
            assert r.status_code == 200

    # ── 11  Sync stats ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_11_sync_stats(self):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BASE}/sync/stats")
            assert r.status_code == 200
            data = r.json()
            assert isinstance(data, dict)

    # ── 12  Trigger sync ─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_12_trigger_sync(self):
        sid = TestYeyoNetFlow._satellite_id
        assert sid, "Satellite ID not set"
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{BASE}/sync/trigger/{sid}")
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "ok"
            assert "memories_pushed" in data

    # ── 13  Cancel job ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_13_cancel_job(self):
        jid = TestYeyoNetFlow._job_id
        assert jid, "Job ID not set"
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{BASE}/jobs/{jid}")
            # 200 if cancelled, 400 if already completed
            assert r.status_code in (200, 400)
            if r.status_code == 200:
                assert r.json()["status"] == "cancelled"

    # ── 14  Cleanup — remove test satellite ──────────────────

    @pytest.mark.asyncio
    async def test_14_cleanup(self):
        sid = TestYeyoNetFlow._satellite_id
        if not sid:
            pytest.skip("No satellite to clean up")
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{BASE}/satellites/{sid}")
            assert r.status_code == 200
            assert r.json()["status"] == "removed"

            # Verify gone
            r2 = await client.get(f"{BASE}/satellites/{sid}")
            assert r2.status_code == 404
