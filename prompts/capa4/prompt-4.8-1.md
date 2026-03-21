## ═══════════════════════════════════════
## MICRO-FASE 4.8 — Package Database
## Tipo: VSCODE | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 4.8-1 [VSCODE] — Base de datos SQLite para paquetes instalados

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 4.8 de Capa 4 (Sistema Nervioso): crear la base de datos SQLite para tracking de paquetes instalados y sus permisos.

CONTEXTO:
- Micro-fases 4.0-4.7 completadas: paquetes, permisos, containers, pipelines
- SQLite para persistencia local de paquetes y permisos
- Dos tablas: packages (info de paquetes) y package_permissions (permisos concedidos)
- Reemplaza el registry.json del installer con persistencia real

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/pkg/database.py:

   Ruta: ~/yeyo-os/src/pkg/database.py
   Contenido:

   """
   YeyoOS — Package Database (SQLite)
   Micro-fase 4.8 — Capa 4: Sistema Nervioso

   Base de datos SQLite para tracking de paquetes instalados
   y permisos concedidos. Persistencia real para el sistema de paquetes.
   """

   import aiosqlite
   from datetime import datetime, timezone
   from typing import Optional
   from pathlib import Path


   class PackageDatabase:
       """Base de datos SQLite para paquetes de YeyoOS."""

       def __init__(self, db_path: str = "data/packages.db"):
           self.db_path = Path(db_path)
           self.db_path.parent.mkdir(parents=True, exist_ok=True)
           self._db: Optional[aiosqlite.Connection] = None

       async def connect(self) -> None:
           """Conecta a la base de datos y crea tablas si no existen."""
           self._db = await aiosqlite.connect(str(self.db_path))
           self._db.row_factory = aiosqlite.Row
           await self._create_tables()

       async def close(self) -> None:
           """Cierra la conexión a la base de datos."""
           if self._db:
               await self._db.close()
               self._db = None

       async def _create_tables(self) -> None:
           """Crea las tablas necesarias."""
           await self._db.execute("""
               CREATE TABLE IF NOT EXISTS packages (
                   name TEXT PRIMARY KEY,
                   version TEXT NOT NULL,
                   author TEXT NOT NULL,
                   description TEXT NOT NULL,
                   type TEXT NOT NULL,
                   privilege_level TEXT NOT NULL DEFAULT 'L2',
                   manifest_json TEXT,
                   installed_at TEXT NOT NULL,
                   updated_at TEXT,
                   status TEXT NOT NULL DEFAULT 'installed'
               )
           """)
           await self._db.execute("""
               CREATE TABLE IF NOT EXISTS package_permissions (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   package_name TEXT NOT NULL,
                   permission TEXT NOT NULL,
                   granted INTEGER NOT NULL DEFAULT 0,
                   granted_at TEXT,
                   granted_by TEXT DEFAULT 'user',
                   FOREIGN KEY (package_name) REFERENCES packages(name) ON DELETE CASCADE,
                   UNIQUE(package_name, permission)
               )
           """)
           await self._db.commit()

       async def register(self, manifest: dict) -> None:
           """Registra un paquete instalado en la base de datos."""
           now = datetime.now(timezone.utc).isoformat()
           import json

           try:
               await self._db.execute(
                   """
                   INSERT INTO packages (name, version, author, description, type,
                                        privilege_level, manifest_json, installed_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   """,
                   (
                       manifest["name"],
                       manifest["version"],
                       manifest["author"],
                       manifest["description"],
                       manifest["type"],
                       manifest.get("privilege_level", "L2"),
                       json.dumps(manifest),
                       now,
                       "installed",
                   ),
               )
               await self._db.commit()
           except aiosqlite.IntegrityError:
               raise ValueError(f"Paquete '{manifest['name']}' ya está registrado")

       async def unregister(self, name: str) -> None:
           """Elimina un paquete de la base de datos."""
           cursor = await self._db.execute(
               "SELECT name FROM packages WHERE name = ?", (name,)
           )
           row = await cursor.fetchone()
           if not row:
               raise ValueError(f"Paquete '{name}' no encontrado")

           await self._db.execute(
               "DELETE FROM package_permissions WHERE package_name = ?", (name,)
           )
           await self._db.execute("DELETE FROM packages WHERE name = ?", (name,))
           await self._db.commit()

       async def get(self, name: str) -> dict:
           """Obtiene información de un paquete."""
           cursor = await self._db.execute(
               "SELECT * FROM packages WHERE name = ?", (name,)
           )
           row = await cursor.fetchone()
           if not row:
               raise ValueError(f"Paquete '{name}' no encontrado")
           return dict(row)

       async def list_all(self) -> list[dict]:
           """Lista todos los paquetes instalados."""
           cursor = await self._db.execute(
               "SELECT * FROM packages ORDER BY installed_at DESC"
           )
           rows = await cursor.fetchall()
           return [dict(row) for row in rows]

       async def update_status(self, name: str, status: str) -> None:
           """Actualiza el estado de un paquete."""
           now = datetime.now(timezone.utc).isoformat()
           cursor = await self._db.execute(
               "UPDATE packages SET status = ?, updated_at = ? WHERE name = ?",
               (status, now, name),
           )
           if cursor.rowcount == 0:
               raise ValueError(f"Paquete '{name}' no encontrado")
           await self._db.commit()

       async def grant_permission(
           self, package_name: str, permission: str, granted_by: str = "user"
       ) -> None:
           """Concede un permiso a un paquete."""
           now = datetime.now(timezone.utc).isoformat()
           await self._db.execute(
               """
               INSERT INTO package_permissions (package_name, permission, granted, granted_at, granted_by)
               VALUES (?, ?, 1, ?, ?)
               ON CONFLICT(package_name, permission)
               DO UPDATE SET granted = 1, granted_at = ?, granted_by = ?
               """,
               (package_name, permission, now, granted_by, now, granted_by),
           )
           await self._db.commit()

       async def revoke_permission(self, package_name: str, permission: str) -> None:
           """Revoca un permiso de un paquete."""
           await self._db.execute(
               """
               UPDATE package_permissions SET granted = 0, granted_at = NULL
               WHERE package_name = ? AND permission = ?
               """,
               (package_name, permission),
           )
           await self._db.commit()

       async def get_permissions(self, package_name: str) -> list[dict]:
           """Obtiene los permisos de un paquete."""
           cursor = await self._db.execute(
               "SELECT * FROM package_permissions WHERE package_name = ? AND granted = 1",
               (package_name,),
           )
           rows = await cursor.fetchall()
           return [dict(row) for row in rows]

       async def has_permission(self, package_name: str, permission: str) -> bool:
           """Verifica si un paquete tiene un permiso concedido."""
           cursor = await self._db.execute(
               """
               SELECT granted FROM package_permissions
               WHERE package_name = ? AND permission = ? AND granted = 1
               """,
               (package_name, permission),
           )
           row = await cursor.fetchone()
           return row is not None

