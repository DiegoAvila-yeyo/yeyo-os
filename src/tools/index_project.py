"""
YeyoOS — ProjectIndexer
Indexa el codebase completo en Flash Memory para que la IA
pueda responder preguntas sobre el proyecto con contexto real.

Uso:
    python -m src.tools.index_project              # indexar todo
    python -m src.tools.index_project --force      # re-indexar todo aunque ya esté
    python -m src.tools.index_project --stats      # ver estadísticas del índice
"""

import asyncio
import gc
import hashlib
import json
import logging
import sys
from pathlib import Path

import asyncpg

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger("yeyoos.indexer")

# Raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Qué indexar y con qué source
INDEX_TARGETS = [
    {"path": "README.md",     "extensions": {".md"},  "source": "docs",    "importance": 1.0},
    {"path": "docs",          "extensions": {".md"},  "source": "docs",    "importance": 0.9},
    {"path": "prompts",       "extensions": {".md"},  "source": "prompts", "importance": 0.85},
    {"path": "db/migrations", "extensions": {".sql"}, "source": "schema",  "importance": 0.8},
    {"path": "src",           "extensions": {".py"},  "source": "code",    "importance": 0.7},
]

IGNORE_DIRS = {"__pycache__", ".git", "node_modules", ".next", "venv", ".venv", "__pycache__"}
IGNORE_FILES = {"__init__.py"}

# ~500 tokens por chunk
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


def chunk_text(text: str, file_path: str) -> list[dict]:
    """Divide texto en chunks con solapamiento, cortando en líneas."""
    if not text.strip():
        return []

    chunks = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            cutpoint = text.rfind("\n\n", start, end)
            if cutpoint <= start:
                cutpoint = text.rfind("\n", start, end)
            if cutpoint <= start:
                cutpoint = end
            end = cutpoint

        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"content": chunk, "idx": idx, "file": file_path})
            idx += 1

        start = end - CHUNK_OVERLAP
        if start >= len(text):
            break

    total = len(chunks)
    for c in chunks:
        c["total"] = total
    return chunks


def file_checksum(content: str, rel_path: str) -> str:
    return hashlib.sha256(f"{rel_path}:{content}".encode()).hexdigest()[:16]


async def get_indexed_checksums(conn: asyncpg.Connection) -> set[str]:
    try:
        rows = await conn.fetch(
            """
            SELECT metadata->>'file_checksum' AS cs
            FROM flash_memories
            WHERE source IN ('docs', 'code', 'prompts', 'schema')
              AND metadata->>'file_checksum' IS NOT NULL
            """
        )
        return {row["cs"] for row in rows if row["cs"]}
    except Exception:
        return set()


