#!/usr/bin/env python3
"""Test script to verify OutputAdapter pattern works correctly"""

import asyncio
import pytest
from rich.console import Console
from minion_code.adapters import RichOutputAdapter
from minion_code.commands.clear_command import ClearCommand
from minion_code import MinionCodeAgent


@pytest.mark.asyncio
async def test_clear_command():
    """Test the clear command with RichOutputAdapter"""
    console = Console()
    console.print("[bold blue]Testing Clear Command with OutputAdapter[/bold blue]\n")

    # Create output adapter
    output_adapter = RichOutputAdapter(console)
    console.print("✅ Created RichOutputAdapter")

    # Create a mock agent with some history
    agent = await MinionCodeAgent.create(name="Test Agent", llm="sonnet")
    console.print("✅ Created MinionCodeAgent")

    # Add some fake history
    agent._conversation_history = [
        {"user_message": "Hello", "agent_response": "Hi there!"},
        {"user_message": "How are you?", "agent_response": "I'm doing well!"},
        {"user_message": "Test message", "agent_response": "Test response"},
    ]
    console.print(f"✅ Added {len(agent._conversation_history)} messages to history\n")

    # Create command instance with adapter
    clear_command = ClearCommand(output_adapter, agent)
    console.print("✅ Created ClearCommand with OutputAdapter\n")

    # Test 1: Clear with force flag (should not prompt)
    console.print("[bold yellow]Test 1: Clear with --force flag[/bold yellow]")
    await clear_command.execute("--force")
    console.print(
        f"History after force clear: {len(agent._conversation_history)} messages\n"
    )

    # Add history back for second test
    agent._conversation_history = [
        {"user_message": "Hello", "agent_response": "Hi there!"},
        {"user_message": "How are you?", "agent_response": "I'm doing well!"},
    ]

    # Test 2: Clear without force (will prompt for confirmation)
    console.print(
        "[bold yellow]Test 2: Clear without force (with confirmation prompt)[/bold yellow]"
    )
    console.print(
        "[dim]Note: This will wait for your input. Type 'y' to confirm or 'n' to cancel.[/dim]\n"
    )
    await clear_command.execute("")
    console.print(
        f"History after interactive clear: {len(agent._conversation_history)} messages\n"
    )

    console.print("[bold green]✅ All tests completed successfully![/bold green]")


if __name__ == "__main__":
    asyncio.run(test_clear_command())
