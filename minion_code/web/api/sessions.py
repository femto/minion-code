#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sessions API endpoints.

Handles session creation, retrieval, and management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from ..services.session_manager import session_manager, HistoryMode

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    """Request body for creating a session."""
    project_path: str = Field(default=".", description="Working directory for the session")
    history_mode: Optional[HistoryMode] = Field(
        default=None,
        description="History mode: 'full' (stateless) or 'incremental' (stateful)"
    )


class SessionResponse(BaseModel):
    """Response for session operations."""
    session_id: str
    project_path: str
    history_mode: str
    created_at: float
    message_count: int = 0


class SessionListResponse(BaseModel):
    """Response for listing sessions."""
    sessions: List[Dict[str, Any]]


@router.post("", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    Create a new session.

    Returns a session ID that can be used for subsequent chat requests.
    """
    try:
        session = await session_manager.create_session(
            project_path=request.project_path,
            history_mode=request.history_mode
        )

        return SessionResponse(
            session_id=session.session_id,
            project_path=session.project_path,
            history_mode=session.history_mode,
            created_at=session.created_at,
            message_count=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=SessionListResponse)
async def list_sessions():
    """List all active sessions."""
    sessions = session_manager.list_sessions()
    return SessionListResponse(sessions=sessions)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    Get session details.

    Returns session info including message history.
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session_manager.get_messages(session)

    return SessionResponse(
        session_id=session.session_id,
        project_path=session.project_path,
        history_mode=session.history_mode,
        created_at=session.created_at,
        message_count=len(messages)
    )


@router.get("/{session_id}/messages")
async def get_session_messages(session_id: str):
    """
    Get message history for a session.

    Returns all messages in the conversation.
    """
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = session_manager.get_messages(session)

    return {"session_id": session_id, "messages": messages}


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    deleted = await session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "ok", "session_id": session_id}


@router.post("/{session_id}/abort")
async def abort_session_task(session_id: str):
    """
    Abort the current task in a session.

    Sends abort signal to stop ongoing processing.
    """
    aborted = await session_manager.abort_task(session_id)
    if not aborted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "ok", "session_id": session_id}