async def index_file(
    conn: asyncpg.Connection,
    file_path: Path,
    source: str,
    indexed_checksums: set[str],
    force: bool = False,
) -> tuple[int, int]:
    """Retorna (chunks_nuevos, skipped)."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"  No se pudo leer {file_path.name}: {e}")
        return 0, 0

    if not content.strip():
        return 0, 0

    rel = str(file_path.relative_to(PROJECT_ROOT))
    cs = file_checksum(content, rel)

    if not force and cs in indexed_checksums:
        return 0, 1

    chunks = chunk_text(content, rel)
    if not chunks:
        return 0, 0

    new_count = 0
    for chunk in chunks:
        header = f"[{rel} — chunk {chunk['idx']+1}/{chunk['total']}]\n"
        full_content = header + chunk["content"]
        metadata = {
            "file": rel,
            "chunk_index": chunk["idx"],
            "total_chunks": chunk["total"],
            "file_checksum": cs,
            "indexed_by": "ProjectIndexer",
        }
        try:
            await conn.execute(
                """
                INSERT INTO flash_memories (content, type, metadata, source)
                VALUES ($1, $2, $3, $4)
                """,
                full_content,
                "fact",
                json.dumps(metadata),
                source,
            )
            new_count += 1
        except Exception as e:
            logger.warning(f"  Error guardando chunk: {e}")

    return new_count, 0


async def run_index(force: bool = False, batch: int = 0):
    """Indexa todo el proyecto en Flash Memory.
    batch=N: procesa solo N archivos nuevos y para (0 = sin límite).
    """
    from src.core.config import get_config
    config = get_config()

    logger.info("🔍 YeyoOS ProjectIndexer iniciando...")
    conn = await asyncpg.connect(config.database_url)

    total_new = 0
    total_skipped = 0
    total_files = 0
    files_processed = 0

    try:
        indexed_checksums = await get_indexed_checksums(conn)
        logger.info(f"  Checksums ya en BD: {len(indexed_checksums)}")
        if batch:
            logger.info(f"  Modo batch: máx {batch} archivos nuevos")

        for target in INDEX_TARGETS:
            if batch and files_processed >= batch:
                break

            path = PROJECT_ROOT / target["path"]
            exts = target["extensions"]
            source = target["source"]

            # Archivo individual (README.md)
            if path.is_file():
                if path.suffix in exts:
                    new, skipped = await index_file(conn, path, source, indexed_checksums, force)
                    total_new += new
                    total_skipped += skipped
                    total_files += 1
                    if new:
                        files_processed += 1
                    status = f"{new} chunks nuevos" if new else "sin cambios ⏭"
                    logger.info(f"  {path.name}: {status}")
                    gc.collect()
                continue

            if not path.exists():
                logger.warning(f"  ⚠️  No existe: {target['path']}")
                continue

            files = sorted([
                f for f in path.rglob("*")
                if f.is_file()
                and f.suffix in exts
                and f.name not in IGNORE_FILES
                and not any(d in f.parts for d in IGNORE_DIRS)
            ])

            logger.info(f"\n📁 {target['path']}/ ({len(files)} archivos)")
            for fp in files:
                if batch and files_processed >= batch:
                    logger.info(f"  ⏸  Batch completado ({batch} archivos). Corre de nuevo para continuar.")
                    break

                new, skipped = await index_file(conn, fp, source, indexed_checksums, force)
                total_new += new
                total_skipped += skipped
                total_files += 1
                if new:
                    files_processed += 1
                rel = fp.relative_to(PROJECT_ROOT)
                if new:
                    logger.info(f"    ✅ {rel} → {new} chunks")
                gc.collect()
    finally:
        await conn.close()
    logger.info(f"\n{'='*50}")
    logger.info(f"  Archivos procesados: {total_files}")
    logger.info(f"  Chunks nuevos:       {total_new}")
    logger.info(f"  Archivos sin cambios: {total_skipped}")
    logger.info(f"{'='*50}")
    logger.info("✅ Indexación completada — la IA ya puede responder sobre el proyecto")


async def run_stats():
    """Estadísticas del índice actual."""
    from src.core.config import get_config
    config = get_config()
    conn = await asyncpg.connect(config.database_url)

    try:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM flash_memories WHERE source IN ('docs','code','prompts','schema')"
        )
        by_source = await conn.fetch(
            """
            SELECT source, COUNT(*) as count
            FROM flash_memories
            WHERE source IN ('docs', 'code', 'prompts', 'schema')
            GROUP BY source ORDER BY count DESC
            """
        )
        top_files = await conn.fetch(
            """
            SELECT metadata->>'file' AS file, COUNT(*) AS chunks
            FROM flash_memories
            WHERE source IN ('docs', 'code', 'prompts', 'schema')
            GROUP BY metadata->>'file'
            ORDER BY MAX(created_at) DESC
            LIMIT 15
            """
        )
    finally:
        await conn.close()

    logger.info(f"\n📊 Flash Memory — Índice del proyecto")
    logger.info(f"  Total chunks indexados: {total}")
    logger.info(f"\n  Por fuente:")
    for row in by_source:
        logger.info(f"    {row['source']:10} → {row['count']} chunks")
    logger.info(f"\n  Archivos más recientes:")
    for row in top_files:
        if row["file"]:
            logger.info(f"    {row['file']} ({row['chunks']} chunks)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--stats" in args:
        asyncio.run(run_stats())
    else:
        force = "--force" in args
        batch = 0
        for arg in args:
            if arg.startswith("--batch="):
                batch = int(arg.split("=")[1])
        asyncio.run(run_index(force=force, batch=batch))
