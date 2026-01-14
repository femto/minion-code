#!/usr/bin/env python3
"""
Task Tool for launching specialized agents to handle complex, multi-step tasks.
Uses SubagentRegistry to dynamically manage available agent types.
"""

import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from minion.tools import AsyncBaseTool
from minion.types import AgentState


def generate_task_tool_prompt() -> str:
    """
    Generate the complete Task tool prompt including available subagents.
    This is used to generate the Task tool description dynamically.

    Returns:
        Complete task tool prompt with all available subagents
    """
    from ..subagents import load_subagents

    registry = load_subagents()
    subagents = registry.list_all()

    if not subagents:
        return """Launch a new agent to handle complex, multi-step tasks autonomously.

No subagents are currently available."""

    # Generate subagent descriptions
    subagent_lines = registry.generate_tool_description_lines()

    return f"""Launch a new agent to handle complex, multi-step tasks autonomously.

Available agent types and the tools they have access to:
{subagent_lines}

When using the Task tool, you must specify a subagent_type parameter to select which agent type to use. Default is "general-purpose".

When to use the Task tool:
- For complex, multi-step tasks that require specialized expertise
- When you need to delegate a complete subtask to a focused agent
- For exploration tasks (use "Explore" subagent)
- For planning and architecture design (use "Plan" subagent)
- For documentation lookup (use "claude-code-guide" subagent)

When NOT to use the Task tool:
- If you want to read a specific file path, use the file_read tool instead
- For simple grep searches, use the grep tool directly
- For single bash commands, use the bash tool directly
- For simple questions you can answer directly without tools

Usage notes:
1. Each agent invocation is stateless and autonomous
2. Provide detailed task descriptions for best results
3. Choose the appropriate subagent_type for your specific task
4. Read-only subagents (Explore, Plan) cannot modify files

Example usage:
- Task(description="Explore auth", prompt="Find all authentication-related files", subagent_type="Explore")
- Task(description="Plan feature", prompt="Design implementation plan for user settings", subagent_type="Plan")
- Task(description="Complex refactor", prompt="Refactor the database layer...", subagent_type="general-purpose")
"""


class TaskTool(AsyncBaseTool):
    """
    A tool for launching specialized agents to handle complex, multi-step tasks autonomously.
    Uses SubagentRegistry to dynamically manage available agent types.
    """

    name = "Task"
    # Description will be set dynamically in __init__
    description = "Launch a new agent to handle complex, multi-step tasks autonomously"
    readonly = True  # Task execution is read-only from the perspective of the calling agent
    needs_state = True

    inputs = {
        "description": {
            "type": "string",
            "description": "A short (3-5 word) description of the task"
        },
        "prompt": {
            "type": "string",
            "description": "The task for the agent to perform"
        },
        "model_name": {
            "type": "string",
            "description": "Optional: Specific model name to use for this task",
            "required": False
        },
        "subagent_type": {
            "type": "string",
            "description": "The type of specialized agent to use (default: general-purpose)",
            "required": False
        }
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None):
        super().__init__()
        self._registry = None
        self._workdir = Path(workdir) if workdir else None
        # Set dynamic description
        self.description = generate_task_tool_prompt()

    @property
    def registry(self):
        """Get the subagent registry, loading subagents if needed."""
        if self._registry is None:
            from ..subagents import load_subagents
            self._registry = load_subagents()
        return self._registry

    async def forward(self, description: str, prompt: str, model_name: Optional[str] = None,
                      subagent_type: Optional[str] = None, *, state: AgentState) -> str:
        """Execute the task using a specialized agent (async)."""
        start_time = time.time()

        # Default to general-purpose
        agent_type = subagent_type or "general-purpose"

        # Get subagent config from registry
        subagent_config = self.registry.get(agent_type)

        if subagent_config is None:
            available_types = self.registry.list_names()
            return f"Agent type '{agent_type}' not found.\n\nAvailable agents:\n" + \
                   "\n".join(f"  - {t}" for t in available_types) + \
                   "\n\nUse one of the available agent types."

        # Build effective prompt
        effective_prompt = prompt
        if subagent_config.system_prompt:
            effective_prompt = f"{subagent_config.system_prompt}\n\n{prompt}"

        # Determine model
        effective_model = model_name or "gpt-4o-mini"
        if not model_name and subagent_config.model_name != "inherit":
            effective_model = subagent_config.model_name

        # Progress messages
        progress_messages = [
            f"Starting agent: {agent_type}",
            f"Using model: {effective_model}",
            f"Task: {description}",
        ]

        try:
            from ..agents.code_agent import MinionCodeAgent

            # Determine working directory
            workdir = self._workdir or Path.cwd()

            # Create agent with filtered tools
            agent = await MinionCodeAgent.create(
                name=f"Task Agent ({agent_type})",
                llm=effective_model,
                system_prompt=effective_prompt if subagent_config.system_prompt else None,
                workdir=workdir,
                additional_tools=self._get_filtered_tools(subagent_config.tools)
            )

            # Execute
            response = await agent.run_async(prompt)

            # Extract response
            if hasattr(response, 'answer'):
                result_text = response.answer
            elif hasattr(response, 'content'):
                result_text = response.content
            else:
                result_text = str(response)

            duration = time.time() - start_time
            completion_message = f"Task completed ({self._format_duration(duration)})"

            return "\n".join(progress_messages) + f"\n\n{result_text}\n\n{completion_message}"

        except Exception as e:
            return "\n".join(progress_messages) + f"\n\nError during task execution: {str(e)}"

    def _get_filtered_tools(self, tool_filter: Union[str, List[str]]) -> Optional[List]:
        """Get filtered tools based on subagent configuration."""
        if tool_filter == "*" or (isinstance(tool_filter, list) and "*" in tool_filter):
            return None  # Use all default tools

        # TODO: Implement actual tool filtering based on tool names
        # For now, return None to use all tools
        return None

    def _format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable way."""
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"

    def _validate_input(self, description: str, prompt: str,
                        model_name: Optional[str] = None,
                        subagent_type: Optional[str] = None) -> Dict[str, Any]:
        """Validate input parameters."""

        if not description or not isinstance(description, str):
            return {
                "valid": False,
                "message": "Description is required and must be a string"
            }

        if not prompt or not isinstance(prompt, str):
            return {
                "valid": False,
                "message": "Prompt is required and must be a string"
            }

        # Validate subagent_type if provided
        if subagent_type and not self.registry.exists(subagent_type):
            available_types = self.registry.list_names()
            return {
                "valid": False,
                "message": f"Agent type '{subagent_type}' does not exist. Available types: {', '.join(available_types)}"
            }

        return {"valid": True}

    @classmethod
    def get_available_agent_types(cls) -> List[str]:
        """Get list of available agent types."""
        from ..subagents import get_available_subagents
        return [s.name for s in get_available_subagents()]

    @classmethod
    def get_agent_description(cls, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get description for a specific agent type."""
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

    @classmethod
    def get_prompt_text(cls) -> str:
        """Get the tool prompt text for agent instructions."""
        return generate_task_tool_prompt()
