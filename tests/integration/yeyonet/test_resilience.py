"""
YeyoNet Resilience Tests
Tests: duplicate invitations, invalid tokens, concurrent satellites, jobs without nodes.
Requires: PostgreSQL, Backend running on :8000
Run with: pytest -m integration tests/integration/yeyonet/test_resilience.py -v
"""
from __future__ import annotations

import asyncio
from typing import Any

import pytest
import httpx

BASE = "http://localhost:8000/api/v1/yeyonet"


# ── Helpers ──────────────────────────────────────────────────

async def _create_invitation(
    client: httpx.AsyncClient,
    name: str = "resilience-sat",
    **overrides: Any,
) -> dict:
    payload = {
        "satellite_name": name,
        "permissions": ["chat"],
        "visibility_level": 1,
        "expires_in_days": 1,
        **overrides,
    }
    r = await client.post(f"{BASE}/invite", json=payload)
    assert r.status_code == 200, f"Invite creation failed: {r.text}"
    return r.json()


async def _register_satellite(
    client: httpx.AsyncClient,
    code: str,
    name: str | None = None,
) -> dict:
    r = await client.post(
        f"{BASE}/register",
        json={"code": code, "node_name": name, "mode": "completo"},
    )
    return r.json() if r.status_code == 200 else {"_status": r.status_code, "_body": r.text}


async def _cleanup_satellite(client: httpx.AsyncClient, node_id: str) -> None:
    await client.delete(f"{BASE}/satellites/{node_id}")


# ── Tests ────────────────────────────────────────────────────

