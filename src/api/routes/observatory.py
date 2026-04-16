"""
YeyoOS — Observatory API Routes
Real-time monitoring endpoints for agents and workflows.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from src.observatory.service import ObservatoryService, get_observatory_service

router = APIRouter(prefix="/api/v1/observatory", tags=["observatory"])


@router.get("/metrics", summary="Current observatory metrics")
async def get_metrics(
    service: ObservatoryService = Depends(get_observatory_service),
) -> dict:
    """Return aggregated metrics for workflows, agents, and system health."""
    return service.get_metrics()


@router.get("/agents", summary="Tracked agent states")
async def get_agents(
    service: ObservatoryService = Depends(get_observatory_service),
) -> list[dict]:
    """Return the current state of every tracked agent."""
    return service.get_agents()


@router.get("/events", summary="Recent events")
async def get_events(
    limit: int = Query(default=50, ge=1, le=500, description="Max events to return"),
    service: ObservatoryService = Depends(get_observatory_service),
) -> list[dict]:
    """Return the most-recent observatory events (newest first)."""
    return service.get_recent_events(limit)


@router.websocket("/live")
async def observatory_live(
    ws: WebSocket,
    service: ObservatoryService = Depends(get_observatory_service),
) -> None:
    """WebSocket endpoint that streams observatory events in real-time."""
    await ws.accept()
    service.add_ws(ws)
    try:
        while True:
            # Keep the connection alive by reading client messages (pings, etc.)
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        service.remove_ws(ws)
