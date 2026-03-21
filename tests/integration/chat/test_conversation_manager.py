"""
Tests de integración para ConversationManager — Micro-fase 2.7
Requieren PostgreSQL corriendo con schema de conversaciones.
"""

import pytest
import os
from src.chat.conversation import ConversationManager
from src.ia.interfaces import IAMessage


pytestmark = pytest.mark.integration

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yeyo:yeyo_dev_2026@127.0.0.1:5432/yeyo_db"
)


@pytest.fixture
async def conv_manager():
    cm = await ConversationManager.create(DATABASE_URL)
    yield cm
    await cm.close()


@pytest.mark.asyncio
async def test_create_conversation_returns_uuid(conv_manager):
    conv_id = await conv_manager.create_conversation()
    assert isinstance(conv_id, str)
    assert len(conv_id) == 36


@pytest.mark.asyncio
async def test_create_conversation_with_title(conv_manager):
    conv_id = await conv_manager.create_conversation(title="Mi chat")
    conv = await conv_manager.get_conversation(conv_id)
    assert conv is not None
    assert conv["title"] == "Mi chat"


@pytest.mark.asyncio
async def test_add_message(conv_manager):
    conv_id = await conv_manager.create_conversation()
    await conv_manager.add_message(conv_id, "user", "Hola YeyoOS")
    history = await conv_manager.get_history(conv_id)
    assert len(history) == 1
    assert history[0].role == "user"
    assert history[0].content == "Hola YeyoOS"


@pytest.mark.asyncio
async def test_messages_in_order(conv_manager):
    conv_id = await conv_manager.create_conversation()
    await conv_manager.add_message(conv_id, "user", "Primero")
    await conv_manager.add_message(conv_id, "assistant", "Segundo")
    await conv_manager.add_message(conv_id, "user", "Tercero")
    history = await conv_manager.get_history(conv_id)
    assert len(history) == 3
    assert history[0].content == "Primero"
    assert history[1].content == "Segundo"
    assert history[2].content == "Tercero"


@pytest.mark.asyncio
async def test_history_limit(conv_manager):
    conv_id = await conv_manager.create_conversation()
    for i in range(10):
        await conv_manager.add_message(conv_id, "user", f"Mensaje {i}")
    history = await conv_manager.get_history(conv_id, limit=3)
    assert len(history) == 3
    assert history[-1].content == "Mensaje 9"


@pytest.mark.asyncio
async def test_get_history_returns_ia_messages(conv_manager):
    conv_id = await conv_manager.create_conversation()
    await conv_manager.add_message(conv_id, "user", "Test")
    history = await conv_manager.get_history(conv_id)
    assert all(isinstance(m, IAMessage) for m in history)


@pytest.mark.asyncio
async def test_list_conversations(conv_manager):
    await conv_manager.create_conversation(title="Conv test")
    convos = await conv_manager.list_conversations()
    assert isinstance(convos, list)
    assert len(convos) > 0
    assert all("id" in c for c in convos)
    assert all("title" in c for c in convos)


@pytest.mark.asyncio
async def test_get_conversation_not_found(conv_manager):
    result = await conv_manager.get_conversation("00000000-0000-0000-0000-000000000000")
    assert result is None


@pytest.mark.asyncio
async def test_message_count_auto_increments(conv_manager):
    conv_id = await conv_manager.create_conversation()
    await conv_manager.add_message(conv_id, "user", "Uno")
    await conv_manager.add_message(conv_id, "assistant", "Dos")
    conv = await conv_manager.get_conversation(conv_id)
    assert conv["message_count"] == 2


@pytest.mark.asyncio
async def test_messages_have_timestamps(conv_manager):
    conv_id = await conv_manager.create_conversation()
    await conv_manager.add_message(conv_id, "user", "Test timestamp")
    conv = await conv_manager.get_conversation(conv_id)
    assert conv["created_at"] is not None
    assert conv["updated_at"] is not None
