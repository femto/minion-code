#!/usr/bin/env python3
"""Read details for managed background tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from minion.tools import BaseTool

from ..utils.background_tasks import get_background_task_manager


class TaskGetTool(BaseTool):
    """Return structured details for a background task."""

    name = "TaskGet"
    description = "Get the current details of a background task by task_id."
    readonly = True
    inputs = {
        "task_id": {
            "type": "string",
            "description": "The task_id returned by bash or TaskCreate.",
        }
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None):
        super().__init__()
        self.workdir = Path(workdir).resolve() if workdir else Path.cwd().resolve()

    def forward(self, task_id: str) -> dict[str, Any]:
        manager = get_background_task_manager(self.workdir)
        record = manager.get_record(task_id)
        if record is None:
            return {"task_id": task_id, "status": "missing", "error": "Task not found"}
        return record.to_dict()

    def format_for_observation(self, output: Any) -> str:
        return json.dumps(output, ensure_ascii=False, indent=2)
