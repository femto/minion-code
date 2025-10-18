#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help command - Show available commands and their usage
"""

from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from minion_code.commands import BaseCommand


class HelpCommand(BaseCommand):
    """Show help information for commands."""
    
    name = "help"
    description = "Show available commands and their usage"
    usage = "/help [command_name]"
    aliases = ["h", "?"]
    
    async def execute(self, args: str) -> None:
        """Execute the help command."""
        args = args.strip()
        
        if args:
            # Show help for specific command
            await self._show_command_help(args)
        else:
            # Show general help
            await self._show_general_help()
    
    async def _show_command_help(self, command_name: str) -> None:
        """Show help for a specific command."""
        from minion_code.commands import command_registry
        
        command_class = command_registry.get_command(command_name)
        if not command_class:
            error_panel = Panel(
                f"❌ [bold red]Command '/{command_name}' not found[/bold red]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)
            return
        
        # Create temporary command instance to get help
        temp_command = command_class(self.console, self.agent)
        help_text = temp_command.get_help()
        
        help_panel = Panel(
            Markdown(help_text),
            title=f"[bold blue]Help: /{command_name}[/bold blue]",
            border_style="blue"
        )
        self.console.print(help_panel)
    
    async def _show_general_help(self) -> None:
        """Show general help with all commands."""
        from minion_code.commands import command_registry
        
        commands = command_registry.list_commands()
        
        help_table = Table(
            title="📚 Available Commands", 
            show_header=True, 
            header_style="bold blue"
        )
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        help_table.add_column("Aliases", style="yellow")
        
        for name, command_class in sorted(commands.items()):
            aliases = ", ".join(f"/{alias}" for alias in command_class.aliases)
            help_table.add_row(
                f"/{name}",
                command_class.description,
                aliases or "-"
            )
        
        self.console.print(help_table)
        
        # Show usage info
        usage_panel = Panel(
            "💡 [italic]Commands must start with '/' (e.g., /help, /tools)[/italic]\n"
            "💬 [italic]Regular messages are sent to the AI agent[/italic]\n"
            "🔍 [italic]Use '/help <command>' for detailed help on a specific command[/italic]",
            title="[bold green]Usage Tips[/bold green]",
            border_style="green"
        )
        self.console.print(usage_panel)