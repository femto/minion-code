#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interactions API endpoint.

Handles user responses to input_required events (permission, text input, choice).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Union, Optional, Any

from ..services.session_manager import session_manager

router = APIRouter(prefix="/api/tasks", tags=["interactions"])


class InteractionResponse(BaseModel):
    """Request body for responding to an interaction."""
    interaction_id: str = Field(..., description="Interaction ID from input_required event")
    response: Any = Field(
        ...,
        description="User's response: bool for permission, int for choice, str for text"
    )


class InteractionResult(BaseModel):
    """Response after processing interaction."""
    status: str
    interaction_id: str
    task_id: Optional[str] = None


@router.post("/{task_id}/input", response_model=InteractionResult)
async def respond_to_interaction(task_id: str, body: InteractionResponse):
    """
    Respond to an input_required event.

    This endpoint is called when the user responds to a permission request,
    makes a choice, or provides text input.

    The response type depends on the interaction kind:
    - permission: bool (true = allow, false = deny)
    - choice: int (selected index, -1 = cancelled)
    - text: str or null (null = cancelled)

    Example:
        POST /api/tasks/task_123/input
        {
            "interaction_id": "int_456",
            "response": true
        }
    """
    # Find session containing this interaction
    session = session_manager.find_session_by_interaction(body.interaction_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Interaction {body.interaction_id} not found"
        )

    # Verify task_id matches (optional validation)
    if session.current_task_id and session.current_task_id != task_id:
        raise HTTPException(
            status_code=400,
            detail=f"Task ID mismatch: expected {session.current_task_id}, got {task_id}"
        )

    # Resolve the interaction
    resolved = session.adapter.resolve_interaction(body.interaction_id, body.response)
    if not resolved:
        raise HTTPException(
            status_code=400,
            detail=f"Interaction {body.interaction_id} already resolved or not found"
        )

    return InteractionResult(
        status="ok",
        interaction_id=body.interaction_id,
        task_id=task_id
    )


@router.post("/{task_id}/cancel")
async def cancel_interaction(task_id: str, interaction_id: str):
    """
    Cancel a pending interaction.

    Sets appropriate default value based on interaction type:
    - permission: false (denied)
    - choice: -1 (cancelled)
    - text: null (cancelled)
    """
    session = session_manager.find_session_by_interaction(interaction_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Interaction {interaction_id} not found"
        )

    cancelled = session.adapter.cancel_interaction(interaction_id)
    if not cancelled:
        raise HTTPException(
            status_code=400,
            detail=f"Interaction {interaction_id} already resolved or not found"
        )

    return {
        "status": "cancelled",
        "interaction_id": interaction_id,
        "task_id": task_id
    }


# Alternative endpoint path for convenience
@router.post("/input/{interaction_id}")
async def respond_to_interaction_by_id(interaction_id: str, response: Any):
    """
    Alternative endpoint to respond by interaction ID only.

    Useful when task_id is not readily available.
    """
    session = session_manager.find_session_by_interaction(interaction_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Interaction {interaction_id} not found"
        )

    resolved = session.adapter.resolve_interaction(interaction_id, response)
    if not resolved:
        raise HTTPException(
            status_code=400,
            detail=f"Interaction {interaction_id} already resolved or not found"
        )

    return {
        "status": "ok",
        "interaction_id": interaction_id,
        "task_id": session.current_task_id
    }
