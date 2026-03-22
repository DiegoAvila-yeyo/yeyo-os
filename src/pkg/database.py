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
