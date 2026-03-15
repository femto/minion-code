#!/usr/bin/env python3
"""TaskCreate tool for running subagents as managed jobs."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from minion.tools import AsyncBaseTool
from minion.types import AgentState

from ..utils.background_tasks import TaskRecord, get_background_task_manager

SUPPORTED_SUBAGENT_TOOL_NAMES = {
    "TaskCreate",
    "TaskGet",
    "TaskList",
    "TaskOutput",
    "TaskStop",
    "bash",
    "file_edit",
    "file_read",
    "file_write",
    "glob",
    "grep",
    "ls",
    "multi_edit",
    "python_interpreter",
    "Skill",
    "todo_read",
    "todo_write",
    "user_input",
    "web_fetch",
    "web_search",
}


def generate_task_tool_prompt() -> str:
    """Generate the dynamic TaskCreate tool description."""
    from ..subagents import load_subagents

    registry = load_subagents()
    subagents = registry.list_all()

    if not subagents:
        return """Launch a subagent job to handle a complex task.

No subagents are currently available."""

    subagent_lines = registry.generate_tool_description_lines()
    return f"""Launch a subagent job to handle complex, multi-step tasks.

Available agent types and the tools they have access to:
{subagent_lines}

This tool can finish in the foreground for short tasks or return a background task handle for long tasks.

