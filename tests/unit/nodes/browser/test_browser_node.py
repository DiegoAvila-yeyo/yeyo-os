"""Tests para Browser Node — Micro-fase 5.13"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.nodes.browser.service import BrowserNode


class TestBrowserNavigation:

    def test_navigate_sets_url(self):
        node = BrowserNode()
        result = node._navigate("https://example.com")
        assert result["url"] == "https://example.com"
        assert node._current_url == "https://example.com"

    def test_navigate_adds_https(self):
        node = BrowserNode()
        result = node._navigate("example.com")
        assert result["url"] == "https://example.com"

    def test_navigate_preserves_http(self):
        node = BrowserNode()
        result = node._navigate("http://example.com")
        assert result["url"] == "http://example.com"

    def test_navigate_empty_url_error(self):
        node = BrowserNode()
        result = node._navigate("")
        assert "error" in result

    def test_back_and_forward(self):
        node = BrowserNode()
        node._navigate("https://a.com")
        node._navigate("https://b.com")
        node._navigate("https://c.com")

        back_result = node._go_back()
        assert back_result["url"] == "https://b.com"

        forward_result = node._go_forward()
        assert forward_result["url"] == "https://c.com"

    def test_back_at_start_error(self):
        node = BrowserNode()
        result = node._go_back()
        assert "error" in result

    def test_forward_at_end_error(self):
        node = BrowserNode()
        node._navigate("https://a.com")
        result = node._go_forward()
        assert "error" in result

    def test_navigate_truncates_forward_history(self):
        node = BrowserNode()
        node._navigate("https://a.com")
        node._navigate("https://b.com")
        node._navigate("https://c.com")
        node._go_back()
        node._go_back()
        node._navigate("https://d.com")
        # Forward should be gone
        result = node._go_forward()
        assert "error" in result


class TestBrowserBookmarks:

    def test_add_bookmark(self):
        node = BrowserNode()
        node._current_url = "https://example.com"
        result = node._add_bookmark("Example", "https://example.com")
        assert result["title"] == "Example"
        assert len(node._bookmarks) == 1

    def test_bookmark_uses_current_url_if_empty(self):
        node = BrowserNode()
        node._current_url = "https://current.com"
        result = node._add_bookmark("Test", "")
        assert result["url"] == "https://current.com"

    @pytest.mark.asyncio
    async def test_render_ui_has_bookmarks(self):
        node = BrowserNode()
        node._add_bookmark("Test", "https://test.com")
        ui = await node.render_ui()
        assert len(ui["props"]["bookmarks"]) == 1


class TestBrowserSummarize:

    @pytest.mark.asyncio
    async def test_summarize_page(self):
        node = BrowserNode()
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=MagicMock(
            content="Esta página habla sobre tecnología."
        ))
        mock_module = MagicMock()
        mock_module.OllamaProvider = MagicMock(return_value=mock_provider)
        with patch.dict("sys.modules", {"src.ia.ollama_provider": mock_module}):
            result = await node._summarize_page("Lots of text about tech...")
            assert "summary" in result
            assert len(result["summary"]) > 0

    @pytest.mark.asyncio
    async def test_summarize_empty_text_error(self):
        node = BrowserNode()
        result = await node._summarize_page("")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_unknown_action(self):
        node = BrowserNode()
        result = await node.process({"action": "unknown"})
        assert "error" in result
