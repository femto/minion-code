#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP-specific hooks for tool execution notifications.

These hooks integrate with the ACP protocol to send session_update
notifications when tools are called.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from acp import Client
from acp.schema import (
    ToolCallStart,
    ToolCallProgress,
    ToolCallUpdate,
    PermissionOption,
    TextContentBlock,
    ContentToolCallContent,
)

from ..agents.hooks import (
    HookConfig,
    PreToolUseResult,
    PostToolUseResult,
    PermissionDecision,
)
from .permissions import PermissionStore

logger = logging.getLogger(__name__)


# Map tool names to ToolKind
TOOL_KIND_MAP = {
    "file_read": "read",
    "file_write": "edit",
    "file_edit": "edit",
    "glob": "search",
    "grep": "search",
    "bash": "execute",
    "python_interpreter": "execute",
    "web_fetch": "fetch",
    "web_search": "search",
    "think": "think",
}

# Tools that are safe and don't need permission
# These are read-only, internal, or non-destructive operations
SAFE_TOOLS = {
    # Read-only tools
    # "file_read",
    # "glob",
    # "grep",
    # "ls",
    # "todo_read",
    # Internal/non-destructive tools
    "think",
    "final_answer",
    "user_input",
    # Note: file_write, file_edit, bash, python_interpreter are NOT safe
}


def get_tool_kind(tool_name: str) -> str:
    """Get the ACP ToolKind for a tool name."""
    return TOOL_KIND_MAP.get(tool_name, "other")


@dataclass
class ACPToolHooks:
    """
    ACP-specific tool hooks that send session_update notifications.

    This class creates pre/post tool use hooks that:
    1. pre_tool_use: Sends ToolCallStart notification (status="in_progress")
    2. post_tool_use: Sends ToolCallProgress update (status="completed"/"failed")
    """

    client: Client
    session_id: str
    request_permission: bool = False  # Whether to request permission via ACP
    permission_store: Optional[PermissionStore] = None  # Persistent permission storage
    _tool_call_ids: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def _generate_tool_call_id() -> str:
        """Generate a unique tool call ID."""
        return str(uuid.uuid4())

    async def pre_tool_use(
        self, tool_name: str, tool_input: Dict[str, Any], tool_use_id: str
    ) -> PreToolUseResult:
        """
        Pre-tool-use hook that sends ToolCallStart notification.

        Sends a session_update with ToolCallStart to notify the ACP client
        that a tool is about to be executed.
        """
        # Generate and store tool call ID
        tool_call_id = self._generate_tool_call_id()
        self._tool_call_ids[tool_use_id] = tool_call_id

        # Check if this tool needs permission
        needs_permission = self.request_permission and tool_name not in SAFE_TOOLS

        if tool_name in SAFE_TOOLS:
            logger.debug(f"Tool {tool_name} is safe, skipping permission request")

        # Check persistent permissions first
        if needs_permission and self.permission_store:
            stored_permission = self.permission_store.is_allowed(tool_name)
            if stored_permission is True:
                logger.info(
                    f"Tool {tool_name} has persistent allow permission, skipping request"
                )
                needs_permission = False
            elif stored_permission is False:
                logger.info(f"Tool {tool_name} has persistent reject permission")
                return PreToolUseResult(
                    decision=PermissionDecision.DENY,
                    reason="Tool permanently rejected by user",
                )

        # Request permission via ACP if enabled and tool is not safe
        if needs_permission:
            try:
                # Create permission options
                options = [
                    PermissionOption(
                        option_id="allow_once",
                        name="Allow once",
                        kind="allow_once",
                    ),
                    PermissionOption(
                        option_id="allow_always",
                        name="Always allow this tool",
                        kind="allow_always",
                    ),
                    PermissionOption(
                        option_id="reject_once",
                        name="Reject",
                        kind="reject_once",
                    ),
                ]

                # Create tool call info for permission request (use ToolCallUpdate, not ToolCallStart)
                tool_call_for_permission = ToolCallUpdate(
                    tool_call_id=tool_call_id,
                    title=f"Permission: {tool_name}",
                    kind=get_tool_kind(tool_name),
                    status="pending",
                    content=[
                        ContentToolCallContent(
                            type="content",
                            content=TextContentBlock(
                                type="text",
                                text=f"Tool: {tool_name}\nInput: {tool_input}",
                            ),
                        )
                    ],
                )

                # Request permission from user
                permission_response = await self.client.request_permission(
                    options=options,
                    session_id=self.session_id,
                    tool_call=tool_call_for_permission,
                )

                # Check response - extract option_id and outcome
                raw_outcome = permission_response.outcome
                option_id = None
                outcome = raw_outcome

                # Handle nested structures from different ACP clients
                if hasattr(raw_outcome, "option_id"):
                    option_id = raw_outcome.option_id
                if hasattr(raw_outcome, "outcome"):
                    outcome = raw_outcome.outcome
                    if hasattr(outcome, "option_id"):
                        option_id = outcome.option_id

                # Use option_id if available (more reliable), otherwise fall back to outcome
                selected = option_id or outcome

                logger.info(
                    f"Permission response for {tool_name}: selected={selected}, option_id={option_id}, outcome={outcome}"
                )

                if selected in ("rejected", "reject_once", "reject_always"):
                    logger.info(f"Permission denied for {tool_name}: {selected}")
                    # Save persistent rejection if "always"
                    if selected == "reject_always" and self.permission_store:
                        self.permission_store.set_permission(
                            tool_name, always_allow=False
                        )
                    return PreToolUseResult(
                        decision=PermissionDecision.DENY,
                        reason="User denied permission",
                    )

                # Save persistent allowance if "always"
                if selected == "allow_always" and self.permission_store:
                    self.permission_store.set_permission(tool_name, always_allow=True)
                    logger.info(f"Saved persistent allow permission for {tool_name}")

                logger.info(f"Permission granted for {tool_name}: {selected}")

            except Exception as e:
                logger.error(f"Failed to request permission: {e}")
                # Continue without permission on error (fail open)

        # Send tool_call start notification
        try:
            tool_call = ToolCallStart(
                session_update="tool_call",
                tool_call_id=tool_call_id,
                title=f"Running {tool_name}",
                kind=get_tool_kind(tool_name),
                status="in_progress",
                raw_input=tool_input,
            )
            await self.client.session_update(
                session_id=self.session_id,
                update=tool_call,
            )
        except Exception as e:
            logger.error(f"Failed to send tool_call notification: {e}")

        return PreToolUseResult(decision=PermissionDecision.ACCEPT)

    async def post_tool_use(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: str,
        result: Any,
        error: Optional[Exception] = None,
    ) -> PostToolUseResult:
        """
        Post-tool-use hook that sends ToolCallProgress notification.

        Sends a session_update with ToolCallProgress to notify the ACP client
        about the tool execution result.
        """
        # Get the tool call ID
        tool_call_id = self._tool_call_ids.pop(tool_use_id, None)
        if not tool_call_id:
            logger.warning(f"No tool_call_id found for {tool_use_id}")
            return PostToolUseResult()

        # Determine status and format output
        if error:
            status = "failed"
            output = str(error)
        else:
            status = "completed"
            # Format result for display
            if isinstance(result, str):
                output = result
            elif result is None:
                output = "(no output)"
            else:
                try:
                    import json

                    output = json.dumps(result, indent=2, default=str)
                except Exception:
                    output = str(result)

        # Send tool_call progress notification
        try:
            update = ToolCallProgress(
                session_update="tool_call_update",
                tool_call_id=tool_call_id,
                status=status,
                raw_output=output,
            )
            await self.client.session_update(
                session_id=self.session_id,
                update=update,
            )
        except Exception as e:
            logger.error(f"Failed to send tool_call_update notification: {e}")

        return PostToolUseResult()


