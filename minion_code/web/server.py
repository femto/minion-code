#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI Web Server for minion-code.

Provides HTTP/SSE API for cross-process frontend communication.
"""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat_router, sessions_router, interactions_router

logger = logging.getLogger(__name__)


def create_app(
    title: str = "Minion Code API",
    version: str = "1.0.0",
    cors_origins: Optional[list] = None,
) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        title: API title
        version: API version
        cors_origins: Allowed CORS origins (default: localhost:3000, localhost:5173)

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        version=version,
        description="""
Minion Code Web API

Provides streaming chat interface with:
- SSE (Server-Sent Events) for real-time responses
- A2A-style input_required for bidirectional interactions
- Session management with full/incremental history modes

## Endpoints

### Sessions
- `POST /api/sessions` - Create new session
- `GET /api/sessions` - List active sessions
- `GET /api/sessions/{id}` - Get session details
- `GET /api/sessions/{id}/messages` - Get message history
- `DELETE /api/sessions/{id}` - Delete session
- `POST /api/sessions/{id}/abort` - Abort current task

### Chat
- `POST /api/chat/{session_id}` - Send message, receive SSE stream

### Interactions
- `POST /api/tasks/{task_id}/input` - Respond to input_required event
- `POST /api/tasks/{task_id}/cancel` - Cancel pending interaction

## SSE Event Types

- `task_status` - Task state changes
- `content` - Streaming text content
- `thinking` - LLM reasoning content
- `tool_call` - Tool invocation
- `tool_result` - Tool execution result
- `input_required` - Request for user input
- `error` - Error message

## History Modes

- `full` - Each request creates new agent, loads full history (stateless, scalable)
- `incremental` - Reuse agent, only send new message (stateful, low latency)
        """,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration
    if cors_origins is None:
        cors_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(sessions_router)
    app.include_router(chat_router)
    app.include_router(interactions_router)

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    # Root endpoint
    @app.get("/")
    async def root():
        return {"name": title, "version": version, "docs": "/docs", "health": "/health"}

    return app


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info",
):
    """
    Run the web server.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
        log_level: Logging level
    """
    import uvicorn

    logger.info(f"Starting Minion Code Web API on {host}:{port}")

    uvicorn.run(
        "minion_code.web.server:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )


# For direct module execution
if __name__ == "__main__":
    run_server()
