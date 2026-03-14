#!/usr/bin/env python3
"""Read incremental output for managed background tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from minion.tools import BaseTool

from ..utils.background_tasks import get_background_task_manager


class TaskOutputTool(BaseTool):
    """Read logs from a managed background task."""

    name = "TaskOutput"
    description = "Read incremental output from a background task by task_id."
    readonly = True
    inputs = {
        "task_id": {
            "type": "string",
            "description": "The task_id returned by bash or TaskCreate.",
        },
        "offset": {
            "type": "integer",
            "description": "Byte offset to resume reading from. Defaults to 0.",
            "nullable": True,
        },
        "limit": {
            "type": "integer",
            "description": "Maximum bytes of output to read. Defaults to 8192.",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None):
        super().__init__()
        self.workdir = Path(workdir).resolve() if workdir else Path.cwd().resolve()

    def forward(
        self, task_id: str, offset: Optional[int] = 0, limit: Optional[int] = 8192
    ) -> dict[str, Any]:
        manager = get_background_task_manager(self.workdir)
        return manager.read_output(task_id, offset=offset or 0, limit=limit or 8192)

    def format_for_observation(self, output: Any) -> str:
        return json.dumps(output, ensure_ascii=False, indent=2)
