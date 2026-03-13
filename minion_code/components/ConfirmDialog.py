#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dialog Components for Textual TUI

These components provide user interaction dialogs for confirmation,
choice selection, and text input in the Textual TUI.
"""

from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Button, Static, Label, Input, Select
from textual.app import ComposeResult
from textual import on
from typing import Callable, Optional, List


class ConfirmDialog(Container):
    """
    Confirmation dialog component.

    Displays a message with Yes/No buttons and calls a callback
    with the user's choice.
    """

    DEFAULT_CSS = """
    ConfirmDialog {
        width: 60;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
        layer: overlay;
    }

    ConfirmDialog .dialog-title {
        text-style: bold;
        text-align: center;
        color: $warning;
        margin-bottom: 1;
    }

    ConfirmDialog .dialog-message {
        text-align: left;
        color: $text;
        margin-bottom: 2;
        padding: 1;
    }

    ConfirmDialog .dialog-buttons {
        height: 3;
        align: center middle;
    }

    ConfirmDialog Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        interaction_id: str,
        message: str,
        title: str = "Confirm",
        ok_text: str = "Yes",
        cancel_text: str = "No",
        on_result: Optional[Callable[[str, bool], None]] = None,
        **kwargs,
    ):
        """
        Initialize confirmation dialog.

        Args:
            interaction_id: Unique ID for this interaction
            message: Message to display
            title: Dialog title
            ok_text: Text for confirmation button
            cancel_text: Text for cancel button
            on_result: Callback function (interaction_id, result)
        """
        super().__init__(**kwargs)
        self.interaction_id = interaction_id
        self.message = message
        self.title = title
        self.ok_text = ok_text
        self.cancel_text = cancel_text
        self.on_result = on_result

    def compose(self) -> ComposeResult:
        """Compose the dialog UI."""
        with Vertical():
            yield Static(self.title, classes="dialog-title")
            yield Static(self.message, classes="dialog-message")
            with Horizontal(classes="dialog-buttons"):
                yield Button(self.ok_text, id="confirm_ok", variant="success")
                yield Button(self.cancel_text, id="confirm_cancel", variant="error")

    @on(Button.Pressed, "#confirm_ok")
    def on_ok(self):
        """Handle confirmation button click."""
        if self.on_result:
            self.on_result(self.interaction_id, True)
        self.remove()

    @on(Button.Pressed, "#confirm_cancel")
    def on_cancel(self):
        """Handle cancel button click."""
        if self.on_result:
            self.on_result(self.interaction_id, False)
        self.remove()


