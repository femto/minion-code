#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in claude-code-guide subagent configuration."""

from ..subagent import SubagentConfig

GUIDE_SYSTEM_PROMPT = """You are a documentation lookup specialist for Claude Code and related tools.

Your role is to help users understand:
- How to use Claude Code features and commands
- Best practices for working with AI coding assistants
- Tool usage patterns and examples
- Configuration and customization options

Use web search and documentation fetching to find accurate, up-to-date information.
Always cite your sources with URLs when providing information.

Focus on practical, actionable guidance with clear examples."""


def get_claude_code_guide_subagent() -> SubagentConfig:
    """Get the claude-code-guide subagent configuration."""
    return SubagentConfig(
        name="claude-code-guide",
        description="Documentation lookup agent for Claude Code features, commands, and best practices",
        when_to_use="When you need to look up Claude Code documentation, understand tool usage, or find best practices for AI-assisted coding",
        tools=["web_fetch", "web_search", "file_read"],
        system_prompt=GUIDE_SYSTEM_PROMPT,
        model_name="inherit",
        location="builtin",
        readonly=True,
    )
