#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Status command - Show system status and information
"""

import sys
import platform
from datetime import datetime
from minion_code.commands import BaseCommand, CommandType


class StatusCommand(BaseCommand):
    """Show system status and information."""

    name = "status"
    description = "Show system status, agent info, and statistics"
    usage = "/status"
    aliases = ["info", "stat"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        """Execute the status command."""
        # Prepare table data
        headers = ["Component", "Status", "Details"]
        rows = []

        # System info
        rows.append(
            ["System", "✅ Running", f"{platform.system()} {platform.release()}"]
        )

        rows.append(["Python", "✅ Active", f"{sys.version.split()[0]}"])

        # Agent info
        if self.agent:
            history = self.agent.get_conversation_history()
            tools_count = len(self.agent.tools) if self.agent.tools else 0
            metadata = getattr(getattr(self.agent, "state", None), "metadata", {}) or {}
            mode_name = metadata.get("session_mode_name", "Unknown")

            rows.append(["Agent", "✅ Ready", f"{tools_count} tools loaded"])
            rows.append(["Mode", "⚙️ Active", mode_name])

            rows.append(
                [
                    "Conversation",
                    "📝 Active" if history else "📝 Empty",
                    f"{len(history)} messages" if history else "No messages",
                ]
            )
        else:
            rows.append(["Agent", "❌ Not Ready", "Not initialized"])

        # Memory info (basic)
        try:
            import psutil

            memory = psutil.virtual_memory()
            rows.append(
                [
                    "Memory",
                    "📊 Monitored",
                    f"{memory.percent}% used ({memory.available // (1024**3)} GB free)",
                ]
            )
        except ImportError:
            rows.append(["Memory", "❌ Not Available", "psutil not installed"])

        # Display table
        self.output.table(headers, rows, title="📊 System Status")

        # Additional info panel
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        info_lines = [f"🕒 Current Time: {current_time}"]

        if self.agent:
            info_lines.append(
                f"🤖 Agent Model: {getattr(self.agent, 'llm', 'Unknown')}"
            )
            metadata = getattr(getattr(self.agent, "state", None), "metadata", {}) or {}
            if metadata.get("session_mode_description"):
                info_lines.append(
                    f"⚙️ Session Mode: {metadata.get('session_mode_name')} - {metadata.get('session_mode_description')}"
                )

            if self.agent.tools:
                tool_names = [tool.name for tool in self.agent.tools[:5]]
                if len(self.agent.tools) > 5:
                    tool_names.append(f"... and {len(self.agent.tools) - 5} more")
                info_lines.append(f"🛠️ Available Tools: {', '.join(tool_names)}")
            else:
                info_lines.append("🛠️ Available Tools: None")

        self.output.panel(
            "\n".join(info_lines), title="Additional Information", border_style="green"
        )
