"""Services module for minion_code."""

from .event_system import (
    EventDispatcher,
    EventContext,
    EventType,
    EventCallback,
    global_event_dispatcher,
    add_event_listener,
    emit_event,
    remove_event_listener,
)

from .file_freshness_service import (
    FileFreshnessService,
    FileTimestamp,
    FreshnessResult,
    file_freshness_service,
    record_file_read,
    record_file_edit,
    check_file_freshness,
    generate_file_modification_reminder,
    reset_file_freshness_session,
    start_watching_todo_file,
    stop_watching_todo_file,
)

__all__ = [
    # Event system
    "EventDispatcher",
    "EventContext",
    "EventType",
    "EventCallback",
    "global_event_dispatcher",
    "add_event_listener",
    "emit_event",
    "remove_event_listener",
    # File freshness service
    "FileFreshnessService",
    "FileTimestamp",
    "FreshnessResult",
    "file_freshness_service",
    "record_file_read",
    "record_file_edit",
    "check_file_freshness",
    "generate_file_modification_reminder",
    "reset_file_freshness_session",
    "start_watching_todo_file",
    "stop_watching_todo_file",
]
