#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in subagent configurations."""

from typing import List
from ..subagent import SubagentConfig

from .general_purpose import get_general_purpose_subagent
from .explore import get_explore_subagent
from .plan import get_plan_subagent
from .claude_code_guide import get_claude_code_guide_subagent


def get_all_builtin_subagents() -> List[SubagentConfig]:
    """Get all built-in subagent configurations."""
    return [
        get_general_purpose_subagent(),
        get_explore_subagent(),
        get_plan_subagent(),
        get_claude_code_guide_subagent(),
    ]


__all__ = [
    "get_all_builtin_subagents",
    "get_general_purpose_subagent",
    "get_explore_subagent",
    "get_plan_subagent",
    "get_claude_code_guide_subagent",
]
