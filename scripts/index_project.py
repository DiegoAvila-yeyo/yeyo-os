#!/usr/bin/env python3.11
"""
YeyoOS — index_project.py (standalone)
Indexa el proyecto en Flash Memory sin cargar el stack completo de YeyoOS.
Corre este script desde la raíz del proyecto:

    python3.11 scripts/index_project.py           # indexar todo en batches
    python3.11 scripts/index_project.py --force   # re-indexar todo
    python3.11 scripts/index_project.py --stats   # ver qué está indexado
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
logger = logging.getLogger("indexer")

DATABASE_URL = "postgresql://eltitoyeyo@localhost:5432/yeyoos"
PROJECT_ROOT = Path(__file__).parent.parent

INDEX_TARGETS = [
    {"path": "README.md",     "ext": {".md"},  "source": "docs"},
    {"path": "docs",          "ext": {".md"},  "source": "docs"},
    {"path": "prompts",       "ext": {".md"},  "source": "prompts"},
    {"path": "db/migrations", "ext": {".sql"}, "source": "schema"},
    {"path": "src",           "ext": {".py"},  "source": "code"},
]

IGNORE_DIRS = {"__pycache__", ".git", "node_modules", ".next", "venv", ".venv"}
IGNORE_FILES = {"__init__.py"}
CHUNK_SIZE = 2000
CHUNK_OVERLAP = 200


def chunk_file(text: str, rel_path: str) -> list[dict]:
    if not text.strip():
        return []
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        if end < len(text):
            cp = text.rfind("\n\n", start, end)
            if cp <= start:
                cp = text.rfind("\n", start, end)
            if cp <= start:
                cp = end
            end = cp
        chunk = text[start:end].strip()
        if chunk:
            chunks.append({"text": chunk, "idx": idx, "file": rel_path})
            idx += 1
        start = end - CHUNK_OVERLAP
        if start >= len(text):
            break
    total = len(chunks)
    for c in chunks:
        c["total"] = total
    return chunks


def checksum(content: str, rel: str) -> str:
    return hashlib.sha256(f"{rel}:{content}".encode()).hexdigest()[:16]


async def index_one_file(
    conn: asyncpg.Connection,
    fp: Path,
    source: str,
    done_checksums: set[str],
    force: bool,
) -> int:
    """Indexa un archivo. Retorna número de chunks insertados."""
    try:
        content = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"  No se puede leer {fp.name}: {e}")
        return 0

    if not content.strip():
        return 0

    rel = str(fp.relative_to(PROJECT_ROOT))
    cs = checksum(content, rel)

    if not force and cs in done_checksums:
        return -1  # ya indexado

    chunks = chunk_file(content, rel)
    inserted = 0
    for c in chunks:
        header = f"[{rel} — chunk {c['idx']+1}/{c['total']}]\n"
        meta = json.dumps({
            "file": rel,
            "chunk_index": c["idx"],
            "total_chunks": c["total"],
            "file_checksum": cs,
        })
        try:
            await conn.execute(
                "INSERT INTO flash_memories (content, type, metadata, source) VALUES ($1,$2,$3,$4)",
                header + c["text"], "fact", meta, source,
            )
            inserted += 1
        except Exception as e:
            logger.warning(f"  Error insertando chunk de {fp.name}: {e}")
    return inserted


def collect_files(target: dict) -> list[Path]:
    path = PROJECT_ROOT / target["path"]
    exts = target["ext"]

    if path.is_file():
        return [path] if path.suffix in exts else []

    if not path.exists():
        return []

    return sorted([
        f for f in path.rglob("*")
        if f.is_file()
        and f.suffix in exts
        and f.name not in IGNORE_FILES
        and not any(d in f.parts for d in IGNORE_DIRS)
    ])


async def run(force: bool = False):
    logger.info("🔍 YeyoOS ProjectIndexer")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        rows = await conn.fetch(
            """SELECT metadata->>'file_checksum' AS cs FROM flash_memories
               WHERE source IN ('docs','code','prompts','schema')
               AND metadata->>'file_checksum' IS NOT NULL"""
        )
        done = {r["cs"] for r in rows if r["cs"]}
        logger.info(f"  Archivos ya indexados: {len(done)}")

        total_new = 0
        total_skip = 0

        for target in INDEX_TARGETS:
            files = collect_files(target)
            if not files:
                continue

            label = target["path"]
            source = target["source"]
            logger.info(f"\n📁 {label}/ ({len(files)} archivos)")

            for fp in files:
                result = await index_one_file(conn, fp, source, done, force)
                gc.collect()

                rel = fp.relative_to(PROJECT_ROOT)
                if result == -1:
                    total_skip += 1
                elif result > 0:
                    total_new += result
                    logger.info(f"  ✅ {rel} → {result} chunks")
                    done.add(checksum(fp.read_text(encoding="utf-8", errors="ignore"), str(rel)))

        logger.info(f"\n{'='*50}")
        logger.info(f"  Chunks nuevos:  {total_new}")
        logger.info(f"  Sin cambios:    {total_skip}")
        logger.info(f"{'='*50}")
        logger.info("✅ Listo — la IA ya conoce el proyecto")

    finally:
        await conn.close()


async def stats():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM flash_memories WHERE source IN ('docs','code','prompts','schema')"
        )
        by_source = await conn.fetch(
            """SELECT source, COUNT(*) as n FROM flash_memories
               WHERE source IN ('docs','code','prompts','schema')
               GROUP BY source ORDER BY n DESC"""
        )
        files = await conn.fetch(
            """SELECT metadata->>'file' AS f, COUNT(*) AS n FROM flash_memories
               WHERE source IN ('docs','code','prompts','schema')
               GROUP BY metadata->>'file'
               ORDER BY MAX(created_at) DESC LIMIT 20"""
        )
    finally:
        await conn.close()

    logger.info(f"\n📊 Índice del proyecto en Flash Memory")
    logger.info(f"  Total chunks: {total}")
    logger.info(f"\n  Por fuente:")
    for r in by_source:
        logger.info(f"    {r['source']:10} {r['n']} chunks")
    logger.info(f"\n  Últimos archivos indexados:")
    for r in files:
        if r["f"]:
            logger.info(f"    {r['f']} ({r['n']} chunks)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--stats" in args:
        asyncio.run(stats())
    elif "--file" in args:
        # Modo single-file: python3.11 scripts/index_project.py --file docs/09-stack.md
        idx = args.index("--file")
        target_file = args[idx + 1]
        force = "--force" in args

        async def single():
            conn = await asyncpg.connect(DATABASE_URL)
            rows = await conn.fetch(
                "SELECT metadata->>'file_checksum' AS cs FROM flash_memories "
                "WHERE source IN ('docs','code','prompts','schema') "
                "AND metadata->>'file_checksum' IS NOT NULL"
            )
            done = {r["cs"] for r in rows if r["cs"]}
            fp = PROJECT_ROOT / target_file
            source = "code" if ".py" in target_file else ("schema" if ".sql" in target_file else "docs" if "prompts" not in target_file else "prompts")
            result = await index_one_file(conn, fp, source, done, force)
            if result > 0:
                print(f"✅ {target_file} → {result} chunks")
            elif result == -1:
                print(f"⏭  {target_file} (sin cambios)")
            await conn.close()

        asyncio.run(single())
    else:
        asyncio.run(run(force="--force" in args))
