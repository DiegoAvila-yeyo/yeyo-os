"""Tests para MiniChat v2 — Micro-fase 5.18"""

import pytest
from src.minichat.service import MiniChatV2Service, NODE_CONTEXTS, DEFAULT_CONTEXT


class TestMiniChatV2Context:

    def test_set_context_changes_node_type(self):
        service = MiniChatV2Service()
        result = service.set_context("image", "node-123")
        assert result["node_type"] == "image"
        assert service._current_node_type == "image"

    def test_suggestions_change_per_node(self):
        service = MiniChatV2Service()
        service.set_context("image", "node-1")
        image_suggestions = service.get_suggestions()

        service.set_context("code", "node-2")
        code_suggestions = service.get_suggestions()

        assert image_suggestions != code_suggestions

    def test_image_node_has_describe_suggestion(self):
        service = MiniChatV2Service()
        service.set_context("image", "node-1")
        suggestions = service.get_suggestions()
        assert any("imagen" in s.lower() or "describe" in s.lower() for s in suggestions)

    def test_code_node_has_explain_suggestion(self):
        service = MiniChatV2Service()
        service.set_context("code", "node-1")
        suggestions = service.get_suggestions()
        assert any("código" in s.lower() or "explica" in s.lower() for s in suggestions)

    def test_video_node_has_trim_suggestion(self):
        service = MiniChatV2Service()
        service.set_context("video", "node-1")
        suggestions = service.get_suggestions()
        assert any("recorta" in s.lower() or "minuto" in s.lower() for s in suggestions)

    def test_unknown_node_uses_default(self):
        service = MiniChatV2Service()
        service.set_context("unknown_node", "node-1")
        suggestions = service.get_suggestions()
        assert suggestions == DEFAULT_CONTEXT["suggestions"]

    def test_system_prompt_includes_node_context(self):
        service = MiniChatV2Service()
        service.set_context("image", "node-1")
        prompt = service.get_system_prompt()
        assert "imagen" in prompt.lower() or "image" in prompt.lower()


class TestMiniChatV2Messages:

    def test_clear_resets_state(self):
        service = MiniChatV2Service()
        service.set_context("image", "node-1")
        service.clear()
        assert service._current_node_type is None
        assert len(service._messages) == 0

    def test_all_node_contexts_defined(self):
        expected_nodes = {"chat", "image", "video", "code", "automation",
                          "files", "browser", "config"}
        assert expected_nodes.issubset(set(NODE_CONTEXTS.keys()))

    def test_each_context_has_suggestions(self):
        for node_type, context in NODE_CONTEXTS.items():
            assert "suggestions" in context, f"{node_type} missing suggestions"
            assert len(context["suggestions"]) > 0, f"{node_type} has no suggestions"

    def test_each_context_has_system_prompt(self):
        for node_type, context in NODE_CONTEXTS.items():
            assert "system_prompt" in context, f"{node_type} missing system_prompt"
            assert len(context["system_prompt"]) > 0

    def test_set_context_clears_messages(self):
        service = MiniChatV2Service()
        service._messages.append(
            type("Msg", (), {"role": "user", "content": "test"})()
        )
        service.set_context("code", "node-1")
        assert len(service._messages) == 0
