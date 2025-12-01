#!/usr/bin/env python3
"""Simple test script to verify OutputAdapter pattern works correctly"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from rich.console import Console
from minion_code.adapters import RichOutputAdapter


class MockAgent:
    """Mock agent for testing"""
    def __init__(self):
        self._conversation_history = [
            {"user_message": "Hello", "agent_response": "Hi there!"},
            {"user_message": "How are you?", "agent_response": "I'm doing well!"},
            {"user_message": "Test message", "agent_response": "Test response"}
        ]
        self.tools = []

    def get_conversation_history(self):
        return self._conversation_history

    def clear_conversation_history(self):
        self._conversation_history.clear()


@pytest.mark.asyncio
async def test_adapter():
    """Test the adapter pattern"""
    console = Console(force_terminal=False)  # Disable terminal features for testing

    # Test 1: Create adapter
    output_adapter = RichOutputAdapter(console)
    assert output_adapter is not None
    assert output_adapter.console is console

    # Test 2: Test panel method (should not raise)
    output_adapter.panel(
        "This is a test panel message",
        title="Test Panel",
        border_style="green"
    )

    # Test 3: Test table method
    headers = ["Column 1", "Column 2", "Column 3"]
    rows = [
        ["Data 1", "Data 2", "Data 3"],
        ["Row 2-1", "Row 2-2", "Row 2-3"]
    ]
    output_adapter.table(headers, rows, title="Test Table")

    # Test 4: Test text method
    output_adapter.text("This is simple text output")

    # Test 5: Test command with adapter
    from minion_code.commands.clear_command import ClearCommand

    mock_agent = MockAgent()
    clear_command = ClearCommand(output_adapter, mock_agent)

    assert len(mock_agent.get_conversation_history()) == 3
    await clear_command.execute("--force")
    assert len(mock_agent.get_conversation_history()) == 0

    # Test 6: Test confirm method with mock (avoid stdin)
    with patch('rich.prompt.Confirm.ask', return_value=True):
        result = await output_adapter.confirm(
            "Do you want to continue?",
            title="Test Confirmation",
            ok_text="Yes",
            cancel_text="No"
        )
        assert result is True

    # Test 7: Test confirm returns False when user declines
    with patch('rich.prompt.Confirm.ask', return_value=False):
        result = await output_adapter.confirm("Continue?")
        assert result is False


if __name__ == "__main__":
    asyncio.run(test_adapter())
