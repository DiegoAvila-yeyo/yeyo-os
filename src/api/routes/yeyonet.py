"""
YeyoNet — API Routes.
Endpoints para gestionar la red distribuida.
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from src.yeyonet.models import (
    InviteRequest,
    JobCreateRequest,
    RegisterRequest,
    RegisterResponse,
    SatelliteUpdate,
)

logger = logging.getLogger("yeyonet.routes")

router = APIRouter(prefix="/api/v1/yeyonet", tags=["yeyonet"])


def _build_central_ws_url(request: Request) -> str:
    scheme = "wss" if request.url.scheme == "https" else "ws"
    return f"{scheme}://{request.url.netloc}/ws/yeyonet"


def _normalize_central_url(raw_url: str) -> str:
    central_url = raw_url.strip().rstrip("/")
    if not central_url:
        raise HTTPException(400, "URL de la Central requerida")
    if not central_url.startswith(("http://", "https://")):
        raise HTTPException(400, "La URL de la Central debe empezar con http:// o https://")
    return central_url


def _extract_upstream_error(response: httpx.Response):
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail:
            return detail
        error = payload.get("error")
        if error:
            return error

    return payload or response.text.strip() or f"HTTP {response.status_code}"


def _describe_http_error(exc: httpx.HTTPError) -> str:
    if isinstance(exc, httpx.ConnectTimeout):
        base = "timeout de conexión"
    elif isinstance(exc, httpx.ReadTimeout):
        base = "la Central no respondió a tiempo"
    elif isinstance(exc, httpx.ConnectError):
        base = "no se pudo abrir conexión TCP"
    elif isinstance(exc, httpx.NetworkError):
        base = "fallo de red"
    elif isinstance(exc, httpx.RemoteProtocolError):
        base = "la Central respondió con un protocolo inválido"
    else:
        base = exc.__class__.__name__

    message = str(exc).strip()
    if message and message.lower() != base.lower():
        return f"{base}: {message}"

    return base


# ─── Dependency injection placeholders ───────────────────────

async def get_invite_manager():
    raise HTTPException(503, "InviteManager not initialized")


async def get_satellite_manager():
    raise HTTPException(503, "SatelliteManager not initialized")


async def get_node_identity():
    raise HTTPException(503, "NodeIdentity not initialized")


# ─── Invitaciones ────────────────────────────────────────────

@router.post("/invite")
async def create_invitation(
    request: InviteRequest,
    invite_mgr=Depends(get_invite_manager),
):
    """Genera un código de invitación para un nuevo satélite."""
    invitation = await invite_mgr.create_invitation(
        satellite_name=request.satellite_name,
        permissions=request.permissions,
        visibility_level=request.visibility_level,
        expires_in_days=request.expires_in_days,
    )
    return {
        "code": invitation.code,
        "satellite_name": invitation.satellite_name,
        "permissions": invitation.permissions,
        "visibility_level": invitation.visibility_level,
        "expires_at": invitation.expires_at.isoformat(),
    }


@router.get("/invitations")
async def list_invitations(
    include_used: bool = Query(False),
    invite_mgr=Depends(get_invite_manager),
):
    """Lista invitaciones activas."""
    invitations = await invite_mgr.list_invitations(include_used=include_used)
    return [
        {
            "id": inv.id,
            "code": inv.code,
            "satellite_name": inv.satellite_name,
            "permissions": inv.permissions,
            "visibility_level": inv.visibility_level,
            "used": inv.used,
            "used_at": inv.used_at.isoformat() if inv.used_at else None,
            "expires_at": inv.expires_at.isoformat(),
            "is_available": inv.is_available,
        }
        for inv in invitations
    ]


@router.delete("/invitations/{invitation_id}")
async def delete_invitation(
    invitation_id: str,
    invite_mgr=Depends(get_invite_manager),
):
    """Elimina una invitación no usada."""
    deleted = await invite_mgr.delete_invitation(invitation_id)
    if not deleted:
        raise HTTPException(404, "Invitación no encontrada o ya usada")
    return {"status": "deleted"}


# ─── Registro de satélites ───────────────────────────────────

@router.post("/register", response_model=RegisterResponse)
async def register_satellite(
    body: RegisterRequest,
    http_request: Request,
    invite_mgr=Depends(get_invite_manager),
    sat_mgr=Depends(get_satellite_manager),
    identity=Depends(get_node_identity),
):
    """Un satélite se registra usando un código de invitación."""
    # Validar código
    invitation = await invite_mgr.validate_code(body.code)
    if not invitation:
        raise HTTPException(400, "Código inválido, expirado o ya usado")

    # Registrar satélite
    name = body.node_name or invitation.satellite_name
    node = await sat_mgr.register_satellite(
        name=name,
        mode=body.mode,
        permissions=invitation.permissions,
        visibility_level=invitation.visibility_level,
        ollama_host=body.ollama_host,
    )

    # Marcar invitación como usada
    await invite_mgr.mark_used(body.code, node.id)

    return RegisterResponse(
        node_id=node.id,
        auth_token=node.auth_token,
        central_ws_url=_build_central_ws_url(http_request),
        permissions=node.permissions,
        visibility_level=node.visibility_level,
    )


class RemoteRegisterRequest(RegisterRequest):
    central_url: str


@router.post("/register-via-central", response_model=RegisterResponse)
async def register_satellite_via_central(
    body: RemoteRegisterRequest,
):
    """Registra este nodo usando la Central remota desde el backend local."""
    central_url = _normalize_central_url(body.central_url)
    register_url = f"{central_url}/api/v1/yeyonet/register"
    payload = body.model_dump(exclude_none=True, exclude={"central_url"})

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            response = await client.post(register_url, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("[satellite] failed remote register against %s: %s", central_url, exc)
        detail = _describe_http_error(exc)
        raise HTTPException(
            502,
            (
                f"No se pudo alcanzar la Central en {central_url}. "
                "Verifica que el backend esté corriendo en :8000, expuesto en 0.0.0.0 "
                "y que ambas PCs estén en la misma red. "
                f"Detalle: {detail}"
            ),
        ) from exc

    if response.is_error:
        detail = _extract_upstream_error(response)
        raise HTTPException(response.status_code, detail)

    return RegisterResponse.model_validate(response.json())


# ─── Gestión de satélites ───────────────────────────────────

@router.get("/satellites")
async def list_satellites(
    include_offline: bool = Query(True),
    sat_mgr=Depends(get_satellite_manager),
):
    """Lista todos los satélites registrados."""
    satellites = await sat_mgr.list_satellites(include_offline=include_offline)
    return [
        {
            "id": s.id,
            "name": s.name,
            "mode": s.mode,
            "status": s.status,
            "permissions": s.permissions,
            "visibility_level": s.visibility_level,
            "resources": s.resources.model_dump() if hasattr(s.resources, 'model_dump') else s.resources,
            "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in satellites
    ]


@router.get("/satellites/{node_id}")
async def get_satellite(
    node_id: str,
    sat_mgr=Depends(get_satellite_manager),
):
    """Obtiene detalles de un satélite."""
    node = await sat_mgr.get_satellite(node_id)
    if not node:
        raise HTTPException(404, "Satélite no encontrado")
    return {
        "id": node.id,
        "name": node.name,
        "mode": node.mode,
        "status": node.status,
        "permissions": node.permissions,
        "visibility_level": node.visibility_level,
        "resources": node.resources.model_dump() if hasattr(node.resources, 'model_dump') else node.resources,
        "ollama_host": node.ollama_host,
        "ip_address": node.ip_address,
        "last_seen_at": node.last_seen_at.isoformat() if node.last_seen_at else None,
        "created_at": node.created_at.isoformat() if node.created_at else None,
    }


@router.put("/satellites/{node_id}")
async def update_satellite(
    node_id: str,
    update: SatelliteUpdate,
    sat_mgr=Depends(get_satellite_manager),
):
    """Actualiza permisos/nombre de un satélite."""
    node = await sat_mgr.update_satellite(
        node_id=node_id,
        name=update.name,
        permissions=update.permissions,
        visibility_level=update.visibility_level,
    )
    if not node:
        raise HTTPException(404, "Satélite no encontrado")
    return {"status": "updated", "id": node.id, "name": node.name}


@router.delete("/satellites/{node_id}")
async def remove_satellite(
    node_id: str,
    sat_mgr=Depends(get_satellite_manager),
):
    """Desconecta y elimina un satélite de la red."""
    deleted = await sat_mgr.remove_satellite(node_id)
    if not deleted:
        raise HTTPException(404, "Satélite no encontrado")
    return {"status": "removed"}


# ─── Estadísticas de la red ──────────────────────────────────

@router.get("/stats")
async def network_stats(
    sat_mgr=Depends(get_satellite_manager),
    identity=Depends(get_node_identity),
):
    """Estadísticas generales de la red."""
    stats = await sat_mgr.get_network_stats()
    return {
        "central_node_id": identity.node_id,
        "role": identity.role.value,
        **stats,
    }


# ─── Identidad del nodo actual ───────────────────────────────

@router.get("/identity")
async def get_identity(
    identity=Depends(get_node_identity),
):
    """Retorna la identidad de este nodo."""
    node = await identity.get_node()
    if not node:
        raise HTTPException(500, "No se pudo obtener la identidad del nodo")
    return {
        "node_id": node.id,
        "name": node.name,
        "role": node.role,
        "status": node.status,
    }


# ─── Job Orchestrator dependency ─────────────────────────────

async def get_job_orchestrator():
    raise HTTPException(503, "JobOrchestrator not initialized")


async def get_sync_manager():
    raise HTTPException(503, "SyncManager not initialized")


# ─── Jobs ────────────────────────────────────────────────────

@router.post("/jobs")
async def create_job(
    request: JobCreateRequest,
    orchestrator=Depends(get_job_orchestrator),
    identity=Depends(get_node_identity),
):
    """Crea un nuevo job en la cola."""
    job = await orchestrator.create_job(
        job_type=request.type,
        payload=request.payload,
        requested_by=identity.node_id,
        priority=request.priority,
        timeout_seconds=request.timeout_seconds,
    )
    return {"job_id": job.id, "type": job.type.value, "status": job.status.value}


@router.post("/jobs/distributed")
async def create_distributed_job(
    request: JobCreateRequest,
    orchestrator=Depends(get_job_orchestrator),
    identity=Depends(get_node_identity),
):
    """Crea un job distribuido con múltiples items (para render farm)."""
    items = request.payload.get("items", [])
    if not items:
        raise HTTPException(400, "payload.items is required for distributed jobs")

    result = await orchestrator.create_distributed_job(
        job_type=request.type,
        items=items,
        requested_by=identity.node_id,
        priority=request.priority,
    )
    return result


@router.get("/jobs")
async def list_jobs(
    status: str | None = Query(None),
    type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    orchestrator=Depends(get_job_orchestrator),
):
    """Lista jobs con filtros opcionales."""
    jobs = await orchestrator.list_jobs(status=status, job_type=type, limit=limit)
    return jobs


@router.get("/jobs/stats")
async def job_stats(
    orchestrator=Depends(get_job_orchestrator),
):
    """Estadísticas de la cola de jobs."""
    return await orchestrator.get_queue_stats()


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    orchestrator=Depends(get_job_orchestrator),
):
    """Obtiene estado y resultado de un job."""
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    return job


@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: str,
    orchestrator=Depends(get_job_orchestrator),
):
    """Obtiene sub-resultados de un job distribuido."""
    results = await orchestrator.get_job_results(job_id)
    return results


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    orchestrator=Depends(get_job_orchestrator),
):
    """Cancela un job si aún no completó."""
    cancelled = await orchestrator.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(400, "No se pudo cancelar (ya completado o no existe)")
    return {"status": "cancelled"}


# ─── Memory Sync ─────────────────────────────────────────────

@router.post("/sync/trigger/{node_id}")
async def trigger_sync(
    node_id: str,
    sync_mgr=Depends(get_sync_manager),
    sat_mgr=Depends(get_satellite_manager),
):
    """Fuerza un push de memorias hacia un satélite específico."""
    sat = await sat_mgr.get_satellite(node_id)
    if not sat:
        raise HTTPException(404, "Satélite no encontrado")
    pushed = await sync_mgr.push_memories_to_satellite(node_id)
    return {"status": "ok", "memories_pushed": pushed}


@router.get("/sync/stats")
async def sync_stats(
    sync_mgr=Depends(get_sync_manager),
):
    """Estadísticas del sistema de sincronización."""
    stats = await sync_mgr.get_sync_stats()
    return stats


@router.post("/sync/training-corpus/{node_id}")
async def share_training_corpus(
    node_id: str,
    language: Optional[str] = Query(None),
    min_score: float = Query(7.0),
    sync_mgr=Depends(get_sync_manager),
    sat_mgr=Depends(get_satellite_manager),
):
    """Comparte el corpus de entrenamiento con un satélite."""
    sat = await sat_mgr.get_satellite(node_id)
    if not sat:
        raise HTTPException(404, "Satélite no encontrado")
    shared = await sync_mgr.share_training_corpus(
        node_id, language=language, min_score=min_score
    )
    return {"status": "ok", "entries_shared": shared}


# ─── Satellite connection management ────────────────────────


class ConnectRequest(BaseModel):
    node_id: str | None = None
    auth_token: str | None = None
    central_ws_url: str | None = None
    central_name: str | None = None


async def get_yeyonet_client():
    """Dependency placeholder — overridden in main.py."""
    return None


@router.post("/connect")
async def connect_as_satellite(
    body: ConnectRequest | None = None,
    client_holder=Depends(get_yeyonet_client),
):
    """Start WebSocket client to Central using saved or provided satellite config."""
    from src.yeyonet.satellite_config import load_config, save_config

    # If body has config fields, save them first
    if body and body.node_id and body.auth_token and body.central_ws_url:
        save_config(
            node_id=body.node_id,
            auth_token=body.auth_token,
            central_ws_url=body.central_ws_url,
            central_name=body.central_name or "",
        )

    config = load_config()
    if not config:
        raise HTTPException(404, "No satellite config found. Register first.")

    # client_holder is a dict with "client" key, managed by main.py
    holder = client_holder if client_holder is not None else {}
    existing = holder.get("client")

    # If already connected, return status
    if existing and existing.connected:
        return {
            "status": "already_connected",
            "connected": True,
            "central_ws_url": config["central_ws_url"],
            "node_id": config["node_id"],
            "central_name": config.get("central_name", ""),
        }

    # Stop old client if exists but disconnected
    if existing:
        try:
            await existing.stop()
        except Exception:
            pass

    # Start new client
    from src.yeyonet.client import YeyoNetClient

    new_client = YeyoNetClient(
        central_ws_url=config["central_ws_url"],
        node_id=config["node_id"],
        auth_token=config["auth_token"],
    )
    await new_client.start()
    holder["client"] = new_client
    logger.info(f"[satellite] WebSocket client started → {config['central_ws_url']}")

    return {
        "status": "connecting",
        "connected": False,  # still connecting async
        "central_ws_url": config["central_ws_url"],
        "node_id": config["node_id"],
        "central_name": config.get("central_name", ""),
    }


@router.post("/disconnect")
async def disconnect_satellite(
    client_holder=Depends(get_yeyonet_client),
):
    """Stop WebSocket client and clear config."""
    from src.yeyonet.satellite_config import clear_config

    holder = client_holder if client_holder is not None else {}
    existing = holder.get("client")
    if existing:
        await existing.stop()
        holder["client"] = None
        logger.info("[satellite] WebSocket client stopped")

    clear_config()
    return {"status": "disconnected", "connected": False}


@router.get("/connection")
async def get_connection_status(
    client_holder=Depends(get_yeyonet_client),
):
    """Get current satellite connection status."""
    from src.yeyonet.satellite_config import load_config

    config = load_config()
    holder = client_holder if client_holder is not None else {}
    existing = holder.get("client")

    connected = bool(existing and existing.connected)

    return {
        "configured": config is not None,
        "connected": connected,
        "central_ws_url": config["central_ws_url"] if config else None,
        "node_id": config["node_id"] if config else None,
        "central_name": config.get("central_name", "") if config else None,
        "connected_at": config.get("connected_at") if config else None,
    }
