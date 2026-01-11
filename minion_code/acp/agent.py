#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Agent implementation for minion-code.

Implements the ACP Agent protocol to allow minion-code to be used
with ACP-compatible clients.
"""

import asyncio
import logging
import sys
import uuid
from typing import Any, Dict, List, Optional

from acp import Client
from acp.schema import (
    AgentCapabilities,
    AgentMessageChunk,
    AgentThoughtChunk,
    AuthenticateResponse,
    CancelNotification,
    ClientCapabilities,
    ForkSessionRequest,
    ForkSessionResponse,
    HttpMcpServer,
    ImageContentBlock,
    Implementation,
    InitializeRequest,
    InitializeResponse,
    ListSessionsRequest,
    ListSessionsResponse,
    LoadSessionRequest,
    LoadSessionResponse,
    McpServerStdio,
    NewSessionRequest,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    ResumeSessionRequest,
    ResumeSessionResponse,
    SetSessionModelRequest,
    SetSessionModelResponse,
    SetSessionModeRequest,
    SetSessionModeResponse,
    SseMcpServer,
    StopReason,
    TextContentBlock,
    ToolCallStart,
    ToolCallUpdate,
)

from ..agents.code_agent import MinionCodeAgent
from ..agents.hooks import HookConfig, wrap_tools_with_hooks
from .hooks import create_acp_hooks

logger = logging.getLogger(__name__)

# Protocol version
PROTOCOL_VERSION = 1


class MinionACPAgent:
    """
    ACP Agent implementation wrapping MinionCodeAgent.

    This class implements the ACP Agent protocol, allowing minion-code
    to communicate with ACP clients over stdio.
    """

    def __init__(self):
        self.client: Optional[Client] = None
        self.sessions: Dict[str, "ACPSession"] = {}
        self._cancel_events: Dict[str, asyncio.Event] = {}

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
        logger.info(f"Creating new session {session_id} in {cwd}")

        # Create session
        session = ACPSession(
            session_id=session_id,
            cwd=cwd,
            client=self.client,
            mcp_servers=mcp_servers,
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
        prompt: List[TextContentBlock | ImageContentBlock],
        session_id: str,
        **kwargs: Any,
    ) -> PromptResponse:
        """Process a user prompt."""
        logger.info(f"Processing prompt for session {session_id}")

        session = self.sessions.get(session_id)
        if not session:
            logger.error(f"Session {session_id} not found")
            return PromptResponse(stop_reason=StopReason.error)

        # Clear cancel event
        cancel_event = self._cancel_events.get(session_id)
        if cancel_event:
            cancel_event.clear()

        # Extract text from prompt
        text_parts = []
        for block in prompt:
            if isinstance(block, TextContentBlock):
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
                    update=AgentMessageChunk(
                        delta=f"Error: {str(e)}"
                    ),
                )
            return PromptResponse(stop_reason=StopReason.error)

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
    ):
        self.session_id = session_id
        self.cwd = cwd
        self.client = client
        self.mcp_servers = mcp_servers
        self.agent: Optional[MinionCodeAgent] = None
        self.hooks: Optional[HookConfig] = None
        self._message_history: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize the session and create the agent."""
        # Create ACP hooks
        if self.client:
            self.hooks = create_acp_hooks(
                client=self.client,
                session_id=self.session_id,
                request_permission=False,  # For now, auto-accept tools
                include_dangerous_check=True,
            )

        # Create the agent
        self.agent = await MinionCodeAgent.create(
            hooks=self.hooks,
            cwd=self.cwd,
        )

    async def run_prompt(
        self,
        message: str,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> StopReason:
        """
        Run a prompt through the agent and stream results.

        Returns the stop reason for the prompt response.
        """
        if not self.agent or not self.client:
            return StopReason.error

        try:
            # Run agent with streaming
            async for chunk in self.agent.run_async(message, stream=True):
                # Check for cancellation
                if cancel_event and cancel_event.is_set():
                    return StopReason.cancelled

                # Handle different chunk types
                await self._handle_stream_chunk(chunk)

            return StopReason.end_turn

        except asyncio.CancelledError:
            return StopReason.cancelled
        except Exception as e:
            logger.error(f"Error in run_prompt: {e}")
            return StopReason.error

    async def _handle_stream_chunk(self, chunk: Any) -> None:
        """Handle a stream chunk from the agent."""
        if not self.client:
            return

        # Import StreamChunk type
        from minion.types import StreamChunk

        if isinstance(chunk, StreamChunk):
            chunk_type = chunk.chunk_type
            content = chunk.content

            if chunk_type == "thinking":
                # Send as thought chunk
                await self.client.session_update(
                    session_id=self.session_id,
                    update=AgentThoughtChunk(delta=content),
                )
            elif chunk_type == "content":
                # Send as message chunk
                await self.client.session_update(
                    session_id=self.session_id,
                    update=AgentMessageChunk(delta=content),
                )
            elif chunk_type == "code_start":
                # Code execution starting - send as tool call
                await self.client.session_update(
                    session_id=self.session_id,
                    update=ToolCallStart(
                        id=str(uuid.uuid4()),
                        name="python_execute",
                        input={"code": content},
                        state="running",
                    ),
                )
            elif chunk_type == "code_result":
                # Code result - handled by post_tool_use hook
                pass
            # Other chunk types can be handled as needed

        elif hasattr(chunk, 'answer'):
            # Final response
            await self.client.session_update(
                session_id=self.session_id,
                update=AgentMessageChunk(delta=chunk.answer or ""),
            )


__all__ = ["MinionACPAgent", "ACPSession"]
