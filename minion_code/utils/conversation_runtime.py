#!/usr/bin/env python3
"""Runtime state for buffered prompts and pending system reminders."""

from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional

from ..services.file_freshness_service import file_freshness_service


@dataclass
class QueuedPrompt:
    """A prompt waiting for its turn to be processed."""

    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemReminder:
    """A queued reminder to prepend before the next user prompt."""

    key: str
    topic: str
    message: str
    persistent: bool = False


class ConversationRuntimeState:
    """Tracks buffered prompts and system reminders for one conversation runtime."""

    def __init__(self):
        self.processing_lock = asyncio.Lock()
        self.pending_prompts: Deque[QueuedPrompt] = deque()
        self.pending_system_reminders: "OrderedDict[str, SystemReminder]" = OrderedDict()
        self.persistent_system_reminders: "OrderedDict[str, SystemReminder]" = (
            OrderedDict()
        )

    @property
    def is_processing(self) -> bool:
        return self.processing_lock.locked()

    def queue_prompt(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        self.pending_prompts.append(
            QueuedPrompt(content=content, metadata=metadata or {})
        )
        return len(self.pending_prompts)

    def pop_prompt(self) -> Optional[QueuedPrompt]:
        if not self.pending_prompts:
            return None
        return self.pending_prompts.popleft()

    def pending_prompt_count(self) -> int:
        return len(self.pending_prompts)

    def enqueue_system_reminder(
        self,
        key: str,
        message: str,
        topic: str,
        persistent: bool = False,
    ) -> bool:
        reminder = SystemReminder(
            key=key,
            topic=topic,
            message=message,
            persistent=persistent,
        )

        if persistent:
            existing = self.persistent_system_reminders.get(key)
            if existing == reminder:
                return False
            self.persistent_system_reminders[key] = reminder
            return True

        existing = self.pending_system_reminders.get(key)
        if existing == reminder:
            return False
        self.pending_system_reminders[key] = reminder
        return True

    def clear_system_reminder(self, key: str) -> None:
        self.pending_system_reminders.pop(key, None)
        self.persistent_system_reminders.pop(key, None)

    def _render_reminder(self, reminder: SystemReminder) -> str:
        return (
            f'<reminder source="system" topic="{reminder.topic}">'
            f"{reminder.message} "
            "Do not reply to or mention this reminder to the user."
            "</reminder>"
        )

    def refresh_file_reminders(self) -> None:
        active_file_keys = set()
        for file_path in file_freshness_service.get_session_files():
            reminder = file_freshness_service.generate_file_modification_reminder(
                file_path
            )
            reminder_key = f"file:{file_path}"
            if reminder:
                active_file_keys.add(reminder_key)
                self.enqueue_system_reminder(
                    reminder_key,
                    (
                        f"System notice: {reminder} Re-read this file before relying on its previous contents or editing it."
                    ),
                    "file-freshness",
                    persistent=True,
                )
            else:
                self.clear_system_reminder(reminder_key)

        stale_keys = [
            key
            for key in list(self.persistent_system_reminders.keys())
            if key.startswith("file:") and key not in active_file_keys
        ]
        for key in stale_keys:
            self.clear_system_reminder(key)

    def prepare_user_message(self, message: str) -> str:
        self.refresh_file_reminders()
        reminders = list(self.persistent_system_reminders.values())
        reminders.extend(
            reminder
            for key, reminder in self.pending_system_reminders.items()
            if key not in self.persistent_system_reminders
        )

        if not reminders:
            return message

        self.pending_system_reminders.clear()

        prefix = "\n\n".join(self._render_reminder(reminder) for reminder in reminders)
        return f"{prefix}\n\n{message}"
