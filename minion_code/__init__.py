#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minion Code Tools Package

A collection of tools and enhanced agents for the Minion framework including
file operations, system commands, web interactions, and specialized agents
with dynamic system prompts and state management.
"""

__version__ = "0.1.0"
__all__ = ["tools", "agents", "MinionCodeAgent", "create_minion_code_agent"]


def __getattr__(name):
    """Lazy import for heavy modules."""
    if name == "tools":
        from . import tools
        return tools
    elif name == "agents":
        from . import agents
        return agents
    elif name == "MinionCodeAgent":
        from .agents import MinionCodeAgent
        return MinionCodeAgent
    elif name == "create_minion_code_agent":
        from .agents import create_minion_code_agent
        return create_minion_code_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
