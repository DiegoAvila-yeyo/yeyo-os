## ═══════════════════════════════════════
## MICRO-FASE 7.3 — YEYO Store Server
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.3-1 [VSCODE] — Crear backend del YEYO Store (marketplace de paquetes)

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.3 de Capa 7 (Evolución): crear el servidor backend del YEYO Store, el marketplace de paquetes de YeyoOS.

CONTEXTO:
- Capas 0-6 completadas + micro-fases 7.0-7.2 (training pipeline)
- YEYO Store es el marketplace donde developers publican paquetes (.ypkg)
- Pipeline de submission: developer sube → scan de seguridad → review → publicado
- Trust levels: Verified (equipo YeyoOS), Trusted (comunidad con historial), New (review completo)
- Rating system: 1-5 estrellas + reviews
- REST API con FastAPI
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura de directorios si no existe:
   mkdir -p src/store
   mkdir -p tests/unit/store

2. Crear archivo src/store/__init__.py:

   Ruta: ~/yeyo-os/src/store/__init__.py
   Contenido:
   from .server import StoreServer, Package, PackageSubmission, TrustLevel

3. Crear archivo src/store/server.py:

   Ruta: ~/yeyo-os/src/store/server.py
   Contenido:

   """
   YeyoOS — YEYO Store Server
   Micro-fase 7.3 — Capa 7: Evolución

   Backend del marketplace de paquetes.
   Pipeline: submit → security scan → review → publish.
   Trust levels: Verified, Trusted, New.
   """

   import json
   import logging
   import uuid
   from datetime import datetime
   from enum import Enum
   from pathlib import Path
   from typing import Optional

   from fastapi import FastAPI, HTTPException, UploadFile, File, Query
   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.store.server")


   class TrustLevel(str, Enum):
       """Nivel de confianza del developer."""
       VERIFIED = "verified"    # Equipo YeyoOS — auto-approved
       TRUSTED = "trusted"      # Comunidad con historial — fast review
       NEW = "new"              # Primer paquete — full manual review


   class PackageStatus(str, Enum):
       """Estado del paquete en el pipeline."""
       SUBMITTED = "submitted"
       SCANNING = "scanning"
       REVIEW = "review"
       APPROVED = "approved"
       REJECTED = "rejected"
       PUBLISHED = "published"


   class PackagePermission(str, Enum):
       """Permisos que un paquete puede solicitar."""
       FILESYSTEM_READ = "filesystem.read"
       FILESYSTEM_WRITE = "filesystem.write"
       NETWORK_LOCAL = "network.local"
       NETWORK_INTERNET = "network.internet"
       GPU_ACCESS = "gpu.access"
       SYSTEM_INFO = "system.info"
       NOTIFICATIONS = "notifications"


   class DeveloperProfile(BaseModel):
       """Perfil de developer en la store."""
       developer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
       name: str
       email: str
       trust_level: TrustLevel = TrustLevel.NEW
       packages_published: int = Field(default=0, ge=0)
       avg_rating: float = Field(default=0.0, ge=0.0, le=5.0)
       joined_at: str = Field(default_factory=lambda: datetime.now().isoformat())


   class PackageManifest(BaseModel):
       """Manifiesto de un paquete .ypkg."""
       name: str = Field(min_length=2, max_length=64)
       version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
       description: str = Field(max_length=500)
       author: str
       permissions: list[PackagePermission] = []
       min_yeyo_version: str = Field(default="1.0.0")
       category: str = Field(default="general")
       tags: list[str] = Field(default_factory=list)
       homepage: Optional[str] = None
       license: str = Field(default="MIT")


   class Package(BaseModel):
       """Paquete publicado en la store."""
       package_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
       manifest: PackageManifest
       developer_id: str
       status: PackageStatus = PackageStatus.SUBMITTED
       security_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
       download_count: int = Field(default=0, ge=0)
       avg_rating: float = Field(default=0.0, ge=0.0, le=5.0)
       total_reviews: int = Field(default=0, ge=0)
       published_at: Optional[str] = None
       submitted_at: str = Field(default_factory=lambda: datetime.now().isoformat())
       file_size_bytes: int = Field(default=0, ge=0)
       file_hash: str = ""


   class PackageReview(BaseModel):
       """Review de un paquete."""
       review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
       package_id: str
       user_id: str
       rating: int = Field(ge=1, le=5)
       comment: str = Field(max_length=1000)
       created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


   class PackageSubmission(BaseModel):
       """Datos para submit de un paquete."""
       manifest: PackageManifest
       developer_id: str


   class SearchResult(BaseModel):
       """Resultado de búsqueda en la store."""
       packages: list[Package]
       total: int
       page: int
       per_page: int


   class StoreServer:
       """Backend del YEYO Store."""

       SECURITY_AUTO_APPROVE_THRESHOLD = 90.0

       def __init__(self, data_dir: str = "data/store"):
           self.data_dir = Path(data_dir)
           self.data_dir.mkdir(parents=True, exist_ok=True)
           self._packages: dict[str, Package] = {}
           self._developers: dict[str, DeveloperProfile] = {}
           self._reviews: dict[str, list[PackageReview]] = {}
           self.app = self._create_app()

       def _create_app(self) -> FastAPI:
           """Crea la aplicación FastAPI del Store."""
           app = FastAPI(
               title="YEYO Store API",
               description="Marketplace de paquetes para YeyoOS",
               version="1.0.0",
           )

           @app.get("/api/store/packages", response_model=SearchResult)
           async def list_packages(
               page: int = Query(default=1, ge=1),
               per_page: int = Query(default=20, ge=1, le=100),
               category: Optional[str] = None,
               search: Optional[str] = None,
           ):
               packages = list(self._packages.values())
               packages = [p for p in packages if p.status == PackageStatus.PUBLISHED]

               if category:
                   packages = [p for p in packages
                               if p.manifest.category == category]
               if search:
                   search_lower = search.lower()
                   packages = [
                       p for p in packages
                       if search_lower in p.manifest.name.lower()
                       or search_lower in p.manifest.description.lower()
                       or any(search_lower in t.lower() for t in p.manifest.tags)
                   ]

               total = len(packages)
               start = (page - 1) * per_page
               end = start + per_page
               return SearchResult(
                   packages=packages[start:end],
                   total=total, page=page, per_page=per_page,
               )

           @app.get("/api/store/packages/{package_id}", response_model=Package)
           async def get_package(package_id: str):
               if package_id not in self._packages:
                   raise HTTPException(status_code=404, detail="Paquete no encontrado")
               return self._packages[package_id]

           @app.post("/api/store/packages/submit", response_model=Package)
           async def submit_package(submission: PackageSubmission):
               developer = self._developers.get(submission.developer_id)
               if not developer:
                   raise HTTPException(status_code=404, detail="Developer no encontrado")

               package = Package(
                   manifest=submission.manifest,
                   developer_id=submission.developer_id,
               )

               # Determinar pipeline según trust level
               if developer.trust_level == TrustLevel.VERIFIED:
                   package.status = PackageStatus.SCANNING
               elif developer.trust_level == TrustLevel.TRUSTED:
                   package.status = PackageStatus.SCANNING
               else:
                   package.status = PackageStatus.SCANNING

               self._packages[package.package_id] = package
               logger.info(f"Paquete submitted: {package.manifest.name} "
                           f"v{package.manifest.version} por {developer.name} "
                           f"(trust: {developer.trust_level})")
               return package

           @app.post("/api/store/packages/{package_id}/review", response_model=PackageReview)
           async def add_review(package_id: str, review: PackageReview):
               if package_id not in self._packages:
                   raise HTTPException(status_code=404, detail="Paquete no encontrado")

               review.package_id = package_id
               if package_id not in self._reviews:
                   self._reviews[package_id] = []
               self._reviews[package_id].append(review)

               # Actualizar avg rating
               reviews = self._reviews[package_id]
               avg = sum(r.rating for r in reviews) / len(reviews)
               self._packages[package_id].avg_rating = round(avg, 2)
               self._packages[package_id].total_reviews = len(reviews)

               logger.info(f"Review agregada a {package_id}: {review.rating}/5")
               return review

           @app.get("/api/store/packages/{package_id}/reviews",
                     response_model=list[PackageReview])
           async def get_reviews(package_id: str):
               if package_id not in self._packages:
                   raise HTTPException(status_code=404, detail="Paquete no encontrado")
               return self._reviews.get(package_id, [])

           @app.post("/api/store/developers", response_model=DeveloperProfile)
           async def register_developer(profile: DeveloperProfile):
               self._developers[profile.developer_id] = profile
               logger.info(f"Developer registrado: {profile.name} ({profile.trust_level})")
               return profile

           @app.get("/api/store/health")
           async def health():
               return {
                   "status": "ok",
                   "total_packages": len(self._packages),
                   "published_packages": sum(
                       1 for p in self._packages.values()
                       if p.status == PackageStatus.PUBLISHED
                   ),
                   "total_developers": len(self._developers),
               }

           return app

       def register_developer(self, profile: DeveloperProfile) -> DeveloperProfile:
           """Registra un developer (uso interno)."""
           self._developers[profile.developer_id] = profile
           return profile

       async def process_security_result(
           self, package_id: str, security_score: float
       ) -> Package:
           """Procesa resultado del security scan y avanza el pipeline."""
           if package_id not in self._packages:
               raise ValueError(f"Paquete no encontrado: {package_id}")

           package = self._packages[package_id]
           package.security_score = security_score
           developer = self._developers.get(package.developer_id)

           if security_score >= self.SECURITY_AUTO_APPROVE_THRESHOLD:
               if developer and developer.trust_level == TrustLevel.VERIFIED:
                   package.status = PackageStatus.PUBLISHED
                   package.published_at = datetime.now().isoformat()
                   logger.info(f"Paquete auto-aprobado (verified): {package.manifest.name}")
               elif developer and developer.trust_level == TrustLevel.TRUSTED:
                   package.status = PackageStatus.APPROVED
                   logger.info(f"Paquete fast-approved (trusted): {package.manifest.name}")
               else:
                   package.status = PackageStatus.REVIEW
                   logger.info(f"Paquete en review manual (new): {package.manifest.name}")
           else:
               package.status = PackageStatus.REVIEW
               logger.info(f"Paquete en review (score bajo: {security_score}): "
                           f"{package.manifest.name}")

           return package

       def get_package(self, package_id: str) -> Optional[Package]:
           return self._packages.get(package_id)

       def search_packages(self, query: str) -> list[Package]:
           """Búsqueda simple de paquetes publicados."""
           query_lower = query.lower()
           return [
               p for p in self._packages.values()
               if p.status == PackageStatus.PUBLISHED
               and (query_lower in p.manifest.name.lower()
                    or query_lower in p.manifest.description.lower())
           ]

