"""
YeyoNet — InviteManager.
Genera y valida códigos de invitación YEYO-XXXX-XXXX-XXXX.
"""
from __future__ import annotations

import logging
import secrets
import string
import uuid
from datetime import datetime, timedelta

import asyncpg

from .models import Permission, YeyoNetInvitation

logger = logging.getLogger("yeyonet.invite")

# Caracteres para generar códigos (sin ambiguos: 0/O, 1/I/L)
_CODE_CHARS = string.ascii_uppercase.replace("O", "").replace("I", "").replace("L", "") + "23456789"


def generate_invite_code() -> str:
    """Genera código formato YEYO-XXXX-XXXX-XXXX."""
    blocks = []
    for _ in range(3):
        block = "".join(secrets.choice(_CODE_CHARS) for _ in range(4))
        blocks.append(block)
    return f"YEYO-{blocks[0]}-{blocks[1]}-{blocks[2]}"


class InviteManager:
    """Gestiona invitaciones para satélites."""

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def create_invitation(
        self,
        satellite_name: str,
        permissions: list[Permission] | None = None,
        visibility_level: int = 1,
        expires_in_days: int = 7,
    ) -> YeyoNetInvitation:
        """Crea una nueva invitación con código único."""
        if permissions is None:
            permissions = [Permission.CHAT]

        code = generate_invite_code()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        perms_json = [p.value if isinstance(p, Permission) else p for p in permissions]

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO yeyonet_invitations
                    (code, satellite_name, permissions, visibility_level, expires_at)
                VALUES ($1, $2, $3::jsonb, $4, $5)
                RETURNING *
                """,
                code,
                satellite_name,
                str(perms_json).replace("'", '"'),
                visibility_level,
                expires_at,
            )

        invitation = _row_to_invitation(row)
        logger.info(f"[yeyonet] Invitación creada: {code} para '{satellite_name}' "
                     f"(permisos={perms_json}, expira en {expires_in_days}d)")
        return invitation

    async def validate_code(self, code: str) -> YeyoNetInvitation | None:
        """Valida un código. Retorna la invitación si es válida, None si no."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM yeyonet_invitations WHERE code = $1",
                code.upper().strip(),
            )

        if not row:
            logger.warning(f"[yeyonet] Código no encontrado: {code}")
            return None

        invitation = _row_to_invitation(row)

        if invitation.used:
            logger.warning(f"[yeyonet] Código ya usado: {code}")
            return None

        if invitation.is_expired:
            logger.warning(f"[yeyonet] Código expirado: {code}")
            return None

        return invitation

    async def mark_used(self, code: str, node_id: str) -> bool:
        """Marca una invitación como usada por un nodo."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE yeyonet_invitations
                SET used = TRUE, used_by_node_id = $1, used_at = NOW()
                WHERE code = $2 AND NOT used
                """,
                uuid.UUID(node_id),
                code.upper().strip(),
            )
        updated = result.split()[-1] != "0"
        if updated:
            logger.info(f"[yeyonet] Invitación {code} usada por nodo {node_id[:8]}...")
        return updated

    async def list_invitations(self, include_used: bool = False) -> list[YeyoNetInvitation]:
        """Lista invitaciones. Por defecto solo las activas."""
        async with self._pool.acquire() as conn:
            if include_used:
                rows = await conn.fetch(
                    "SELECT * FROM yeyonet_invitations ORDER BY created_at DESC"
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM yeyonet_invitations WHERE NOT used ORDER BY created_at DESC"
                )
        return [_row_to_invitation(r) for r in rows]

    async def delete_invitation(self, invitation_id: str) -> bool:
        """Elimina una invitación no usada."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM yeyonet_invitations WHERE id = $1 AND NOT used",
                uuid.UUID(invitation_id),
            )
        return result.split()[-1] != "0"


def _row_to_invitation(row: asyncpg.Record) -> YeyoNetInvitation:
    """Convierte row de DB a modelo."""
    import json
    perms = row["permissions"]
    if isinstance(perms, str):
        perms = json.loads(perms)

    return YeyoNetInvitation(
        id=str(row["id"]),
        code=row["code"],
        satellite_name=row["satellite_name"],
        permissions=perms,
        visibility_level=row["visibility_level"],
        used=row["used"],
        used_by_node_id=str(row["used_by_node_id"]) if row["used_by_node_id"] else None,
        used_at=row.get("used_at"),
        expires_at=row["expires_at"],
        created_at=row["created_at"],
    )
