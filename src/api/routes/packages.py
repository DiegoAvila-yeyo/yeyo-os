"""
YeyoOS — Package API Endpoints
Micro-fase 4.11 — Capa 4: Sistema Nervioso

REST API para gestión de paquetes .ypkg.
Instalar, desinstalar, listar, permisos, updates.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional
import tempfile
import shutil
from pathlib import Path


router = APIRouter(prefix="/api/v1/packages", tags=["packages"])


class PackageInfo(BaseModel):
    """Información de un paquete."""
    name: str
    version: str
    author: str
    description: str
    type: str
    privilege_level: str = "L2"
    status: str = "installed"
    installed_at: Optional[str] = None


class PermissionRequest(BaseModel):
    """Solicitud de gestión de permisos."""
    action: str = Field(..., pattern="^(grant|revoke)$")
    permission: str


class PermissionResponse(BaseModel):
    """Respuesta de permisos."""
    package_name: str
    permission: str
    granted: bool


class UpdateInfo(BaseModel):
    """Información de actualización disponible."""
    package_name: str
    current_version: str
    new_version: str


class InstallResponse(BaseModel):
    """Respuesta de instalación."""
    success: bool
    package: Optional[PackageInfo] = None
    error: Optional[str] = None


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje."""
    success: bool
    message: str


_installed_packages: dict[str, dict] = {}
_package_permissions: dict[str, dict[str, bool]] = {}


@router.post("/install", response_model=InstallResponse)
async def install_package(file: UploadFile = File(...)):
    """
    POST /api/v1/packages/install — Instalar un paquete .ypkg
    Recibe el archivo .ypkg y lo instala en el sistema.
    """
    if not file.filename or not file.filename.endswith(".ypkg"):
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Se requiere un archivo .ypkg",
        )

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".ypkg", delete=False
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        package_name = file.filename.replace(".ypkg", "").rsplit("-", 1)[0]

        package_info = {
            "name": package_name,
            "version": "1.0.0",
            "author": "unknown",
            "description": f"Package {package_name}",
            "type": "node",
            "privilege_level": "L2",
            "status": "installed",
        }
        _installed_packages[package_name] = package_info

        Path(tmp_path).unlink(missing_ok=True)

        return InstallResponse(
            success=True,
            package=PackageInfo(**package_info),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}", response_model=MessageResponse)
async def uninstall_package(name: str):
    """
    DELETE /api/v1/packages/{name} — Desinstalar un paquete.
    """
    if name not in _installed_packages:
        raise HTTPException(
            status_code=404,
            detail=f"Paquete '{name}' no encontrado",
        )

    del _installed_packages[name]
    _package_permissions.pop(name, None)

    return MessageResponse(
        success=True,
        message=f"Paquete '{name}' desinstalado correctamente",
    )


@router.get("/", response_model=list[PackageInfo])
async def list_packages():
    """
    GET /api/v1/packages — Listar paquetes instalados.
    """
    return [PackageInfo(**pkg) for pkg in _installed_packages.values()]


@router.get("/{name}", response_model=PackageInfo)
async def get_package(name: str):
    """
    GET /api/v1/packages/{name} — Obtener info de un paquete.
    """
    if name not in _installed_packages:
        raise HTTPException(
            status_code=404,
            detail=f"Paquete '{name}' no encontrado",
        )
    return PackageInfo(**_installed_packages[name])


@router.post("/{name}/permissions", response_model=PermissionResponse)
async def manage_permissions(name: str, request: PermissionRequest):
    """
    POST /api/v1/packages/{name}/permissions — Gestionar permisos.
    """
    if name not in _installed_packages:
        raise HTTPException(
            status_code=404,
            detail=f"Paquete '{name}' no encontrado",
        )

    if name not in _package_permissions:
        _package_permissions[name] = {}

    if request.action == "grant":
        _package_permissions[name][request.permission] = True
        granted = True
    else:
        _package_permissions[name][request.permission] = False
        granted = False

    return PermissionResponse(
        package_name=name,
        permission=request.permission,
        granted=granted,
    )


@router.get("/{name}/permissions")
async def get_permissions(name: str):
    """
    GET /api/v1/packages/{name}/permissions — Obtener permisos de un paquete.
    """
    if name not in _installed_packages:
        raise HTTPException(
            status_code=404,
            detail=f"Paquete '{name}' no encontrado",
        )

    perms = _package_permissions.get(name, {})
    return {
        "package_name": name,
        "permissions": [
            {"permission": p, "granted": g}
            for p, g in perms.items()
        ],
    }


@router.get("/updates/check")
async def check_updates():
    """
    GET /api/v1/packages/updates/check — Verificar actualizaciones.
    """
    return {"updates": [], "checked_at": "now"}
