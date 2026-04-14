"""
YeyoNet — API Routes.
Endpoints para gestionar la red distribuida.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.yeyonet.models import (
    InviteRequest,
    JobCreateRequest,
    RegisterRequest,
    RegisterResponse,
    SatelliteUpdate,
)

logger = logging.getLogger("yeyonet.routes")

router = APIRouter(prefix="/api/v1/yeyonet", tags=["yeyonet"])


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
    request: RegisterRequest,
    invite_mgr=Depends(get_invite_manager),
    sat_mgr=Depends(get_satellite_manager),
    identity=Depends(get_node_identity),
):
    """Un satélite se registra usando un código de invitación."""
    # Validar código
    invitation = await invite_mgr.validate_code(request.code)
    if not invitation:
        raise HTTPException(400, "Código inválido, expirado o ya usado")

    # Registrar satélite
    name = request.node_name or invitation.satellite_name
    node = await sat_mgr.register_satellite(
        name=name,
        mode=request.mode,
        permissions=invitation.permissions,
        visibility_level=invitation.visibility_level,
        ollama_host=request.ollama_host,
    )

    # Marcar invitación como usada
    await invite_mgr.mark_used(request.code, node.id)

    return RegisterResponse(
        node_id=node.id,
        auth_token=node.auth_token,
        central_ws_url=f"ws://localhost:8000/ws/yeyonet",
        permissions=node.permissions,
        visibility_level=node.visibility_level,
    )


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
