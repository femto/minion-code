#!/usr/bin/env python3
"""
Task Tool for launching specialized agents to handle complex, multi-step tasks.
Based on the TypeScript TaskTool implementation.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator, Union
from minion.tools import BaseTool
from minion.types import AgentState

# Import will be done dynamically to avoid circular imports


class TaskTool(BaseTool):
    """
    A tool for launching specialized agents to handle complex, multi-step tasks autonomously.
    """
    
    name = "task"
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
            "description": "Optional: Specific model name to use for this task. If not provided, uses the default task model.",
            "required": False
        },
        "subagent_type": {
            "type": "string",
            "description": "The type of specialized agent to use for this task (default: general-purpose)",
            "required": False
        }
    }
    output_type = "string"
    
    # Available agent types and their configurations
    AGENT_TYPES = {
        "general-purpose": {
            "description": "General coding and development tasks",
            "when_to_use": "For general coding, file operations, and development tasks",
            "tools": ["*"],  # All tools available
            "system_prompt": None,
            "model_name": "inherit"
        },
        "code-reviewer": {
            "description": "Code review and analysis",
            "when_to_use": "Use this agent after writing significant code to review quality, bugs, and improvements",
            "tools": ["file_read", "grep", "glob", "ls"],
            "system_prompt": "You are a code reviewer. Analyze code for bugs, performance issues, security vulnerabilities, and suggest improvements. Focus on code quality, best practices, and maintainability.",
            "model_name": "inherit"
        },
        "debugger": {
            "description": "Debug and troubleshoot issues",
            "when_to_use": "When encountering errors, bugs, or unexpected behavior that needs investigation",
            "tools": ["file_read", "file_edit", "bash", "grep", "python_interpreter"],
            "system_prompt": "You are a debugging specialist. Analyze errors, trace issues, and provide solutions. Use systematic debugging approaches and explain your reasoning.",
            "model_name": "inherit"
        },
        "researcher": {
            "description": "Research and information gathering",
            "when_to_use": "For gathering information, analyzing codebases, or understanding complex systems",
            "tools": ["file_read", "grep", "glob", "ls"],
            "system_prompt": "You are a research specialist. Gather information systematically, analyze patterns, and provide comprehensive summaries. Focus on understanding and documenting findings.",
            "model_name": "inherit"
        }
    }
    
    def forward(self, description: str, prompt: str, model_name: Optional[str] = None, 
                subagent_type: Optional[str] = None, *, state: AgentState) -> str:
        """Execute the task using a specialized agent."""
        try:
            # Run the async task execution
            return asyncio.run(self._execute_task_async(
                description, prompt, model_name, subagent_type, state
            ))
        except Exception as e:
            return f"Error executing task: {str(e)}"
    
    async def _execute_task_async(self, description: str, prompt: str, 
                                 model_name: Optional[str], subagent_type: Optional[str],
                                 state: AgentState) -> str:
        """Execute the task asynchronously."""
        start_time = time.time()
        
        # Default to general-purpose if no subagent_type specified
        agent_type = subagent_type or "general-purpose"
        
        # Validate agent type
        if agent_type not in self.AGENT_TYPES:
            available_types = list(self.AGENT_TYPES.keys())
            return f"Agent type '{agent_type}' not found.\n\nAvailable agents:\n" + \
                   "\n".join(f"  • {t}: {self.AGENT_TYPES[t]['when_to_use']}" for t in available_types) + \
                   "\n\nUse one of the available agent types."
        
        # Get agent configuration
        agent_config = self.AGENT_TYPES[agent_type]
        
        # Prepare effective prompt and model
        effective_prompt = prompt
        if agent_config["system_prompt"]:
            effective_prompt = f"{agent_config['system_prompt']}\n\n{prompt}"
        
        effective_model = model_name or "gpt-4o-mini"  # Default model
        if not model_name and agent_config["model_name"] != "inherit":
            effective_model = agent_config["model_name"]
        
        # Generate unique task ID
        task_id = str(uuid.uuid4())[:8]
        
        # Create progress messages
        progress_messages = [
            f"Starting agent: {agent_type}",
            f"Using model: {effective_model}",
            f"Task: {description}",
            f"Prompt: {prompt[:150] + '...' if len(prompt) > 150 else prompt}"
        ]
        
        try:
            # Import MinionCodeAgent dynamically to avoid circular imports
            from ..agents.code_agent import MinionCodeAgent
            
            # Create the specialized agent
            agent = await MinionCodeAgent.create(
                name=f"Task Agent ({agent_type})",
                llm=effective_model,
                system_prompt=effective_prompt if agent_config["system_prompt"] else None,
                additional_tools=self._get_filtered_tools(agent_config["tools"])
            )
            
            # Execute the task
            response = await agent.run_async(prompt)
            
            # Extract the response text
            if hasattr(response, 'answer'):
                result_text = response.answer
            elif hasattr(response, 'content'):
                result_text = response.content
            else:
                result_text = str(response)
            
            # Calculate execution stats
            duration = time.time() - start_time
            
            # Format the final result
            completion_message = f"Task completed ({self._format_duration(duration)})"
            
            # Combine progress and result
            full_result = "\n".join(progress_messages) + f"\n\n{result_text}\n\n{completion_message}"
            
            return full_result
            
        except Exception as e:
            error_message = f"Error during task execution: {str(e)}"
            return "\n".join(progress_messages) + f"\n\n{error_message}"
    
    def _get_filtered_tools(self, tool_filter: Union[str, List[str]]) -> Optional[List]:
        """Get filtered tools based on agent configuration."""
        if tool_filter == "*" or (isinstance(tool_filter, list) and tool_filter == ["*"]):
            return None  # Use all default tools
        
        if isinstance(tool_filter, list):
            # For now, return None to use all tools
            # In a full implementation, you would filter the actual tool instances
            return None
        
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
        if subagent_type and subagent_type not in self.AGENT_TYPES:
            available_types = list(self.AGENT_TYPES.keys())
            return {
                "valid": False,
                "message": f"Agent type '{subagent_type}' does not exist. Available types: {', '.join(available_types)}"
            }
        
        return {"valid": True}
    
    @classmethod
    def get_available_agent_types(cls) -> List[str]:
        """Get list of available agent types."""
        return list(cls.AGENT_TYPES.keys())
    
    @classmethod
    def get_agent_description(cls, agent_type: str) -> Optional[Dict[str, Any]]:
        """Get description for a specific agent type."""
        return cls.AGENT_TYPES.get(agent_type)
    
    @classmethod
    def get_prompt_text(cls) -> str:
        """Get the tool prompt text for agent instructions."""
        agent_descriptions = []
        for agent_type, config in cls.AGENT_TYPES.items():
            tools_str = ", ".join(config["tools"]) if config["tools"] != ["*"] else "*"
            agent_descriptions.append(f"- {agent_type}: {config['when_to_use']} (Tools: {tools_str})")
        
        return f"""Launch a new agent to handle complex, multi-step tasks autonomously.

Available agent types and the tools they have access to:
{chr(10).join(agent_descriptions)}

When using the Task tool, you can specify a subagent_type parameter to select which agent type to use.

When to use the Task tool:
- For complex, multi-step tasks that require specialized expertise
- When you need to delegate a complete subtask to a focused agent
- For tasks that benefit from specialized system prompts and tool sets

When NOT to use the Task tool:
- For simple file operations (use file_read, file_write, file_edit instead)
- For single grep searches (use grep tool instead)
- For basic bash commands (use bash tool instead)
- For simple Python execution (use python_interpreter instead)

Usage notes:
1. Each agent invocation is stateless and autonomous
2. Provide detailed task descriptions for best results
3. The agent will return a complete result in a single response
4. Choose the appropriate subagent_type for your specific task
5. Agent outputs should generally be trusted and acted upon

Example usage:
- Task(description="Review code", prompt="Review the authentication module for security issues", subagent_type="code-reviewer")
- Task(description="Debug error", prompt="Investigate why the API is returning 500 errors", subagent_type="debugger")
- Task(description="Research codebase", prompt="Analyze the database layer architecture", subagent_type="researcher")
"""