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


DEFAULT_MODE_ID = "default"
PLAN_MODE_ID = "plan"


SESSION_MODE_SPECS = {
    DEFAULT_MODE_ID: SessionModeSpec(
        id=DEFAULT_MODE_ID,
        name="Default",
        description="Standard coding mode with the full toolset.",
        readonly_only=False,
        prompt_name="default",
    ),
    PLAN_MODE_ID: SessionModeSpec(
        id=PLAN_MODE_ID,
        name="Plan Mode",
        description="Read-only planning mode. Analyze, inspect, and propose changes without editing files or running mutating commands.",
        readonly_only=True,
        prompt_name="plan",
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
