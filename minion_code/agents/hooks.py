#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook system for MinionCodeAgent.

Re-exports base hooks from minion framework and provides
minion-code specific hook implementations.
"""

import logging
from typing import Any, Dict, List, Optional, Union, Callable, Set

# Re-export base types from minion framework
from minion.main.tool_hooks import (
    PermissionDecision,
    PreToolUseResult,
    PostToolUseResult,
    ToolCallInfo,
    PreToolUseHook,
    PostToolUseHook,
    HookMatcher,
    PostHookMatcher,
    HookConfig,
    ToolHooks,
    NoOpToolHooks,
    HookedTool,
    wrap_tools_with_hooks,
    create_auto_accept_hook,
    create_auto_deny_hook,
    create_dangerous_command_check_hook,
    create_logging_hook,
)

logger = logging.getLogger(__name__)


# ============================================================================
# minion-code Specific Hook Implementations
# ============================================================================

def _format_tool_input(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Format tool input for display in confirmation dialog."""
    if tool_name == "bash":
        return f"Command: {tool_input.get('command', '')}"

    if tool_name in ("file_write", "file_edit"):
        path = tool_input.get("file_path", tool_input.get("path", ""))
        return f"File: {path}"

    if tool_name == "file_read":
        return f"File: {tool_input.get('file_path', '')}"

    # Default: show all parameters
    parts = []
    for key, value in tool_input.items():
        if isinstance(value, str) and len(value) > 100:
            value = value[:100] + "..."
        parts.append(f"{key}: {value}")

    return "\n".join(parts) if parts else "(no parameters)"


def create_confirm_writes_hook(
    adapter: Any,  # OutputAdapter
    tools_registry: Optional[Dict[str, Any]] = None,
    skip_readonly: bool = True
) -> PreToolUseHook:
    """
    Create a hook that requests user confirmation for non-readonly tools.

    Args:
        adapter: OutputAdapter instance with confirm() method
        tools_registry: Optional dict mapping tool names to tool instances
        skip_readonly: If True, auto-accept readonly tools without confirmation
    """
    async def confirm_writes(tool_name: str, tool_input: Dict[str, Any], tool_use_id: str) -> PreToolUseResult:
        # Check if tool is readonly
        if skip_readonly and tools_registry:
            tool = tools_registry.get(tool_name)
            if tool and getattr(tool, 'readonly', False):
                return PreToolUseResult(decision=PermissionDecision.ACCEPT)

        # Known readonly tools (fallback if no registry)
        if skip_readonly:
            readonly_tools = {"file_read", "glob", "grep", "ls", "web_fetch", "web_search", "todo_read"}
            if tool_name in readonly_tools:
                return PreToolUseResult(decision=PermissionDecision.ACCEPT)

        # Format tool input for display
        input_summary = _format_tool_input(tool_name, tool_input)

        # Request confirmation
        try:
            confirmed = await adapter.confirm(
                message=f"Allow {tool_name}?\n{input_summary}",
                title="Tool Permission",
                resource_type="tool",
                resource_name=tool_name,
                resource_args=tool_input
            )
        except Exception as e:
            logger.error(f"Error during confirmation: {e}")
            return PreToolUseResult(
                decision=PermissionDecision.DENY,
                reason=f"Confirmation error: {e}"
            )

        if confirmed:
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)
        else:
            return PreToolUseResult(
                decision=PermissionDecision.DENY,
                reason="User denied permission"
            )

    return confirm_writes


def create_cli_confirm_hook(
    allowed_tools: Optional[Set[str]] = None,
    session_allowed: Optional[Set[str]] = None,
) -> PreToolUseHook:
    """
    Create a hook that prompts for confirmation in CLI/terminal.

    Args:
        allowed_tools: Set of tool names that are always allowed (persistent)
        session_allowed: Set of tool names allowed for this session only
    """
    if allowed_tools is None:
        allowed_tools = set()
    if session_allowed is None:
        session_allowed = set()

    readonly_tools = {"file_read", "glob", "grep", "ls", "web_fetch", "web_search", "todo_read"}

    async def cli_confirm(tool_name: str, tool_input: Dict[str, Any], tool_use_id: str) -> PreToolUseResult:
        if tool_name in readonly_tools:
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)

        if tool_name in allowed_tools or tool_name in session_allowed:
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)

        input_summary = _format_tool_input(tool_name, tool_input)

        print(f"\n{'='*60}")
        print(f"🔧 Tool: {tool_name}")
        print(f"{'='*60}")
        print(input_summary)
        print(f"{'='*60}")
        print("Options:")
        print("  [y] Yes, allow this once")
        print("  [n] No, deny")
        print("  [a] Always allow this tool (session)")
        print("  [A] Always allow this tool (permanent)")

        try:
            response = input("Allow? [y/n/a/A]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return PreToolUseResult(
                decision=PermissionDecision.DENY,
                reason="User cancelled"
            )

        if response == 'y':
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)
        elif response == 'a':
            session_allowed.add(tool_name)
            logger.info(f"Tool '{tool_name}' allowed for this session")
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)
        elif response == 'A':
            allowed_tools.add(tool_name)
            logger.info(f"Tool '{tool_name}' permanently allowed")
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)
        else:
            return PreToolUseResult(
                decision=PermissionDecision.DENY,
                reason="User denied permission"
            )

    return cli_confirm


def create_cli_hooks(auto_accept: bool = False) -> HookConfig:
    """
    Create hook configuration for CLI usage.

    Args:
        auto_accept: If True, auto-accept all tools (no confirmation prompts)
    """
    if auto_accept:
        return create_autonomous_hooks()

    return HookConfig(
        pre_tool_use=[
            HookMatcher("bash", create_dangerous_command_check_hook()),
            HookMatcher("*", create_cli_confirm_hook()),
        ]
    )


def create_default_hooks(adapter: Any) -> HookConfig:
    """
    Create default hook configuration with:
    - Dangerous command blocking for bash
    - User confirmation for write operations
    """
    return HookConfig(
        pre_tool_use=[
            HookMatcher("bash", create_dangerous_command_check_hook()),
            HookMatcher("*", create_confirm_writes_hook(adapter)),
        ]
    )


def create_autonomous_hooks() -> HookConfig:
    """
    Create hook configuration for autonomous/unattended mode.
    Blocks dangerous commands but auto-accepts everything else.
    """
    return HookConfig(
        pre_tool_use=[
            HookMatcher("bash", create_dangerous_command_check_hook()),
            HookMatcher("*", create_auto_accept_hook()),
        ]
    )


__all__ = [
    # Re-exported from minion.main.tool_hooks
    "PermissionDecision",
    "PreToolUseResult",
    "PostToolUseResult",
    "ToolCallInfo",
    "PreToolUseHook",
    "PostToolUseHook",
    "HookMatcher",
    "PostHookMatcher",
    "HookConfig",
    "ToolHooks",
    "NoOpToolHooks",
    "HookedTool",
    "wrap_tools_with_hooks",
    "create_auto_accept_hook",
    "create_auto_deny_hook",
    "create_dangerous_command_check_hook",
    "create_logging_hook",
    # minion-code specific
    "create_confirm_writes_hook",
    "create_cli_confirm_hook",
    "create_cli_hooks",
    "create_default_hooks",
    "create_autonomous_hooks",
]
