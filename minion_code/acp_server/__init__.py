#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP (Agent Client Protocol) integration for minion-code.

This module provides ACP server implementation allowing minion-code
to be used with ACP-compatible clients like Zed editor.

Note: Imports are lazy to avoid circular import issues with the external 'acp' package.
Use: from minion_code.acp.agent import MinionACPAgent
"""

__all__ = [
    "MinionACPAgent",
    "create_acp_hooks",
    "ACPToolHooks",
]


def __getattr__(name):
    """Lazy imports to avoid circular import with external 'acp' package."""
    if name == "MinionACPAgent":
        from .agent import MinionACPAgent

        return MinionACPAgent
    elif name == "create_acp_hooks":
        from .hooks import create_acp_hooks

        return create_acp_hooks
    elif name == "ACPToolHooks":
        from .hooks import ACPToolHooks

        return ACPToolHooks
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
