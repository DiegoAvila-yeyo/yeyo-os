"""Tests para img2img + Analysis — Micro-fase 5.3"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.nodes.image.img2img import Img2ImgService
from src.nodes.image.analysis import ImageAnalysisService, VISION_MODELS


class TestImg2Img:

    @pytest.mark.asyncio
    async def test_transform_invalid_resolution_rejected(self):
        mock_node = MagicMock()
        service = Img2ImgService(mock_node)
        result = await service.transform(
            source_image=b"fake", prompt="test", resolution="2048x2048"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_strength_clamped(self):
        mock_node = MagicMock()
        mock_node.request_gpu = AsyncMock(return_value=True)
        mock_node.release_gpu = AsyncMock()
        service = Img2ImgService(mock_node)
        service._run_img2img = AsyncMock(return_value=b"result_png")
        result = await service.transform(
            source_image=b"fake", prompt="test", strength=2.0
        )
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_gpu_released_after_transform(self):
        mock_node = MagicMock()
        mock_node.request_gpu = AsyncMock(return_value=True)
        mock_node.release_gpu = AsyncMock()
        service = Img2ImgService(mock_node)
        service._run_img2img = AsyncMock(return_value=b"result_png")
        await service.transform(source_image=b"fake", prompt="test")
        mock_node.release_gpu.assert_called_once()

    @pytest.mark.asyncio
    async def test_gpu_released_on_error(self):
        mock_node = MagicMock()
        mock_node.request_gpu = AsyncMock(return_value=True)
        mock_node.release_gpu = AsyncMock()
        service = Img2ImgService(mock_node)
        service._run_img2img = AsyncMock(side_effect=RuntimeError("fail"))
        result = await service.transform(source_image=b"fake", prompt="test")
        assert "error" in result
        mock_node.release_gpu.assert_called_once()

    @pytest.mark.asyncio
    async def test_gpu_not_available(self):
        mock_node = MagicMock()
        mock_node.request_gpu = AsyncMock(return_value=False)
        service = Img2ImgService(mock_node)
        result = await service.transform(source_image=b"fake", prompt="test")
        assert "error" in result


class TestImageAnalysis:

    def test_vision_models_exist(self):
        assert len(VISION_MODELS) >= 2
        names = [m["name"] for m in VISION_MODELS]
        assert "llava:7b" in names
        assert "llava:3b" in names

    @pytest.mark.asyncio
    async def test_analyze_with_fallback(self):
        service = ImageAnalysisService()
        service._query_llava = AsyncMock(
            side_effect=[Exception("7b fail"), "A beautiful landscape"]
        )
        result = await service.analyze(b"fake_image", "Describe this")
        assert result["model_used"] == "llava:3b"
        assert "landscape" in result["description"]

    @pytest.mark.asyncio
    async def test_analyze_all_models_fail(self):
        service = ImageAnalysisService()
        service._query_llava = AsyncMock(side_effect=Exception("all fail"))
        result = await service.analyze(b"fake_image")
        assert "error" in result
        assert result["fallback"] == "text_only"

    @pytest.mark.asyncio
    async def test_analyze_first_model_success(self):
        service = ImageAnalysisService()
        service._query_llava = AsyncMock(return_value="A cat sitting on a chair")
        result = await service.analyze(b"fake_image")
        assert result["model_used"] == "llava:7b"
