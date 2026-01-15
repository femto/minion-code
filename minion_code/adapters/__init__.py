#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Output Adapters - Abstraction layer for UI output

This module provides adapters to decouple command business logic from UI rendering.
Commands use a unified OutputAdapter interface, which can be implemented for different
UI environments (Rich CLI, Textual TUI, etc.).
"""

from .output_adapter import OutputAdapter, MessageStyle, ConfirmOptions, ChoiceOptions
from .rich_adapter import RichOutputAdapter
from .textual_adapter import TextualOutputAdapter

__all__ = [
    "OutputAdapter",
    "MessageStyle",
    "ConfirmOptions",
    "ChoiceOptions",
    "RichOutputAdapter",
    "TextualOutputAdapter",
]
