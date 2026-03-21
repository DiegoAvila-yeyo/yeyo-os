## ═══════════════════════════════════════
## MICRO-FASE 4.11 — Package API Endpoints
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 4.11-1 [VSCODE] — API REST para gestión de paquetes

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.11 de Capa 4 (Sistema Nervioso): crear los endpoints REST API para gestión de paquetes.

CONTEXTO:
- Micro-fases 4.0-4.10 completadas: paquetes, permisos, containers, pipelines, database, updater, apt
- API REST para gestionar paquetes desde el frontend
- FastAPI como framework (ya configurado en Capa 1)
- Endpoints para instalar, desinstalar, listar, permisos, updates

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/api/routes

2. Crear archivo src/api/routes/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/src/api/routes/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo src/api/routes/packages.py:

   Ruta: ~/yeyo-os/src/api/routes/packages.py
   Contenido:

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

4. Crear archivo tests/unit/api/__init__.py (vacío si no existe):

   Ruta: ~/yeyo-os/tests/unit/api/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/api/test_packages_api.py:

   Ruta: ~/yeyo-os/tests/unit/api/test_packages_api.py
   Contenido:

   """Tests para Package API Endpoints — Micro-fase 4.11"""

   import io
   import pytest
   from fastapi import FastAPI
   from fastapi.testclient import TestClient

   from src.api.routes.packages import router, _installed_packages, _package_permissions


   @pytest.fixture
   def client():
       app = FastAPI()
       app.include_router(router)
       _installed_packages.clear()
       _package_permissions.clear()
       return TestClient(app)


   @pytest.fixture
   def client_with_package(client):
       _installed_packages["test-pkg"] = {
           "name": "test-pkg",
           "version": "1.0.0",
           "author": "Test",
           "description": "Test package",
           "type": "node",
           "privilege_level": "L2",
           "status": "installed",
       }
       return client


   class TestListPackages:
       """Tests para GET /api/v1/packages"""

       def test_list_empty(self, client):
           response = client.get("/api/v1/packages/")
           assert response.status_code == 200
           assert response.json() == []

       def test_list_returns_packages(self, client_with_package):
           response = client_with_package.get("/api/v1/packages/")
           assert response.status_code == 200
           data = response.json()
           assert len(data) == 1
           assert data[0]["name"] == "test-pkg"


   class TestGetPackage:
       """Tests para GET /api/v1/packages/{name}"""

       def test_get_existing_package(self, client_with_package):
           response = client_with_package.get("/api/v1/packages/test-pkg")
           assert response.status_code == 200
           assert response.json()["name"] == "test-pkg"

       def test_get_nonexistent_returns_404(self, client):
           response = client.get("/api/v1/packages/nonexistent")
           assert response.status_code == 404


   class TestUninstallPackage:
       """Tests para DELETE /api/v1/packages/{name}"""

       def test_uninstall_existing(self, client_with_package):
           response = client_with_package.delete("/api/v1/packages/test-pkg")
           assert response.status_code == 200
           assert response.json()["success"] is True

           response = client_with_package.get("/api/v1/packages/test-pkg")
           assert response.status_code == 404

       def test_uninstall_nonexistent_returns_404(self, client):
           response = client.delete("/api/v1/packages/nonexistent")
           assert response.status_code == 404


   class TestPermissions:
       """Tests para POST/GET /api/v1/packages/{name}/permissions"""

       def test_grant_permission(self, client_with_package):
           response = client_with_package.post(
               "/api/v1/packages/test-pkg/permissions",
               json={"action": "grant", "permission": "memory.read"},
           )
           assert response.status_code == 200
           assert response.json()["granted"] is True

       def test_revoke_permission(self, client_with_package):
           client_with_package.post(
               "/api/v1/packages/test-pkg/permissions",
               json={"action": "grant", "permission": "memory.read"},
           )
           response = client_with_package.post(
               "/api/v1/packages/test-pkg/permissions",
               json={"action": "revoke", "permission": "memory.read"},
           )
           assert response.status_code == 200
           assert response.json()["granted"] is False

       def test_get_permissions(self, client_with_package):
           client_with_package.post(
               "/api/v1/packages/test-pkg/permissions",
               json={"action": "grant", "permission": "memory.read"},
           )
           response = client_with_package.get(
               "/api/v1/packages/test-pkg/permissions"
           )
           assert response.status_code == 200
           perms = response.json()["permissions"]
           assert len(perms) == 1

       def test_permissions_nonexistent_package(self, client):
           response = client.post(
               "/api/v1/packages/nonexistent/permissions",
               json={"action": "grant", "permission": "memory.read"},
           )
           assert response.status_code == 404

       def test_invalid_action_rejected(self, client_with_package):
           response = client_with_package.post(
               "/api/v1/packages/test-pkg/permissions",
               json={"action": "invalid", "permission": "memory.read"},
           )
           assert response.status_code == 422


   class TestCheckUpdates:
       """Tests para GET /api/v1/packages/updates/check"""

       def test_check_updates(self, client):
           response = client.get("/api/v1/packages/updates/check")
           assert response.status_code == 200
           assert "updates" in response.json()


   class TestInstallPackage:
       """Tests para POST /api/v1/packages/install"""

       def test_install_invalid_format_rejected(self, client):
           file_content = b"not a real package"
           response = client.post(
               "/api/v1/packages/install",
               files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")},
           )
           assert response.status_code == 400

       def test_install_ypkg_file(self, client):
           file_content = b"fake ypkg content"
           response = client.post(
               "/api/v1/packages/install",
               files={"file": ("test-pkg-1.0.0.ypkg", io.BytesIO(file_content), "application/gzip")},
           )
           assert response.status_code == 200
           assert response.json()["success"] is True

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install fastapi httpx python-multipart
   python -m pytest tests/unit/api/test_packages_api.py -v

VERIFICAR:
- [ ] Archivo src/api/routes/packages.py existe con router
- [ ] POST /api/v1/packages/install acepta archivos .ypkg
- [ ] DELETE /api/v1/packages/{name} desinstala correctamente
- [ ] GET /api/v1/packages/ lista todos los paquetes como JSON
- [ ] GET /api/v1/packages/{name} retorna info del paquete
- [ ] POST /api/v1/packages/{name}/permissions gestiona permisos (grant/revoke)
- [ ] GET /api/v1/packages/{name}/permissions retorna permisos
- [ ] GET /api/v1/packages/updates/check verifica actualizaciones
- [ ] 404 para paquetes no existentes
- [ ] 422 para acciones de permiso inválidas
- [ ] TODOS los tests pasan

SI FALLA:
- FastAPI no instalado: pip install fastapi
- python-multipart no instalado: pip install python-multipart
- httpx no instalado: pip install httpx (para TestClient)
- TestClient import: from fastapi.testclient import TestClient

NO HACER:
- No implementar autenticación (eso sería otra capa)
- No conectar con PackageInstaller real (integración posterior)
- No agregar endpoints que no están en la especificación

GATE: API REST completa para paquetes, todos los endpoints existen y funcionan, permisos gestionados, JSON responses, todos los tests pasan.
```
