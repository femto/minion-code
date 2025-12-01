#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear command - Clear conversation history
"""

from minion_code.commands import BaseCommand, CommandType


class ClearCommand(BaseCommand):
    """Clear conversation history."""

    name = "clear"
    description = "Clear the conversation history"
    usage = "/clear"
    aliases = ["c", "reset"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        """Execute the clear command."""
        if not self.agent:
            self.output.panel(
                "❌ Agent not initialized",
                title="Error",
                border_style="red"
            )
            return

        history = self.agent.get_conversation_history()
        if not history:
            self.output.panel(
                "📝 No conversation history to clear.",
                title="Info",
                border_style="blue"
            )
            return

        # Clear the history directly without confirmation
        self.agent.clear_conversation_history()

        self.output.panel(
            f"🗑️ Successfully cleared {len(history)} messages from history.",
            title="History Cleared",
            border_style="green"
        )