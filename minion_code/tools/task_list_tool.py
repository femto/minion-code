#!/usr/bin/env python3
"""List managed background tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from minion.tools import BaseTool

from ..utils.background_tasks import get_background_task_manager


class TaskListTool(BaseTool):
    """List known background tasks."""

    name = "TaskList"
    description = "List background tasks, optionally filtered by status or kind."
    readonly = True
    inputs = {
        "status": {
            "type": "string",
            "description": "Optional status filter: queued, running, completed, failed, cancelled.",
            "nullable": True,
        },
        "kind": {
            "type": "string",
            "description": "Optional kind filter: bash or subagent.",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None):
        super().__init__()
        self.workdir = Path(workdir).resolve() if workdir else Path.cwd().resolve()

    def forward(
        self, status: Optional[str] = None, kind: Optional[str] = None
    ) -> dict[str, Any]:
        manager = get_background_task_manager(self.workdir)
        records = manager.list_records(status=status, kind=kind)
        return {"tasks": [record.to_dict() for record in records]}

    def format_for_observation(self, output: Any) -> str:
        return json.dumps(output, ensure_ascii=False, indent=2)
