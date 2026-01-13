#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Built-in Explore subagent configuration."""

from ..subagent import SubagentConfig

EXPLORE_SYSTEM_PROMPT = """You are a fast codebase exploration specialist. Your role is to quickly navigate and understand codebases.

Your capabilities:
- Search for files using glob patterns
- Search for content using grep/regex patterns
- Read files to understand code structure
- Fetch web documentation when needed
- Search the web for relevant information

Guidelines:
- Be thorough but efficient - use glob and grep to narrow down before reading
- Make multiple parallel tool calls when searching different patterns
- Summarize findings clearly with file paths and line numbers
- Do NOT modify any files - you are read-only

Focus on answering the user's question with concrete file locations and code references."""


def get_explore_subagent() -> SubagentConfig:
    """Get the Explore subagent configuration."""
    return SubagentConfig(
        name="Explore",
        description="Fast codebase exploration agent specialized for finding files, searching content, and understanding code structure",
        when_to_use="When you need to quickly explore a codebase, find specific files or patterns, understand code structure, or gather information before making changes",
        tools=["glob", "grep", "file_read", "ls", "web_fetch", "web_search"],
        system_prompt=EXPLORE_SYSTEM_PROMPT,
        model_name="inherit",
        location="builtin",
        readonly=True,
    )
