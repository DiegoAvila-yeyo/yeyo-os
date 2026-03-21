"""
YeyoOS — Ejecutor de migraciones
Ejecuta archivos SQL contra PostgreSQL.
Uso: python db/run_migration.py db/migrations/002_flash_memory.sql
"""

import sys
import os
import asyncio
import asyncpg


async def run_migration(sql_file: str):
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
    )

    conn = await asyncpg.connect(database_url)
    try:
        with open(sql_file, "r") as f:
            sql = f.read()
        await conn.execute(sql)
        print(f"✅ Migración ejecutada: {sql_file}")
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python db/run_migration.py <archivo.sql>")
        sys.exit(1)
    asyncio.run(run_migration(sys.argv[1]))
