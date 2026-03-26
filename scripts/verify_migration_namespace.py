#!/usr/bin/env python3.11
"""
YeyoOS — Verificación de migración namespace
Fase 1.2: verifica que la columna namespace existe y los datos están correctos.
"""

import asyncio
import os
import sys

import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
)

ROLLBACK_SQL = "ALTER TABLE flash_memories DROP COLUMN namespace;"


async def verify():
    ok = True
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"❌ Conexión a PostgreSQL falló: {e}")
        print(f"\nRollback SQL:\n  {ROLLBACK_SQL}")
        sys.exit(1)

    # 1. Columna namespace existe
    col = await conn.fetchval("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='flash_memories' AND column_name='namespace'
    """)
    if col:
        print("✅ Columna namespace existe")
    else:
        print("❌ Columna namespace NO existe")
        ok = False

    # 2. Índice existe
    idx = await conn.fetchval("""
        SELECT indexname FROM pg_indexes
        WHERE tablename='flash_memories' AND indexname='idx_memories_namespace'
    """)
    if idx:
        print("✅ Índice idx_memories_namespace existe")
    else:
        print("❌ Índice idx_memories_namespace NO existe")
        ok = False

    # 3. Conteo por namespace
    rows = await conn.fetch("""
        SELECT namespace, COUNT(*) as count
        FROM flash_memories
        GROUP BY namespace
        ORDER BY namespace
    """)
    print("\n📊 Memorias por namespace:")
    for row in rows:
        print(f"   {row['namespace']}: {row['count']}")

    # 4. Detectar NULLs
    nulls = await conn.fetchval(
        "SELECT COUNT(*) FROM flash_memories WHERE namespace IS NULL"
    )
    if nulls == 0:
        print("\n✅ Sin memorias con namespace NULL")
    else:
        print(f"\n❌ {nulls} memorias con namespace NULL")
        ok = False

    # 5. Verificar datos migrados
    chat_count = await conn.fetchval(
        "SELECT COUNT(*) FROM flash_memories WHERE namespace='chat:usuario'"
    )
    docs_count = await conn.fetchval(
        "SELECT COUNT(*) FROM flash_memories WHERE namespace='sistema:docs'"
    )

    if chat_count > 0:
        print(f"✅ chat:usuario tiene {chat_count} memorias")
    else:
        print("⚠️  chat:usuario tiene 0 memorias (puede ser normal si no hay historial)")

    if docs_count > 0:
        print(f"✅ sistema:docs tiene {docs_count} memorias")
    else:
        print("⚠️  sistema:docs tiene 0 memorias")

    await conn.close()

    print("\n" + ("✅ Migración verificada correctamente" if ok else "❌ Migración tiene problemas"))

    if not ok:
        print(f"\nRollback SQL:\n  {ROLLBACK_SQL}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(verify())
