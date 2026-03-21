"""
Tests para FeedbackService — Micro-fase 2.14
Tests unitarios y de integración.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.chat.feedback import FeedbackService


class TestFeedbackValidation:
    """Tests de validación de input."""

    @pytest.mark.asyncio
    async def test_rating_must_be_1_to_5(self):
        """Solo ratings 1-5 son válidos."""
        service = FeedbackService(pool=MagicMock())
        with pytest.raises(ValueError, match="entre 1 y 5"):
            await service.rate_response(str(uuid.uuid4()), rating=0)

    @pytest.mark.asyncio
    async def test_rating_6_rejected(self):
        service = FeedbackService(pool=MagicMock())
        with pytest.raises(ValueError):
            await service.rate_response(str(uuid.uuid4()), rating=6)

    @pytest.mark.asyncio
    async def test_empty_correction_rejected(self):
        service = FeedbackService(pool=MagicMock())
        with pytest.raises(ValueError, match="vacía"):
            await service.report_incorrect(str(uuid.uuid4()), correction="")

    @pytest.mark.asyncio
    async def test_whitespace_correction_rejected(self):
        service = FeedbackService(pool=MagicMock())
        with pytest.raises(ValueError, match="vacía"):
            await service.report_incorrect(str(uuid.uuid4()), correction="   ")

    @pytest.mark.asyncio
    async def test_negative_rating_rejected(self):
        service = FeedbackService(pool=MagicMock())
        with pytest.raises(ValueError):
            await service.rate_response(str(uuid.uuid4()), rating=-1)

    @pytest.mark.asyncio
    async def test_float_rating_rejected(self):
        service = FeedbackService(pool=MagicMock())
        with pytest.raises(ValueError):
            await service.rate_response(str(uuid.uuid4()), rating=4.5)


@pytest.mark.integration
class TestFeedbackIntegration:
    """Tests de integración con PostgreSQL."""

    @pytest.fixture
    async def feedback_service(self):
        import os
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://yeyo:yeyo@localhost:5432/yeyoos"
        )
        mock_memory = AsyncMock()
        mock_memory.store.return_value = MagicMock(id="mem-123")
        service = await FeedbackService.create(db_url, flash_memory=mock_memory)
        yield service
        await service.close()

    @pytest.mark.asyncio
    async def test_rate_response(self, feedback_service):
        msg_id = str(uuid.uuid4())
        result = await feedback_service.rate_response(
            message_id=msg_id,
            rating=4,
            comment="Buena respuesta",
        )
        assert result["rating"] == 4
        assert result["message_id"] == msg_id

    @pytest.mark.asyncio
    async def test_rate_all_valid_ratings(self, feedback_service):
        for rating in [1, 2, 3, 4, 5]:
            result = await feedback_service.rate_response(
                message_id=str(uuid.uuid4()),
                rating=rating,
            )
            assert result["rating"] == rating

    @pytest.mark.asyncio
    async def test_report_incorrect_creates_correction(self, feedback_service):
        result = await feedback_service.report_incorrect(
            message_id=str(uuid.uuid4()),
            correction="Mi nombre es Diego, no Juan",
        )
        assert result["correction"] == "Mi nombre es Diego, no Juan"
        assert result["memory_created"] is not None

    @pytest.mark.asyncio
    async def test_get_feedback_stats(self, feedback_service):
        # Crear algunos feedbacks
        for i in range(3):
            await feedback_service.rate_response(
                message_id=str(uuid.uuid4()),
                rating=4,
            )
        stats = await feedback_service.get_feedback_stats()
        assert isinstance(stats, dict)
        assert "total_feedback" in stats
        assert "average_rating" in stats
        assert "rating_distribution" in stats
        assert "total_corrections" in stats
        assert stats["total_feedback"] > 0

    @pytest.mark.asyncio
    async def test_get_feedback_for_message(self, feedback_service):
        msg_id = str(uuid.uuid4())
        await feedback_service.rate_response(msg_id, rating=5, comment="Perfecto")
        results = await feedback_service.get_feedback_for_message(msg_id)
        assert len(results) >= 1
        assert results[0]["rating"] == 5
