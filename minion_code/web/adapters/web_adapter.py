#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Output Adapter - SSE implementation for cross-process communication.

This adapter outputs events to an asyncio.Queue for SSE streaming.
It follows the A2A-style input_required pattern for bidirectional interactions.
"""

from typing import List, Optional, Dict, Any, Literal
import asyncio
import time
from dataclasses import dataclass, field, asdict
from enum import Enum

from minion_code.adapters.output_adapter import OutputAdapter


class TaskState(str, Enum):
    """Task lifecycle states (A2A style)"""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InputKind(str, Enum):
    """Types of user input requests"""
    PERMISSION = "permission"
    TEXT = "text"
    CHOICE = "choice"
    FORM = "form"


@dataclass
class PermissionData:
    """Data for permission requests (tool use confirm)"""
    resource_type: str  # "tool", "file", "network", "system"
    resource_name: str
    resource_args: Optional[Dict[str, Any]] = None
    risk_level: str = "medium"  # "low", "medium", "high"


@dataclass
class TextInputData:
    """Data for text input requests"""
    placeholder: str = ""
    default_value: str = ""
    multiline: bool = False
    max_length: Optional[int] = None


@dataclass
class ChoiceData:
    """Data for choice requests"""
    choices: List[Dict[str, Any]] = field(default_factory=list)
    allow_multiple: bool = False
    default_index: int = 0


@dataclass
class InputRequest:
    """Request for user input (A2A input_required)"""
    interaction_id: str
    kind: str  # InputKind value
    title: str
    message: str
    data: Dict[str, Any]
    timeout_seconds: Optional[int] = 300


@dataclass
class SSEEvent:
    """Server-Sent Event data structure"""
    type: str
    data: Dict[str, Any]
    task_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "timestamp": self.timestamp,
            **self.data
        }
        if self.task_id:
            result["task_id"] = self.task_id
        return result


@dataclass
class PendingInteraction:
    """Represents a user interaction waiting for response"""
    interaction_id: str
    kind: str
    data: Dict[str, Any]
    future: asyncio.Future


class WebOutputAdapter(OutputAdapter):
    """
    Web SSE adapter for cross-process frontend communication.

    This adapter:
    1. Outputs events to an asyncio.Queue for SSE streaming
    2. Uses asyncio.Future for blocking interactions (confirm, choice, input)
    3. Follows A2A-style input_required pattern

    Workflow:
    1. Agent calls adapter methods (panel, text, confirm, etc.)
    2. Adapter creates SSEEvent and puts to event_queue
    3. API endpoint reads from event_queue and sends SSE to client
    4. For interactions, adapter creates Future and waits
    5. Client responds via HTTP POST → resolve_interaction() → Future completes
    """

    def __init__(
        self,
        session_id: str,
        task_id: Optional[str] = None,
        timeout_seconds: int = 300
    ):
        """
        Initialize Web adapter.

        Args:
            session_id: Session identifier
            task_id: Current task identifier (set per query)
            timeout_seconds: Default timeout for interactions
        """
        self.session_id = session_id
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds

        # Event queue for SSE output
        self.event_queue: asyncio.Queue[SSEEvent] = asyncio.Queue()

        # Pending interactions waiting for user response
        self._pending_interactions: Dict[str, PendingInteraction] = {}
        self._interaction_counter = 0
        self._message_counter = 0

        # Current task state
        self._task_state = TaskState.SUBMITTED

    def set_task_id(self, task_id: str):
        """Set current task ID for new query."""
        self.task_id = task_id
        self._task_state = TaskState.SUBMITTED

    def _generate_interaction_id(self) -> str:
        """Generate unique interaction ID."""
        self._interaction_counter += 1
        return f"int_{self.session_id}_{self._interaction_counter}"

    def _generate_message_id(self) -> str:
        """Generate unique message ID."""
        self._message_counter += 1
        return f"msg_{self.session_id}_{self._message_counter}"

    async def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit SSE event to queue."""
        event = SSEEvent(
            type=event_type,
            data=data,
            task_id=self.task_id
        )
        await self.event_queue.put(event)

    def _emit_event_sync(self, event_type: str, data: Dict[str, Any]):
        """Emit SSE event synchronously (for non-async methods)."""
        event = SSEEvent(
            type=event_type,
            data=data,
            task_id=self.task_id
        )
        # Use put_nowait for sync context
        try:
            self.event_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Drop event if queue is full

    async def emit_task_status(self, state: TaskState):
        """Emit task status change event."""
        self._task_state = state
        await self._emit_event("task_status", {
            "state": state.value,
            "session_id": self.session_id
        })

    # ========== OutputAdapter interface implementation ==========

    def panel(self, content: str, title: str = "", border_style: str = "blue") -> None:
        """Send panel output as SSE event."""
        self._emit_event_sync("panel", {
            "content": content,
            "title": title,
            "style": border_style
        })

    def table(self, headers: List[str], rows: List[List[str]], title: str = "") -> None:
        """Send table output as SSE event."""
        self._emit_event_sync("table", {
            "headers": headers,
            "rows": rows,
            "title": title
        })

    def text(self, content: str, style: str = "") -> None:
        """Send text output as SSE event."""
        self._emit_event_sync("text", {
            "content": content,
            "style": style
        })

    async def confirm(
        self,
        message: str,
        title: str = "Confirm",
        default: bool = False,
        ok_text: str = "Yes",
        cancel_text: str = "No"
    ) -> bool:
        """
        Request user confirmation via input_required event.

        This method:
        1. Changes task state to input_required
        2. Sends input_required SSE event
        3. Creates Future and waits for response
        4. Changes task state back to working
        """
        interaction_id = self._generate_interaction_id()
        future: asyncio.Future[bool] = asyncio.Future()

        # Store pending interaction
        self._pending_interactions[interaction_id] = PendingInteraction(
            interaction_id=interaction_id,
            kind=InputKind.PERMISSION.value,
            data={
                "message": message,
                "title": title,
                "default": default,
                "ok_text": ok_text,
                "cancel_text": cancel_text
            },
            future=future
        )

        # Change state to input_required
        await self.emit_task_status(TaskState.INPUT_REQUIRED)

        # Send input_required event
        await self._emit_event("input_required", {
            "request": {
                "interaction_id": interaction_id,
                "kind": InputKind.PERMISSION.value,
                "title": title,
                "message": message,
                "data": {
                    "resource_type": "action",
                    "resource_name": title,
                    "default": default,
                    "ok_text": ok_text,
                    "cancel_text": cancel_text
                },
                "timeout_seconds": self.timeout_seconds
            }
        })

        # Wait for user response
        try:
            result = await asyncio.wait_for(future, timeout=self.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return default
        finally:
            self._pending_interactions.pop(interaction_id, None)
            # Change state back to working
            await self.emit_task_status(TaskState.WORKING)

    async def choice(
        self,
        message: str,
        choices: List[str],
        title: str = "Select",
        default_index: int = 0
    ) -> int:
        """
        Request user choice selection via input_required event.

        Returns the selected index (0-based), or -1 if cancelled/timeout.
        """
        interaction_id = self._generate_interaction_id()
        future: asyncio.Future[int] = asyncio.Future()

        self._pending_interactions[interaction_id] = PendingInteraction(
            interaction_id=interaction_id,
            kind=InputKind.CHOICE.value,
            data={
                "message": message,
                "choices": choices,
                "title": title,
                "default_index": default_index
            },
            future=future
        )

        await self.emit_task_status(TaskState.INPUT_REQUIRED)

        await self._emit_event("input_required", {
            "request": {
                "interaction_id": interaction_id,
                "kind": InputKind.CHOICE.value,
                "title": title,
                "message": message,
                "data": {
                    "choices": [{"label": c, "value": i} for i, c in enumerate(choices)],
                    "default_index": default_index
                },
                "timeout_seconds": self.timeout_seconds
            }
        })

        try:
            result = await asyncio.wait_for(future, timeout=self.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return -1
        finally:
            self._pending_interactions.pop(interaction_id, None)
            await self.emit_task_status(TaskState.WORKING)

    async def input(
        self,
        message: str,
        title: str = "Input",
        default: str = "",
        placeholder: str = ""
    ) -> Optional[str]:
        """
        Request user text input via input_required event.

        Returns the input string, or None if cancelled/timeout.
        """
        interaction_id = self._generate_interaction_id()
        future: asyncio.Future[Optional[str]] = asyncio.Future()

        self._pending_interactions[interaction_id] = PendingInteraction(
            interaction_id=interaction_id,
            kind=InputKind.TEXT.value,
            data={
                "message": message,
                "title": title,
                "default": default,
                "placeholder": placeholder
            },
            future=future
        )

        await self.emit_task_status(TaskState.INPUT_REQUIRED)

        await self._emit_event("input_required", {
            "request": {
                "interaction_id": interaction_id,
                "kind": InputKind.TEXT.value,
                "title": title,
                "message": message,
                "data": {
                    "placeholder": placeholder,
                    "default_value": default
                },
                "timeout_seconds": self.timeout_seconds
            }
        })

        try:
            result = await asyncio.wait_for(future, timeout=self.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_interactions.pop(interaction_id, None)
            await self.emit_task_status(TaskState.WORKING)

    def print(self, *args, **kwargs) -> None:
        """Generic print - converts to text output."""
        content = " ".join(str(arg) for arg in args)
        self.text(content)

    # ========== Interaction resolution ==========

    def resolve_interaction(self, interaction_id: str, result: Any) -> bool:
        """
        Resolve a pending interaction with user's response.

        This method should be called by the HTTP endpoint when
        user responds to an input_required event.

        Args:
            interaction_id: The interaction ID from the request
            result: The user's response (bool, int, or str depending on kind)

        Returns:
            True if interaction was found and resolved, False otherwise
        """
        interaction = self._pending_interactions.get(interaction_id)
        if interaction and not interaction.future.done():
            interaction.future.set_result(result)
            return True
        return False

    def cancel_interaction(self, interaction_id: str) -> bool:
        """
        Cancel a pending interaction.

        Sets appropriate default value based on interaction kind.
        """
        interaction = self._pending_interactions.get(interaction_id)
        if interaction and not interaction.future.done():
            if interaction.kind == InputKind.PERMISSION.value:
                interaction.future.set_result(False)
            elif interaction.kind == InputKind.CHOICE.value:
                interaction.future.set_result(-1)
            elif interaction.kind == InputKind.TEXT.value:
                interaction.future.set_result(None)
            return True
        return False

    def get_pending_interaction(self, interaction_id: str) -> Optional[PendingInteraction]:
        """Get a pending interaction by ID."""
        return self._pending_interactions.get(interaction_id)

    def has_pending_interactions(self) -> bool:
        """Check if there are any pending interactions."""
        return len(self._pending_interactions) > 0

    # ========== Streaming helpers ==========

    async def emit_content(self, chunk: str):
        """Emit streaming content chunk."""
        await self._emit_event("content", {"chunk": chunk})

    async def emit_thinking(self, chunk: str):
        """Emit thinking/reasoning content chunk."""
        await self._emit_event("thinking", {"chunk": chunk})

    async def emit_tool_call(self, name: str, args: Dict[str, Any]):
        """Emit tool call event."""
        await self._emit_event("tool_call", {
            "name": name,
            "args": args
        })

    async def emit_tool_result(self, success: bool, output: str):
        """Emit tool result event."""
        await self._emit_event("tool_result", {
            "success": success,
            "output": output
        })

    async def emit_error(self, message: str, code: Optional[str] = None):
        """Emit error event."""
        data = {"message": message}
        if code:
            data["code"] = code
        await self._emit_event("error", data)

    async def emit_done(self):
        """Emit stream end event."""
        await self._emit_event("done", {})

    # ========== Tool permission helper ==========

    async def confirm_tool_use(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        description: str = ""
    ) -> bool:
        """
        Request user permission for tool execution.

        This is a convenience method for tool permission confirmation.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments to the tool
            description: Human-readable description of what the tool will do

        Returns:
            True if user allows, False if denied or timeout
        """
        interaction_id = self._generate_interaction_id()
        future: asyncio.Future[bool] = asyncio.Future()

        self._pending_interactions[interaction_id] = PendingInteraction(
            interaction_id=interaction_id,
            kind=InputKind.PERMISSION.value,
            data={
                "tool_name": tool_name,
                "tool_args": tool_args,
                "description": description
            },
            future=future
        )

        await self.emit_task_status(TaskState.INPUT_REQUIRED)

        await self._emit_event("input_required", {
            "request": {
                "interaction_id": interaction_id,
                "kind": InputKind.PERMISSION.value,
                "title": f"Allow {tool_name}?",
                "message": description or f"Agent wants to execute {tool_name}",
                "data": {
                    "resource_type": "tool",
                    "resource_name": tool_name,
                    "resource_args": tool_args,
                    "risk_level": "medium"
                },
                "timeout_seconds": self.timeout_seconds
            }
        })

        try:
            result = await asyncio.wait_for(future, timeout=self.timeout_seconds)
            return result
        except asyncio.TimeoutError:
            return False
        finally:
            self._pending_interactions.pop(interaction_id, None)
            await self.emit_task_status(TaskState.WORKING)
