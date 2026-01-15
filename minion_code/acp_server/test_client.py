#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple ACP client for testing minion-code ACP agent.

Usage:
    python -m minion_code.acp_server.test_client
    python -m minion_code.acp_server.test_client "your prompt here"
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

from acp import spawn_agent_process, text_block
from acp.interfaces import Client


class TestClient(Client):
    """Simple client that prints all updates."""

    async def request_permission(self, options, session_id, tool_call, **kwargs: Any):
        """Auto-accept all permissions for testing."""
        print(f"[PERMISSION] {tool_call}")
        return {"outcome": {"outcome": "accepted"}}

    async def session_update(self, session_id, update, **kwargs):
        """Print all session updates."""
        update_type = type(update).__name__

        # Format based on update type
        if hasattr(update, "delta"):
            # AgentMessageChunk or AgentThoughtChunk
            content = update.delta
            if update_type == "AgentThoughtChunk":
                print(f"[THOUGHT] {content}", end="", flush=True)
            else:
                print(f"{content}", end="", flush=True)
        elif hasattr(update, "tool_call_id"):
            # ToolCallStart or ToolCallProgress
            # Check session_update to distinguish them
            session_update_type = getattr(update, "session_update", None)
            if session_update_type == "tool_call":
                # ToolCallStart
                print(f"\n[TOOL START] {update.title} (id={update.tool_call_id})")
                # Print content if available
                if hasattr(update, "content") and update.content:
                    for c in update.content:
                        if hasattr(c, "content") and hasattr(c.content, "text"):
                            print(f"  Code:\n{c.content.text}")
            elif session_update_type == "tool_call_update":
                # ToolCallProgress
                status = getattr(update, "status", "unknown")
                print(f"\n[TOOL {status.upper()}] id={update.tool_call_id}")
                # Print content if available
                if hasattr(update, "content") and update.content:
                    for c in update.content:
                        if hasattr(c, "content") and hasattr(c.content, "text"):
                            print(f"  Result: {c.content.text}")
        else:
            print(f"\n[UPDATE] {update_type}: {update}")


async def main(prompt: str = "Hello! What can you do?") -> None:
    """Run the test client."""
    print(f"Starting minion-code ACP agent...")
    print(f"Prompt: {prompt}")
    print("=" * 60)

    # Spawn the minion-code ACP agent
    async with spawn_agent_process(
        TestClient(), sys.executable, "-m", "minion_code.acp_server.main"
    ) as (conn, proc):
        print("Agent spawned, initializing...")

        # Initialize
        init_response = await conn.initialize(protocol_version=1)
        print(
            f"Initialized: {init_response.agent_info.name} v{init_response.agent_info.version}"
        )

        # Create session
        cwd = str(Path.cwd())
        session = await conn.new_session(cwd=cwd, mcp_servers=[])
        print(f"Session created: {session.session_id}")
        print("=" * 60)
        print()

        # Send prompt
        response = await conn.prompt(
            session_id=session.session_id,
            prompt=[text_block(prompt)],
        )

        print()
        print("=" * 60)
        print(f"Response stop_reason: {response.stop_reason}")


if __name__ == "__main__":
    # Get prompt from command line or use default
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Hello! What can you do?"
    asyncio.run(main(prompt))
