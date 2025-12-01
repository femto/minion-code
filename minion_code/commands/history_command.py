#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
History command - Show conversation history
"""

from minion_code.commands import BaseCommand, CommandType


class HistoryCommand(BaseCommand):
    """Show conversation history."""

    name = "history"
    description = "Show conversation history with the agent"
    usage = "/history [count]"
    aliases = ["hist", "h"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        """Execute the history command."""
        if not self.agent:
            self.output.panel(
                "❌ Agent not initialized",
                title="Error",
                border_style="red"
            )
            return

        # Parse count argument
        count = 5  # default
        if args.strip():
            try:
                count = int(args.strip())
                if count <= 0:
                    count = 5
            except ValueError:
                self.output.panel(
                    f"❌ Invalid count: '{args.strip()}'. Using default (5)",
                    title="Warning",
                    border_style="yellow"
                )

        history = self.agent.get_conversation_history()
        if not history:
            self.output.panel(
                "📝 No conversation history yet.",
                title="History",
                border_style="blue"
            )
            return

        # Show header
        self.output.panel(
            f"📝 Conversation History (showing last {min(count, len(history))} of {len(history)} messages)",
            border_style="blue"
        )

        # Show recent messages
        recent_history = history[-count:] if count < len(history) else history

        for i, entry in enumerate(recent_history, 1):
            message_num = len(history) - len(recent_history) + i

            # User message
            user_msg = entry['user_message']
            if len(user_msg) > 150:
                user_msg = user_msg[:150] + "..."

            self.output.panel(
                user_msg,
                title=f"👤 You (#{message_num})",
                border_style="cyan"
            )

            # Agent response
            agent_msg = entry['agent_response']
            if len(agent_msg) > 200:
                agent_msg = agent_msg[:200] + "..."

            self.output.panel(
                agent_msg,
                title="🤖 Agent",
                border_style="green"
            )

            if i < len(recent_history):  # Don't add spacing after last message
                self.output.text("")

        # Show summary if there are more messages
        if len(history) > count:
            self.output.panel(
                f"💡 Showing {count} most recent messages. "
                f"Use '/history {len(history)}' to see all {len(history)} messages.",
                title="Note",
                border_style="yellow"
            )