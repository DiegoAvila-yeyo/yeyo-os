"""YeyoOS — Yeyo-pruebas Vault API

- Clona e ingiere un repo a un namespace aislado (vault)
- Expone stats para verificar que no se mezcla con otras memorias

IMPORTANTE:
- Esto NO mezcla con FlashMemory global mientras uses un namespace dedicado.
- El chat de /api/v1/pruebas/chat usa SOLO ese namespace cuando use_vault=true.
"""

import asyncio
import logging
import os
import re
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.tools.pruebas_vault_ingest import ingest_repo_to_flash_memory

logger = logging.getLogger("yeyoos.api.pruebas_vault")

router = APIRouter(prefix="/api/v1/pruebas/vault", tags=["pruebas"])

_flash_memory = None
_embedding_service = None


def set_flash_memory(mem):
    global _flash_memory
    _flash_memory = mem


def set_embedding_service(emb):
    global _embedding_service
    _embedding_service = emb


class IngestRepoRequest(BaseModel):
    repo_url: str = Field(..., min_length=5)
    namespace: str = Field(default="pruebas:vault:yeyo-pruebas")


class IngestRepoResponse(BaseModel):
    namespace: str
    repo_dir: str
    files_indexed: int
    chunks_indexed: int
    files_failed: int = 0
    chunks_failed: int = 0
    chunks_skipped: int = 0


def _repo_slug(repo_url: str) -> str:
    # e.g. https://github.com/user/repo.git -> repo
    name = repo_url.rstrip('/').split('/')[-1]
    name = re.sub(r"\.git$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^a-zA-Z0-9._-]+", "-", name)
    return name.lower() or "repo"


@router.post("/ingest_repo", response_model=IngestRepoResponse)
async def ingest_repo(req: IngestRepoRequest) -> IngestRepoResponse:
    if _flash_memory is None:
        raise HTTPException(status_code=503, detail="FlashMemory no disponible (PostgreSQL apagado)")

    # Clonar fuera del repo de YeyoOS para no ensuciar git
    vault_root = Path(
        os.getenv(
            "PRUEBAS_VAULT_ROOT",
            str(Path.home() / ".yeyo" / "pruebas-vaults"),
        )
    )
    slug = _repo_slug(req.repo_url)
    repo_dir = vault_root / slug
    err_path = vault_root / "_ingest_last_error.txt"

    try:
        result = await ingest_repo_to_flash_memory(
            repo_url=req.repo_url,
            dest_dir=repo_dir,
            namespace=req.namespace,
            flash_memory=_flash_memory,
            embedding_service=_embedding_service,
        )

        return IngestRepoResponse(
            namespace=req.namespace,
            repo_dir=result.repo_dir,
            files_indexed=result.files_indexed,
            chunks_indexed=result.chunks_indexed,
            files_failed=getattr(result, "files_failed", 0),
            chunks_failed=getattr(result, "chunks_failed", 0),
            chunks_skipped=getattr(result, "chunks_skipped", 0),
        )

    except asyncio.CancelledError as e:
        logger.exception("Vault ingest cancelled")
        try:
            err_path.parent.mkdir(parents=True, exist_ok=True)
            err_path.write_text(traceback.format_exc(), encoding="utf-8", errors="ignore")
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"cancelled: {repr(e)}")

    except BaseException as e:
        logger.exception("Vault ingest failed")
        try:
            err_path.parent.mkdir(parents=True, exist_ok=True)
            err_path.write_text(traceback.format_exc(), encoding="utf-8", errors="ignore")
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=repr(e))


@router.get("/stats")
async def stats(namespace: str = "pruebas:vault:yeyo-pruebas") -> dict:
    if _flash_memory is None:
        raise HTTPException(status_code=503, detail="FlashMemory no disponible")

    # Query directo para contar chunks en el namespace
    try:
        async with _flash_memory.pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM flash_memories WHERE namespace = $1",
                namespace,
            )
            files = await conn.fetchval(
                "SELECT COUNT(DISTINCT metadata->>'repo_path') FROM flash_memories WHERE namespace = $1",
                namespace,
            )
        return {"namespace": namespace, "chunks": int(total or 0), "files": int(files or 0)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
