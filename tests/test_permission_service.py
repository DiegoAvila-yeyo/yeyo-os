"""
Tests para PermissionService — Micro-fase 3.21
"""

import asyncio
import pytest

from src.security.permission_service import (
    PermissionService,
    PermissionRequest,
    PermissionZone,
    PackageInfo,
)


@pytest.fixture
def service():
    """Instancia fresca de PermissionService por test."""
    return PermissionService()


@pytest.mark.asyncio
async def test_zona_verde_auto_aprueba(service):
    """Zona verde siempre retorna allowed=True sin esperar."""
    req = PermissionRequest(
        node_id="nodo-chat",
        permission="fs.read",
        permission_label="Leer archivos",
        zone=PermissionZone.GREEN,
        task_description="Leer configuración",
    )
    decision = await service.request(req)
    assert decision.allowed is True
    assert decision.remember is True


@pytest.mark.asyncio
async def test_zona_verde_no_espera_ws(service):
    """Zona verde retorna inmediatamente aunque no haya WS callback."""
    service.set_ws_callback(None)
    req = PermissionRequest(
        node_id="nodo-img",
        permission="gpu.compute",
        permission_label="GPU",
        zone=PermissionZone.GREEN,
        task_description="Generar imagen",
    )
    # Debe completarse en < 0.1s
    decision = await asyncio.wait_for(service.request(req), timeout=0.1)
    assert decision.allowed is True


@pytest.mark.asyncio
async def test_zona_amarilla_espera_respuesta(service):
    """Zona amarilla espera hasta que se llame resolve()."""
    sent_payloads = []

    async def mock_ws(payload):
        sent_payloads.append(payload)

    service.set_ws_callback(mock_ws)

    req = PermissionRequest(
        node_id="nodo-code",
        permission="sandbox.exec",
        permission_label="Ejecutar sandbox",
        zone=PermissionZone.YELLOW,
        task_description="Correr código del usuario",
    )

    # Lanzar request en background
    task = asyncio.create_task(service.request(req))
    await asyncio.sleep(0.05)  # Dar tiempo al task para iniciar

    # Verificar que se envió el evento WS
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["type"] == "permission_request"
    assert sent_payloads[0]["zone"] == "yellow"

    # Resolver desde "frontend"
    service.resolve(req.request_id, allowed=True, remember=False)

    decision = await asyncio.wait_for(task, timeout=1.0)
    assert decision.allowed is True
    assert decision.remember is False


@pytest.mark.asyncio
async def test_timeout_retorna_denied(service):
    """Si no hay respuesta en timeout, retorna denegado."""
    async def mock_ws(payload):
        pass  # No resuelve nunca

    service.set_ws_callback(mock_ws)
    service.TIMEOUT_SECONDS = 0.1  # Reducir timeout para el test

    req = PermissionRequest(
        node_id="nodo-test",
        permission="net.external",
        permission_label="Red externa",
        zone=PermissionZone.YELLOW,
        task_description="Llamada a API externa",
    )

    decision = await service.request(req)
    assert decision.allowed is False


@pytest.mark.asyncio
async def test_zona_roja_llega_al_frontend(service):
    """Zona roja también emite evento WS con zone=red."""
    sent = []

    async def mock_ws(payload):
        sent.append(payload)

    service.set_ws_callback(mock_ws)

    req = PermissionRequest(
        node_id="nodo-files",
        permission="fs.delete_all",
        permission_label="Borrar todo",
        zone=PermissionZone.RED,
        task_description="Limpiar directorio",
        package_info=PackageInfo(name="rm-tool", origin="pypi", size="2KB"),
    )

    task = asyncio.create_task(service.request(req))
    await asyncio.sleep(0.05)

    assert len(sent) == 1
    assert sent[0]["zone"] == "red"
    assert sent[0]["package_info"]["name"] == "rm-tool"

    service.resolve(req.request_id, allowed=False, remember=False)
    decision = await asyncio.wait_for(task, timeout=1.0)
    assert decision.allowed is False


def test_resolve_request_inexistente(service):
    """resolve() retorna False para request_id desconocido."""
    result = service.resolve("id-que-no-existe", allowed=True, remember=False)
    assert result is False
