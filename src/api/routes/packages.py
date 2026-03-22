"""
YeyoOS — Package API Endpoints
Micro-fase 4.11 — Capa 4: Sistema Nervioso

REST API para gestión de paquetes .ypkg.
Delega a PackageInstaller, PackageDatabase y PermissionManager reales.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from src.pkg.installer import PackageInstaller, InstallError, PermissionDeniedError, SignatureError
from src.pkg.database import PackageDatabase
from src.security.permissions import PermissionManager, Permission


router = APIRouter(prefix="/api/v1/packages", tags=["packages"])

# Servicios — inicializados al arrancar la app via init_package_services()
_installer: Optional[PackageInstaller] = None
_db: Optional[PackageDatabase] = None
_perm_manager: Optional[PermissionManager] = None


def init_package_services(
    installer: Optional[PackageInstaller] = None,
    db: Optional[PackageDatabase] = None,
    perm_manager: Optional[PermissionManager] = None,
) -> None:
    """Inicializa los servicios de paquetes. Llamar al arrancar la app."""
    global _installer, _db, _perm_manager
    _installer = installer or PackageInstaller()
    _db = db
    _perm_manager = perm_manager or PermissionManager()


def _get_installer() -> PackageInstaller:
    if _installer is None:
        init_package_services()
    return _installer  # type: ignore


def _get_perm_manager() -> PermissionManager:
    if _perm_manager is None:
        init_package_services()
    return _perm_manager  # type: ignore


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


@router.post("/install", response_model=InstallResponse)
async def install_package(file: UploadFile = File(...)):
    """
    POST /api/v1/packages/install — Instalar un paquete .ypkg
    Recibe el archivo .ypkg y lo instala via PackageInstaller.
    """
    if not file.filename or not file.filename.endswith(".ypkg"):
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Se requiere un archivo .ypkg",
        )

    installer = _get_installer()
    tmp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".ypkg", delete=False
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        pkg_info = await installer.install(tmp_path)

        return InstallResponse(
            success=True,
            package=PackageInfo(**pkg_info),
        )
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SignatureError as e:
        raise HTTPException(status_code=422, detail=f"Firma inválida: {e}")
    except InstallError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


@router.delete("/{name}", response_model=MessageResponse)
async def uninstall_package(name: str):
    """
    DELETE /api/v1/packages/{name} — Desinstalar un paquete via PackageInstaller.
    """
    installer = _get_installer()

    try:
        await installer.uninstall(name)
    except InstallError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return MessageResponse(
        success=True,
        message=f"Paquete '{name}' desinstalado correctamente",
    )


@router.get("/", response_model=list[PackageInfo])
async def list_packages():
    """
    GET /api/v1/packages — Listar paquetes instalados.
    """
    installer = _get_installer()
    packages = installer.list_installed()
    return [PackageInfo(**pkg) for pkg in packages]


@router.get("/{name}", response_model=PackageInfo)
async def get_package(name: str):
    """
    GET /api/v1/packages/{name} — Obtener info de un paquete.
    """
    installer = _get_installer()
    try:
        pkg = installer.get_info(name)
    except InstallError:
        raise HTTPException(
            status_code=404,
            detail=f"Paquete '{name}' no encontrado",
        )
    return PackageInfo(**pkg)


@router.post("/{name}/permissions", response_model=PermissionResponse)
async def manage_permissions(name: str, request: PermissionRequest):
    """
    POST /api/v1/packages/{name}/permissions — Gestionar permisos (ALLOWLIST).
    """
    installer = _get_installer()
    try:
        installer.get_info(name)
    except InstallError:
        raise HTTPException(
            status_code=404,
            detail=f"Paquete '{name}' no encontrado",
        )

    pm = _get_perm_manager()

    try:
        perm = Permission(request.permission)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Permiso inválido: {request.permission}",
        )

    if request.action == "grant":
        await pm.request(name, [perm])
        granted = True
    else:
        await pm.revoke(name, perm)
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
    installer = _get_installer()
    try:
        installer.get_info(name)
    except InstallError:
        raise HTTPException(
            status_code=404,
            detail=f"Paquete '{name}' no encontrado",
        )

    pm = _get_perm_manager()
    granted_perms = await pm.get_grants(name)

    return {
        "package_name": name,
        "permissions": [
            {"permission": p.value, "granted": True}
            for p in granted_perms
        ],
    }


@router.get("/updates/check")
async def check_updates():
    """
    GET /api/v1/packages/updates/check — Verificar actualizaciones.
    """
    return {
        "updates": [],
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
