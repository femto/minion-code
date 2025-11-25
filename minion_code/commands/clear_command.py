#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear command - Clear conversation history
"""

from minion_code.commands import BaseCommand


class ClearCommand(BaseCommand):
    """Clear conversation history."""

    name = "clear"
    description = "Clear the conversation history"
    usage = "/clear [--force]"
    aliases = ["c", "reset"]

    async def execute(self, args: str) -> None:
        """Execute the clear command."""
        if not self.agent:
            self.output.panel(
                "❌ Agent not initialized",
                title="Error",
                border_style="red"
            )
            return

        force = "--force" in args or "-f" in args

        history = self.agent.get_conversation_history()
        if not history:
            self.output.panel(
                "📝 No conversation history to clear.",
                title="Info",
                border_style="blue"
            )
            return

        # Confirm before clearing unless --force is used
        if not force:
            self.output.panel(
                f"⚠️ This will clear {len(history)} messages from history.\n"
                "This action cannot be undone.",
                title="Confirm Clear",
                border_style="yellow"
            )

            confirmed = await self.output.confirm(
                "Are you sure you want to clear the history?",
                title="Confirm Clear",
                ok_text="Clear",
                cancel_text="Cancel"
            )

            if not confirmed:
                self.output.panel(
                    "❌ Clear operation cancelled.",
                    title="Cancelled",
                    border_style="blue"
                )
                return

        # Clear the history
        self.agent.clear_conversation_history()

        self.output.panel(
            f"🗑️ Successfully cleared {len(history)} messages from history.",
            title="History Cleared",
            border_style="green"
        )