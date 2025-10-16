#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clear command - Clear conversation history
"""

from rich.panel import Panel
from rich.prompt import Confirm
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
            error_panel = Panel(
                "❌ [bold red]Agent not initialized[/bold red]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)
            return
        
        force = "--force" in args or "-f" in args
        
        history = self.agent.get_conversation_history()
        if not history:
            no_history_panel = Panel(
                "📝 [italic]No conversation history to clear.[/italic]",
                title="[bold blue]Info[/bold blue]",
                border_style="blue"
            )
            self.console.print(no_history_panel)
            return
        
        # Confirm before clearing unless --force is used
        if not force:
            confirm_panel = Panel(
                f"⚠️ [bold yellow]This will clear {len(history)} messages from history.[/bold yellow]\n"
                "This action cannot be undone.",
                title="[bold yellow]Confirm Clear[/bold yellow]",
                border_style="yellow"
            )
            self.console.print(confirm_panel)
            
            if not Confirm.ask("Are you sure you want to clear the history?", console=self.console):
                cancel_panel = Panel(
                    "❌ [bold blue]Clear operation cancelled.[/bold blue]",
                    title="[bold blue]Cancelled[/bold blue]",
                    border_style="blue"
                )
                self.console.print(cancel_panel)
                return
        
        # Clear the history
        self.agent.clear_conversation_history()
        
        success_panel = Panel(
            f"🗑️ [bold green]Successfully cleared {len(history)} messages from history.[/bold green]",
            title="[bold green]History Cleared[/bold green]",
            border_style="green"
        )
        self.console.print(success_panel)