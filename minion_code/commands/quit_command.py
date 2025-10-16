#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quit command - Exit the application
"""

from rich.panel import Panel
from minion_code.commands import BaseCommand


class QuitCommand(BaseCommand):
    """Exit the application."""
    
    name = "quit"
    description = "Exit the application"
    usage = "/quit"
    aliases = ["exit", "q", "bye"]
    
    async def execute(self, args: str) -> None:
        """Execute the quit command."""
        goodbye_panel = Panel(
            "👋 [bold yellow]Goodbye! Thanks for using MinionCode![/bold yellow]",
            title="[bold red]Exit[/bold red]",
            border_style="red"
        )
        self.console.print(goodbye_panel)
        
        # Set a flag that the TUI can check
        if hasattr(self, '_tui_instance'):
            self._tui_instance.running = False