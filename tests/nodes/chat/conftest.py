"""
Pytest configuration and fixtures for chat node tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


@pytest.fixture
def mock_database():
    """Create a properly configured mock database."""
    mock_db = AsyncMock()
    mock_db.store_message = AsyncMock(return_value=None)
    mock_db.create_conversation = AsyncMock(return_value={"id": "conv-123"})
    mock_db.get_conversation = AsyncMock(return_value=None)
    mock_db.get_messages = AsyncMock(return_value=[])
    mock_db.get_user_preferences = AsyncMock(return_value={})
    mock_db.get_average_response_time = AsyncMock(return_value=None)
    return mock_db


@pytest.fixture
def mock_get_database(mock_database):
    """Create a properly configured mock get_database function."""
    return AsyncMock(return_value=mock_database)


@pytest.fixture
def mock_conversation_agent():
    """Create a properly configured mock ConversationAgent."""
    agent = MagicMock()
    agent.get_system_prompt = MagicMock(return_value="You are a helpful assistant")
    agent.validate_output = MagicMock(return_value=(True, ""))  # Returns (is_valid, reason)
    return agent


@pytest.fixture(autouse=True)
def patch_conversation_agent_class(mock_conversation_agent):
    """Auto-patch ConversationAgent class for all tests."""
    # Patch where it's imported from
    with patch("src.agents.conversation.ConversationAgent") as mock_class:
        mock_class.return_value = mock_conversation_agent
        yield mock_class



