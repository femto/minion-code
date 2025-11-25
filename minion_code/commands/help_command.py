#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Help command - Show available commands and their usage
"""

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
            self.output.panel(
                f"❌ Command '/{command_name}' not found",
                title="Error",
                border_style="red"
            )
            return

        # Create temporary command instance to get help
        temp_command = command_class(self.output, self.agent)
        help_text = temp_command.get_help()

        self.output.panel(
            help_text,
            title=f"Help: /{command_name}",
            border_style="blue"
        )

    async def _show_general_help(self) -> None:
        """Show general help with all commands."""
        from minion_code.commands import command_registry

        commands = command_registry.list_commands()

        # Prepare table data
        headers = ["Command", "Description", "Aliases"]
        rows = []

        for name, command_class in sorted(commands.items()):
            aliases = ", ".join(f"/{alias}" for alias in command_class.aliases)
            rows.append([
                f"/{name}",
                command_class.description,
                aliases or "-"
            ])

        self.output.table(headers, rows, title="📚 Available Commands")

        # Show usage info
        self.output.panel(
            "💡 Commands must start with '/' (e.g., /help, /tools)\n"
            "💬 Regular messages are sent to the AI agent\n"
            "🔍 Use '/help <command>' for detailed help on a specific command",
            title="Usage Tips",
            border_style="green"
        )