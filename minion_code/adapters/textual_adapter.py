#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual Output Adapter - TUI implementation

This adapter integrates with Textual TUI through a callback system.
It uses asyncio.Future to implement non-blocking user interactions,
allowing the TUI to display dialogs and return results asynchronously.
"""

from typing import List, Optional, Callable, Dict, Any
import asyncio
from dataclasses import dataclass

from .output_adapter import OutputAdapter


@dataclass
class PendingInteraction:
    """Represents a user interaction waiting for response"""
    type: str  # "confirm", "choice", "input"
    data: Dict[str, Any]
    future: asyncio.Future


class TextualOutputAdapter(OutputAdapter):
    """
    Textual TUI adapter for non-blocking user interaction.

    This adapter communicates with the TUI through a callback function.
    For user interactions (confirm, choice, input), it creates asyncio.Future
    objects and waits for the TUI to resolve them via resolve_interaction().

    Workflow:
    1. Command calls adapter.confirm()
    2. Adapter creates Future and calls on_output callback
    3. TUI displays dialog and waits for user action
    4. User clicks button → TUI calls adapter.resolve_interaction()
    5. Future completes, command continues
    """

    def __init__(self, on_output: Optional[Callable[[str, dict], None]] = None):
        """
        Initialize Textual adapter.

        Args:
            on_output: Callback function to send output to TUI.
                      Called with (output_type: str, data: dict)
                      Example: on_output("confirm", {"message": "...", ...})
        """
        self.on_output = on_output or self._default_output
        self._pending_interactions: Dict[str, PendingInteraction] = {}
        self._interaction_counter = 0

    def _default_output(self, output_type: str, data: dict):
        """Default output handler (prints to console for debugging)."""
        print(f"[TextualAdapter] {output_type}: {data}")

    def _generate_interaction_id(self) -> str:
        """Generate unique interaction ID."""
        self._interaction_counter += 1
        return f"interaction_{self._interaction_counter}"

    def panel(self, content: str, title: str = "", border_style: str = "blue") -> None:
        """Send panel output to TUI."""
        self.on_output("panel", {
            "content": content,
            "title": title,
            "border_style": border_style
        })

    def table(self, headers: List[str], rows: List[List[str]], title: str = "") -> None:
        """Send table output to TUI."""
        self.on_output("table", {
            "headers": headers,
            "rows": rows,
            "title": title
        })

    def text(self, content: str, style: str = "") -> None:
        """Send text output to TUI."""
        self.on_output("text", {
            "content": content,
            "style": style
        })

    async def confirm(self,
                     message: str,
                     title: str = "Confirm",
                     default: bool = False,
                     ok_text: str = "Yes",
                     cancel_text: str = "No") -> bool:
        """
        Request user confirmation (non-blocking).

        Creates a Future, sends notification to TUI, and waits for
        the TUI to call resolve_interaction() with the result.
        """
        interaction_id = self._generate_interaction_id()
        future = asyncio.Future()

        # Store pending interaction
        self._pending_interactions[interaction_id] = PendingInteraction(
            type="confirm",
            data={
                "message": message,
                "title": title,
                "default": default,
                "ok_text": ok_text,
                "cancel_text": cancel_text
            },
            future=future
        )

        # Notify TUI to display confirmation dialog
        self.on_output("confirm", {
            "interaction_id": interaction_id,
            "message": message,
            "title": title,
            "default": default,
            "ok_text": ok_text,
            "cancel_text": cancel_text
        })

        # Wait for TUI to resolve this interaction
        try:
            result = await future
            return result
        finally:
            # Clean up
            self._pending_interactions.pop(interaction_id, None)

    async def choice(self,
                    message: str,
                    choices: List[str],
                    title: str = "Select",
                    default_index: int = 0) -> int:
        """
        Request user choice selection (non-blocking).

        Returns the selected index (0-based), or -1 if cancelled.
        """
        interaction_id = self._generate_interaction_id()
        future = asyncio.Future()

        self._pending_interactions[interaction_id] = PendingInteraction(
            type="choice",
            data={
                "message": message,
                "choices": choices,
                "title": title,
                "default_index": default_index
            },
            future=future
        )

        self.on_output("choice", {
            "interaction_id": interaction_id,
            "message": message,
            "choices": choices,
            "title": title,
            "default_index": default_index
        })

        try:
            result = await future
            return result
        finally:
            self._pending_interactions.pop(interaction_id, None)

    async def input(self,
                   message: str,
                   title: str = "Input",
                   default: str = "",
                   placeholder: str = "") -> Optional[str]:
        """
        Request user text input (non-blocking).

        Returns the input string, or None if cancelled.
        """
        interaction_id = self._generate_interaction_id()
        future = asyncio.Future()

        self._pending_interactions[interaction_id] = PendingInteraction(
            type="input",
            data={
                "message": message,
                "title": title,
                "default": default,
                "placeholder": placeholder
            },
            future=future
        )

        self.on_output("input", {
            "interaction_id": interaction_id,
            "message": message,
            "title": title,
            "default": default,
            "placeholder": placeholder
        })

        try:
            result = await future
            return result
        finally:
            self._pending_interactions.pop(interaction_id, None)

    def resolve_interaction(self, interaction_id: str, result: Any):
        """
        Resolve a pending interaction with a result.

        This method should be called by the TUI when the user completes
        an interaction (clicks a button, enters text, etc.).

        Args:
            interaction_id: The interaction ID from the original request
            result: The user's response (bool for confirm, int for choice, str for input)
        """
        interaction = self._pending_interactions.get(interaction_id)
        if interaction and not interaction.future.done():
            interaction.future.set_result(result)

    def cancel_interaction(self, interaction_id: str):
        """
        Cancel a pending interaction.

        This should be called if the user cancels the dialog or it's
        dismissed without a response.

        Args:
            interaction_id: The interaction ID to cancel
        """
        interaction = self._pending_interactions.get(interaction_id)
        if interaction and not interaction.future.done():
            # Set appropriate default value based on interaction type
            if interaction.type == "confirm":
                interaction.future.set_result(False)
            elif interaction.type == "choice":
                interaction.future.set_result(-1)
            elif interaction.type == "input":
                interaction.future.set_result(None)

    def print(self, *args, **kwargs) -> None:
        """Generic print - converts to text output."""
        content = " ".join(str(arg) for arg in args)
        self.text(content)