2. Actualizar archivo src/pkg/__init__.py:

   Ruta: ~/yeyo-os/src/pkg/__init__.py
   Contenido:
   from .manifest import ManifestParser, PackageManifest
   from .builder import PackageBuilder, BuildError
   from .installer import PackageInstaller, InstallError, SignatureError, PermissionDeniedError
   from .database import PackageDatabase

3. Crear archivo tests/unit/pkg/test_database.py:

   Ruta: ~/yeyo-os/tests/unit/pkg/test_database.py
   Contenido:

   """Tests para Package Database — Micro-fase 4.8"""

   import os
   import tempfile
   import pytest

   from src.pkg.database import PackageDatabase


   SAMPLE_MANIFEST = {
       "name": "test-pkg",
       "version": "1.0.0",
       "author": "TestAuthor",
       "description": "Test package",
       "type": "node",
       "privilege_level": "L2",
   }


   @pytest.fixture
   async def db():
       """Crea una base de datos temporal para tests."""
       with tempfile.TemporaryDirectory() as tmpdir:
           db_path = os.path.join(tmpdir, "test_packages.db")
           database = PackageDatabase(db_path=db_path)
           await database.connect()
           yield database
           await database.close()


   class TestPackageDatabase:
       """Tests para PackageDatabase."""

       @pytest.mark.asyncio
       async def test_register_package(self, db):
           await db.register(SAMPLE_MANIFEST)
           pkg = await db.get("test-pkg")
           assert pkg["name"] == "test-pkg"
           assert pkg["version"] == "1.0.0"
           assert pkg["status"] == "installed"

       @pytest.mark.asyncio
       async def test_register_duplicate_rejected(self, db):
           await db.register(SAMPLE_MANIFEST)
           with pytest.raises(ValueError, match="ya está registrado"):
               await db.register(SAMPLE_MANIFEST)

       @pytest.mark.asyncio
       async def test_unregister_removes_package(self, db):
           await db.register(SAMPLE_MANIFEST)
           await db.unregister("test-pkg")
           with pytest.raises(ValueError, match="no encontrado"):
               await db.get("test-pkg")

       @pytest.mark.asyncio
       async def test_unregister_nonexistent_raises(self, db):
           with pytest.raises(ValueError, match="no encontrado"):
               await db.unregister("nonexistent")

       @pytest.mark.asyncio
       async def test_list_all_returns_packages(self, db):
           await db.register(SAMPLE_MANIFEST)
           await db.register({**SAMPLE_MANIFEST, "name": "pkg-2"})
           packages = await db.list_all()
           assert len(packages) == 2

       @pytest.mark.asyncio
       async def test_list_all_empty(self, db):
           packages = await db.list_all()
           assert packages == []

       @pytest.mark.asyncio
       async def test_update_status(self, db):
           await db.register(SAMPLE_MANIFEST)
           await db.update_status("test-pkg", "updating")
           pkg = await db.get("test-pkg")
           assert pkg["status"] == "updating"

       @pytest.mark.asyncio
       async def test_update_status_nonexistent_raises(self, db):
           with pytest.raises(ValueError, match="no encontrado"):
               await db.update_status("nonexistent", "active")

       @pytest.mark.asyncio
       async def test_get_nonexistent_raises(self, db):
           with pytest.raises(ValueError, match="no encontrado"):
               await db.get("nonexistent")


   class TestPackagePermissionsDB:
       """Tests para permisos en la base de datos."""

       @pytest.mark.asyncio
       async def test_grant_permission(self, db):
           await db.register(SAMPLE_MANIFEST)
           await db.grant_permission("test-pkg", "memory.read")
           assert await db.has_permission("test-pkg", "memory.read") is True

       @pytest.mark.asyncio
       async def test_has_permission_false_by_default(self, db):
           await db.register(SAMPLE_MANIFEST)
           assert await db.has_permission("test-pkg", "memory.read") is False

       @pytest.mark.asyncio
       async def test_revoke_permission(self, db):
           await db.register(SAMPLE_MANIFEST)
           await db.grant_permission("test-pkg", "memory.read")
           await db.revoke_permission("test-pkg", "memory.read")
           assert await db.has_permission("test-pkg", "memory.read") is False

       @pytest.mark.asyncio
       async def test_get_permissions(self, db):
           await db.register(SAMPLE_MANIFEST)
           await db.grant_permission("test-pkg", "memory.read")
           await db.grant_permission("test-pkg", "clipboard")
           perms = await db.get_permissions("test-pkg")
           assert len(perms) == 2

       @pytest.mark.asyncio
       async def test_unregister_cascades_permissions(self, db):
           await db.register(SAMPLE_MANIFEST)
           await db.grant_permission("test-pkg", "memory.read")
           await db.unregister("test-pkg")
           assert await db.has_permission("test-pkg", "memory.read") is False

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   pip install aiosqlite
   python -m pytest tests/unit/pkg/test_database.py -v

VERIFICAR:
- [ ] Archivo src/pkg/database.py existe con PackageDatabase
- [ ] register funciona y almacena manifest
- [ ] Duplicado rechazado con ValueError
- [ ] unregister remueve paquete y permisos asociados (CASCADE)
- [ ] list_all retorna todos los paquetes
- [ ] update_status modifica correctamente
- [ ] grant_permission / revoke_permission / has_permission funcionan
- [ ] get_permissions retorna solo permisos activos
- [ ] TODOS los tests pasan

SI FALLA:
- aiosqlite no instalado: pip install aiosqlite
- Fixture async: usar @pytest.fixture con async def y pytest-asyncio
- Row factory: aiosqlite.Row para acceso por nombre de columna

NO HACER:
- No migrar el installer para usar esta DB aún (integración posterior)
- No agregar tablas adicionales
- No usar PostgreSQL (SQLite es suficiente para esto)

GATE: PackageDatabase persiste paquetes y permisos en SQLite, register/unregister/list/permissions funcionan, todos los tests pasan.
```
