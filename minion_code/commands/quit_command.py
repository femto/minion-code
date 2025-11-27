#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quit command - Exit the application
"""

from minion_code.commands import BaseCommand, CommandType


class QuitCommand(BaseCommand):
    """Exit the application."""

    name = "quit"
    description = "Exit the application"
    usage = "/quit"
    aliases = ["exit", "q", "bye"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        """Execute the quit command."""
        self.output.panel(
            "👋 Goodbye! Thanks for using MinionCode!",
            title="Exit",
            border_style="red"
        )

        # Set a flag that the TUI can check and cleanup resources
        if hasattr(self, '_tui_instance'):
            self._tui_instance.running = False
            # Cleanup MCP resources
            await self._tui_instance.cleanup()