"""Tests para Image Generation Node — Micro-fase 5.2"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.nodes.image.service import (
    ImageGenerationNode, SAFE_RESOLUTIONS, MAX_RESOLUTION,
    SD_VRAM_REQUIRED, STYLE_PRESETS,
)


class TestImageGenLifecycle:

    def test_node_name(self):
        node = ImageGenerationNode()
        assert node.name == "Image Generation"

    @pytest.mark.asyncio
    async def test_render_ui_has_styles_and_resolutions(self):
        node = ImageGenerationNode()
        ui = await node.render_ui()
        assert "styles" in ui["props"]
        assert "resolutions" in ui["props"]
        assert len(ui["props"]["styles"]) == len(STYLE_PRESETS)
        assert len(ui["props"]["resolutions"]) == len(SAFE_RESOLUTIONS)

    @pytest.mark.asyncio
    async def test_cleanup_clears_gallery(self):
        node = ImageGenerationNode()
        node._gallery.append(MagicMock())
        await node.cleanup()
        assert len(node._gallery) == 0

    @pytest.mark.asyncio
    async def test_process_unknown_action(self):
        node = ImageGenerationNode()
        result = await node.process({"action": "unknown"})
        assert "error" in result


class TestImageGenResolution:

    def test_max_resolution_is_512(self):
        assert MAX_RESOLUTION == 512

    def test_all_resolutions_within_limit(self):
        for name, (w, h) in SAFE_RESOLUTIONS.items():
            assert w <= MAX_RESOLUTION, f"{name} width {w} > {MAX_RESOLUTION}"
            assert h <= MAX_RESOLUTION, f"{name} height {h} > {MAX_RESOLUTION}"

    @pytest.mark.asyncio
    async def test_invalid_resolution_rejected(self):
        node = ImageGenerationNode()
        result = await node._generate_image(
            prompt="test", resolution="1024x1024"
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_concurrent_generation_rejected(self):
        node = ImageGenerationNode()
        node._is_generating = True
        result = await node._generate_image(prompt="test")
        assert "error" in result
        assert "en curso" in result["error"]


class TestImageGenGPU:

    def test_sd_vram_required(self):
        assert SD_VRAM_REQUIRED == 2500

    @pytest.mark.asyncio
    async def test_gpu_released_after_generation(self):
        node = ImageGenerationNode()
        node.request_gpu = AsyncMock(return_value=True)
        node.release_gpu = AsyncMock()
        node._enhance_prompt = AsyncMock(return_value={
            "original_prompt": "test",
            "enhanced_prompt": "test enhanced",
        })
        node._load_sd_pipeline = AsyncMock(return_value=MagicMock())
        node._run_sd_inference = AsyncMock(return_value=b"fake_png_data")

        await node._generate_image(prompt="test cat")
        node.release_gpu.assert_called_once()

    @pytest.mark.asyncio
    async def test_gpu_released_on_error(self):
        node = ImageGenerationNode()
        node.request_gpu = AsyncMock(return_value=True)
        node.release_gpu = AsyncMock()
        node._enhance_prompt = AsyncMock(return_value={
            "original_prompt": "test",
            "enhanced_prompt": "test enhanced",
        })
        node._load_sd_pipeline = AsyncMock(side_effect=RuntimeError("boom"))

        result = await node._generate_image(prompt="test")
        assert "error" in result
        node.release_gpu.assert_called()

    @pytest.mark.asyncio
    async def test_gpu_not_available(self):
        node = ImageGenerationNode()
        node.request_gpu = AsyncMock(return_value=False)
        node._enhance_prompt = AsyncMock(return_value={
            "original_prompt": "test",
            "enhanced_prompt": "test enhanced",
        })

        result = await node._generate_image(prompt="test")
        assert "error" in result
        assert "GPU" in result["error"]


class TestImageGenStyles:

    def test_style_presets_exist(self):
        assert "none" in STYLE_PRESETS
        assert "photorealistic" in STYLE_PRESETS
        assert "anime" in STYLE_PRESETS
        assert len(STYLE_PRESETS) >= 8

    @pytest.mark.asyncio
    async def test_style_appended_to_prompt(self):
        node = ImageGenerationNode()
        node.request_gpu = AsyncMock(return_value=True)
        node.release_gpu = AsyncMock()
        node._enhance_prompt = AsyncMock(return_value={
            "original_prompt": "cat",
            "enhanced_prompt": "a beautiful cat",
        })
        node._load_sd_pipeline = AsyncMock(return_value=MagicMock())
        node._run_sd_inference = AsyncMock(return_value=b"fake_png_data")

        result = await node._generate_image(prompt="cat", style="anime")
        assert "anime" in result.get("enhanced_prompt", "").lower()


class TestImageGenPromptEnhancement:

    @pytest.mark.asyncio
    async def test_enhance_prompt_calls_ollama(self):
        node = ImageGenerationNode()
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=MagicMock(
            content="A beautiful cat sitting on a window"
        ))

        mock_module = MagicMock()
        mock_module.OllamaProvider = MagicMock(return_value=mock_provider)
        with patch.dict("sys.modules", {"src.ia.ollama_provider": mock_module}):
            result = await node._enhance_prompt("cat")
            assert result["original_prompt"] == "cat"
            assert len(result["enhanced_prompt"]) > 0
