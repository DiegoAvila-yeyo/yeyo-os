## ═══════════════════════════════════════
## MICRO-FASE 5.11 — Automation Node (Social APIs)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.11-1 [VSCODE] — Integración con APIs sociales (YouTube, Twitter)

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.11 de Capa 5 (Órganos): añadir integración con APIs sociales al Automation Node.

CONTEXTO:
- Micro-fase 5.10 completada: AutomationNode con pipeline visual
- YouTube: upload, analytics (OAuth2)
- Twitter/X: post, leer timeline (OAuth2)
- Scheduling: publicar en horario específico
- API keys almacenadas ENCRIPTADAS en Flash Memory (Capa 2)
- Rate limiting respetado para cada API
- Frontend: Next.js 14 + Tailwind + Zustand
- Backend: Python 3.11 + FastAPI

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/automation/social.py:

   Ruta: ~/yeyo-os/src/nodes/automation/social.py
   Contenido:

   """
   YeyoOS — Social APIs Integration
   Micro-fase 5.11 — Capa 5: Órganos

   YouTube, Twitter/X y otras APIs sociales.
   API keys encriptadas en Flash Memory.
   Rate limiting respetado.
   """

   import asyncio
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

           # Almacenar encriptado en Flash Memory
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

           # Verificar rate limiting
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
           import uuid
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
           # Placeholder para YouTube Data API v3
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

2. Actualizar src/nodes/automation/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/automation/__init__.py
   Contenido:
   from .service import AutomationNode
   from .social import SocialAPIService, SocialPlatform

3. Crear archivo tests/unit/nodes/automation/test_social.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/automation/test_social.py
   Contenido:

   """Tests para Social APIs — Micro-fase 5.11"""

   import pytest
   from datetime import datetime, timezone, timedelta
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.automation.social import (
       SocialAPIService, SocialPlatform, SocialCredentials,
       RateLimitState, ScheduledPost,
   )


   class TestSocialConfiguration:

       @pytest.mark.asyncio
       async def test_configure_platform(self):
           service = SocialAPIService()
           mock_flash = MagicMock()
           mock_flash.store_encrypted = AsyncMock()
           mock_flash.get_instance = MagicMock(return_value=mock_flash)

           with patch("src.nodes.automation.social.FlashMemory", mock_flash):
               result = await service.configure_platform(
                   SocialPlatform.TWITTER, "client123", "token456", "refresh789"
               )
               assert result["configured"] is True
               assert SocialPlatform.TWITTER in service._credentials

       @pytest.mark.asyncio
       async def test_post_unconfigured_returns_error(self):
           service = SocialAPIService()
           result = await service.post(SocialPlatform.YOUTUBE, "Hello")
           assert "error" in result


   class TestSocialScheduling:

       @pytest.mark.asyncio
       async def test_schedule_post(self):
           service = SocialAPIService()
           future = datetime.now(timezone.utc) + timedelta(hours=1)
           result = await service.schedule_post(
               SocialPlatform.TWITTER, "Scheduled tweet", future
           )
           assert "post_id" in result
           assert len(service._scheduled_posts) == 1

       @pytest.mark.asyncio
       async def test_get_scheduled_posts(self):
           service = SocialAPIService()
           future = datetime.now(timezone.utc) + timedelta(hours=1)
           await service.schedule_post(SocialPlatform.TWITTER, "Tweet 1", future)
           await service.schedule_post(SocialPlatform.TWITTER, "Tweet 2", future)
           posts = await service.get_scheduled_posts()
           assert len(posts) == 2


   class TestSocialRateLimiting:

       @pytest.mark.asyncio
       async def test_rate_limit_allows_when_remaining(self):
           service = SocialAPIService()
           service._rate_limits[SocialPlatform.TWITTER] = RateLimitState(
               remaining=10,
               reset_at=datetime.now(timezone.utc) + timedelta(minutes=15),
               limit=100,
           )
           assert await service._check_rate_limit(SocialPlatform.TWITTER) is True

       @pytest.mark.asyncio
       async def test_rate_limit_blocks_when_zero(self):
           service = SocialAPIService()
           service._rate_limits[SocialPlatform.TWITTER] = RateLimitState(
               remaining=0,
               reset_at=datetime.now(timezone.utc) + timedelta(minutes=15),
               limit=100,
           )
           assert await service._check_rate_limit(SocialPlatform.TWITTER) is False

       @pytest.mark.asyncio
       async def test_rate_limit_resets_after_expiry(self):
           service = SocialAPIService()
           service._rate_limits[SocialPlatform.TWITTER] = RateLimitState(
               remaining=0,
               reset_at=datetime.now(timezone.utc) - timedelta(minutes=1),  # Already expired
               limit=100,
           )
           assert await service._check_rate_limit(SocialPlatform.TWITTER) is True

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/automation/test_social.py -v

VERIFICAR:
- [ ] Configuración de plataformas con credenciales
- [ ] API keys almacenadas encriptadas en Flash Memory
- [ ] Post a YouTube y Twitter funciona (con mocks)
- [ ] Scheduling programa posts para horario futuro
- [ ] Rate limiting respetado: bloquea cuando remaining=0
- [ ] Rate limiting se resetea después del período
- [ ] Plataforma no configurada retorna error
- [ ] TODOS los tests pasan

SI FALLA:
- FlashMemory no existe: tests usan mock
- httpx: `pip install httpx`
- Import error: verificar __init__.py

NO HACER:
- No usar API keys reales en tests (solo mocks)
- No hacer llamadas reales a YouTube/Twitter
- No almacenar credenciales en texto plano

GATE: Social APIs configuradas, credenciales encriptadas, scheduling funciona, rate limiting respetado, todos los tests pasan.
```