class ChoiceDialog(Container):
    """
    Choice selection dialog component.

    Displays a list of choices as buttons and calls a callback
    with the selected index. Supports keyboard navigation with
    arrow keys and number keys.
    """

    BINDINGS = [
        ("up", "move_up", "Previous"),
        ("down", "move_down", "Next"),
        ("k", "move_up", "Previous"),
        ("j", "move_down", "Next"),
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Select"),
    ]

    DEFAULT_CSS = """
    ChoiceDialog {
        width: 60;
        max-height: 80%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
        layer: overlay;
    }

    ChoiceDialog .dialog-title {
        text-style: bold;
        text-align: center;
        color: $accent;
        margin-bottom: 1;
    }

    ChoiceDialog .dialog-message {
        text-align: left;
        color: $text;
        margin-bottom: 1;
        padding: 1;
    }

    ChoiceDialog .dialog-hint {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }

    ChoiceDialog .choice-scroll {
        max-height: 50vh;
        min-height: 10;
        padding: 1;
        scrollbar-gutter: stable;
    }

    ChoiceDialog Button {
        width: 100%;
        margin: 0 0 1 0;
    }

    ChoiceDialog Button:focus {
        background: $accent;
    }

    ChoiceDialog .cancel-button {
        margin-top: 1;
    }
    """

    def __init__(
        self,
        interaction_id: str,
        message: str,
        choices: List[str],
        title: str = "Select",
        on_result: Optional[Callable[[str, int], None]] = None,
        **kwargs,
    ):
        """
        Initialize choice dialog.

        Args:
            interaction_id: Unique ID for this interaction
            message: Message to display
            choices: List of choice strings
            title: Dialog title
            on_result: Callback function (interaction_id, selected_index)
        """
        super().__init__(**kwargs)
        self.interaction_id = interaction_id
        self.message = message
        self.choices = choices
        self.title = title
        self.on_result = on_result
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """Compose the dialog UI."""
        with Vertical():
            yield Static(self.title, classes="dialog-title")
            if self.message:
                yield Static(self.message, classes="dialog-message")
            yield Static(
                "Use ↑↓/jk to navigate, Enter to select, Esc to cancel",
                classes="dialog-hint",
            )
            with VerticalScroll(classes="choice-scroll"):
                for i, choice in enumerate(self.choices):
                    yield Button(
                        f"{i+1}. {choice}", id=f"choice_{i}", variant="primary"
                    )
            yield Button(
                "Cancel", id="choice_cancel", variant="error", classes="cancel-button"
            )

    def on_mount(self):
        """Focus first button when dialog appears."""
        try:
            first_button = self.query_one("#choice_0", Button)
            first_button.focus()
        except Exception:
            pass

    def action_move_up(self):
        """Move focus to previous choice."""
        try:
            focused = self.app.focused
            if focused and focused.id and focused.id.startswith("choice_"):
                if focused.id == "choice_cancel":
                    # Move from cancel to last choice
                    last_btn = self.query_one(f"#choice_{len(self.choices)-1}", Button)
                    last_btn.focus()
                    self._scroll_to_button(last_btn)
                else:
                    idx = int(focused.id.split("_")[1])
                    if idx > 0:
                        prev_btn = self.query_one(f"#choice_{idx-1}", Button)
                        prev_btn.focus()
                        self._scroll_to_button(prev_btn)
        except Exception:
            pass

    def action_move_down(self):
        """Move focus to next choice."""
        try:
            focused = self.app.focused
            if focused and focused.id and focused.id.startswith("choice_"):
                idx = int(focused.id.split("_")[1])
                if idx < len(self.choices) - 1:
                    next_btn = self.query_one(f"#choice_{idx+1}", Button)
                    next_btn.focus()
                    self._scroll_to_button(next_btn)
                else:
                    # Move to cancel button
                    cancel_btn = self.query_one("#choice_cancel", Button)
                    cancel_btn.focus()
        except Exception:
            pass

    def _scroll_to_button(self, button: Button):
        """Scroll to make the button visible."""
        try:
            scroll_container = self.query_one(".choice-scroll", VerticalScroll)
            scroll_container.scroll_to_widget(button)
        except Exception:
            pass

    def action_select(self):
        """Select the currently focused choice."""
        try:
            focused = self.app.focused
            if focused and focused.id:
                focused.press()
        except Exception:
            pass

    def action_cancel(self):
        """Cancel the dialog."""
        if self.on_result:
            self.on_result(self.interaction_id, -1)
        self.remove()

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button click."""
        button_id = event.button.id

        if button_id == "choice_cancel":
            if self.on_result:
                self.on_result(self.interaction_id, -1)
        elif button_id and button_id.startswith("choice_"):
            try:
                choice_index = int(button_id.split("_")[1])
                if self.on_result:
                    self.on_result(self.interaction_id, choice_index)
            except (ValueError, IndexError):
                pass

        self.remove()


class InputDialog(Container):
    """
    Text input dialog component.

    Displays an input field and calls a callback with the entered text.
    """

    DEFAULT_CSS = """
    InputDialog {
        width: 60;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
        layer: overlay;
    }

    InputDialog .dialog-title {
        text-style: bold;
        text-align: center;
        color: $accent;
        margin-bottom: 1;
    }

    InputDialog .dialog-message {
        text-align: left;
        color: $text;
        margin-bottom: 1;
        padding: 1;
    }

    InputDialog Input {
        width: 100%;
        margin: 1 0;
    }

    InputDialog .dialog-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    InputDialog Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        interaction_id: str,
        message: str,
        title: str = "Input",
        default: str = "",
        placeholder: str = "",
        on_result: Optional[Callable[[str, Optional[str]], None]] = None,
        **kwargs,
    ):
        """
        Initialize input dialog.

        Args:
            interaction_id: Unique ID for this interaction
            message: Message to display
            title: Dialog title
            default: Default input value
            placeholder: Placeholder text
            on_result: Callback function (interaction_id, input_text or None)
        """
        super().__init__(**kwargs)
        self.interaction_id = interaction_id
        self.message = message
        self.title = title
        self.default = default
        self.placeholder = placeholder
        self.on_result = on_result

    def compose(self) -> ComposeResult:
        """Compose the dialog UI."""
        from textual.widgets import Input

        with Vertical():
            yield Static(self.title, classes="dialog-title")
            if self.message:
                yield Static(self.message, classes="dialog-message")
            yield Input(
                value=self.default, placeholder=self.placeholder, id="input_field"
            )
            with Horizontal(classes="dialog-buttons"):
                yield Button("OK", id="input_ok", variant="success")
                yield Button("Cancel", id="input_cancel", variant="error")

    def on_mount(self):
        """Focus the input field when dialog appears."""
        try:
            input_field = self.query_one("#input_field")
            input_field.focus()
        except:
            pass

    @on(Button.Pressed, "#input_ok")
    def on_ok(self):
        """Handle OK button click."""
        try:
            input_field = self.query_one("#input_field")
            value = input_field.value
            if self.on_result:
                self.on_result(self.interaction_id, value)
        except:
            if self.on_result:
                self.on_result(self.interaction_id, None)
        self.remove()

    @on(Button.Pressed, "#input_cancel")
    def on_cancel(self):
        """Handle cancel button click."""
        if self.on_result:
            self.on_result(self.interaction_id, None)
        self.remove()


