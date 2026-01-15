#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chat API endpoint with SSE streaming.

Handles chat messages and returns streaming responses via Server-Sent Events.
"""

import asyncio
import json
import logging
from typing import Optional, AsyncGenerator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.session_manager import session_manager, HistoryMode
from ..adapters.web_adapter import TaskState, SSEEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(..., description="User message content")
    history_mode: Optional[HistoryMode] = Field(
        default=None, description="Override session's history mode for this request"
    )


def format_sse_event(event: SSEEvent) -> str:
    """Format event as SSE string."""
    data = json.dumps(event.to_dict(), ensure_ascii=False)
    return f"data: {data}\n\n"


def format_sse_done() -> str:
    """Format done event."""
    return "data: [DONE]\n\n"


async def process_chat_stream(
    session_id: str, message: str, history_mode: Optional[HistoryMode] = None
) -> AsyncGenerator[str, None]:
    """
    Process chat message and yield SSE events.

    This is the core streaming logic:
    1. Get or create session
    2. Create task ID and update adapter
    3. Get agent (based on history mode)
    4. Run agent and forward events
    5. Save messages to storage
    """
    # Get session
    session = await session_manager.get_session(session_id)
    if not session:
        yield format_sse_event(
            SSEEvent(
                type="error",
                data={"message": "Session not found", "code": "SESSION_NOT_FOUND"},
            )
        )
        yield format_sse_done()
        return

    # Use request history_mode or session default
    effective_history_mode = history_mode or session.history_mode

    # Generate task ID
    task_id = session.generate_task_id()
    session.current_task_id = task_id
    session.adapter.set_task_id(task_id)

    # Reset abort event
    session.abort_event.clear()

    try:
        # Emit task started
        await session.adapter.emit_task_status(TaskState.SUBMITTED)
        yield format_sse_event(
            SSEEvent(
                type="task_status",
                data={"state": TaskState.SUBMITTED.value, "task_id": task_id},
                task_id=task_id,
            )
        )

        # Get or create agent
        agent = await session_manager.get_or_create_agent(session)

        # Emit working status
        await session.adapter.emit_task_status(TaskState.WORKING)
        yield format_sse_event(
            SSEEvent(
                type="task_status",
                data={"state": TaskState.WORKING.value, "task_id": task_id},
                task_id=task_id,
            )
        )

        # Save user message
        session_manager.save_message(session, "user", message)

        # Run agent with streaming
        full_response = ""

        # Create concurrent tasks for agent execution and event forwarding
        async def run_agent():
            nonlocal full_response
            async for chunk in agent.run_async(message, stream=True):
                # Check for abort
                if session.abort_event.is_set():
                    break

                chunk_type = getattr(chunk, "chunk_type", "text")
                chunk_content = getattr(chunk, "content", str(chunk))
                chunk_metadata = getattr(chunk, "metadata", {})

                if chunk_type == "step_start":
                    await session.adapter._emit_event(
                        "step_start", {"content": chunk_content}
                    )
                elif chunk_type == "thinking":
                    await session.adapter.emit_thinking(chunk_content)
                elif chunk_type == "code_start":
                    await session.adapter._emit_event(
                        "code_start",
                        {
                            "code": chunk_content,
                            "language": chunk_metadata.get("language", ""),
                        },
                    )
                elif chunk_type == "code_result":
                    await session.adapter.emit_tool_result(
                        success=chunk_metadata.get("success", True),
                        output=chunk_content,
                    )
                elif chunk_type == "tool_call":
                    await session.adapter.emit_tool_call(
                        name=chunk_metadata.get("tool_name", ""),
                        args=chunk_metadata.get("args", {}),
                    )
                elif chunk_type in ("final_answer", "agent_response", "completion"):
                    final_content = (
                        getattr(chunk, "answer", chunk_content) or chunk_content
                    )
                    full_response = str(final_content)
                    await session.adapter.emit_content(full_response)
                else:
                    # Default: treat as content
                    if chunk_content:
                        await session.adapter.emit_content(chunk_content)

        # Start agent execution in background
        agent_task = asyncio.create_task(run_agent())

        # Forward events from adapter queue to SSE
        try:
            while True:
                try:
                    # Try to get event with timeout
                    event = await asyncio.wait_for(
                        session.adapter.event_queue.get(), timeout=0.1
                    )
                    yield format_sse_event(event)
                except asyncio.TimeoutError:
                    pass

                # Check if agent is done
                if agent_task.done():
                    # Drain remaining events
                    while not session.adapter.event_queue.empty():
                        event = await session.adapter.event_queue.get()
                        yield format_sse_event(event)

                    # Check for exception
                    if agent_task.exception():
                        raise agent_task.exception()

                    break

                # Check for abort
                if session.abort_event.is_set():
                    agent_task.cancel()
                    yield format_sse_event(
                        SSEEvent(
                            type="task_status",
                            data={
                                "state": TaskState.CANCELLED.value,
                                "task_id": task_id,
                            },
                            task_id=task_id,
                        )
                    )
                    break

        except Exception as e:
            logger.error(f"Error in event forwarding: {e}")
            raise

        # Save assistant response
        if full_response:
            session_manager.save_message(session, "assistant", full_response)

        # Emit completed status
        await session.adapter.emit_task_status(TaskState.COMPLETED)
        yield format_sse_event(
            SSEEvent(
                type="task_status",
                data={"state": TaskState.COMPLETED.value, "task_id": task_id},
                task_id=task_id,
            )
        )

    except asyncio.CancelledError:
        yield format_sse_event(
            SSEEvent(
                type="task_status",
                data={"state": TaskState.CANCELLED.value, "task_id": task_id},
                task_id=task_id,
            )
        )
    except Exception as e:
        logger.exception(f"Error processing chat: {e}")
        await session.adapter.emit_error(str(e))
        yield format_sse_event(
            SSEEvent(type="error", data={"message": str(e)}, task_id=task_id)
        )
        await session.adapter.emit_task_status(TaskState.FAILED)
        yield format_sse_event(
            SSEEvent(
                type="task_status",
                data={"state": TaskState.FAILED.value, "task_id": task_id},
                task_id=task_id,
            )
        )
    finally:
        session.current_task_id = None
        yield format_sse_done()


@router.post("/{session_id}")
async def chat(session_id: str, request: ChatRequest):
    """
    Send a chat message and receive streaming response.

    Returns a Server-Sent Events stream with the following event types:
    - task_status: Task state changes (submitted, working, input_required, completed, failed)
    - content: Streaming text content
    - thinking: LLM reasoning content
    - tool_call: Tool invocation
    - tool_result: Tool execution result
    - input_required: Request for user input (permission, text, choice)
    - error: Error message
    - done: Stream end marker ([DONE])

    For input_required events, respond via POST /api/tasks/{task_id}/input
    """
    # Validate session exists
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return StreamingResponse(
        process_chat_stream(session_id, request.message, request.history_mode),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
