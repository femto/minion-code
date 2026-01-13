#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in general-purpose subagent configuration."""

from ..subagent import SubagentConfig


def get_general_purpose_subagent() -> SubagentConfig:
    """Get the general-purpose subagent configuration."""
    return SubagentConfig(
        name="general-purpose",
        description="General-purpose agent for complex tasks requiring full tool access",
        when_to_use="For complex, multi-step tasks that need full tool capabilities including file editing, bash, and code execution",
        tools=["*"],
        system_prompt=None,  # Uses default system prompt
        model_name="inherit",
        location="builtin",
        readonly=False,
    )
