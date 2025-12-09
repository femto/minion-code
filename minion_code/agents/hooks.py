#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook system for MinionCodeAgent.

Provides pre/post tool execution hooks for permission control and customization.
Inspired by claude-agent-sdk's hook architecture.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)
import fnmatch
import logging

logger = logging.getLogger(__name__)


class PermissionDecision(Enum):
    """Decision from a permission hook."""
    ACCEPT = "accept"
    DENY = "deny"


@dataclass
class PreToolUseResult:
    """Result from a PreToolUse hook."""
    decision: PermissionDecision
    reason: Optional[str] = None
    modified_input: Optional[Dict[str, Any]] = None  # Optional: modify tool input


# Type alias for hook functions
# (tool_name, tool_input, tool_use_id) -> PreToolUseResult
PreToolUseHook = Callable[
    [str, Dict[str, Any], str],
    Awaitable[PreToolUseResult]
]


@dataclass
class HookMatcher:
    """
    Matcher for determining which tools trigger a hook.

    Args:
        matcher: Tool name pattern(s) or callable predicate
            - "*" matches all tools
            - "bash" matches only bash tool
            - ["bash", "file_*"] matches bash and file_read, file_write, etc.
            - callable: (tool_name) -> bool
        hook: The hook function to call when matched
    """
    matcher: Union[str, List[str], Callable[[str], bool]]
    hook: PreToolUseHook

    def matches(self, tool_name: str) -> bool:
        """Check if this matcher matches the given tool name."""
        if callable(self.matcher):
            return self.matcher(tool_name)

        patterns = [self.matcher] if isinstance(self.matcher, str) else self.matcher

        for pattern in patterns:
            if pattern == "*":
                return True
            if fnmatch.fnmatch(tool_name, pattern):
                return True

        return False


@dataclass
class HookConfig:
    """
    Configuration for agent hooks.

    Example:
        config = HookConfig(
            pre_tool_use=[
                HookMatcher("bash", check_dangerous_commands),
                HookMatcher("*", confirm_writes),
            ]
        )
    """
    pre_tool_use: List[HookMatcher] = field(default_factory=list)

    def add_pre_tool_use(
        self,
        matcher: Union[str, List[str], Callable[[str], bool]],
        hook: PreToolUseHook
    ) -> "HookConfig":
        """Add a pre-tool-use hook. Returns self for chaining."""
        self.pre_tool_use.append(HookMatcher(matcher=matcher, hook=hook))
        return self


# ============================================================================
# Built-in Hook Implementations
# ============================================================================

def create_auto_accept_hook() -> PreToolUseHook:
    """
    Create a hook that auto-accepts all tool calls.
    Useful for unattended/autonomous mode.
    """
    async def auto_accept(tool_name: str, tool_input: Dict[str, Any], tool_use_id: str) -> PreToolUseResult:
        return PreToolUseResult(decision=PermissionDecision.ACCEPT)

    return auto_accept


def create_auto_deny_hook(reason: str = "Tool execution blocked") -> PreToolUseHook:
    """
    Create a hook that denies all tool calls.
    Useful for testing or sandboxed environments.
    """
    async def auto_deny(tool_name: str, tool_input: Dict[str, Any], tool_use_id: str) -> PreToolUseResult:
        return PreToolUseResult(decision=PermissionDecision.DENY, reason=reason)

    return auto_deny


def create_dangerous_command_check_hook(
    dangerous_patterns: Optional[List[str]] = None
) -> PreToolUseHook:
    """
    Create a hook that blocks dangerous bash commands.

    Args:
        dangerous_patterns: List of dangerous command patterns to block.
            Defaults to common destructive commands.
    """
    if dangerous_patterns is None:
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf *",
            "sudo rm",
            "mkfs",
            "dd if=",
            ":(){:|:&};:",  # fork bomb
            "> /dev/sd",
            "chmod -R 777 /",
        ]

    async def check_dangerous(tool_name: str, tool_input: Dict[str, Any], tool_use_id: str) -> PreToolUseResult:
        if tool_name != "bash":
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)

        command = tool_input.get("command", "")

        for pattern in dangerous_patterns:
            if pattern.lower() in command.lower():
                logger.warning(f"Blocked dangerous command: {command}")
                return PreToolUseResult(
                    decision=PermissionDecision.DENY,
                    reason=f"Dangerous command pattern detected: {pattern}"
                )

        return PreToolUseResult(decision=PermissionDecision.ACCEPT)

    return check_dangerous


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
            (used to check readonly property)
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
            # Default to deny on error
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


