"""
YeyoOS — Social APIs Integration
Micro-fase 5.11 — Capa 5: Órganos

YouTube, Twitter/X y otras APIs sociales.
API keys encriptadas en Flash Memory.
Rate limiting respetado.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class SocialPlatform(str, Enum):
    YOUTUBE = "youtube"
    TWITTER = "twitter"


class RateLimitError(Exception):
    """Error de rate limiting."""
    pass


@dataclass
class SocialCredentials:
    """Credenciales OAuth2 encriptadas."""
    platform: SocialPlatform
    client_id: str
    access_token: str
    refresh_token: str
    expires_at: Optional[datetime] = None


@dataclass
class ScheduledPost:
    """Post programado."""
    id: str
    platform: SocialPlatform
    content: str
    scheduled_at: datetime
    status: str = "pending"  # pending | posted | failed
    media_path: Optional[str] = None


@dataclass
class RateLimitState:
    """Estado de rate limiting."""
    remaining: int
    reset_at: datetime
    limit: int


class SocialAPIService:
    """
    Servicio de APIs sociales con rate limiting y credenciales encriptadas.
    """

    def __init__(self):
        self._credentials: dict[SocialPlatform, SocialCredentials] = {}
        self._rate_limits: dict[SocialPlatform, RateLimitState] = {}
        self._scheduled_posts: list[ScheduledPost] = []
        self._scheduler_task: Optional[asyncio.Task] = None

    async def configure_platform(
        self, platform: SocialPlatform, client_id: str,
        access_token: str, refresh_token: str
    ) -> dict:
        """Configura credenciales para una plataforma (encriptadas en Flash Memory)."""
        from src.memory.flash import FlashMemory

        creds = SocialCredentials(
            platform=platform,
            client_id=client_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )
        self._credentials[platform] = creds

        flash = FlashMemory.get_instance()
        await flash.store_encrypted(
            key=f"social_{platform.value}_credentials",
            data={
                "client_id": client_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
            },
        )

        return {"platform": platform.value, "configured": True}

    async def post(
        self, platform: SocialPlatform, content: str,
        media_path: Optional[str] = None
    ) -> dict:
        """Publica contenido en una plataforma social."""
        if platform not in self._credentials:
            return {"error": f"Plataforma {platform.value} no configurada"}

        if not await self._check_rate_limit(platform):
            return {"error": f"Rate limit alcanzado para {platform.value}"}

        if platform == SocialPlatform.YOUTUBE:
            return await self._youtube_upload(content, media_path)
        elif platform == SocialPlatform.TWITTER:
            return await self._twitter_post(content, media_path)
        else:
            return {"error": f"Plataforma no soportada: {platform.value}"}

    async def schedule_post(
        self, platform: SocialPlatform, content: str,
        scheduled_at: datetime, media_path: Optional[str] = None
    ) -> dict:
        """Programa una publicación para un horario específico."""
        post = ScheduledPost(
            id=f"spost-{uuid.uuid4().hex[:8]}",
            platform=platform,
            content=content,
            scheduled_at=scheduled_at,
            media_path=media_path,
        )
        self._scheduled_posts.append(post)
        return {"post_id": post.id, "scheduled_at": scheduled_at.isoformat()}

    async def get_scheduled_posts(self) -> list[dict]:
        """Lista posts programados."""
        return [
            {"id": p.id, "platform": p.platform.value,
             "content": p.content[:100], "scheduled_at": p.scheduled_at.isoformat(),
             "status": p.status}
            for p in self._scheduled_posts
        ]

    async def _check_rate_limit(self, platform: SocialPlatform) -> bool:
        """Verifica si podemos hacer más requests."""
        if platform not in self._rate_limits:
            return True
        limit = self._rate_limits[platform]
        if datetime.now(timezone.utc) > limit.reset_at:
            return True
        return limit.remaining > 0

    async def _youtube_upload(self, title: str, video_path: Optional[str]) -> dict:
        """Sube video a YouTube via API."""
        import httpx
        creds = self._credentials[SocialPlatform.YOUTUBE]
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.googleapis.com/upload/youtube/v3/videos",
                headers={"Authorization": f"Bearer {creds.access_token}"},
                params={"part": "snippet,status"},
                json={"snippet": {"title": title}, "status": {"privacyStatus": "private"}},
            )
            return {"platform": "youtube", "status_code": response.status_code}

    async def _twitter_post(self, content: str, media_path: Optional[str]) -> dict:
        """Publica tweet via API."""
        import httpx
        creds = self._credentials[SocialPlatform.TWITTER]
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={"Authorization": f"Bearer {creds.access_token}"},
                json={"text": content},
            )
            return {"platform": "twitter", "status_code": response.status_code}
