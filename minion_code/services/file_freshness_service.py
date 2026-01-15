"""File freshness tracking service."""

import os
import time
from pathlib import Path
from typing import Dict, Optional, Union, Set, List, NamedTuple
from dataclasses import dataclass
import logging
import threading

from .event_system import EventDispatcher, EventContext, emit_event, add_event_listener
from ..utils.todo_file_utils import get_todo_file_path

logger = logging.getLogger(__name__)

# Try to import watchdog, fall back to polling if not available
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

    # Create dummy classes for when watchdog is not available
    class FileSystemEventHandler:
        pass

    class Observer:
        pass

    logger.warning(
        "watchdog library not available, file watching will use polling fallback"
    )


@dataclass
class FileTimestamp:
    """Information about a file's timestamp tracking."""

    path: str
    last_read: float
    last_modified: float
    size: int
    last_agent_edit: Optional[float] = None


class FreshnessResult(NamedTuple):
    """Result of file freshness check."""

    is_fresh: bool
    last_read: Optional[float] = None
    current_modified: Optional[float] = None
    conflict: bool = False


class TodoFileWatcher(FileSystemEventHandler):
    """File system event handler for todo files."""

    def __init__(self, agent_id: str, file_path: str, service: "FileFreshnessService"):
        self.agent_id = agent_id
        self.file_path = file_path
        self.service = service
        super().__init__()

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if the modified file is our watched file
        if os.path.abspath(event.src_path) == os.path.abspath(self.file_path):
            logger.debug(
                f"Todo file modified: {self.file_path} for agent {self.agent_id}"
            )

            # Check if this was an external modification
            reminder = self.service.generate_file_modification_reminder(self.file_path)
            if reminder:
                # File was modified externally, emit todo change reminder
                emit_event(
                    "todo:file_changed",
                    {
                        "agent_id": self.agent_id,
                        "file_path": self.file_path,
                        "reminder": reminder,
                        "timestamp": time.time(),
                        "current_stats": self._get_file_stats(),
                    },
                )

    def _get_file_stats(self) -> Dict[str, Union[float, int]]:
        """Get current file statistics."""
        try:
            if os.path.exists(self.file_path):
                stats = os.stat(self.file_path)
                return {"mtime": stats.st_mtime, "size": stats.st_size}
        except Exception:
            pass
        return {"mtime": 0, "size": 0}


class PollingWatcher:
    """Fallback polling-based file watcher."""

    def __init__(
        self,
        agent_id: str,
        file_path: str,
        service: "FileFreshnessService",
        interval: float = 1.0,
    ):
        self.agent_id = agent_id
        self.file_path = file_path
        self.service = service
        self.interval = interval
        self.running = False
        self.thread = None
        self.last_mtime = None

        # Get initial modification time
        if os.path.exists(file_path):
            self.last_mtime = os.path.getmtime(file_path)

    def start(self):
        """Start polling for file changes."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.debug(f"Started polling watcher for {self.file_path}")

    def stop(self):
        """Stop polling for file changes."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.debug(f"Stopped polling watcher for {self.file_path}")

    def _poll_loop(self):
        """Main polling loop."""
        while self.running:
            try:
                if os.path.exists(self.file_path):
                    current_mtime = os.path.getmtime(self.file_path)

                    if self.last_mtime is not None and current_mtime > self.last_mtime:
                        # File was modified
                        logger.debug(f"Polling detected modification: {self.file_path}")

                        reminder = self.service.generate_file_modification_reminder(
                            self.file_path
                        )
                        if reminder:
                            emit_event(
                                "todo:file_changed",
                                {
                                    "agent_id": self.agent_id,
                                    "file_path": self.file_path,
                                    "reminder": reminder,
                                    "timestamp": time.time(),
                                },
                            )

                    self.last_mtime = current_mtime
                elif self.last_mtime is not None:
                    # File was deleted
                    logger.debug(f"Polling detected deletion: {self.file_path}")
                    self.last_mtime = None

                time.sleep(self.interval)

            except Exception as error:
                logger.error(f"Error in polling loop for {self.file_path}: {error}")
                time.sleep(self.interval)


@dataclass
class FileFreshnessState:
    """State container for file freshness tracking."""

    read_timestamps: Dict[str, FileTimestamp]
    edit_conflicts: Set[str]
    session_files: Set[str]
    watched_todo_files: Dict[str, str]  # agent_id -> file_path
    file_watchers: Dict[str, Union[Observer, PollingWatcher]]  # agent_id -> watcher
    todo_handlers: Dict[str, TodoFileWatcher]  # agent_id -> handler


