#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Manager for Web API.

Manages web sessions, agent instances, and the relationship between them.
Supports two history modes:
- full: Each request creates new Agent, loads full history (stateless, scalable)
- incremental: Reuse Agent, only send new message (stateful, low latency)
"""

import asyncio
import time
import uuid
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Literal, List, Any

from ..adapters.web_adapter import WebOutputAdapter, TaskState
from minion_code.utils.session_storage import (
    Session, SessionStorage, SessionMessage,
    create_session, load_session, save_session, add_message,
    restore_agent_history
)
from minion_code.agents.hooks import (
    HookConfig, HookMatcher,
    create_confirm_writes_hook,
    create_dangerous_command_check_hook
)

logger = logging.getLogger(__name__)

HistoryMode = Literal["full", "incremental"]


@dataclass
class WebSession:
    """Web session containing agent and adapter."""
    session_id: str
    project_path: str
    adapter: WebOutputAdapter
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    history_mode: HistoryMode = "full"

    # Agent instance (only used in incremental mode)
    _agent: Optional[Any] = field(default=None, repr=False)

    # Abort event for cancelling current task
    abort_event: asyncio.Event = field(default_factory=asyncio.Event)

    # Current task ID
    current_task_id: Optional[str] = None

    # Session storage (persisted)
    _storage_session: Optional[Session] = field(default=None, repr=False)

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def generate_task_id(self) -> str:
        """Generate unique task ID."""
        return f"task_{self.session_id}_{int(time.time() * 1000)}"


class SessionManager:
    """
    Web session manager.

    Manages the lifecycle of web sessions and their associated resources.
    """

    def __init__(
        self,
        max_sessions: int = 100,
        session_timeout: int = 3600,  # 1 hour
        default_history_mode: HistoryMode = "full"
    ):
        """
        Initialize session manager.

        Args:
            max_sessions: Maximum number of concurrent sessions
            session_timeout: Session timeout in seconds
            default_history_mode: Default history mode for new sessions
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.default_history_mode = default_history_mode

        self.sessions: Dict[str, WebSession] = {}
        self.storage = SessionStorage()
        self._lock = asyncio.Lock()

    async def create_session(
        self,
        project_path: str = ".",
        history_mode: Optional[HistoryMode] = None
    ) -> WebSession:
        """
        Create a new web session.

        Args:
            project_path: Working directory for the session
            history_mode: History mode ('full' or 'incremental')

        Returns:
            New WebSession instance
        """
        async with self._lock:
            # Cleanup expired sessions
            await self._cleanup_expired_sessions()

            if len(self.sessions) >= self.max_sessions:
                raise Exception("Maximum sessions reached")

            # Generate session ID
            session_id = str(uuid.uuid4())[:8]

            # Create adapter
            adapter = WebOutputAdapter(session_id=session_id)

            # Create web session
            session = WebSession(
                session_id=session_id,
                project_path=str(Path(project_path).resolve()),
                adapter=adapter,
                history_mode=history_mode or self.default_history_mode
            )

            # Create persistent storage session
            storage_session = self.storage.create_session(session.project_path)
            # Override session_id to match web session
            storage_session.metadata.session_id = session_id
            session._storage_session = storage_session

            self.sessions[session_id] = session
            logger.info(f"Created session {session_id} with history_mode={session.history_mode}")

            return session

    async def get_session(self, session_id: str) -> Optional[WebSession]:
        """
        Get a session by ID.

        Args:
            session_id: Session identifier

        Returns:
            WebSession if found, None otherwise
        """
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session

    async def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        project_path: str = ".",
        history_mode: Optional[HistoryMode] = None
    ) -> WebSession:
        """
        Get existing session or create new one.

        Args:
            session_id: Optional session ID to look up
            project_path: Working directory for new session
            history_mode: History mode for new session

        Returns:
            WebSession instance
        """
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session

        return await self.create_session(project_path, history_mode)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        async with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                # Abort any running task
                session.abort_event.set()
                logger.info(f"Deleted session {session_id}")
                return True
            return False

    def find_session_by_interaction(self, interaction_id: str) -> Optional[WebSession]:
        """
        Find session containing a pending interaction.

        Args:
            interaction_id: Interaction identifier

        Returns:
            WebSession if found, None otherwise
        """
        for session in self.sessions.values():
            if session.adapter.get_pending_interaction(interaction_id):
                return session
        return None

    def _create_hooks_for_session(self, session: WebSession) -> HookConfig:
        """
        Create hook configuration for a session.

        Configures:
        - Dangerous command blocking for bash
        - User confirmation for write operations via adapter.confirm()

        Args:
            session: WebSession with adapter for confirmations

        Returns:
            HookConfig for the session
        """
        return HookConfig(
            pre_tool_use=[
                # Block dangerous bash commands
                HookMatcher("bash", create_dangerous_command_check_hook()),
                # Confirm non-readonly tools via WebOutputAdapter
                HookMatcher("*", create_confirm_writes_hook(session.adapter)),
            ]
        )

    async def get_or_create_agent(self, session: WebSession):
        """
        Get or create agent for session based on history mode.

        For 'full' mode: Creates new agent, restores history from storage
        For 'incremental' mode: Reuses existing agent or creates new one

        Args:
            session: WebSession to get agent for

        Returns:
            MinionCodeAgent instance
        """
        from minion_code.agents import MinionCodeAgent

        # Create hooks for permission control
        hooks = self._create_hooks_for_session(session)

        if session.history_mode == "full":
            # Full mode: Always create new agent and restore history
            agent = await MinionCodeAgent.create(
                name=f"WebAgent-{session.session_id}",
                llm="sonnet",
                workdir=session.project_path,
                hooks=hooks
            )

            # Restore history from storage
            if session._storage_session and session._storage_session.messages:
                restore_agent_history(agent, session._storage_session, verbose=False)

            return agent

        else:  # incremental mode
            # Incremental mode: Reuse agent if available
            if session._agent is None:
                session._agent = await MinionCodeAgent.create(
                    name=f"WebAgent-{session.session_id}",
                    llm="sonnet",
                    workdir=session.project_path,
                    hooks=hooks
                )

                # Restore history on first creation
                if session._storage_session and session._storage_session.messages:
                    restore_agent_history(session._agent, session._storage_session, verbose=False)

            return session._agent

    def save_message(
        self,
        session: WebSession,
        role: str,
        content: str
    ):
        """
        Save a message to session storage.

        Args:
            session: WebSession to save message for
            role: 'user' or 'assistant'
            content: Message content
        """
        if session._storage_session:
            add_message(session._storage_session, role, content, auto_save=True)

    def get_messages(self, session: WebSession) -> List[Dict[str, str]]:
        """
        Get all messages from session storage.

        Args:
            session: WebSession to get messages for

        Returns:
            List of message dicts with 'role' and 'content'
        """
        if session._storage_session:
            return [
                {"role": msg.role, "content": msg.content}
                for msg in session._storage_session.messages
            ]
        return []

    async def abort_task(self, session_id: str) -> bool:
        """
        Abort the current task in a session.

        Args:
            session_id: Session identifier

        Returns:
            True if abort signal was sent, False if session not found
        """
        session = self.sessions.get(session_id)
        if session:
            session.abort_event.set()
            # Reset for next task
            session.abort_event = asyncio.Event()
            logger.info(f"Aborted task in session {session_id}")
            return True
        return False

    async def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        current_time = time.time()
        expired = [
            sid for sid, session in self.sessions.items()
            if current_time - session.last_activity > self.session_timeout
        ]
        for sid in expired:
            del self.sessions[sid]
            logger.info(f"Cleaned up expired session {sid}")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions.

        Returns:
            List of session info dicts
        """
        return [
            {
                "session_id": s.session_id,
                "project_path": s.project_path,
                "history_mode": s.history_mode,
                "created_at": s.created_at,
                "last_activity": s.last_activity,
                "has_pending_interactions": s.adapter.has_pending_interactions()
            }
            for s in self.sessions.values()
        ]


# Global instance
session_manager = SessionManager()