def create_acp_hooks(
    client: Client,
    session_id: str,
    request_permission: bool = False,
    include_dangerous_check: bool = True,
    permission_store: Optional[PermissionStore] = None,
) -> HookConfig:
    """
    Create HookConfig with ACP-specific hooks.

    Args:
        client: ACP Client instance
        session_id: Current session ID
        request_permission: Whether to request permission via ACP for tool calls
        include_dangerous_check: Whether to include dangerous command blocking
        permission_store: Optional persistent permission storage

    Returns:
        HookConfig configured for ACP integration
    """
    acp_hooks = ACPToolHooks(
        client=client,
        session_id=session_id,
        request_permission=request_permission,
        permission_store=permission_store,
    )

    # Create hook functions
    async def acp_pre_tool_use(
        tool_name: str, tool_input: Dict[str, Any], tool_use_id: str
    ) -> PreToolUseResult:
        return await acp_hooks.pre_tool_use(tool_name, tool_input, tool_use_id)

    async def acp_post_tool_use(
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_use_id: str,
        result: Any,
        error: Optional[Exception] = None,
    ) -> PostToolUseResult:
        return await acp_hooks.post_tool_use(
            tool_name, tool_input, tool_use_id, result, error
        )

    config = HookConfig()

    # Add dangerous command check if requested
    if include_dangerous_check:
        from ..agents.hooks import create_dangerous_command_check_hook

        config.add_pre_tool_use("bash", create_dangerous_command_check_hook())

    # Add ACP hooks for all tools
    config.add_pre_tool_use("*", acp_pre_tool_use)
    config.add_post_tool_use("*", acp_post_tool_use)

    return config


__all__ = [
    "ACPToolHooks",
    "create_acp_hooks",
]
