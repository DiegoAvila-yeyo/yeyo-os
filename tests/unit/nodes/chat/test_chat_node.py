"""Tests para Chat Node — Micro-fase 5.1"""

import pytest
from src.nodes.chat.service import ChatNode, Conversation, ChatMessage


class TestChatNodeLifecycle:
    """Tests del lifecycle del Chat Node."""

    @pytest.mark.asyncio
    async def test_initialize_creates_default_conversation(self):
        node = ChatNode()
        await node.initialize()
        assert len(node._conversations) == 1
        assert node._active_conversation_id is not None

    @pytest.mark.asyncio
    async def test_render_ui_returns_component(self):
        node = ChatNode()
        await node.initialize()
        ui = await node.render_ui()
        assert ui["component"] == "ChatNode"
        assert "conversations" in ui["props"]

    @pytest.mark.asyncio
    async def test_cleanup_clears_conversations(self):
        node = ChatNode()
        await node.initialize()
        await node.cleanup()
        assert len(node._conversations) == 0
        assert node._active_conversation_id is None


class TestChatNodeMultiConversation:
    """Tests de multi-conversación."""

    @pytest.mark.asyncio
    async def test_new_conversation_creates_tab(self):
        node = ChatNode()
        await node.initialize()
        result = await node.new_conversation("Test Conv")
        assert result["title"] == "Test Conv"
        assert len(node._conversations) == 2

    @pytest.mark.asyncio
    async def test_switch_conversation(self):
        node = ChatNode()
        await node.initialize()
        conv = await node.new_conversation("Segunda")
        result = await node.switch_conversation(conv["conversation_id"])
        assert node._active_conversation_id == conv["conversation_id"]

    @pytest.mark.asyncio
    async def test_switch_to_nonexistent_returns_error(self):
        node = ChatNode()
        await node.initialize()
        result = await node.switch_conversation("fake-id")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_delete_conversation(self):
        node = ChatNode()
        await node.initialize()
        conv = await node.new_conversation("Para borrar")
        result = await node.delete_conversation(conv["conversation_id"])
        assert result is True
        assert conv["conversation_id"] not in node._conversations

    @pytest.mark.asyncio
    async def test_delete_active_switches_to_remaining(self):
        node = ChatNode()
        await node.initialize()
        first_id = node._active_conversation_id
        conv = await node.new_conversation("Segunda")
        await node.delete_conversation(conv["conversation_id"])
        assert node._active_conversation_id == first_id

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self):
        node = ChatNode()
        await node.initialize()
        result = await node.delete_conversation("fake-id")
        assert result is False


class TestChatNodeSearch:
    """Tests de búsqueda de mensajes."""

    @pytest.mark.asyncio
    async def test_search_finds_messages(self):
        node = ChatNode()
        await node.initialize()
        conv_id = node._active_conversation_id
        conv = node._conversations[conv_id]
        conv.messages.append(ChatMessage(
            id="msg-1", role="user", content="Hola mundo"
        ))
        conv.messages.append(ChatMessage(
            id="msg-2", role="assistant", content="Hola! Soy YeyoOS"
        ))
        results = await node.search_messages("mundo")
        assert len(results) == 1
        assert results[0]["content"] == "Hola mundo"

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        node = ChatNode()
        await node.initialize()
        conv_id = node._active_conversation_id
        conv = node._conversations[conv_id]
        conv.messages.append(ChatMessage(
            id="msg-1", role="user", content="PYTHON es genial"
        ))
        results = await node.search_messages("python")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_across_conversations(self):
        node = ChatNode()
        await node.initialize()
        conv1_id = node._active_conversation_id
        node._conversations[conv1_id].messages.append(
            ChatMessage(id="msg-1", role="user", content="Hola en conv1")
        )
        conv2 = await node.new_conversation("Segunda")
        node._conversations[conv2["conversation_id"]].messages.append(
            ChatMessage(id="msg-2", role="user", content="Hola en conv2")
        )
        results = await node.search_messages("Hola")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        node = ChatNode()
        await node.initialize()
        results = await node.search_messages("inexistente")
        assert len(results) == 0


class TestChatNodeExport:
    """Tests de export a markdown."""

    @pytest.mark.asyncio
    async def test_export_creates_markdown(self):
        node = ChatNode()
        await node.initialize()
        conv_id = node._active_conversation_id
        conv = node._conversations[conv_id]
        conv.title = "Test Export"
        conv.messages.append(ChatMessage(
            id="msg-1", role="user", content="Pregunta"
        ))
        conv.messages.append(ChatMessage(
            id="msg-2", role="assistant", content="Respuesta"
        ))
        md = await node.export_conversation(conv_id)
        assert "# Test Export" in md
        assert "**Usuario:** Pregunta" in md
        assert "**YeyoOS:** Respuesta" in md

    @pytest.mark.asyncio
    async def test_export_nonexistent_raises(self):
        node = ChatNode()
        await node.initialize()
        with pytest.raises(ValueError):
            await node.export_conversation("fake-id")
