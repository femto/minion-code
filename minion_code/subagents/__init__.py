#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subagents system for MinionCode

Subagents are specialized agent configurations that can be invoked via the Task tool.
Each subagent has specific tools, system prompts, and use cases.

Subagent search paths (in priority order):
- builtin (code-defined)
- .claude/subagents or .minion/subagents (project-level, highest priority)
- ~/.claude/subagents or ~/.minion/subagents (user-level)
"""

from .subagent import SubagentConfig
from .subagent_registry import (
    SubagentRegistry,
    get_subagent_registry,
    reset_subagent_registry,
)
from .subagent_loader import SubagentLoader, load_subagents, get_available_subagents

__all__ = [
    "SubagentConfig",
    "SubagentRegistry",
    "get_subagent_registry",
    "reset_subagent_registry",
    "SubagentLoader",
    "load_subagents",
    "get_available_subagents",
]
