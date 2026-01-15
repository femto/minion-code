"""Event system for minion_code services."""

from typing import Dict, List, Callable, Any, Optional
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Supported event types."""

    SESSION_STARTUP = "session:startup"
    TODO_CHANGED = "todo:changed"
    TODO_FILE_CHANGED = "todo:file_changed"
    FILE_READ = "file:read"
    FILE_EDITED = "file:edited"
    FILE_CONFLICT = "file:conflict"
    AGENT_MENTIONED = "agent:mentioned"
    FILE_MENTIONED = "file:mentioned"
    ASK_MODEL_MENTIONED = "ask-model:mentioned"
    REMINDER_INJECT = "reminder:inject"


@dataclass
class EventContext:
    """Context data for events."""

    event_type: str
    timestamp: float
    data: Dict[str, Any]


EventCallback = Callable[[EventContext], None]


class EventDispatcher:
    """Simple event dispatcher for handling system events."""

    def __init__(self):
        self._listeners: Dict[str, List[EventCallback]] = {}

    def add_event_listener(self, event_type: str, callback: EventCallback) -> None:
        """Add an event listener for a specific event type."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
        logger.debug(f"Added event listener for {event_type}")

    def remove_event_listener(self, event_type: str, callback: EventCallback) -> bool:
        """Remove a specific event listener."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
                logger.debug(f"Removed event listener for {event_type}")
                return True
            except ValueError:
                pass
        return False

    def emit_event(
        self, event_type: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit an event to all registered listeners."""
        if event_type not in self._listeners:
            return

        import time

        context = EventContext(
            event_type=event_type, timestamp=time.time(), data=data or {}
        )

        listeners = self._listeners[
            event_type
        ].copy()  # Avoid modification during iteration
        for callback in listeners:
            try:
                callback(context)
            except Exception as error:
                logger.error(f"Error in event listener for {event_type}: {error}")

    def clear_listeners(self, event_type: Optional[str] = None) -> None:
        """Clear listeners for a specific event type or all listeners."""
        if event_type:
            self._listeners.pop(event_type, None)
        else:
            self._listeners.clear()

    def get_listener_count(self, event_type: str) -> int:
        """Get the number of listeners for an event type."""
        return len(self._listeners.get(event_type, []))


# Global event dispatcher instance
global_event_dispatcher = EventDispatcher()


# Convenience functions
def add_event_listener(event_type: str, callback: EventCallback) -> None:
    """Add an event listener using the global dispatcher."""
    global_event_dispatcher.add_event_listener(event_type, callback)


def emit_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Emit an event using the global dispatcher."""
    global_event_dispatcher.emit_event(event_type, data)


def remove_event_listener(event_type: str, callback: EventCallback) -> bool:
    """Remove an event listener using the global dispatcher."""
    return global_event_dispatcher.remove_event_listener(event_type, callback)