4. Crear archivo tests/unit/store/__init__.py:

   Ruta: ~/yeyo-os/tests/unit/store/__init__.py
   Contenido: (archivo vacío)

5. Crear archivo tests/unit/store/test_store_server.py:

   Ruta: ~/yeyo-os/tests/unit/store/test_store_server.py
   Contenido:

   """Tests para YEYO Store Server — Micro-fase 7.3"""

   import pytest
   from fastapi.testclient import TestClient
   from src.store.server import (
       StoreServer, Package, PackageManifest, PackageSubmission,
       DeveloperProfile, TrustLevel, PackageStatus, PackageReview,
   )


   class TestStoreServer:
       """Tests para StoreServer."""

       def setup_method(self):
           import tempfile
           self.tmp_dir = tempfile.mkdtemp()
           self.server = StoreServer(data_dir=self.tmp_dir)
           self.client = TestClient(self.server.app)
           # Registrar developer de prueba
           self.dev = DeveloperProfile(
               name="Test Dev", email="dev@test.com",
               trust_level=TrustLevel.VERIFIED,
           )
           self.server.register_developer(self.dev)

       def test_health_endpoint(self):
           resp = self.client.get("/api/store/health")
           assert resp.status_code == 200
           data = resp.json()
           assert data["status"] == "ok"

       def test_submit_package(self):
           submission = {
               "manifest": {
                   "name": "test-pkg",
                   "version": "1.0.0",
                   "description": "Un paquete de prueba",
                   "author": "Test Dev",
                   "permissions": [],
               },
               "developer_id": self.dev.developer_id,
           }
           resp = self.client.post("/api/store/packages/submit", json=submission)
           assert resp.status_code == 200
           data = resp.json()
           assert data["manifest"]["name"] == "test-pkg"
           assert data["status"] == "scanning"

       def test_submit_package_unknown_developer(self):
           submission = {
               "manifest": {
                   "name": "test", "version": "1.0.0",
                   "description": "test", "author": "unknown",
               },
               "developer_id": "nonexistent-id",
           }
           resp = self.client.post("/api/store/packages/submit", json=submission)
           assert resp.status_code == 404

       def test_search_packages(self):
           # Agregar paquete publicado
           pkg = Package(
               manifest=PackageManifest(
                   name="neural-tools", version="1.0.0",
                   description="Herramientas neuronales", author="Test",
               ),
               developer_id=self.dev.developer_id,
               status=PackageStatus.PUBLISHED,
           )
           self.server._packages[pkg.package_id] = pkg

           resp = self.client.get("/api/store/packages?search=neural")
           data = resp.json()
           assert data["total"] == 1
           assert data["packages"][0]["manifest"]["name"] == "neural-tools"

       def test_add_review(self):
           pkg = Package(
               manifest=PackageManifest(
                   name="test-pkg", version="1.0.0",
                   description="test", author="Test",
               ),
               developer_id=self.dev.developer_id,
               status=PackageStatus.PUBLISHED,
           )
           self.server._packages[pkg.package_id] = pkg

           review = {
               "package_id": pkg.package_id,
               "user_id": "user-1",
               "rating": 4,
               "comment": "Muy buen paquete",
           }
           resp = self.client.post(
               f"/api/store/packages/{pkg.package_id}/review", json=review,
           )
           assert resp.status_code == 200
           assert self.server._packages[pkg.package_id].avg_rating == 4.0
           assert self.server._packages[pkg.package_id].total_reviews == 1

       def test_get_reviews(self):
           pkg = Package(
               manifest=PackageManifest(
                   name="test", version="1.0.0",
                   description="test", author="Test",
               ),
               developer_id=self.dev.developer_id,
               status=PackageStatus.PUBLISHED,
           )
           self.server._packages[pkg.package_id] = pkg
           resp = self.client.get(f"/api/store/packages/{pkg.package_id}/reviews")
           assert resp.status_code == 200
           assert resp.json() == []

       @pytest.mark.asyncio
       async def test_security_auto_approve_verified(self):
           pkg = Package(
               manifest=PackageManifest(
                   name="safe-pkg", version="1.0.0",
                   description="Safe package", author="Test",
               ),
               developer_id=self.dev.developer_id,
           )
           self.server._packages[pkg.package_id] = pkg
           result = await self.server.process_security_result(pkg.package_id, 95.0)
           assert result.status == PackageStatus.PUBLISHED

       @pytest.mark.asyncio
       async def test_security_low_score_goes_to_review(self):
           dev = DeveloperProfile(
               name="New Dev", email="new@test.com",
               trust_level=TrustLevel.NEW,
           )
           self.server.register_developer(dev)
           pkg = Package(
               manifest=PackageManifest(
                   name="risky", version="1.0.0",
                   description="test", author="New Dev",
               ),
               developer_id=dev.developer_id,
           )
           self.server._packages[pkg.package_id] = pkg
           result = await self.server.process_security_result(pkg.package_id, 70.0)
           assert result.status == PackageStatus.REVIEW

       def test_trust_levels_exist(self):
           assert TrustLevel.VERIFIED == "verified"
           assert TrustLevel.TRUSTED == "trusted"
           assert TrustLevel.NEW == "new"

       def test_search_only_published(self):
           pkg = Package(
               manifest=PackageManifest(
                   name="hidden", version="1.0.0",
                   description="test", author="Test",
               ),
               developer_id=self.dev.developer_id,
               status=PackageStatus.SCANNING,
           )
           self.server._packages[pkg.package_id] = pkg
           results = self.server.search_packages("hidden")
           assert len(results) == 0

6. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/store/test_store_server.py -v

VERIFICAR:
- [ ] Archivo src/store/server.py existe con StoreServer, Package, TrustLevel
- [ ] REST API con FastAPI: list, get, submit, review endpoints
- [ ] Trust levels: Verified (auto-approve), Trusted (fast review), New (full review)
- [ ] Security score threshold 90+ para auto-approve
- [ ] Rating system 1-5 estrellas + reviews
- [ ] Search funciona por nombre, descripción, tags
- [ ] Solo paquetes PUBLISHED aparecen en búsqueda
- [ ] TODOS los tests pasan

SI FALLA:
- FastAPI no instalado: pip install fastapi httpx
- pytest-asyncio: pip install pytest-asyncio

NO HACER:
- No implementar almacenamiento persistente (por ahora in-memory)
- No implementar upload real de archivos aún

GATE: Store Server con REST API, trust levels, security pipeline, ratings, búsqueda, todos los tests pasan.
```