class FileFreshnessService:
    """Service for tracking file freshness and changes."""

    def __init__(self):
        self.state = FileFreshnessState(
            read_timestamps={},
            edit_conflicts=set(),
            session_files=set(),
            watched_todo_files={},
            file_watchers={},
            todo_handlers={},
        )
        self.setup_event_listeners()

    def setup_event_listeners(self) -> None:
        """Setup event listeners for session management."""
        # Listen for session startup events
        add_event_listener("session:startup", self._handle_session_startup)

        # Listen for todo change events
        add_event_listener("todo:changed", self._handle_todo_changed)

        # Listen for file access events
        add_event_listener("file:read", self._handle_file_read)

        # Listen for file edit events
        add_event_listener("file:edited", self._handle_file_edited)

    def _handle_session_startup(self, context: EventContext) -> None:
        """Handle session startup event."""
        self.reset_session()
        logger.info("File freshness session reset on startup")

    def _handle_todo_changed(self, context: EventContext) -> None:
        """Handle todo change event."""
        # Update last todo update time if needed
        logger.debug("Todo changed event received")

    def _handle_file_read(self, context: EventContext) -> None:
        """Handle file read event."""
        # This handler is for external events, not for self-generated events
        # We don't need to do anything here as the event was already processed
        pass

    def _handle_file_edited(self, context: EventContext) -> None:
        """Handle file edit event."""
        # This handler is for external events, not for self-generated events
        # We don't need to do anything here as the event was already processed
        pass

    def record_file_read(self, file_path: Union[str, Path]) -> None:
        """Record file read operation with timestamp tracking."""
        path_str = str(file_path)

        try:
            if not os.path.exists(path_str):
                return

            stats = os.stat(path_str)
            timestamp = FileTimestamp(
                path=path_str,
                last_read=time.time(),
                last_modified=stats.st_mtime,
                size=stats.st_size,
            )

            self.state.read_timestamps[path_str] = timestamp
            self.state.session_files.add(path_str)

            # Emit file read event
            emit_event(
                "file:read",
                {
                    "file_path": path_str,
                    "timestamp": timestamp.last_read,
                    "size": timestamp.size,
                    "modified": timestamp.last_modified,
                },
            )

            logger.debug(f"Recorded file read: {path_str}")

        except Exception as error:
            logger.error(f"Error recording file read for {path_str}: {error}")

    def check_file_freshness(self, file_path: Union[str, Path]) -> FreshnessResult:
        """Check if file has been modified since last read."""
        path_str = str(file_path)
        recorded = self.state.read_timestamps.get(path_str)

        if not recorded:
            return FreshnessResult(is_fresh=True, conflict=False)

        try:
            if not os.path.exists(path_str):
                return FreshnessResult(is_fresh=False, conflict=True)

            current_stats = os.stat(path_str)
            is_fresh = current_stats.st_mtime <= recorded.last_modified
            conflict = not is_fresh

            if conflict:
                self.state.edit_conflicts.add(path_str)

                # Emit file conflict event
                emit_event(
                    "file:conflict",
                    {
                        "file_path": path_str,
                        "last_read": recorded.last_read,
                        "last_modified": recorded.last_modified,
                        "current_modified": current_stats.st_mtime,
                        "size_diff": current_stats.st_size - recorded.size,
                    },
                )

                logger.warning(f"File conflict detected: {path_str}")

            return FreshnessResult(
                is_fresh=is_fresh,
                last_read=recorded.last_read,
                current_modified=current_stats.st_mtime,
                conflict=conflict,
            )

        except Exception as error:
            logger.error(f"Error checking freshness for {path_str}: {error}")
            return FreshnessResult(is_fresh=False, conflict=True)

    def record_file_edit(
        self, file_path: Union[str, Path], content: Optional[str] = None
    ) -> None:
        """Record file edit operation by Agent."""
        path_str = str(file_path)

        try:
            now = time.time()

            # Update recorded timestamp after edit
            if os.path.exists(path_str):
                stats = os.stat(path_str)
                existing = self.state.read_timestamps.get(path_str)

                if existing:
                    existing.last_modified = stats.st_mtime
                    existing.size = stats.st_size
                    existing.last_agent_edit = now
                    self.state.read_timestamps[path_str] = existing
                else:
                    # Create new record for Agent-edited file
                    timestamp = FileTimestamp(
                        path=path_str,
                        last_read=now,
                        last_modified=stats.st_mtime,
                        size=stats.st_size,
                        last_agent_edit=now,
                    )
                    self.state.read_timestamps[path_str] = timestamp

            # Remove from conflicts since we just edited it
            self.state.edit_conflicts.discard(path_str)

            # Emit file edit event
            emit_event(
                "file:edited",
                {
                    "file_path": path_str,
                    "timestamp": now,
                    "content_length": len(content) if content else 0,
                    "source": "agent",
                },
            )

            logger.debug(f"Recorded file edit: {path_str}")

        except Exception as error:
            logger.error(f"Error recording file edit for {path_str}: {error}")

    def generate_file_modification_reminder(
        self, file_path: Union[str, Path]
    ) -> Optional[str]:
        """Generate reminder message for externally modified files."""
        path_str = str(file_path)
        recorded = self.state.read_timestamps.get(path_str)

        if not recorded:
            return None

        try:
            if not os.path.exists(path_str):
                return f"Note: {path_str} was deleted since last read."

            current_stats = os.stat(path_str)
            is_modified = current_stats.st_mtime > recorded.last_modified

            if not is_modified:
                return None

            # Check if this was an Agent-initiated change
            # Use small time tolerance to handle filesystem timestamp precision issues
            TIME_TOLERANCE_MS = 0.1  # 100ms in seconds
            if (
                recorded.last_agent_edit
                and recorded.last_agent_edit
                >= recorded.last_modified - TIME_TOLERANCE_MS
            ):
                # Agent modified this file recently, no reminder needed
                return None

            # External modification detected - generate reminder
            return f"Note: {path_str} was modified externally since last read. The file may have changed outside of this session."

        except Exception as error:
            logger.error(f"Error checking modification for {path_str}: {error}")
            return None

    def get_conflicted_files(self) -> List[str]:
        """Get list of files with edit conflicts."""
        return list(self.state.edit_conflicts)

    def get_session_files(self) -> List[str]:
        """Get list of files accessed in current session."""
        return list(self.state.session_files)

    def reset_session(self) -> None:
        """Reset session state."""
        # Clean up existing todo file watchers
        for agent_id in list(self.state.watched_todo_files.keys()):
            self.stop_watching_todo_file(agent_id)

        self.state = FileFreshnessState(
            read_timestamps={},
            edit_conflicts=set(),
            session_files=set(),
            watched_todo_files={},
            file_watchers={},
            todo_handlers={},
        )
        logger.info("File freshness session reset")

    def get_file_info(self, file_path: Union[str, Path]) -> Optional[FileTimestamp]:
        """Get file timestamp information."""
        path_str = str(file_path)
        return self.state.read_timestamps.get(path_str)

    def is_file_tracked(self, file_path: Union[str, Path]) -> bool:
        """Check if file is being tracked."""
        path_str = str(file_path)
        return path_str in self.state.read_timestamps

    def get_important_files(
        self, max_files: int = 5
    ) -> List[Dict[str, Union[str, float, int]]]:
        """
        Retrieves files prioritized for recovery during conversation compression.

        Selects recently accessed files based on:
        - File access recency (most recent first)
        - File type relevance (excludes dependencies, build artifacts)
        - Development workflow importance
        """
        files = []
        for path, info in self.state.read_timestamps.items():
            if self._is_valid_for_recovery(path):
                files.append(
                    {"path": path, "timestamp": info.last_read, "size": info.size}
                )

        # Sort by timestamp (newest first) and limit results
        files.sort(key=lambda x: x["timestamp"], reverse=True)
        return files[:max_files]

    def _is_valid_for_recovery(self, file_path: str) -> bool:
        """
        Determines which files are suitable for automatic recovery.

        Excludes files that are typically not relevant for development context:
        - Build artifacts and generated files
        - Dependencies and cached files
        - Temporary files and system directories
        """
        return (
            "node_modules" not in file_path
            and ".git" not in file_path
            and not file_path.startswith("/tmp")
            and ".cache" not in file_path
            and "dist/" not in file_path
            and "build/" not in file_path
            and "__pycache__" not in file_path
            and ".pyc" not in file_path
        )

    def start_watching_todo_file(
        self, agent_id: str, file_path: Optional[str] = None
    ) -> None:
        """Start watching todo file for an agent."""
        try:
            # Use provided file_path or generate default path using todo_file_utils
            if file_path is None:
                file_path = get_todo_file_path(agent_id)

            # Don't watch if already watching
            if agent_id in self.state.watched_todo_files:
                logger.debug(f"Already watching todo file for agent {agent_id}")
                return

            self.state.watched_todo_files[agent_id] = file_path

            # Record initial state if file exists
            if os.path.exists(file_path):
                self.record_file_read(file_path)

            # Start watching for changes
            if WATCHDOG_AVAILABLE:
                self._start_watchdog_watcher(agent_id, file_path)
            else:
                self._start_polling_watcher(agent_id, file_path)

            logger.info(f"Started watching todo file for agent {agent_id}: {file_path}")

        except Exception as error:
            logger.error(
                f"Error starting todo file watch for agent {agent_id}: {error}"
            )

    def stop_watching_todo_file(self, agent_id: str) -> None:
        """Stop watching todo file for an agent."""
        try:
            if agent_id not in self.state.watched_todo_files:
                logger.debug(f"Not watching todo file for agent {agent_id}")
                return

            # Stop the appropriate watcher
            if agent_id in self.state.file_watchers:
                watcher = self.state.file_watchers[agent_id]

                if isinstance(watcher, Observer):
                    watcher.stop()
                    watcher.join(timeout=2.0)
                elif isinstance(watcher, PollingWatcher):
                    watcher.stop()

                del self.state.file_watchers[agent_id]

            # Clean up handler
            if agent_id in self.state.todo_handlers:
                del self.state.todo_handlers[agent_id]

            # Remove from watched files
            file_path = self.state.watched_todo_files.pop(agent_id, None)

            logger.info(f"Stopped watching todo file for agent {agent_id}: {file_path}")

        except Exception as error:
            logger.error(
                f"Error stopping todo file watch for agent {agent_id}: {error}"
            )

    def _start_watchdog_watcher(self, agent_id: str, file_path: str) -> None:
        """Start watchdog-based file watcher."""
        try:
            # Create event handler
            handler = TodoFileWatcher(agent_id, file_path, self)
            self.state.todo_handlers[agent_id] = handler

            # Create observer and watch the directory containing the file
            observer = Observer()
            watch_dir = os.path.dirname(os.path.abspath(file_path))

            # Create directory if it doesn't exist
            os.makedirs(watch_dir, exist_ok=True)

            observer.schedule(handler, watch_dir, recursive=False)
            observer.start()

            self.state.file_watchers[agent_id] = observer
            logger.debug(f"Started watchdog watcher for {file_path}")

        except Exception as error:
            logger.error(f"Error starting watchdog watcher for {file_path}: {error}")
            # Fall back to polling
            self._start_polling_watcher(agent_id, file_path)

    def _start_polling_watcher(self, agent_id: str, file_path: str) -> None:
        """Start polling-based file watcher."""
        try:
            watcher = PollingWatcher(agent_id, file_path, self)
            watcher.start()

            self.state.file_watchers[agent_id] = watcher
            logger.debug(f"Started polling watcher for {file_path}")

        except Exception as error:
            logger.error(f"Error starting polling watcher for {file_path}: {error}")

    def get_watched_files(self) -> Dict[str, str]:
        """Get currently watched todo files."""
        return self.state.watched_todo_files.copy()

    def is_watching_agent(self, agent_id: str) -> bool:
        """Check if we're watching todo file for an agent."""
        return agent_id in self.state.watched_todo_files


# Global service instance
file_freshness_service = FileFreshnessService()


# Convenience functions for external use
def record_file_read(file_path: Union[str, Path]) -> None:
    """Record file read operation."""
    file_freshness_service.record_file_read(file_path)


def record_file_edit(
    file_path: Union[str, Path], content: Optional[str] = None
) -> None:
    """Record file edit operation."""
    file_freshness_service.record_file_edit(file_path, content)


def check_file_freshness(file_path: Union[str, Path]) -> FreshnessResult:
    """Check file freshness."""
    return file_freshness_service.check_file_freshness(file_path)


def generate_file_modification_reminder(file_path: Union[str, Path]) -> Optional[str]:
    """Generate file modification reminder."""
    return file_freshness_service.generate_file_modification_reminder(file_path)


def reset_file_freshness_session() -> None:
    """Reset file freshness session."""
    file_freshness_service.reset_session()


def start_watching_todo_file(agent_id: str, file_path: Optional[str] = None) -> None:
    """Start watching todo file for an agent."""
    file_freshness_service.start_watching_todo_file(agent_id, file_path)


def stop_watching_todo_file(agent_id: str) -> None:
    """Stop watching todo file for an agent."""
    file_freshness_service.stop_watching_todo_file(agent_id)
