#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Agent implementation for minion-code.

Implements the ACP Agent protocol to allow minion-code to be used
with ACP-compatible clients.
"""

import asyncio
import logging
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

from acp import Client, text_block
from acp.helpers import (
    update_agent_message_text,
    update_agent_thought_text,
)
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    AgentThoughtChunk,
    AudioContentBlock,
    AuthenticateResponse,
    ClientCapabilities,
    ContentToolCallContent,
    EmbeddedResourceContentBlock,
    ForkSessionResponse,
    HttpMcpServer,
    ImageContentBlock,
    Implementation,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    McpServerStdio,
    NewSessionResponse,
    PromptResponse,
    ResourceContentBlock,
    ResumeSessionResponse,
    SetSessionModelResponse,
    SetSessionModeResponse,
    SseMcpServer,
    TextContentBlock,
    ToolCallStart,
    ToolCallProgress,
)

from ..agents.code_agent import MinionCodeAgent
from ..agents.hooks import HookConfig, wrap_tools_with_hooks
from .hooks import create_acp_hooks
from .permissions import PermissionStore

logger = logging.getLogger(__name__)

# Protocol version
PROTOCOL_VERSION = 1


class MinionACPAgent:
    """
    ACP Agent implementation wrapping MinionCodeAgent.

    This class implements the ACP Agent protocol, allowing minion-code
    to communicate with ACP clients over stdio.
    """

    def __init__(self, skip_permissions: bool = False, config: Optional[Dict] = None, cwd: Optional[str] = None):
        self.client: Optional[Client] = None
        self.sessions: Dict[str, "ACPSession"] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}
        self.skip_permissions = skip_permissions
        self.config = config or {}
        self.cwd = cwd or os.getcwd()

    def on_connect(self, conn: Client) -> None:
        """Called when connected to an ACP client."""
        self.client = conn
        logger.info("Connected to ACP client")

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: Optional[ClientCapabilities] = None,
        client_info: Optional[Implementation] = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        """Initialize the agent and negotiate capabilities."""
        logger.info(f"Initializing with protocol version {protocol_version}")

        return InitializeResponse(
            protocol_version=min(protocol_version, PROTOCOL_VERSION),
            agent_info=Implementation(
                name="minion-code",
                version="0.1.0",
            ),
            agent_capabilities=AgentCapabilities(
                streaming=True,
            ),
        )

    async def new_session(
        self,
        cwd: str,
        mcp_servers: List[HttpMcpServer | SseMcpServer | McpServerStdio],
        **kwargs: Any,
    ) -> NewSessionResponse:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        pid = os.getpid()
        session_count = len(self.sessions) + 1

        # Use CLI-provided cwd as fallback if client doesn't provide one
        if not cwd:
            cwd = self.cwd
        logger.info(f"[PID={pid}] Creating session #{session_count}: {session_id} in {cwd}")

        # Create session
        session = ACPSession(
            session_id=session_id,
            cwd=cwd,
            client=self.client,
            mcp_servers=mcp_servers,
            skip_permissions=self.skip_permissions,
        )
        await session.initialize()

        self.sessions[session_id] = session
        self._cancel_events[session_id] = asyncio.Event()

        return NewSessionResponse(session_id=session_id)

    async def load_session(
        self,
        cwd: str,
        mcp_servers: List[HttpMcpServer | SseMcpServer | McpServerStdio],
        session_id: str,
        **kwargs: Any,
    ) -> Optional[LoadSessionResponse]:
        """Load an existing session."""
        if session_id in self.sessions:
            return LoadSessionResponse()
        return None

    async def list_sessions(
        self,
        cursor: Optional[str] = None,
        cwd: Optional[str] = None,
        **kwargs: Any,
    ) -> ListSessionsResponse:
        """List available sessions."""
        # Simple implementation - just return session IDs
        sessions = []
        for sid in self.sessions.keys():
            sessions.append({"session_id": sid})

        return ListSessionsResponse(sessions=sessions)

    async def set_session_mode(
        self,
        mode_id: str,
        session_id: str,
        **kwargs: Any,
    ) -> Optional[SetSessionModeResponse]:
        """Set the session mode (not implemented)."""
        return None

    async def set_session_model(
        self,
        model_id: str,
        session_id: str,
        **kwargs: Any,
    ) -> Optional[SetSessionModelResponse]:
        """Set the session model (not implemented)."""
        return None

    async def authenticate(
        self,
        method_id: str,
        **kwargs: Any,
    ) -> Optional[AuthenticateResponse]:
        """Authenticate (not implemented)."""
        return None

    async def prompt(
        self,
        prompt: List[
            TextContentBlock
            | ImageContentBlock
            | AudioContentBlock
            | ResourceContentBlock
            | EmbeddedResourceContentBlock
        ],
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        """Process a user prompt."""
        pid = os.getpid()
        logger.info(f"[PID={pid}] Processing prompt for session {session_id}")
        logger.info(f"[PID={pid}] Prompt content: {prompt}")

        session = self.sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return PromptResponse(stop_reason="refusal")

        # Clear cancel event
        cancel_event = self._cancel_events.get(session_id)
        if cancel_event:
            cancel_event.clear()

        # Extract text from prompt (handle both Pydantic models and dicts)
        text_parts = []
        for block in prompt:
            if isinstance(block, dict):
                # Dict format
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            elif isinstance(block, TextContentBlock):
                text_parts.append(block.text)
            elif hasattr(block, "text"):
                text_parts.append(block.text)

        user_message = "\n".join(text_parts)

        try:
            # Run the agent
            stop_reason = await session.run_prompt(
                message=user_message,
                cancel_event=cancel_event,
            )
            return PromptResponse(stop_reason=stop_reason)
        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            # Send error message
            if self.client:
                await self.client.session_update(
                    session_id=session_id,
                    update=update_agent_message_text(f"Error: {str(e)}"),
                )
            return PromptResponse(stop_reason="refusal")

    async def fork_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: Optional[List[HttpMcpServer | SseMcpServer | McpServerStdio]] = None,
        **kwargs: Any,
    ) -> ForkSessionResponse:
        """Fork an existing session."""
        new_session_id = str(uuid.uuid4())

        # Copy session state (simplified)
        if session_id in self.sessions:
            old_session = self.sessions[session_id]
            new_session = ACPSession(
                session_id=new_session_id,
                cwd=cwd,
                client=self.client,
                mcp_servers=mcp_servers or old_session.mcp_servers,
                skip_permissions=self.skip_permissions,
            )
            await new_session.initialize()
            self.sessions[new_session_id] = new_session
            self._cancel_events[new_session_id] = asyncio.Event()

        return ForkSessionResponse(session_id=new_session_id)

    async def resume_session(
        self,
        cwd: str,
        session_id: str,
        mcp_servers: Optional[List[HttpMcpServer | SseMcpServer | McpServerStdio]] = None,
        **kwargs: Any,
    ) -> ResumeSessionResponse:
        """Resume an existing session."""
        if session_id in self.sessions:
            return ResumeSessionResponse()

        # Create new session with the given ID
        session = ACPSession(
            session_id=session_id,
            cwd=cwd,
            client=self.client,
            mcp_servers=mcp_servers or [],
            skip_permissions=self.skip_permissions,
        )
        await session.initialize()
        self.sessions[session_id] = session
        self._cancel_events[session_id] = asyncio.Event()

        return ResumeSessionResponse()

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        """Cancel the current operation in a session."""
        logger.info(f"Cancelling session {session_id}")
        cancel_event = self._cancel_events.get(session_id)
        if cancel_event:
            cancel_event.set()

    async def ext_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle extension method (not implemented)."""
        return {}

    async def ext_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Handle extension notification (not implemented)."""
        pass


class ACPSession:
    """
    Represents an ACP session with an underlying MinionCodeAgent.
    """

    def __init__(
        self,
        session_id: str,
        cwd: str,
        client: Optional[Client],
        mcp_servers: List[Any],
        skip_permissions: bool = False,
    ):
        self.session_id = session_id
        self.cwd = cwd
        self.client = client
        self.mcp_servers = mcp_servers
        self.skip_permissions = skip_permissions
        self.agent: Optional[MinionCodeAgent] = None
        self.hooks: Optional[HookConfig] = None
        self.permission_store: Optional[PermissionStore] = None
        self._message_history: List[Dict[str, Any]] = []
        # Track current code execution tool call ID for pairing start/result
        self._current_code_call_id: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the session and create the agent."""
        # Create permission store for this project
        self.permission_store = PermissionStore(cwd=self.cwd)

        # Create ACP hooks
        if self.client:
            self.hooks = create_acp_hooks(
                client=self.client,
                session_id=self.session_id,
                request_permission=not self.skip_permissions,  # Ask user permission unless skipped
                include_dangerous_check=True,
                permission_store=self.permission_store,
            )

        # Create the agent
        self.agent = await MinionCodeAgent.create(
            hooks=self.hooks,
            workdir=self.cwd,
        )

    async def run_prompt(
        self,
        message: str,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> str:
        """
        Run a prompt through the agent and stream results.

        Returns the stop reason for the prompt response.
        """
        if not self.agent or not self.client:
            return "refusal"

        try:
            # Run agent with streaming - await to get async generator, then iterate
            stream = await self.agent.run_async(message, stream=True)
            async for chunk in stream:
                # Check for cancellation
                if cancel_event and cancel_event.is_set():
                    return "cancelled"

                # Handle different chunk types
                await self._handle_stream_chunk(chunk)

            return "end_turn"

        except asyncio.CancelledError:
            return "cancelled"
        except Exception as e:
            logger.error(f"Error in run_prompt: {e}")
            return "refusal"

    async def _handle_stream_chunk(self, chunk: Any) -> None:
        """Handle a stream chunk from the agent and convert to ACP events."""
        if not self.client:
            return

        # Import StreamChunk type
        from minion.types import StreamChunk, AgentResponse

        if isinstance(chunk, StreamChunk):
            chunk_type = chunk.chunk_type
            content = chunk.content
            metadata = getattr(chunk, 'metadata', {}) or {}

            if chunk_type == "thinking":
                # LLM reasoning/thinking - send as thought chunk
                if content:
                    await self.client.session_update(
                        session_id=self.session_id,
                        update=update_agent_thought_text(content),
                    )

            elif chunk_type in ("text", "content"):
                # Regular assistant message content
                if content:
                    await self.client.session_update(
                        session_id=self.session_id,
                        update=update_agent_message_text(content),
                    )

            elif chunk_type == "code_start":
                # Code execution starting - send ToolCallStart
                self._current_code_call_id = str(uuid.uuid4())
                await self.client.session_update(
                    session_id=self.session_id,
                    update=ToolCallStart(
                        session_update="tool_call",
                        tool_call_id=self._current_code_call_id,
                        title="Executing Python code",
                        kind="execute",
                        status="in_progress",
                        raw_input=f"```python\n{content}\n```",
                        content=[
                            ContentToolCallContent(
                                type="content",
                                content=TextContentBlock(type="text", text=f"```python\n{content}\n```"),
                            )
                        ],
                    ),
                )

            elif chunk_type == "code_result":
                # Code execution result - send ToolCallProgress
                if self._current_code_call_id:
                    success = metadata.get("success", True)
                    await self.client.session_update(
                        session_id=self.session_id,
                        update=ToolCallProgress(
                            session_update="tool_call_update",
                            tool_call_id=self._current_code_call_id,
                            status="completed" if success else "failed",
                            content=[
                                ContentToolCallContent(
                                    type="content",
                                    content=TextContentBlock(type="text", text=content if content else "Executed successfully"),
                                )
                            ],
                        ),
                    )
                    self._current_code_call_id = None

            elif chunk_type == "step_start":
                # Step start notification - can be logged or sent as info
                logger.debug(f"Step started: {metadata.get('iteration', '?')}")

            elif chunk_type == "tool_call":
                # Direct tool call (non-code execution) - handled by pre_tool_use hook
                # But we can also send notification here if needed
                pass

            elif chunk_type == "tool_response":
                # Tool response - handled by post_tool_use hook
                pass

            elif chunk_type == "error":
                # Error message
                if content:
                    await self.client.session_update(
                        session_id=self.session_id,
                        update=update_agent_message_text(f"Error: {content}"),
                    )

            elif chunk_type == "final_answer":
                # Final answer reached
                if content:
                    await self.client.session_update(
                        session_id=self.session_id,
                        update=update_agent_message_text(content),
                    )

        elif isinstance(chunk, AgentResponse):
            # Final AgentResponse with answer
            if chunk.answer:
                await self.client.session_update(
                    session_id=self.session_id,
                    update=update_agent_message_text(chunk.answer),
                )

        elif hasattr(chunk, 'answer') and chunk.answer:
            # Fallback for objects with answer attribute
            await self.client.session_update(
                session_id=self.session_id,
                update=update_agent_message_text(chunk.answer),
            )


__all__ = ["MinionACPAgent", "ACPSession"]