def create_cli_confirm_hook(
    allowed_tools: Optional[set] = None,
    session_allowed: Optional[set] = None,
) -> PreToolUseHook:
    """
    Create a hook that prompts for confirmation in CLI/terminal.

    Args:
        allowed_tools: Set of tool names that are always allowed (persistent)
        session_allowed: Set of tool names allowed for this session only

    Returns:
        PreToolUseHook for CLI confirmation
    """
    # Initialize mutable defaults
    if allowed_tools is None:
        allowed_tools = set()
    if session_allowed is None:
        session_allowed = set()

    # Known readonly tools (auto-accept)
    readonly_tools = {"file_read", "glob", "grep", "ls", "web_fetch", "web_search", "todo_read"}

    async def cli_confirm(tool_name: str, tool_input: Dict[str, Any], tool_use_id: str) -> PreToolUseResult:
        # Auto-accept readonly tools
        if tool_name in readonly_tools:
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)

        # Check if already allowed
        if tool_name in allowed_tools or tool_name in session_allowed:
            return PreToolUseResult(decision=PermissionDecision.ACCEPT)

        # Format tool info for display
        input_summary = _format_tool_input(tool_name, tool_input)

        # Print confirmation prompt
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

    Returns:
        HookConfig for CLI
    """
    if auto_accept:
        return create_autonomous_hooks()

    return HookConfig(
        pre_tool_use=[
            HookMatcher("bash", create_dangerous_command_check_hook()),
            HookMatcher("*", create_cli_confirm_hook()),
        ]
    )


# ============================================================================
# Convenience Functions
# ============================================================================

def create_default_hooks(adapter: Any) -> HookConfig:
    """
    Create default hook configuration with:
    - Dangerous command blocking for bash
    - User confirmation for write operations

    Args:
        adapter: OutputAdapter instance

    Returns:
        HookConfig with sensible defaults
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

    Returns:
        HookConfig for autonomous operation
    """
    return HookConfig(
        pre_tool_use=[
            HookMatcher("bash", create_dangerous_command_check_hook()),
            HookMatcher("*", create_auto_accept_hook()),
        ]
    )


# ============================================================================
# Tool Wrapper for Hook Integration
# ============================================================================

class HookedTool:
    """
    Wrapper that adds pre-tool-use hooks to any tool.

    This wrapper intercepts tool calls and runs configured hooks before
    executing the actual tool. This approach works with any agent framework
    that uses BaseTool-compatible tools.

    Example:
        tool = FileWriteTool()
        hooked = HookedTool(tool, hooks, tools_registry)
        result = hooked.forward(file_path="test.txt", content="hello")
    """

    def __init__(
        self,
        tool: Any,
        hooks: HookConfig,
        tools_registry: Optional[Dict[str, Any]] = None,
        tool_use_id_generator: Optional[Callable[[], str]] = None,
    ):
        """
        Args:
            tool: The actual tool to wrap
            hooks: HookConfig containing pre_tool_use hooks
            tools_registry: Optional dict mapping tool names to instances
            tool_use_id_generator: Optional function to generate tool use IDs
        """
        self._tool = tool
        self._hooks = hooks
        self._tools_registry = tools_registry or {}
        self._id_generator = tool_use_id_generator or self._default_id_generator
        self._call_counter = 0

        # Copy tool metadata
        self.name = getattr(tool, 'name', type(tool).__name__)
        self.description = getattr(tool, 'description', '')
        self.inputs = getattr(tool, 'inputs', {})
        self.output_type = getattr(tool, 'output_type', 'string')
        self.readonly = getattr(tool, 'readonly', None)
        self.needs_state = getattr(tool, 'needs_state', False)

    def _default_id_generator(self) -> str:
        """Generate a unique tool use ID."""
        import time
        self._call_counter += 1
        return f"tool_{self.name}_{int(time.time() * 1000)}_{self._call_counter}"

    async def _run_pre_hooks(self, tool_input: Dict[str, Any], tool_use_id: str) -> PreToolUseResult:
        """Run all matching pre-tool-use hooks."""
        for matcher in self._hooks.pre_tool_use:
            if matcher.matches(self.name):
                try:
                    result = await matcher.hook(self.name, tool_input, tool_use_id)

                    if result.decision == PermissionDecision.DENY:
                        logger.info(f"Hook denied tool {self.name}: {result.reason}")
                        return result

                    # Apply modified input if provided
                    if result.modified_input:
                        tool_input.update(result.modified_input)

                except Exception as e:
                    logger.error(f"Hook error for {self.name}: {e}")
                    # Default to deny on hook error for safety
                    return PreToolUseResult(
                        decision=PermissionDecision.DENY,
                        reason=f"Hook error: {e}"
                    )

        return PreToolUseResult(decision=PermissionDecision.ACCEPT)

    def forward(self, *args, **kwargs) -> Any:
        """
        Execute the tool with hook checks.

        This method is synchronous but internally handles async hooks.
        If running in an async context, use forward_async() instead.
        """
        import asyncio

        # Try to get or create event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context - need to use create_task or similar
            # For simplicity, we'll use a nested event loop via asyncio.run_coroutine_threadsafe
            # But this can be problematic. Better to use forward_async directly.

            # Workaround: use nest_asyncio if available, or just run sync
            try:
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.get_event_loop().run_until_complete(
                    self.forward_async(*args, **kwargs)
                )
            except ImportError:
                # Fall back to sync hook check (limited)
                return self._forward_sync(*args, **kwargs)
        except RuntimeError:
            # No running loop - we can create one
            return asyncio.run(self.forward_async(*args, **kwargs))

    async def forward_async(self, *args, **kwargs) -> Any:
        """
        Execute the tool with async hook checks.
        """
        tool_use_id = self._id_generator()
        tool_input = kwargs.copy()

        # Add positional args to input if any
        if args:
            # Try to map positional args to input names
            input_names = list(self.inputs.keys())
            for i, arg in enumerate(args):
                if i < len(input_names):
                    tool_input[input_names[i]] = arg

        # Run pre-hooks
        hook_result = await self._run_pre_hooks(tool_input, tool_use_id)

        if hook_result.decision == PermissionDecision.DENY:
            return f"Permission denied: {hook_result.reason or 'Tool execution blocked'}"

        # Apply any modified input
        if hook_result.modified_input:
            kwargs.update(hook_result.modified_input)

        # Execute actual tool
        return self._tool.forward(*args, **kwargs)

    def _forward_sync(self, *args, **kwargs) -> Any:
        """
        Synchronous forward when async is not available.
        Note: Hooks that require async (like confirm) won't work here.
        """
        logger.warning(f"Running {self.name} without async hook support")
        return self._tool.forward(*args, **kwargs)

    def __call__(self, *args, **kwargs) -> Any:
        """Make the wrapper callable like the original tool."""
        return self.forward(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the wrapped tool."""
        return getattr(self._tool, name)

    def format_for_observation(self, output: Any) -> str:
        """Delegate format_for_observation to wrapped tool."""
        if hasattr(self._tool, 'format_for_observation'):
            return self._tool.format_for_observation(output)
        return str(output)


def wrap_tools_with_hooks(
    tools: List[Any],
    hooks: HookConfig,
) -> List[HookedTool]:
    """
    Wrap a list of tools with hook support.

    Args:
        tools: List of tool instances
        hooks: HookConfig with pre_tool_use hooks

    Returns:
        List of HookedTool wrappers
    """
    # Build tools registry
    tools_registry = {
        getattr(t, 'name', type(t).__name__): t
        for t in tools
    }

    return [
        HookedTool(tool, hooks, tools_registry)
        for tool in tools
    ]
