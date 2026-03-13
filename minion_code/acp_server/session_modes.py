#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""ACP session mode definitions."""

from __future__ import annotations

from dataclasses import dataclass

from acp.schema import SessionMode, SessionModeState


@dataclass(frozen=True)
class SessionModeSpec:
    """Static configuration for an ACP session mode."""

    id: str
    name: str
    description: str
    readonly_only: bool = False
    prompt_name: str = "default"
    request_permission: bool = True
    include_dangerous_check: bool = True
    auto_allow_tools: tuple[str, ...] = ()


DEFAULT_MODE_ID = "default"
ACCEPT_EDITS_MODE_ID = "accept-edits"
PLAN_MODE_ID = "plan"
DONT_ASK_MODE_ID = "dont-ask"
BYPASS_PERMISSIONS_MODE_ID = "bypass-permissions"

EDIT_TOOL_NAMES = (
    "file_write",
    "file_edit",
    "multi_edit",
    "todo_write",
)

SESSION_MODE_SPECS = {
    DEFAULT_MODE_ID: SessionModeSpec(
        id=DEFAULT_MODE_ID,
        name="Default",
        description="Standard coding mode with the full toolset.",
        readonly_only=False,
        prompt_name="default",
        request_permission=True,
        include_dangerous_check=True,
    ),
    ACCEPT_EDITS_MODE_ID: SessionModeSpec(
        id=ACCEPT_EDITS_MODE_ID,
        name="Accept Edits",
        description="Auto-allow file editing tools, but still ask before running other mutating tools.",
        readonly_only=False,
        prompt_name="default",
        request_permission=True,
        include_dangerous_check=True,
        auto_allow_tools=EDIT_TOOL_NAMES,
    ),
    PLAN_MODE_ID: SessionModeSpec(
        id=PLAN_MODE_ID,
        name="Plan Mode",
        description="Read-only planning mode. Analyze, inspect, and propose changes without editing files or running mutating commands.",
        readonly_only=True,
        prompt_name="plan",
        request_permission=False,
        include_dangerous_check=False,
    ),
    DONT_ASK_MODE_ID: SessionModeSpec(
        id=DONT_ASK_MODE_ID,
        name="Don't Ask",
        description="Run without permission prompts, but still keep dangerous command checks enabled.",
        readonly_only=False,
        prompt_name="default",
        request_permission=False,
        include_dangerous_check=True,
    ),
    BYPASS_PERMISSIONS_MODE_ID: SessionModeSpec(
        id=BYPASS_PERMISSIONS_MODE_ID,
        name="Bypass Permissions",
        description="Disable permission prompts and dangerous command checks. Use only in fully trusted environments.",
        readonly_only=False,
        prompt_name="default",
        request_permission=False,
        include_dangerous_check=False,
    ),
}


def get_session_mode_spec(mode_id: str) -> SessionModeSpec:
    """Return the spec for a known mode ID."""
    try:
        return SESSION_MODE_SPECS[mode_id]
    except KeyError as exc:
        raise KeyError(f"Unknown session mode: {mode_id}") from exc


def build_session_mode_state(current_mode_id: str) -> SessionModeState:
    """Build ACP mode state for session creation responses."""
    return SessionModeState(
        availableModes=[
            SessionMode(
                id=spec.id,
                name=spec.name,
                description=spec.description,
            )
            for spec in SESSION_MODE_SPECS.values()
        ],
        currentModeId=current_mode_id,
    )