Use this tool when:
- The work is complex enough to delegate to a subagent
- You want a subagent to continue running in the background
- You need a separate task_id so you can check status and output later
"""


class TaskCreateTool(AsyncBaseTool):
    """Launch a subagent and optionally background it."""

    name = "TaskCreate"
    description = "Launch a subagent job to handle complex tasks."
    readonly = False
    needs_state = True
    inputs = {
        "description": {
            "type": "string",
            "description": "A short description of the task.",
        },
        "prompt": {
            "type": "string",
            "description": "The prompt the subagent should execute.",
        },
        "model_name": {
            "type": "string",
            "description": "Optional model override for the subagent.",
            "nullable": True,
        },
        "subagent_type": {
            "type": "string",
            "description": "Which subagent type to launch. Defaults to general-purpose.",
            "nullable": True,
        },
        "background": {
            "type": "boolean",
            "description": "If true, launch the subagent in the background and return a task_id immediately.",
            "nullable": True,
        },
        "auto_background_after": {
            "type": "integer",
            "description": "How long to wait before returning a background task handle.",
            "nullable": True,
        },
        "timeout": {
            "type": "integer",
            "description": "Reserved for future use. Included for parity with bash.",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None):
        super().__init__()
        self._registry = None
        self._workdir = Path(workdir).resolve() if workdir else Path.cwd().resolve()
        self.description = generate_task_tool_prompt()

    @property
    def registry(self):
        """Load subagents lazily."""
        if self._registry is None:
            from ..subagents import load_subagents

            self._registry = load_subagents()
        return self._registry

    async def forward(
        self,
        description: str,
        prompt: str,
        model_name: Optional[str] = None,
        subagent_type: Optional[str] = None,
        background: Optional[bool] = False,
        auto_background_after: Optional[int] = 180,
        timeout: Optional[int] = None,
        *,
        state: AgentState,
    ) -> dict[str, Any]:
        """Launch a subagent job and return either a result or a background task handle."""
        del state
        validation = self._validate_input(
            description=description,
            prompt=prompt,
            model_name=model_name,
            subagent_type=subagent_type,
        )
        if not validation["valid"]:
            return {
                "mode": "foreground",
                "status": "failed",
                "error": validation["message"],
            }

        agent_type = subagent_type or "general-purpose"
        subagent_config = self.registry.get(agent_type)
        try:
            allowed_tool_names = self._get_filtered_tools(subagent_config.tools)
        except ValueError as exc:
            return {
                "mode": "foreground",
                "status": "failed",
                "error": str(exc),
            }
        workdir = self._workdir
        manager = get_background_task_manager(workdir)

        async def run_subagent(record: TaskRecord) -> str:
            from ..agents.code_agent import MinionCodeAgent

            effective_prompt = prompt
            if subagent_config.system_prompt:
                effective_prompt = f"{subagent_config.system_prompt}\n\n{prompt}"

            effective_model = model_name or "gpt-4o-mini"
            if not model_name and subagent_config.model_name != "inherit":
                effective_model = subagent_config.model_name

            manager.append_log(
                record.task_id,
                f"[task] {description}\n[subagent] {agent_type}\n[model] {effective_model}\n\n",
            )

            agent = await MinionCodeAgent.create(
                name=f"Task Agent ({agent_type})",
                llm=effective_model,
                system_prompt=(
                    effective_prompt if subagent_config.system_prompt else None
                ),
                workdir=workdir,
                allowed_tool_names=allowed_tool_names,
                readonly_only=subagent_config.readonly,
                decay_enabled=True,
                decay_ttl_steps=3,
                decay_min_size=100_000,
            )

            final_text = ""
            async for chunk in await agent.run_async(prompt, stream=True):
                chunk_type = getattr(chunk, "chunk_type", "text")
                chunk_content = getattr(chunk, "content", str(chunk)) or ""
                chunk_metadata = getattr(chunk, "metadata", {}) or {}

                if chunk_type == "tool_call":
                    tool_name = chunk_metadata.get("tool_name", "unknown")
                    args = chunk_metadata.get("args", {})
                    manager.append_log(
                        record.task_id,
                        f"\n[tool] {tool_name} {json.dumps(args, ensure_ascii=False)}\n",
                    )
                elif chunk_type in ("thinking", "text", "content"):
                    if chunk_content:
                        manager.append_log(record.task_id, chunk_content)
                elif chunk_type in ("agent_response", "final_answer", "completion"):
                    final_text = str(getattr(chunk, "answer", chunk_content) or "")
                    if final_text:
                        manager.append_log(record.task_id, f"\n{final_text}\n")
                elif chunk_type == "error" and chunk_content:
                    manager.append_log(record.task_id, f"\n[error] {chunk_content}\n")

            return final_text

        record = await manager.start_async_task(
            title=description,
            cwd=workdir,
            coroutine_factory=run_subagent,
            timeout=timeout,
            metadata={
                "subagent_type": agent_type,
                "prompt": prompt,
                "description": description,
            },
        )

        if background:
            return {
                "mode": "background",
                "status": record.status,
                "task_id": record.task_id,
                "subagent_type": agent_type,
                "message": "Subagent task started in the background.",
            }

        wait_seconds = max(0, auto_background_after or 0)
        if wait_seconds == 0:
            return {
                "mode": "background",
                "status": record.status,
                "task_id": record.task_id,
                "subagent_type": agent_type,
                "message": "Subagent task moved to the background immediately.",
            }

        deadline = asyncio.get_event_loop().time() + wait_seconds
        while asyncio.get_event_loop().time() < deadline:
            current = manager.get_record(record.task_id)
            if current is None:
                break
            if current.status in {"completed", "failed", "cancelled"}:
                return {
                    "mode": "foreground",
                    "status": current.status,
                    "task_id": current.task_id,
                    "subagent_type": agent_type,
                    "result": current.result or "",
                    "error": current.error,
                }
            await asyncio.sleep(0.2)

        current = manager.get_record(record.task_id) or record
        return {
            "mode": "background",
            "status": current.status,
            "task_id": current.task_id,
            "subagent_type": agent_type,
            "message": (
                f"Subagent task is still running after {wait_seconds} seconds and has been moved to the background."
            ),
        }

    def _get_filtered_tools(
        self, tool_filter: Union[str, List[str]]
    ) -> Optional[List[str]]:
        if tool_filter == "*" or (
            isinstance(tool_filter, list) and "*" in tool_filter
        ):
            return None

        if isinstance(tool_filter, str):
            selected_tools = [tool_filter]
        else:
            selected_tools = list(tool_filter)

        unknown_tools = sorted(
            tool_name
            for tool_name in selected_tools
            if tool_name not in SUPPORTED_SUBAGENT_TOOL_NAMES
        )
        if unknown_tools:
            raise ValueError(
                "Subagent requested unsupported tools: "
                + ", ".join(unknown_tools)
            )

        return selected_tools

    def _validate_input(
        self,
        description: str,
        prompt: str,
        model_name: Optional[str] = None,
        subagent_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        del model_name
        if not description or not isinstance(description, str):
            return {
                "valid": False,
                "message": "Description is required and must be a string",
            }
        if not prompt or not isinstance(prompt, str):
            return {
                "valid": False,
                "message": "Prompt is required and must be a string",
            }
        if subagent_type and not self.registry.exists(subagent_type):
            available_types = self.registry.list_names()
            return {
                "valid": False,
                "message": (
                    f"Agent type '{subagent_type}' does not exist. Available types: {', '.join(available_types)}"
                ),
            }
        return {"valid": True}

    @classmethod
    def get_available_agent_types(cls) -> List[str]:
        from ..subagents import get_available_subagents

        return [subagent.name for subagent in get_available_subagents()]

    @classmethod
    def get_agent_description(cls, agent_type: str) -> Optional[Dict[str, Any]]:
        from ..subagents import get_subagent_registry

        registry = get_subagent_registry()
        subagent = registry.get(agent_type)
        if subagent:
            return {
                "description": subagent.description,
                "when_to_use": subagent.when_to_use,
                "tools": subagent.tools,
                "readonly": subagent.readonly,
            }
        return None

    def format_for_observation(self, output: Any) -> str:
        if isinstance(output, dict):
            return json.dumps(output, ensure_ascii=False, indent=2)
        return str(output)
