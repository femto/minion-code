"""Session storage utilities for minion-code.

This module provides session persistence functionality, allowing users to
save and restore conversation sessions.

Storage location: ~/.minion-code/sessions/<session_id>.json
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionMessage:
    """A single message in a session."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SessionMetadata:
    """Metadata for a session."""

    session_id: str
    created_at: str
    updated_at: str
    project_path: str
    message_count: int = 0
    title: Optional[str] = None  # First user message as title


@dataclass
class Session:
    """A complete session with metadata and messages.

    Attributes:
        metadata: Session metadata (id, timestamps, etc.)
        messages: Original messages (UI display, only grows, never truncated)
        agent_history: Compacted history for agent context (synced after auto-compact)
        compaction_count: Number of times this session has been compacted
    """

    metadata: SessionMetadata
    messages: List[SessionMessage] = field(default_factory=list)
    agent_history: List[Dict[str, Any]] = field(default_factory=list)
    compaction_count: int = 0


class SessionStorage:
    """Session storage manager for minion-code."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize session storage.

        Args:
            storage_dir: Directory for session files. Defaults to ~/.minion-code/sessions
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".minion-code" / "sessions"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.storage_dir / f"{session_id}.json"

    def generate_session_id(self) -> str:
        """Generate a new unique session ID."""
        return str(uuid.uuid4())[:8]  # Short ID for readability

    def save_session(self, session: Session) -> None:
        """Save a session to disk.

        Args:
            session: Session object to save
        """
        session_path = self._get_session_path(session.metadata.session_id)

        # Update the updated_at timestamp
        session.metadata.updated_at = datetime.now().isoformat()
        session.metadata.message_count = len(session.messages)

        # Set title from first user message if not set
        if not session.metadata.title and session.messages:
            for msg in session.messages:
                if msg.role == "user":
                    # Use first 50 chars of first user message as title
                    session.metadata.title = msg.content[:50]
                    if len(msg.content) > 50:
                        session.metadata.title += "..."
                    break

        try:
            # Convert to dict for JSON serialization
            session_dict = {
                "metadata": asdict(session.metadata),
                "messages": [asdict(msg) for msg in session.messages],
                "agent_history": session.agent_history,  # Already list of dicts
                "compaction_count": session.compaction_count,
            }

            with open(session_path, "w", encoding="utf-8") as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)

            logger.debug(
                f"Saved session {session.metadata.session_id} to {session_path}"
            )
        except Exception as e:
            logger.error(f"Failed to save session {session.metadata.session_id}: {e}")
            raise

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from disk.

        Args:
            session_id: ID of the session to load

        Returns:
            Session object if found, None otherwise
        """
        session_path = self._get_session_path(session_id)

        if not session_path.exists():
            logger.warning(f"Session {session_id} not found at {session_path}")
            return None

        try:
            with open(session_path, "r", encoding="utf-8") as f:
                session_dict = json.load(f)

            # Convert dict back to dataclass
            metadata = SessionMetadata(**session_dict["metadata"])
            messages = [
                SessionMessage(**msg) for msg in session_dict.get("messages", [])
            ]
            # Load new fields with backward compatibility (defaults for old sessions)
            agent_history = session_dict.get("agent_history", [])
            compaction_count = session_dict.get("compaction_count", 0)

            return Session(
                metadata=metadata,
                messages=messages,
                agent_history=agent_history,
                compaction_count=compaction_count,
            )
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def get_latest_session_id(
        self, project_path: Optional[str] = None
    ) -> Optional[str]:
        """Get the ID of the most recent session.

        Args:
            project_path: If provided, filter by project path

        Returns:
            Session ID if found, None otherwise
        """
        sessions = self.list_sessions(project_path=project_path)
        if not sessions:
            return None

        # Sessions are sorted by updated_at descending
        return sessions[0].session_id

    def list_sessions(
        self, project_path: Optional[str] = None, limit: int = 20
    ) -> List[SessionMetadata]:
        """List available sessions.

        Args:
            project_path: If provided, filter by project path
            limit: Maximum number of sessions to return

        Returns:
            List of SessionMetadata, sorted by updated_at descending
        """
        sessions = []

        try:
            for session_file in self.storage_dir.glob("*.json"):
                try:
                    with open(session_file, "r", encoding="utf-8") as f:
                        session_dict = json.load(f)

                    metadata = SessionMetadata(**session_dict["metadata"])

                    # Filter by project_path if specified
                    if project_path and metadata.project_path != project_path:
                        continue

                    sessions.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to read session file {session_file}: {e}")
                    continue

            # Sort by updated_at descending (most recent first)
            sessions.sort(key=lambda s: s.updated_at, reverse=True)

            return sessions[:limit]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: ID of the session to delete

        Returns:
            True if deleted, False if not found
        """
        session_path = self._get_session_path(session_id)

        if not session_path.exists():
            return False

        try:
            session_path.unlink()
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    def create_session(self, project_path: Optional[str] = None) -> Session:
        """Create a new session.

        Args:
            project_path: Path of the project for this session

        Returns:
            New Session object
        """
        now = datetime.now().isoformat()
        session_id = self.generate_session_id()

        if project_path is None:
            project_path = os.getcwd()

        metadata = SessionMetadata(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            project_path=project_path,
            message_count=0,
        )

        return Session(metadata=metadata, messages=[])

    def add_message(
        self, session: Session, role: str, content: str, auto_save: bool = True
    ) -> None:
        """Add a message to a session.

        Args:
            session: Session to add message to
            role: 'user' or 'assistant'
            content: Message content
            auto_save: If True, save session after adding message
        """
        message = SessionMessage(role=role, content=content)
        session.messages.append(message)

        if auto_save:
            self.save_session(session)


# Global instance
session_storage = SessionStorage()


# Convenience functions
def create_session(project_path: Optional[str] = None) -> Session:
    """Create a new session."""
    return session_storage.create_session(project_path)


def save_session(session: Session) -> None:
    """Save a session."""
    session_storage.save_session(session)


def load_session(session_id: str) -> Optional[Session]:
    """Load a session by ID."""
    return session_storage.load_session(session_id)


def get_latest_session_id(project_path: Optional[str] = None) -> Optional[str]:
    """Get the most recent session ID."""
    return session_storage.get_latest_session_id(project_path)


def list_sessions(
    project_path: Optional[str] = None, limit: int = 20
) -> List[SessionMetadata]:
    """List available sessions."""
    return session_storage.list_sessions(project_path, limit)


def add_message(
    session: Session, role: str, content: str, auto_save: bool = True
) -> None:
    """Add a message to a session."""
    session_storage.add_message(session, role, content, auto_save)


def restore_agent_history(agent, session: Session, verbose: bool = False) -> int:
    """Restore agent's conversation history from session.

    Prefers `agent_history` (compacted) over `messages` (original) to avoid
    repeated compaction on session restore.

    Args:
        agent: The agent instance with state.history
        session: Session to restore from
        verbose: Print debug info

    Returns:
        Number of messages restored
    """
    if not agent or not session:
        return 0

    # Check if agent has history
    if not hasattr(agent, "state") or not hasattr(agent.state, "history"):
        return 0

    # Clear existing history first
    agent.state.history.clear()

    # Prefer agent_history (compacted) if available
    if session.agent_history:
        for msg in session.agent_history:
            agent.state.history.append(msg)

        if verbose:
            print(
                f"Restored {len(session.agent_history)} messages from agent_history "
                f"(compacted {session.compaction_count} times)"
            )

        return len(session.agent_history)

    # Fallback to original messages (first time or old sessions without agent_history)
    if not session.messages:
        return 0

    for msg in session.messages:
        agent.state.history.append({"role": msg.role, "content": msg.content})

    if verbose:
        print(f"Restored {len(session.messages)} messages from original history")

    return len(session.messages)
