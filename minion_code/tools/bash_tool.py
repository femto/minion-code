#!/usr/bin/env python3
"""Bash command execution with automatic backgrounding for long jobs."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional

from minion.tools import AsyncBaseTool

from ..utils.background_tasks import get_background_task_manager


class BashTool(AsyncBaseTool):
    """Execute bash commands with foreground and background modes."""

    name = "bash"
    description = "Execute bash commands, automatically moving long-running jobs to the background."
    readonly = False
    inputs = {
        "command": {"type": "string", "description": "Bash command to execute"},
        "timeout": {
            "type": "integer",
            "description": "Maximum runtime in seconds before the job is terminated.",
            "nullable": True,
        },
        "background": {
            "type": "boolean",
            "description": "If true, start the command in the background and return a task_id immediately.",
            "nullable": True,
        },
        "auto_background_after": {
            "type": "integer",
            "description": "How long to wait in the foreground before returning a background task handle.",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workdir = Path(workdir).resolve() if workdir else Path.cwd().resolve()

    async def forward(
        self,
        command: str,
        timeout: Optional[int] = 1800,
        background: Optional[bool] = False,
        auto_background_after: Optional[int] = 180,
    ) -> dict[str, Any]:
        """Execute a bash command and background it if it runs too long."""
        dangerous_commands = ["rm -rf", "sudo", "su ", "chmod 777", "mkfs", "dd if="]
        lowered_command = command.lower()
        if any(dangerous in lowered_command for dangerous in dangerous_commands):
            return {
                "mode": "foreground",
                "status": "failed",
                "command": command,
                "error": f"Dangerous command prohibited: {command}",
            }

        manager = get_background_task_manager(self.workdir)
        record = await manager.start_process_task(
            command=command,
            cwd=self.workdir,
            timeout=timeout,
            title=command,
            metadata={"tool": self.name},
        )

        if background:
            return {
                "mode": "background",
                "status": record.status,
                "task_id": record.task_id,
                "command": command,
                "message": "Command started in the background.",
            }

        wait_seconds = max(0, auto_background_after or 0)
        if wait_seconds == 0:
            return {
                "mode": "background",
                "status": record.status,
                "task_id": record.task_id,
                "command": command,
                "message": "Command moved to the background immediately.",
            }

        deadline = asyncio.get_event_loop().time() + wait_seconds
        while asyncio.get_event_loop().time() < deadline:
            current = manager.get_record(record.task_id)
            if current is None:
                break
            if current.status in {"completed", "failed", "cancelled"}:
                output = manager.read_output(record.task_id, offset=0, limit=1_000_000)
                return {
                    "mode": "foreground",
                    "status": current.status,
                    "task_id": current.task_id,
                    "command": command,
                    "exit_code": current.exit_code,
                    "output": output["content"],
                    "error": current.error,
                }
            await asyncio.sleep(0.2)

        current = manager.get_record(record.task_id) or record
        return {
            "mode": "background",
            "status": current.status,
            "task_id": current.task_id,
            "command": command,
            "message": (
                f"Command is still running after {wait_seconds} seconds and has been moved to the background."
            ),
        }

    def format_for_observation(self, output: Any) -> str:
        if isinstance(output, dict):
            return json.dumps(output, ensure_ascii=False, indent=2)
        return str(output)
