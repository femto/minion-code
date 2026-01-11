#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP (Agent Client Protocol) integration for minion-code.

This module provides ACP server implementation allowing minion-code
to be used with ACP-compatible clients like Zed editor.
"""

from .agent import MinionACPAgent
from .hooks import create_acp_hooks, ACPToolHooks

__all__ = [
    "MinionACPAgent",
    "create_acp_hooks",
    "ACPToolHooks",
]
