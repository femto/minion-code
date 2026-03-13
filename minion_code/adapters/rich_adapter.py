#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rich Output Adapter - CLI implementation."""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional
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

    def __init__(self, console: Optional[Console] = None, spinner_controller: Any = None):
        """
        Initialize Rich adapter.

        Args:
            console: Rich Console instance. Creates new one if None.
        """
        self.console = console or Console()
        self.spinner_controller = spinner_controller

    @contextmanager
    def _paused_spinner(self):
        """Pause any active spinner while waiting for terminal input."""
        if self.spinner_controller:
            self.spinner_controller.pause()
        try:
            yield
        finally:
            if self.spinner_controller:
                self.spinner_controller.resume()

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
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
        resource_args: Optional[dict] = None,
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
            with self._paused_spinner():
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
                with self._paused_spinner():
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
            with self._paused_spinner():
                return Prompt.ask(prompt_message, console=self.console, default=default)
        except KeyboardInterrupt:
            return None

    async def form(
        self,
        message: str,
        fields: List[Dict[str, Any]],
        title: str = "Form",
        submit_text: str = "Submit",
    ) -> Optional[Dict[str, Any]]:
        """Render a multi-question form in the console without fighting the spinner."""
        answers: Dict[str, Any] = {}
        if title:
            self.console.print(f"[bold blue]{title}[/bold blue]")
        if message:
            self.console.print(message)
        if fields:
            self.console.print()
            summary = Table(show_header=True, header_style="bold cyan")
            summary.add_column("#", width=4)
            summary.add_column("Field")
            summary.add_column("Type", width=10)
            summary.add_column("Default")
            for index, field in enumerate(fields, start=1):
                default = field.get("default")
                summary.add_row(
                    str(index),
                    str(field.get("label") or field.get("id") or f"field_{index}"),
                    str(field.get("type") or "text"),
                    "" if default is None else str(default),
                )
            self.console.print(summary)
            self.console.print()

        for index, field in enumerate(fields, start=1):
            field_id = str(field.get("id") or f"field_{index}")
            label = str(field.get("label") or field_id)
            field_type = str(field.get("type") or "text").lower()
            default = field.get("default")

            self.console.print(f"[bold cyan]{index}. {label}[/bold cyan]")

            if field_type == "choice":
                raw_options = field.get("options") or []
                options: List[str] = []
                option_values: List[str] = []
                for option in raw_options:
                    if isinstance(option, dict):
                        option_value = str(option.get("value", option.get("label", "")))
                        option_label = str(option.get("label", option_value))
                        option_values.append(option_value)
                        options.append(option_label)
                    else:
                        option_values.append(str(option))
                        options.append(str(option))
                if not options:
                    options = [str(default)] if default is not None else []
                    option_values = options[:]
                if not options:
                    return None

                default_index = 0
                if default is not None:
                    try:
                        default_index = options.index(str(default))
                    except ValueError:
                        default_index = 0

                selected_index = await self.choice(
                    message="Choose one option",
                    choices=options,
                    title="",
                    default_index=default_index,
                )
                if selected_index < 0:
                    return None
                answers[field_id] = option_values[selected_index]
            else:
                placeholder = str(field.get("placeholder") or "")
                value = await self.input(
                    message="Enter value",
                    title="",
                    default=str(default) if default is not None else "",
                    placeholder=placeholder,
                )
                if value is None:
                    return None
                if value == "" and default is not None:
                    value = str(default)
                answers[field_id] = value

            self.console.print()

        if submit_text:
            self.console.print(f"[dim]{submit_text} complete.[/dim]")
        return answers

    def print(self, *args, **kwargs) -> None:
        """Generic print for compatibility."""
        self.console.print(*args, **kwargs)
