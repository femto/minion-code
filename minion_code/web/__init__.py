"""
Web API module for minion-code.

Provides FastAPI-based HTTP/SSE server for cross-process frontend communication.
"""

from .server import create_app, run_server

__all__ = ["create_app", "run_server"]
