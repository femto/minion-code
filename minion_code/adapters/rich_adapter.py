#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rich Output Adapter - CLI implementation

This adapter uses Rich Console for terminal output. It provides synchronous
blocking behavior for user interactions, which is suitable for traditional
CLI applications.
"""

from typing import List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

from .output_adapter import OutputAdapter


class RichOutputAdapter(OutputAdapter):
    """
    Rich Console adapter for CLI mode.

    This adapter provides direct terminal output using Rich Console.
    All user interaction methods (confirm, choice, input) block execution
    until the user responds in the terminal.
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize Rich adapter.

        Args:
            console: Rich Console instance. Creates new one if None.
        """
        self.console = console or Console()

    def panel(self, content: str, title: str = "", border_style: str = "blue") -> None:
        """Display a panel using Rich Panel."""
        panel = Panel(content, title=title, border_style=border_style)
        self.console.print(panel)

    def table(self, headers: List[str], rows: List[List[str]], title: str = "") -> None:
        """Display a table using Rich Table."""
        table = Table(title=title, show_header=True, header_style="bold blue")

        # Add columns
        for header in headers:
            table.add_column(header)

        # Add rows
        for row in rows:
            table.add_row(*row)

        self.console.print(table)

    def text(self, content: str, style: str = "") -> None:
        """Display plain text."""
        if style:
            self.console.print(content, style=style)
        else:
            self.console.print(content)

    async def confirm(
        self,
        message: str,
        title: str = "Confirm",
        default: bool = False,
        ok_text: str = "Yes",
        cancel_text: str = "No",
    ) -> bool:
        """
        Display confirmation dialog (blocking).

        Shows a panel with the title and message, then uses Rich Confirm
        to wait for user input in the terminal.
        """
        # Show title panel if provided
        if title and title != "Confirm":
            self.panel(message, title=title, border_style="yellow")
            prompt_message = f"Continue? ({ok_text}/{cancel_text})"
        else:
            prompt_message = message

        try:
            return Confirm.ask(prompt_message, console=self.console, default=default)
        except KeyboardInterrupt:
            return False

    async def choice(
        self,
        message: str,
        choices: List[str],
        title: str = "Select",
        default_index: int = 0,
    ) -> int:
        """
        Display choice dialog (blocking).

        Shows numbered choices and waits for user to input a number.
        """
        # Show title if provided
        if title:
            self.console.print(f"[bold yellow]{title}[/bold yellow]")

        # Show message
        if message:
            self.console.print(message)
            self.console.print()

        # Show choices
        for i, choice in enumerate(choices):
            marker = "→" if i == default_index else " "
            self.console.print(f"  {marker} [{i+1}] {choice}")

        self.console.print()

        # Get user input
        while True:
            try:
                choice_input = Prompt.ask(
                    "Select number (or 'c' to cancel)",
                    console=self.console,
                    default=str(default_index + 1),
                )

                # Check for cancel
                if choice_input.lower() in ["c", "cancel", "q", "quit"]:
                    return -1

                # Try to parse as number
                index = int(choice_input) - 1
                if 0 <= index < len(choices):
                    return index

                self.console.print("[red]Invalid choice. Please try again.[/red]")

            except (ValueError, KeyboardInterrupt):
                return -1

    async def input(
        self,
        message: str,
        title: str = "Input",
        default: str = "",
        placeholder: str = "",
    ) -> Optional[str]:
        """
        Display input dialog (blocking).

        Uses Rich Prompt to get text input from user.
        """
        # Show title if provided
        if title:
            self.console.print(f"[bold blue]{title}[/bold blue]")

        # Combine message with placeholder if provided
        prompt_message = message
        if placeholder:
            prompt_message = f"{message} (e.g., {placeholder})"

        try:
            return Prompt.ask(prompt_message, console=self.console, default=default)
        except KeyboardInterrupt:
            return None

    def print(self, *args, **kwargs) -> None:
        """Generic print for compatibility."""
        self.console.print(*args, **kwargs)
