#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools command - Show available tools
"""

from minion_code.commands import BaseCommand, CommandType


class ToolsCommand(BaseCommand):
    """Show available tools."""

    name = "tools"
    description = "List all available tools and their descriptions"
    usage = "/tools [filter]"
    aliases = ["t"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        """Execute the tools command."""
        if not self.agent or not self.agent.tools:
            self.output.panel(
                "❌ No tools available or agent not initialized",
                title="Error",
                border_style="red",
            )
            return

        filter_text = args.strip().lower()
        tools = self.agent.tools

        # Filter tools if filter text provided
        if filter_text:
            tools = [
                tool
                for tool in tools
                if filter_text in tool.name.lower()
                or filter_text in tool.description.lower()
            ]

        if not tools:
            self.output.panel(
                f"❌ No tools found matching '{filter_text}'",
                title="No Results",
                border_style="yellow",
            )
            return

        # Prepare tools table data
        headers = ["Tool Name", "Description", "Type", "Inputs"]
        rows = []

        for tool in tools:
            tool_type = (
                "Read-only" if getattr(tool, "readonly", False) else "Read-write"
            )

            # Get input parameters
            inputs = getattr(tool, "inputs", {})
            input_names = list(inputs.keys()) if inputs else []
            input_str = ", ".join(input_names[:3])  # Show first 3 inputs
            if len(input_names) > 3:
                input_str += f" (+{len(input_names) - 3} more)"

            rows.append(
                [
                    tool.name,
                    (
                        tool.description[:50] + "..."
                        if len(tool.description) > 50
                        else tool.description
                    ),
                    tool_type,
                    input_str or "-",
                ]
            )

        title = (
            f"🛠️ Available Tools{f' (filtered: {filter_text})' if filter_text else ''}"
        )
        self.output.table(headers, rows, title=title)

        # Show summary
        summary_text = f"📊 Total: {len(tools)} tools"
        if filter_text:
            summary_text += f" (filtered from {len(self.agent.tools)} total)"

        self.output.panel(summary_text, title="Summary", border_style="green")
