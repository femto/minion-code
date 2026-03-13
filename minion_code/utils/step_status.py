#!/usr/bin/env python3
"""Helpers for normalizing internal step labels into user-facing status text."""

from __future__ import annotations

import re


STEP_PATTERN = re.compile(
    r"^\s*step\s+\d+(?:\s*/\s*\d+)?(?:\s*[:\-]\s*|\s+)?(.*)$",
    re.IGNORECASE,
)


def humanize_step_status(content: str) -> str:
    """Strip synthetic step counters like 'Step 1/5' from UI-facing status text."""
    text = str(content or "").strip()
    if not text:
        return "Working"

    match = STEP_PATTERN.match(text)
    if not match:
        return text

    suffix = match.group(1).strip()
    if suffix:
        return suffix
    return "Working"
