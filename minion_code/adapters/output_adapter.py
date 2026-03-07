#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Output Adapter - Abstract interface for UI output

This module defines the abstract interface that all output adapters must implement.
It provides a unified API for commands to output content and request user interaction,
regardless of the underlying UI system (CLI, TUI, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass


class MessageStyle(Enum):
    """Message style types"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ConfirmOptions:
    """Options for confirmation dialog"""

    message: str
    title: str = "Confirm"
    default: bool = False
    ok_text: str = "Yes"
    cancel_text: str = "No"
    style: MessageStyle = MessageStyle.WARNING


@dataclass
class ChoiceOptions:
    """Options for choice dialog"""

    message: str
    choices: List[str]
    title: str = "Select"
    default_index: int = 0


class OutputAdapter(ABC):
    """
    Abstract output adapter interface.

    This interface defines methods for:
    1. Basic output (panel, table, text)
    2. User interaction (confirm, choice, input)

    All methods that request user interaction are async to support
    both blocking (CLI) and non-blocking (TUI) implementations.
    """

    @abstractmethod
    def panel(self, content: str, title: str = "", border_style: str = "blue") -> None:
        """
        Display a panel with content.

        Args:
            content: Panel content text
            title: Panel title
            border_style: Border color/style
        """
        pass

    @abstractmethod
    def table(self, headers: List[str], rows: List[List[str]], title: str = "") -> None:
        """
        Display a table.

        Args:
            headers: Column headers
            rows: Table rows
            title: Table title
        """
        pass

    @abstractmethod
    def text(self, content: str, style: str = "") -> None:
        """
        Display plain text.

        Args:
            content: Text content
            style: Text style/color
        """
        pass

    def info(self, content: str) -> None:
        """
        Display info message.

        Args:
            content: Message content
        """
        self.text(f"[blue]ℹ {content}[/blue]")

    def success(self, content: str) -> None:
        """
        Display success message.

        Args:
            content: Message content
        """
        self.text(f"[green]✓ {content}[/green]")

    def warning(self, content: str) -> None:
        """
        Display warning message.

        Args:
            content: Message content
        """
        self.text(f"[yellow]⚠ {content}[/yellow]")

    def error(self, content: str) -> None:
        """
        Display error message.

        Args:
            content: Message content
        """
        self.text(f"[red]✗ {content}[/red]")

    @abstractmethod
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
        Display a confirmation dialog and wait for user response.

        Args:
            message: Confirmation message
            title: Dialog title
            default: Default choice
            ok_text: Text for confirmation button
            cancel_text: Text for cancel button
            resource_type: Optional resource category for richer UIs
            resource_name: Optional resource identifier for richer UIs
            resource_args: Optional structured arguments for richer UIs

        Returns:
            True if user confirmed, False if cancelled
        """
        pass

    @abstractmethod
    async def choice(
        self,
        message: str,
        choices: List[str],
        title: str = "Select",
        default_index: int = 0,
    ) -> int:
        """
        Display a choice dialog and wait for user selection.

        Args:
            message: Choice prompt message
            choices: List of choices
            title: Dialog title
            default_index: Default selection index

        Returns:
            Selected index (0-based), or -1 if cancelled
        """
        pass

    @abstractmethod
    async def input(
        self,
        message: str,
        title: str = "Input",
        default: str = "",
        placeholder: str = "",
    ) -> Optional[str]:
        """
        Display an input dialog and wait for user input.

        Args:
            message: Input prompt message
            title: Dialog title
            default: Default value
            placeholder: Placeholder text

        Returns:
            User input string, or None if cancelled
        """
        pass

    async def form(
        self,
        message: str,
        fields: List[Dict[str, Any]],
        title: str = "Form",
        submit_text: str = "Submit",
    ) -> Optional[Dict[str, Any]]:
        """
        Request structured form input.

        Default implementation falls back to sequential `choice` / `input` prompts,
        so richer UIs can override this and render the form in one shot.
        """
        del submit_text  # May be used by richer adapters

        answers: Dict[str, Any] = {}
        for index, field in enumerate(fields):
            field_id = str(field.get("id") or f"field_{index}")
            label = str(field.get("label") or field_id)
            field_type = str(field.get("type") or "text").lower()
            default = field.get("default")

            if field_type == "choice":
                raw_options = field.get("options") or []
                options: List[str] = []
                for option in raw_options:
                    if isinstance(option, dict):
                        options.append(str(option.get("label", option.get("value", ""))))
                    else:
                        options.append(str(option))

                if not options:
                    options = [str(default)] if default is not None else []
                if not options:
                    return None

                default_index = 0
                if default is not None:
                    try:
                        default_index = options.index(str(default))
                    except ValueError:
                        default_index = 0

                selected_index = await self.choice(
                    message=f"{message}\n\n{label}" if message else label,
                    choices=options,
                    title=title,
                    default_index=default_index,
                )
                if selected_index < 0:
                    return None
                answers[field_id] = options[selected_index]
                continue

            placeholder = str(field.get("placeholder") or "")
            value = await self.input(
                message=f"{message}\n\n{label}" if message else label,
                title=title,
                default=str(default) if default is not None else "",
                placeholder=placeholder,
            )
            if value is None:
                return None
            if value == "" and default is not None:
                value = str(default)
            answers[field_id] = value

        return answers

    @abstractmethod
    def print(self, *args, **kwargs) -> None:
        """
        Generic print method for compatibility.

        This method provides a fallback for any console.print() calls
        that haven't been converted to the specific adapter methods.
        """
        pass
