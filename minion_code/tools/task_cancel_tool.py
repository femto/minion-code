#!/usr/bin/env python3
"""Stop managed background tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from minion.tools import AsyncBaseTool

from ..utils.background_tasks import get_background_task_manager


class TaskStopTool(AsyncBaseTool):
    """Stop a running background task."""

    name = "TaskStop"
    description = "Stop a running background task by task_id."
    readonly = False
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

    async def forward(self, task_id: str) -> dict[str, Any]:
        manager = get_background_task_manager(self.workdir)
        return await manager.cancel_task(task_id)

    def format_for_observation(self, output: Any) -> str:
        return json.dumps(output, ensure_ascii=False, indent=2)
