"""Tests para Code Node — Micro-fase 5.7"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.nodes.code.service import (
    CodeNode, SUPPORTED_LANGUAGES, LANGUAGE_EXTENSIONS,
)


class TestCodeNodeLifecycle:

    def test_node_name(self):
        node = CodeNode()
        assert node.name == "Code"

    @pytest.mark.asyncio
    async def test_initialize_creates_default_tab(self):
        node = CodeNode()
        await node.initialize()
        assert len(node._tabs) == 1
        assert node._active_tab_id is not None

    @pytest.mark.asyncio
    async def test_render_ui_has_tabs_and_languages(self):
        node = CodeNode()
        await node.initialize()
        ui = await node.render_ui()
        assert ui["component"] == "CodeNode"
        assert "tabs" in ui["props"]
        assert "languages" in ui["props"]

    @pytest.mark.asyncio
    async def test_cleanup_clears_tabs(self):
        node = CodeNode()
        await node.initialize()
        await node.cleanup()
        assert len(node._tabs) == 0


class TestCodeNodeTabs:

    @pytest.mark.asyncio
    async def test_open_tab(self):
        node = CodeNode()
        await node.initialize()
        result = await node.open_tab("test.js", "console.log('hi')")
        assert result["language"] == "javascript"
        assert len(node._tabs) == 2

    @pytest.mark.asyncio
    async def test_close_tab(self):
        node = CodeNode()
        await node.initialize()
        tab2 = await node.open_tab("test.js")
        result = await node.close_tab(tab2["tab_id"])
        assert result is True
        assert len(node._tabs) == 1

    @pytest.mark.asyncio
    async def test_close_nonexistent_tab(self):
        node = CodeNode()
        await node.initialize()
        result = await node.close_tab("fake-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_save_tab(self):
        node = CodeNode()
        await node.initialize()
        tab_id = node._active_tab_id
        node._tabs[tab_id].is_modified = True
        result = await node.save_tab(tab_id, "new content")
        assert result["saved"] is True
        assert node._tabs[tab_id].content == "new content"
        assert node._tabs[tab_id].is_modified is False

    @pytest.mark.asyncio
    async def test_switch_tab(self):
        node = CodeNode()
        await node.initialize()
        tab2 = await node.open_tab("test.py", "print('hello')")
        first_id = list(node._tabs.keys())[0]
        result = await node.switch_tab(first_id)
        assert node._active_tab_id == first_id

    @pytest.mark.asyncio
    async def test_language_detection_from_extension(self):
        node = CodeNode()
        await node.initialize()
        result = await node.open_tab("style.css")
        assert result["language"] == "css"

    @pytest.mark.asyncio
    async def test_invalid_language_defaults_to_python(self):
        node = CodeNode()
        tab = node._create_tab("test.xyz", "invalid_lang", "")
        assert tab.language == "python"


class TestCodeNodeLanguages:

    def test_supported_languages_count(self):
        assert len(SUPPORTED_LANGUAGES) >= 15

    def test_python_supported(self):
        assert "python" in SUPPORTED_LANGUAGES

    def test_extension_mapping(self):
        assert LANGUAGE_EXTENSIONS[".py"] == "python"
        assert LANGUAGE_EXTENSIONS[".js"] == "javascript"
        assert LANGUAGE_EXTENSIONS[".rs"] == "rust"
        assert LANGUAGE_EXTENSIONS[".go"] == "go"


class TestCodeNodeIA:

    @pytest.mark.asyncio
    async def test_explain_code(self):
        node = CodeNode()
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=MagicMock(
            content="This function prints hello world"
        ))
        mock_module = MagicMock()
        mock_module.OllamaProvider = MagicMock(return_value=mock_provider)
        with patch.dict("sys.modules", {"src.ia.ollama_provider": mock_module}):
            result = await node._explain_code("print('hello')")
            assert "explanation" in result

    @pytest.mark.asyncio
    async def test_generate_code(self):
        node = CodeNode()
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=MagicMock(
            content="def fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)"
        ))
        mock_module = MagicMock()
        mock_module.OllamaProvider = MagicMock(return_value=mock_provider)
        with patch.dict("sys.modules", {"src.ia.ollama_provider": mock_module}):
            result = await node._generate_code("fibonacci function", "python")
            assert "code" in result
            assert result["language"] == "python"

    @pytest.mark.asyncio
    async def test_process_unknown_action(self):
        node = CodeNode()
        result = await node.process({"action": "unknown"})
        assert "error" in result