class FormDialog(Container):
    """Multi-field form dialog for structured user input."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+enter", "submit", "Submit"),
    ]

    DEFAULT_CSS = """
    FormDialog {
        width: 72;
        max-height: 85%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
        layer: overlay;
    }

    FormDialog .dialog-title {
        text-style: bold;
        text-align: center;
        color: $accent;
        margin-bottom: 1;
    }

    FormDialog .dialog-message {
        text-align: left;
        color: $text;
        margin-bottom: 1;
        padding: 1;
    }

    FormDialog .form-scroll {
        max-height: 60vh;
        min-height: 12;
        padding-right: 1;
    }

    FormDialog .field-label {
        margin-top: 1;
        margin-bottom: 0;
        color: $text;
        text-style: bold;
    }

    FormDialog Input,
    FormDialog Select {
        width: 100%;
        margin: 0 0 1 0;
    }

    FormDialog .form-error {
        color: $error;
        margin-top: 1;
        min-height: 1;
    }

    FormDialog .dialog-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    FormDialog Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        interaction_id: str,
        message: str,
        fields: List[dict],
        title: str = "Form",
        submit_text: str = "Submit",
        on_result: Optional[Callable[[str, Optional[dict]], None]] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.interaction_id = interaction_id
        self.message = message
        self.fields = fields
        self.title = title
        self.submit_text = submit_text
        self.on_result = on_result

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.title, classes="dialog-title")
            if self.message:
                yield Static(self.message, classes="dialog-message")
            with VerticalScroll(classes="form-scroll"):
                for index, field in enumerate(self.fields):
                    label = str(field.get("label") or field.get("id") or f"Field {index + 1}")
                    if field.get("required", True):
                        label = f"{label} *"
                    yield Static(label, classes="field-label")

                    if field.get("type") == "choice":
                        options = field.get("options") or []
                        select_options = [
                            (str(option.get("label", option.get("value", ""))), str(option.get("value", option.get("label", ""))))
                            for option in options
                            if isinstance(option, dict)
                        ]
                        default_value = field.get("default")
                        if default_value is None and select_options:
                            default_value = select_options[0][1]
                        yield Select(
                            select_options,
                            value=default_value if default_value is not None else Select.BLANK,
                            allow_blank=not field.get("required", True),
                            prompt=str(field.get("placeholder") or "Select an option"),
                            id=f"form_field_{index}",
                        )
                    else:
                        yield Input(
                            value=str(field.get("default") or ""),
                            placeholder=str(field.get("placeholder") or ""),
                            id=f"form_field_{index}",
                        )
            yield Static("", id="form_error", classes="form-error")
            with Horizontal(classes="dialog-buttons"):
                yield Button(self.submit_text, id="form_submit", variant="success")
                yield Button("Cancel", id="form_cancel", variant="error")

    def on_mount(self):
        try:
            first_widget = self.query_one("#form_field_0")
            first_widget.focus()
        except Exception:
            pass

    @on(Button.Pressed, "#form_submit")
    def on_submit_button(self):
        self._submit_form()

    @on(Input.Submitted)
    def on_input_submitted(self):
        self._submit_form()

    def action_submit(self):
        """Submit the form from a keyboard shortcut."""
        self._submit_form()

    def action_cancel(self):
        """Cancel the form from a keyboard shortcut."""
        self._cancel_form()

    def _submit_form(self):
        answers = {}
        for index, field in enumerate(self.fields):
            widget = self.query_one(f"#form_field_{index}")
            field_id = str(field.get("id") or f"field_{index}")
            required = bool(field.get("required", True))

            if field.get("type") == "choice":
                value = getattr(widget, "value", Select.BLANK)
                if value == Select.BLANK:
                    value = None
            else:
                value = getattr(widget, "value", "")
                if isinstance(value, str):
                    value = value.strip()

            if required and (value is None or value == ""):
                self._set_error(
                    f"Please fill out {field.get('label') or field_id} before submitting."
                )
                try:
                    widget.focus()
                except Exception:
                    pass
                return

            answers[field_id] = value

        if self.on_result:
            self.on_result(self.interaction_id, answers)
        self.remove()

    @on(Button.Pressed, "#form_cancel")
    def on_cancel(self):
        self._cancel_form()

    def _cancel_form(self):
        if self.on_result:
            self.on_result(self.interaction_id, None)
        self.remove()

    def _set_error(self, message: str) -> None:
        try:
            error_widget = self.query_one("#form_error", Static)
            error_widget.update(message)
        except Exception:
            pass
