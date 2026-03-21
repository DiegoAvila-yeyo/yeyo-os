"""
Tests de integración para Flash Memory Schema — Micro-fase 2.0
Requieren PostgreSQL corriendo con pgvector.
Ejecutar con: pytest tests/integration/memory/test_flash_memory_schema.py -v
"""

import pytest
import asyncpg
import os
import uuid


pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
)


@pytest.fixture
async def db_conn():
    conn = await asyncpg.connect(DATABASE_URL)
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_flash_memories_table_exists(db_conn):
    """La tabla flash_memories debe existir."""
    result = await db_conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'flash_memories')"
    )
    assert result is True


@pytest.mark.asyncio
async def test_memory_associations_table_exists(db_conn):
    """La tabla memory_associations debe existir."""
    result = await db_conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memory_associations')"
    )
    assert result is True


@pytest.mark.asyncio
async def test_memory_audit_log_table_exists(db_conn):
    """La tabla memory_audit_log debe existir."""
    result = await db_conn.fetchval(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'memory_audit_log')"
    )
    assert result is True


@pytest.mark.asyncio
async def test_insert_memory_generates_checksum(db_conn):
    """INSERT debe auto-generar checksum SHA-256."""
    row = await db_conn.fetchrow(
        """
        INSERT INTO flash_memories (content, type, checksum)
        VALUES ($1, $2, 'placeholder')
        RETURNING id, checksum
        """,
        "Test memory content",
        "fact"
    )
    assert row["checksum"] is not None
    assert len(row["checksum"]) == 64  # SHA-256 hex = 64 chars
    assert row["checksum"] != "placeholder"  # trigger overwrites
    # Mover a COLD en vez de borrar (no podemos borrar)
    await db_conn.execute(
        "UPDATE flash_memories SET tier = 'COLD' WHERE id = $1",
        row["id"]
    )


@pytest.mark.asyncio
async def test_delete_memory_raises_exception(db_conn):
    """DELETE debe ser IMPOSIBLE — trigger lo previene."""
    row = await db_conn.fetchrow(
        """
        INSERT INTO flash_memories (content, type, checksum)
        VALUES ($1, $2, 'placeholder')
        RETURNING id
        """,
        "Memory that must never be deleted",
        "fact"
    )
    with pytest.raises(asyncpg.RaiseError, match="FORBIDDEN"):
        await db_conn.execute(
            "DELETE FROM flash_memories WHERE id = $1",
            row["id"]
        )


@pytest.mark.asyncio
async def test_invalid_type_rejected(db_conn):
    """Solo los tipos permitidos son aceptados."""
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            """
            INSERT INTO flash_memories (content, type, checksum)
            VALUES ($1, $2, 'placeholder')
            """,
            "Invalid type test",
            "invalid_type"
        )


@pytest.mark.asyncio
async def test_invalid_tier_rejected(db_conn):
    """Solo los tiers HOT/WARM/COLD son aceptados."""
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            """
            INSERT INTO flash_memories (content, type, tier, checksum)
            VALUES ($1, $2, $3, 'placeholder')
            """,
            "Invalid tier test",
            "fact",
            "NONE"
        )


@pytest.mark.asyncio
async def test_default_tier_is_warm(db_conn):
    """El tier por defecto debe ser WARM."""
    row = await db_conn.fetchrow(
        """
        INSERT INTO flash_memories (content, type, checksum)
        VALUES ($1, $2, 'placeholder')
        RETURNING tier
        """,
        "Default tier test",
        "conversation"
    )
    assert row["tier"] == "WARM"


@pytest.mark.asyncio
async def test_pgvector_index_exists(db_conn):
    """El índice vectorial para embeddings debe existir."""
    result = await db_conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = 'idx_memories_embedding'
        )
        """
    )
    assert result is True


@pytest.mark.asyncio
async def test_associations_self_reference_blocked(db_conn):
    """No se pueden crear asociaciones consigo mismo."""
    row = await db_conn.fetchrow(
        """
        INSERT INTO flash_memories (content, type, checksum)
        VALUES ($1, $2, 'placeholder')
        RETURNING id
        """,
        "Self-reference test",
        "fact"
    )
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            """
            INSERT INTO memory_associations (source_id, target_id, relation_type)
            VALUES ($1, $1, 'self')
            """,
            row["id"]
        )


@pytest.mark.asyncio
async def test_audit_log_insert(db_conn):
    """Se pueden insertar registros en audit_log."""
    test_id = uuid.uuid4()
    await db_conn.execute(
        """
        INSERT INTO memory_audit_log (memory_id, action, details)
        VALUES ($1, $2, $3)
        """,
        test_id,
        "CREATE",
        '{"test": true}'
    )
    row = await db_conn.fetchrow(
        "SELECT * FROM memory_audit_log WHERE memory_id = $1",
        test_id
    )
    assert row is not None
    assert row["action"] == "CREATE"


@pytest.mark.asyncio
async def test_association_strength_range(db_conn):
    """La fuerza de asociación debe estar entre 0 y 1."""
    row1 = await db_conn.fetchrow(
        """
        INSERT INTO flash_memories (content, type, checksum)
        VALUES ($1, $2, 'placeholder') RETURNING id
        """,
        "Strength test 1", "fact"
    )
    row2 = await db_conn.fetchrow(
        """
        INSERT INTO flash_memories (content, type, checksum)
        VALUES ($1, $2, 'placeholder') RETURNING id
        """,
        "Strength test 2", "fact"
    )
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            """
            INSERT INTO memory_associations (source_id, target_id, relation_type, strength)
            VALUES ($1, $2, 'related', 1.5)
            """,
            row1["id"], row2["id"]
        )
