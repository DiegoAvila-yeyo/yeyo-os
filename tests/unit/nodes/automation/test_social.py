"""Tests para Social APIs — Micro-fase 5.11"""

import pytest
import sys
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
        mock_flash_class = MagicMock()
        mock_flash_class.get_instance = MagicMock(return_value=mock_flash)

        mock_module = MagicMock()
        mock_module.FlashMemory = mock_flash_class

        with patch.dict("sys.modules", {"src.memory.flash": mock_module}):
            result = await service.configure_platform(
                SocialPlatform.TWITTER, "client123", "token456", "refresh789"
            )
            assert result["configured"] is True
            assert SocialPlatform.TWITTER in service._credentials

    @pytest.mark.asyncio
    async def test_configure_youtube(self):
        service = SocialAPIService()
        mock_flash = MagicMock()
        mock_flash.store_encrypted = AsyncMock()
        mock_flash_class = MagicMock()
        mock_flash_class.get_instance = MagicMock(return_value=mock_flash)

        mock_module = MagicMock()
        mock_module.FlashMemory = mock_flash_class

        with patch.dict("sys.modules", {"src.memory.flash": mock_module}):
            result = await service.configure_platform(
                SocialPlatform.YOUTUBE, "yt_client", "yt_token", "yt_refresh"
            )
            assert result["platform"] == "youtube"
            assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_post_unconfigured_returns_error(self):
        service = SocialAPIService()
        result = await service.post(SocialPlatform.YOUTUBE, "Hello")
        assert "error" in result
        assert "no configurada" in result["error"]


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
    async def test_schedule_multiple_posts(self):
        service = SocialAPIService()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        await service.schedule_post(SocialPlatform.TWITTER, "Tweet 1", future)
        await service.schedule_post(SocialPlatform.TWITTER, "Tweet 2", future)
        assert len(service._scheduled_posts) == 2

    @pytest.mark.asyncio
    async def test_get_scheduled_posts(self):
        service = SocialAPIService()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        await service.schedule_post(SocialPlatform.TWITTER, "Tweet 1", future)
        await service.schedule_post(SocialPlatform.TWITTER, "Tweet 2", future)
        posts = await service.get_scheduled_posts()
        assert len(posts) == 2
        assert posts[0]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_scheduled_post_has_correct_platform(self):
        service = SocialAPIService()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        await service.schedule_post(SocialPlatform.YOUTUBE, "Video post", future)
        posts = await service.get_scheduled_posts()
        assert posts[0]["platform"] == "youtube"


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
            reset_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            limit=100,
        )
        assert await service._check_rate_limit(SocialPlatform.TWITTER) is True

    @pytest.mark.asyncio
    async def test_rate_limit_allows_unconfigured_platform(self):
        service = SocialAPIService()
        assert await service._check_rate_limit(SocialPlatform.YOUTUBE) is True

    @pytest.mark.asyncio
    async def test_post_blocked_by_rate_limit(self):
        service = SocialAPIService()
        service._credentials[SocialPlatform.TWITTER] = SocialCredentials(
            platform=SocialPlatform.TWITTER,
            client_id="c", access_token="t", refresh_token="r",
        )
        service._rate_limits[SocialPlatform.TWITTER] = RateLimitState(
            remaining=0,
            reset_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            limit=100,
        )
        result = await service.post(SocialPlatform.TWITTER, "Test")
        assert "error" in result
        assert "Rate limit" in result["error"]
