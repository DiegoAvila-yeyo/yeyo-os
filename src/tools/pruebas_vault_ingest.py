"""YeyoOS — Yeyo-pruebas Vault Ingest

Clona (si hace falta) y carga un repo a un namespace aislado dentro de flash_memories
para que Yeyo-pruebas haga RAG cerrado.

Se usa desde la API (routes/pruebas_vault.py) o como módulo.
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("yeyoos.pruebas.vault")

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "target"}

DEFAULT_EXTS = {".md", ".rs", ".toml", ".txt", ".lock", ".asm"}


def _chunk_text(text: str, chunk_size: int = 1800, overlap: int = 200) -> list[str]:
    text = text or ""
    if not text.strip():
        return []
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            cp = text.rfind("\n\n", start, end)
            if cp <= start:
                cp = text.rfind("\n", start, end)
            if cp <= start:
                cp = end
            end = cp
        chunk = text[start:end].strip()
        if chunk:
            out.append(chunk)
        start = max(0, end - overlap)
        if end >= len(text):
            break
    return out


def _checksum(rel_path: str, content: str) -> str:
    return hashlib.sha256(f"{rel_path}:{content}".encode("utf-8", errors="ignore")).hexdigest()[:16]


@dataclass
class IngestResult:
    repo_dir: str
    files_indexed: int
    chunks_indexed: int
    files_failed: int = 0
    chunks_failed: int = 0
    chunks_skipped: int = 0


def ensure_repo(repo_url: str, dest_dir: Path) -> None:
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    if dest_dir.exists() and (dest_dir / ".git").exists():
        return
    logger.info(f"[vault] cloning {repo_url} -> {dest_dir}")
    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(dest_dir)], check=True)


async def ingest_repo_to_flash_memory(
    *,
    repo_url: str,
    dest_dir: Path,
    namespace: str,
    flash_memory,
    embedding_service,
    exts: set[str] | None = None,
    max_files: int = 5000,
) -> IngestResult:
    """Index repo into flash_memories with embeddings.

    - Dedupe por metadata.checksum dentro del namespace+repo_url
    - Continúa si un archivo/chunk falla (no aborta toda la ingesta)
    """

    ensure_repo(repo_url, dest_dir)
    exts = exts or DEFAULT_EXTS

    existing_checksums: set[str] = set()
    try:
        async with flash_memory.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT metadata->>'checksum' AS cs
                FROM flash_memories
                WHERE namespace = $1
                  AND source = 'pruebas:vault'
                  AND metadata->>'repo_url' = $2
                  AND (metadata->>'checksum') IS NOT NULL
                """,
                namespace,
                repo_url,
            )
            existing_checksums = {r["cs"] for r in rows if r.get("cs")}
    except Exception:
        existing_checksums = set()

    files = []
    for fp in dest_dir.rglob("*"):
        if not fp.is_file():
            continue
        if fp.suffix.lower() not in exts:
            continue
        if any(part in IGNORE_DIRS for part in fp.parts):
            continue
        files.append(fp)
        if len(files) >= max_files:
            break

    chunks_indexed = 0
    files_indexed = 0
    files_failed = 0
    chunks_failed = 0
    chunks_skipped = 0

    for fp in files:
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            files_failed += 1
            logger.warning(f"[vault] read failed: {fp} ({e})")
            continue
        if not content.strip():
            continue

        rel = str(fp.relative_to(dest_dir))
        parts = _chunk_text(content.replace("\x00", ""))
        if not parts:
            continue

        total = len(parts)
        file_had_any = False

        for i, part in enumerate(parts):
            cs = _checksum(rel, part)
            if cs in existing_checksums:
                chunks_skipped += 1
                continue

            header = f"[{rel} — chunk {i+1}/{total}]\n"
            text = header + part

            emb = None
            try:
                emb = embedding_service.generate(part[:800]) if embedding_service else None
            except Exception as e:
                logger.warning(f"[vault] embedding failed: {rel} chunk={i} ({e})")
                emb = None

            try:
                await flash_memory.store(
                    content=text,
                    type="fact",
                    metadata={
                        "vault": namespace,
                        "repo_url": repo_url,
                        "repo_path": rel,
                        "chunk_index": i,
                        "total_chunks": total,
                        "checksum": cs,
                    },
                    embedding=emb,
                    source="pruebas:vault",
                    namespace=namespace,
                )
                chunks_indexed += 1
                existing_checksums.add(cs)
                file_had_any = True
            except Exception as e:
                chunks_failed += 1
                logger.warning(f"[vault] store failed: {rel} chunk={i} ({repr(e)})")
                continue

        if file_had_any:
            files_indexed += 1

    return IngestResult(
        repo_dir=str(dest_dir),
        files_indexed=files_indexed,
        chunks_indexed=chunks_indexed,
        files_failed=files_failed,
        chunks_failed=chunks_failed,
        chunks_skipped=chunks_skipped,
    )