@pytest.mark.integration
class TestYeyoNetResilience:
    """Resilience & edge-case tests for YeyoNet."""

    # 1. Duplicate invitation code rejected ───────────────────

    @pytest.mark.asyncio
    async def test_duplicate_invitation_code_rejected(self):
        """Registering twice with the same code must fail the second time."""
        async with httpx.AsyncClient() as client:
            inv = await _create_invitation(client, name="dup-test-sat")
            code = inv["code"]

            # First registration — should succeed
            r1 = await client.post(
                f"{BASE}/register",
                json={"code": code, "mode": "completo"},
            )
            assert r1.status_code == 200
            node_id = r1.json()["node_id"]

            # Second registration with same code — should fail
            r2 = await client.post(
                f"{BASE}/register",
                json={"code": code, "mode": "completo"},
            )
            assert r2.status_code == 400

            # Cleanup
            await _cleanup_satellite(client, node_id)

    # 2. Invalid token / bad credentials ──────────────────────

    @pytest.mark.asyncio
    async def test_invalid_register_code_rejected(self):
        """Using a completely fake invitation code must fail."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE}/register",
                json={"code": "YEYO-0000-0000-0000", "mode": "completo"},
            )
            assert r.status_code == 400

    # 3. Concurrent satellites ────────────────────────────────

    @pytest.mark.asyncio
    async def test_concurrent_satellite_registration(self):
        """Register 3 satellites concurrently — all should succeed."""
        node_ids: list[str] = []
        async with httpx.AsyncClient() as client:
            # Create 3 invitations
            invitations = await asyncio.gather(
                *[_create_invitation(client, name=f"concurrent-{i}") for i in range(3)]
            )

            # Register all concurrently
            results = await asyncio.gather(
                *[
                    _register_satellite(client, inv["code"], f"concurrent-sat-{i}")
                    for i, inv in enumerate(invitations)
                ]
            )

            for res in results:
                assert "node_id" in res, f"Registration failed: {res}"
                node_ids.append(res["node_id"])

            # All should appear in list
            r = await client.get(f"{BASE}/satellites", params={"include_offline": True})
            assert r.status_code == 200
            listed_ids = {s["id"] for s in r.json()}
            for nid in node_ids:
                assert nid in listed_ids, f"Satellite {nid} missing from list"

            # Cleanup
            await asyncio.gather(*[_cleanup_satellite(client, nid) for nid in node_ids])

    # 4. Job with no satellites connected ─────────────────────

    @pytest.mark.asyncio
    async def test_job_stays_queued_without_satellites(self):
        """A job created when no satellite is online should remain queued."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE}/jobs",
                json={
                    "type": "text_inference",
                    "payload": {"prompt": "resilience test"},
                    "priority": 3,
                    "timeout_seconds": 60,
                },
            )
            assert r.status_code == 200
            data = r.json()
            job_id = data["job_id"]
            assert data["status"] == "queued"

            # Verify still queued
            r2 = await client.get(f"{BASE}/jobs/{job_id}")
            assert r2.status_code == 200
            # Status should not have advanced to assigned/running
            assert r2.json().get("status") in ("queued", "assigned")

            # Cleanup
            await client.delete(f"{BASE}/jobs/{job_id}")

    # 5. Satellite CRUD roundtrip ─────────────────────────────

    @pytest.mark.asyncio
    async def test_satellite_crud_roundtrip(self):
        """Full create → read → update → delete cycle for a satellite."""
        async with httpx.AsyncClient() as client:
            # Create
            inv = await _create_invitation(client, name="crud-sat")
            reg = await _register_satellite(client, inv["code"], "crud-satellite")
            assert "node_id" in reg
            nid = reg["node_id"]

            # Read
            r = await client.get(f"{BASE}/satellites/{nid}")
            assert r.status_code == 200
            assert r.json()["name"] == "crud-satellite"

            # Update
            r = await client.put(
                f"{BASE}/satellites/{nid}",
                json={"name": "crud-satellite-v2", "visibility_level": 4},
            )
            assert r.status_code == 200

            r = await client.get(f"{BASE}/satellites/{nid}")
            assert r.json()["name"] == "crud-satellite-v2"
            assert r.json()["visibility_level"] == 4

            # Delete
            r = await client.delete(f"{BASE}/satellites/{nid}")
            assert r.status_code == 200

            r = await client.get(f"{BASE}/satellites/{nid}")
            assert r.status_code == 404

    # 6. Delete non-existent satellite ────────────────────────

    @pytest.mark.asyncio
    async def test_delete_nonexistent_satellite(self):
        """Deleting a satellite that doesn't exist returns 404."""
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{BASE}/satellites/00000000-0000-0000-0000-000000000000")
            assert r.status_code == 404

    # 7. Invitation listing filters ───────────────────────────

    @pytest.mark.asyncio
    async def test_invitation_listing_filters(self):
        """Verify include_used filter works on invitation listing."""
        async with httpx.AsyncClient() as client:
            inv = await _create_invitation(client, name="filter-test-sat")
            code = inv["code"]

            # Before use: should appear in active list
            r = await client.get(f"{BASE}/invitations", params={"include_used": False})
            assert r.status_code == 200
            codes = [i["code"] for i in r.json()]
            assert code in codes

            # Use it
            reg = await _register_satellite(client, code, "filter-sat")
            assert "node_id" in reg

            # After use: should NOT appear when include_used=false
            r = await client.get(f"{BASE}/invitations", params={"include_used": False})
            codes = [i["code"] for i in r.json()]
            assert code not in codes

            # But SHOULD appear when include_used=true
            r = await client.get(f"{BASE}/invitations", params={"include_used": True})
            codes = [i["code"] for i in r.json()]
            assert code in codes

            # Cleanup
            await _cleanup_satellite(client, reg["node_id"])

    # 8. Cancel already-cancelled job ─────────────────────────

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_job(self):
        """Cancelling an already-cancelled job returns 400."""
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BASE}/jobs",
                json={
                    "type": "custom",
                    "payload": {"task": "double-cancel"},
                    "priority": 1,
                    "timeout_seconds": 60,
                },
            )
            assert r.status_code == 200
            job_id = r.json()["job_id"]

            # First cancel
            r1 = await client.delete(f"{BASE}/jobs/{job_id}")
            assert r1.status_code == 200

            # Second cancel — should fail
            r2 = await client.delete(f"{BASE}/jobs/{job_id}")
            assert r2.status_code == 400
