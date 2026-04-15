"""
Cloud Sync — API Routes.
Endpoints para monitorear y controlar la sincronización cloud (Supabase).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("cloud_sync.routes")

router = APIRouter(prefix="/api/v1/cloud-sync", tags=["cloud-sync"])


# ─── Dependency injection placeholder ────────────────────

async def get_cloud_sync():
    raise HTTPException(503, "CloudSyncService not initialized")


# ─── Endpoints ───────────────────────────────────────────

@router.get("/status")
async def cloud_sync_status(sync=Depends(get_cloud_sync)):
    """Whether cloud sync is configured and active."""
    if sync is None:
        return JSONResponse(content={
            "configured": False,
            "running": False,
            "message": "SUPABASE_URL / SUPABASE_KEY not set",
        })
    return JSONResponse(content={
        "configured": sync.is_configured,
        "running": sync._running,
    })


@router.get("/stats")
async def cloud_sync_stats(sync=Depends(get_cloud_sync)):
    """Return detailed sync statistics."""
    if sync is None:
        raise HTTPException(503, "Cloud sync not configured")
    return JSONResponse(content=sync.get_stats())


@router.post("/force")
async def cloud_sync_force(sync=Depends(get_cloud_sync)):
    """Trigger a manual full sync cycle (push + pull)."""
    if sync is None:
        raise HTTPException(503, "Cloud sync not configured")
    result = await sync.force_full_sync()
    return JSONResponse(content={"status": "ok", **result})
