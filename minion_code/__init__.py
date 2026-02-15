#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minion Code Tools Package

A collection of tools and enhanced agents for the Minion framework including
file operations, system commands, web interactions, and specialized agents
with dynamic system prompts and state management.
"""

import sys

__version__ = "0.1.0"
__all__ = ["tools", "agents", "MinionCodeAgent", "create_minion_code_agent"]


def __getattr__(name):
    """Lazy import for heavy modules."""
    if name == "tools":
        from . import tools
        # Cache in module namespace to prevent repeated __getattr__ calls
        sys.modules[__name__].__dict__["tools"] = tools
        return tools
    elif name == "agents":
        from . import agents
        sys.modules[__name__].__dict__["agents"] = agents
        return agents
    elif name == "MinionCodeAgent":
        from .agents import MinionCodeAgent
        sys.modules[__name__].__dict__["MinionCodeAgent"] = MinionCodeAgent
        return MinionCodeAgent
    elif name == "create_minion_code_agent":
        from .agents import create_minion_code_agent
        sys.modules[__name__].__dict__["create_minion_code_agent"] = create_minion_code_agent
        return create_minion_code_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
