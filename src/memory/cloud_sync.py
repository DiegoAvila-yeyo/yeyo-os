"""
Cloud Memory Sync — Sincronización automática via Supabase (cloud PostgreSQL).

Cada PC trabaja con DB local (rápido). Este servicio:
  1. Push: sube memorias nuevas locales → Supabase
  2. Pull: baja memorias nuevas de Supabase → DB local
  3. Dedup por checksum, conflictos por timestamp (newest wins)

Usa Supabase REST API directamente con httpx (sin supabase-py).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger("memory.cloud_sync")


class CloudSyncService:
    """
    Sincronización automática de memorias via Supabase (cloud PostgreSQL).

    Cada PC trabaja con DB local (rápido). Este servicio:
    1. Push: sube memorias nuevas locales → Supabase
    2. Pull: baja memorias nuevas de Supabase → DB local
    3. Dedup por checksum, conflictos por timestamp (newest wins)
    """

    def __init__(self, local_pool, supabase_url: str, supabase_key: str, node_id: str):
        self._pool = local_pool
        self._supabase_url = supabase_url.rstrip("/")
        self._supabase_key = supabase_key
        self._node_id = node_id
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._client: Optional[httpx.AsyncClient] = None

        # Stats
        self._pushed = 0
        self._pulled = 0
        self._errors = 0
        self._last_sync: Optional[datetime] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._supabase_url and self._supabase_key)

    # ─── Lifecycle ─────────────────────────────────────────

    async def start(self) -> None:
        """Start background sync loop."""
        if not self.is_configured:
            logger.warning("[cloud_sync] No configurado (SUPABASE_URL/KEY missing)")
            return
        self._client = httpx.AsyncClient(
            base_url=f"{self._supabase_url}/rest/v1",
            headers={
                "apikey": self._supabase_key,
                "Authorization": f"Bearer {self._supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            timeout=30.0,
        )
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info(f"[cloud_sync] ✅ Iniciado (node={self._node_id[:8]}...)")

    async def stop(self) -> None:
        """Stop background sync loop and close HTTP client."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
        logger.info(f"[cloud_sync] Detenido (pushed={self._pushed}, pulled={self._pulled})")

    async def _sync_loop(self) -> None:
        """Background loop: push then pull every 60 seconds."""
        while self._running:
            try:
                pushed = await self.push_new_memories()
                pulled = await self.pull_new_memories()
                self._last_sync = datetime.now(timezone.utc)
                if pushed or pulled:
                    logger.info(f"[cloud_sync] Sync: pushed={pushed}, pulled={pulled}")
            except Exception as e:
                self._errors += 1
                logger.error(f"[cloud_sync] Error: {e}")
            await asyncio.sleep(60)

    # ─── Push (local → cloud) ─────────────────────────────

    async def push_new_memories(self) -> int:
        """Push local memories that don't exist in cloud (by checksum)."""
        cloud_checksums = await self._get_cloud_checksums()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, content, type, tier, checksum, access_count,
                       metadata, source, namespace, importance, tags,
                       created_at, accessed_at, updated_at
                FROM flash_memories
                ORDER BY created_at DESC
                LIMIT 200
            """)

        to_push = [
            self._row_to_cloud_payload(r)
            for r in rows
            if r["checksum"] not in cloud_checksums
        ]

        if not to_push:
            return 0

        pushed = 0
        for i in range(0, len(to_push), 50):
            batch = to_push[i : i + 50]
            try:
                resp = await self._client.post(
                    "/cloud_memories",
                    content=json.dumps(batch, default=str),
                    headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
                )
                if resp.status_code in (200, 201):
                    pushed += len(batch)
                else:
                    logger.warning(f"[cloud_sync] Push error {resp.status_code}: {resp.text[:200]}")
                    self._errors += 1
            except Exception as e:
                logger.error(f"[cloud_sync] Push exception: {e}")
                self._errors += 1

        self._pushed += pushed
        return pushed

    # ─── Pull (cloud → local) ─────────────────────────────

    async def pull_new_memories(self) -> int:
        """Pull memories from cloud that don't exist locally."""
        async with self._pool.acquire() as conn:
            local_rows = await conn.fetch("SELECT checksum FROM flash_memories")
        local_checksums = {r["checksum"] for r in local_rows}

        try:
            resp = await self._client.get(
                "/cloud_memories",
                params={
                    "select": "id,content,type,tier,checksum,access_count,metadata,"
                              "source,namespace,importance,tags,created_at,"
                              "accessed_at,updated_at,origin_node_id",
                    "order": "synced_at.desc",
                    "limit": "200",
                },
            )
            if resp.status_code != 200:
                logger.warning(f"[cloud_sync] Pull error {resp.status_code}")
                return 0
            cloud_memories = resp.json()
        except Exception as e:
            logger.error(f"[cloud_sync] Pull exception: {e}")
            return 0

        new_memories = [m for m in cloud_memories if m["checksum"] not in local_checksums]
        if not new_memories:
            return 0

        pulled = 0
        async with self._pool.acquire() as conn:
            for mem in new_memories:
                try:
                    exists = await conn.fetchval(
                        "SELECT 1 FROM flash_memories WHERE checksum = $1",
                        mem["checksum"],
                    )
                    if exists:
                        continue

                    metadata = mem.get("metadata", {})
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    metadata["synced_from_cloud"] = True
                    metadata["origin_node_id"] = mem.get("origin_node_id", "unknown")

                    await conn.execute(
                        """
                        INSERT INTO flash_memories
                            (id, content, type, tier, checksum, access_count,
                             metadata, source, namespace, importance, tags,
                             created_at, accessed_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb,
                                $8, $9, $10, $11, $12, $13, $14)
                        ON CONFLICT (checksum) DO NOTHING
                        """,
                        mem["id"],
                        mem["content"],
                        mem["type"],
                        mem.get("tier", "WARM"),
                        mem["checksum"],
                        mem.get("access_count", 0),
                        json.dumps(metadata),
                        mem.get("source", "cloud"),
                        mem.get("namespace", "general"),
                        mem.get("importance", 0.5),
                        mem.get("tags", []),
                        mem.get("created_at"),
                        mem.get("accessed_at"),
                        mem.get("updated_at"),
                    )
                    pulled += 1
                except Exception as e:
                    logger.warning(f"[cloud_sync] Pull insert error: {e}")
                    self._errors += 1

        self._pulled += pulled
        return pulled

    # ─── Immediate push (pipeline hook) ───────────────────

    async def push_single(self, memory_data: dict) -> bool:
        """Push a single memory immediately (called from pipeline hook)."""
        if not self.is_configured or not self._client:
            return False
        try:
            payload = {
                "id": str(memory_data.get("id", "")),
                "content": memory_data["content"],
                "type": memory_data.get("type", "fact"),
                "tier": memory_data.get("tier", "WARM"),
                "checksum": memory_data["checksum"],
                "access_count": memory_data.get("access_count", 0),
                "metadata": json.dumps(memory_data.get("metadata", {}), default=str),
                "source": memory_data.get("source", "user"),
                "namespace": memory_data.get("namespace", "general"),
                "importance": memory_data.get("importance", 0.5),
                "tags": memory_data.get("tags", []),
                "origin_node_id": self._node_id,
                "created_at": str(memory_data.get("created_at", "")),
                "accessed_at": str(memory_data.get("accessed_at", "")),
                "updated_at": str(memory_data.get("updated_at", "")),
            }
            resp = await self._client.post(
                "/cloud_memories",
                content=json.dumps(payload, default=str),
                headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            )
            if resp.status_code in (200, 201):
                self._pushed += 1
                return True
            logger.warning(f"[cloud_sync] push_single error: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"[cloud_sync] push_single exception: {e}")
            self._errors += 1
            return False

    # ─── Manual trigger ───────────────────────────────────

    async def force_full_sync(self) -> dict:
        """Force a complete sync cycle (for manual trigger)."""
        pushed = await self.push_new_memories()
        pulled = await self.pull_new_memories()
        self._last_sync = datetime.now(timezone.utc)
        return {"pushed": pushed, "pulled": pulled}

    def get_stats(self) -> dict:
        """Return current sync statistics."""
        return {
            "configured": self.is_configured,
            "running": self._running,
            "total_pushed": self._pushed,
            "total_pulled": self._pulled,
            "errors": self._errors,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "node_id": self._node_id,
        }

    # ─── Internal helpers ─────────────────────────────────

    async def _get_cloud_checksums(self) -> set[str]:
        """Get all checksums from cloud (paginated)."""
        checksums: set[str] = set()
        offset = 0
        page_size = 1000
        while True:
            try:
                resp = await self._client.get(
                    "/cloud_memories",
                    params={
                        "select": "checksum",
                        "limit": str(page_size),
                        "offset": str(offset),
                    },
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                if not data:
                    break
                for row in data:
                    checksums.add(row["checksum"])
                if len(data) < page_size:
                    break
                offset += page_size
            except Exception:
                break
        return checksums

    def _row_to_cloud_payload(self, row) -> dict:
        """Convert an asyncpg Row to a JSON-safe dict for Supabase REST."""
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return {
            "id": str(row["id"]),
            "content": row["content"],
            "type": row["type"],
            "tier": row["tier"],
            "checksum": row["checksum"],
            "access_count": row["access_count"],
            "metadata": json.dumps(metadata, default=str),
            "source": row["source"],
            "namespace": row.get("namespace", "general"),
            "importance": row.get("importance", 0.5),
            "tags": list(row.get("tags", [])),
            "origin_node_id": self._node_id,
            "created_at": str(row["created_at"]),
            "accessed_at": str(row["accessed_at"]),
            "updated_at": str(row["updated_at"]),
        }
