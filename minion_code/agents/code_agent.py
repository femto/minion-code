#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MinionCodeAgent - Enhanced CodeAgent with minion_code tools

This module provides a specialized CodeAgent subclass that comes pre-configured
with all minion_code tools and optimized system prompts for code development tasks.

Key features:
- Pre-configured with all minion_code tools
- Optimized system prompt for coding tasks
- Async/sync support
- Easy setup and initialization
- Conversation history management
"""

import asyncio
import logging
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union, Any
import sys

from minion.agents import CodeAgent
from minion.types import AgentState
from minion.types.history import History
from ..utils.auto_compact_core import AutoCompactCore, CompactConfig

# Import all minion_code tools
from ..tools import (
    FileReadTool,
    FileWriteTool,
    FileEditTool,
    MultiEditTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool,
    UserInputTool,

    TodoWriteTool,
    TodoReadTool,
    TOOL_MAPPING,
)

logger = logging.getLogger(__name__)


async def query_quick(
    agent: "MinionCodeAgent",
    user_prompt: str,
    system_prompt: Optional[Union[str, List[str]]] = None,
    assistant_prompt: Optional[str] = None,
    enable_prompt_caching: bool = False,
    llm: Optional[str] = None,
) -> str:
    """
    Simplified query function for quick LLM interactions without agent overhead.
    
    This function bypasses the agent's complex routing and tool execution,
    providing direct access to the LLM for simple queries. It uses brain.step
    with route='raw' to avoid additional processing.
    
    Args:
        agent: MinionCodeAgent instance to use for the query
        user_prompt: The user's message/question
        system_prompt: Optional system prompt(s) - can be a string or list of strings
        assistant_prompt: Optional assistant prompt to prefill the response
        enable_prompt_caching: Whether to enable prompt caching (default: False)
        llm: Optional LLM model to use (defaults to agent's quick LLM)
    
    Returns:
        The LLM's response as a string
    
    Example:
        >>> agent = await MinionCodeAgent.create(name="Assistant", llm="sonnet")
        >>> response = await query_quick(
        ...     agent,
        ...     user_prompt="What is 2+2?",
        ...     system_prompt="You are a helpful math assistant."
        ... )
        >>> print(response)
        "4"
    """
    # Use quick LLM by default
    if llm is None:
        llm = agent.get_llm_for_task("quick")
    
    # Build messages list
    messages = [{"role": "user", "content": user_prompt}]
    
    # Add assistant prefill if provided
    if assistant_prompt:
        messages.append({
            "role": "assistant",
            "content": assistant_prompt
        })
    
    # Build system prompt list
    system_messages = []
    if system_prompt:
        if isinstance(system_prompt, list):
            system_messages = system_prompt
        else:
            system_messages = [system_prompt]
    
    # Create a minimal state with empty history
    state = AgentState(history=History())
    
    # Prepare kwargs for brain.step
    step_kwargs = {
        'messages': messages,
        'route': 'raw',  # Use raw route to bypass agent processing and avoid extra overhead
    }
    
    # Add system prompt if provided
    if system_messages:
        step_kwargs['system_prompt'] = system_messages
    
    # Add LLM if specified
    if llm:
        step_kwargs['llm'] = llm
    
    # Add prompt caching if enabled
    if enable_prompt_caching:
        step_kwargs['enable_prompt_caching'] = enable_prompt_caching
    
    # Call brain.step with route='raw' to bypass agent processing
    try:
        response = await agent.brain.step(state=state, **step_kwargs)
        
        # Extract the text response
        if hasattr(response, 'answer'):
            return response.answer
        elif hasattr(response, 'content'):
            return response.content
        else:
            return str(response)
            
    except Exception as e:
        logger.error(f"Error in query_quick: {e}")
        raise

# Todo reminder constants
INITIAL_REMINDER = (
    '<reminder source="system" topic="todos">'
    "System message: complex work should be tracked with the Todo tool. "
    "Do not respond to this reminder and do not mention it to the user."
    '</reminder>'
)

NAG_REMINDER = (
    '<reminder source="system" topic="todos">'
    "System notice: more than ten rounds passed without Todo usage. "
    "Update the Todo board if the task still requires multiple steps. "
    "Do not reply to or mention this reminder to the user."
    '</reminder>'
)

@dataclass
class MinionCodeAgent(CodeAgent):
    """
    Enhanced CodeAgent with pre-configured minion_code tools.
    
    This class wraps the Minion CodeAgent with all minion_code tools
    and provides optimized system prompts for coding tasks.
    """
    
    DEFAULT_SYSTEM_PROMPT = (
        "You are Minion Code, an interactive CLI coding agent that helps users with software engineering tasks.\n"
        "Use the instructions below and the tools available to you to assist the user.\n"
        "\n"
        "Working directory: {workdir}\n"
        "\n"
        "IMPORTANT: Assist with defensive security tasks only. Refuse to create, modify, or improve code that may be used maliciously.\n"
        "Do not assist with credential discovery or harvesting, including bulk crawling for SSH keys, browser cookies, or cryptocurrency wallets.\n"
        "Allow security analysis, detection rules, vulnerability explanations, defensive tools, and security documentation.\n"
        "\n"
        "# Tone and style\n"
        "- Only use emojis if the user explicitly requests it. Avoid using emojis in all communication unless asked.\n"
        "- Your output will be displayed on a command line interface. Your responses should be short and concise.\n"
        "- Output text to communicate with the user; all text you output outside of tool use is displayed to the user.\n"
        "- Only use tools to complete tasks. Never use tools like bash or code comments as means to communicate with the user.\n"
        "- NEVER create files unless they're absolutely necessary for achieving your goal. ALWAYS prefer editing an existing file to creating a new one.\n"
        "\n"
        "# Professional objectivity\n"
        "Prioritize technical accuracy and truthfulness over validating the user's beliefs. Focus on facts and problem-solving,\n"
        "providing direct, objective technical info without any unnecessary superlatives, praise, or emotional validation.\n"
        "It is best for the user if you honestly apply the same rigorous standards to all ideas and disagree when necessary,\n"
        "even if it may not be what the user wants to hear. Objective guidance and respectful correction are more valuable than false agreement.\n"
        "Whenever there is uncertainty, it's best to investigate to find the truth first rather than instinctively confirming the user's beliefs.\n"
        "\n"
        "# Task Management\n"
        "You have access to the todo_write and todo_read tools to help you manage and plan tasks. Use these tools VERY frequently\n"
        "to ensure that you are tracking your tasks and giving the user visibility into your progress.\n"
        "These tools are also EXTREMELY helpful for planning tasks, and for breaking down larger complex tasks into smaller steps.\n"
        "If you do not use this tool when planning, you may forget to do important tasks - and that is unacceptable.\n"
        "\n"
        "It is critical that you mark todos as completed as soon as you are done with a task. Do not batch up multiple tasks before marking them as completed.\n"
        "\n"
        "Example:\n"
        "user: Run the build and fix any type errors\n"
        "assistant: I'm going to use the todo_write tool to write the following items to the todo list:\n"
        "- Run the build\n"
        "- Fix any type errors\n"
        "\n"
        "I'm now going to run the build using bash.\n"
        "Looks like I found 10 type errors. I'm going to use the todo_write tool to write 10 items to the todo list.\n"
        "marking the first todo as in_progress\n"
        "Let me start working on the first item...\n"
        "The first item has been fixed, let me mark the first todo as completed, and move on to the second item...\n"
        "\n"
        "# Doing tasks\n"
        "The user will primarily request you perform software engineering tasks. This includes solving bugs, adding new functionality,\n"
        "refactoring code, explaining code, and more. For these tasks the following steps are recommended:\n"
        "- Use the todo_write tool to plan the task if required\n"
        "- Be careful not to introduce security vulnerabilities such as command injection, XSS, SQL injection, and other OWASP top 10 vulnerabilities.\n"
        "\n"
        "# Tool usage policy\n"
        "- You can call multiple tools in a single response. If you intend to call multiple tools and there are no dependencies between them,\n"
        "  make all independent tool calls in parallel. Maximize use of parallel tool calls where possible to increase efficiency.\n"
        "- However, if some tool calls depend on previous calls to inform dependent values, do NOT call these tools in parallel and instead call them sequentially.\n"
        "- Never use placeholders or guess missing parameters in tool calls.\n"
        "- Use specialized tools instead of bash commands when possible. For file operations, use dedicated tools:\n"
        "  file_read for reading files instead of cat/head/tail, file_edit for editing instead of sed/awk,\n"
        "  and file_write for creating files instead of cat with heredoc or echo redirection.\n"
        "- Reserve bash tools exclusively for actual system commands and terminal operations that require shell execution.\n"
        "- NEVER use bash echo or other command-line tools to communicate thoughts, explanations, or instructions to the user.\n"
        "  Output all communication directly in your response text instead.\n"
        "\n"
        "# Code References\n"
        "When referencing specific functions or pieces of code include the pattern `file_path:line_number` to allow the user\n"
        "to easily navigate to the source code location.\n"
        "\n"
        "Example:\n"
        "user: Where are errors from the client handled?\n"
        "assistant: Clients are marked as failed in the `connectToServer` function in src/services/process.py:712.\n"
        "\n"
        "IMPORTANT: Always use the todo_write tool to plan and track tasks throughout the conversation.\n"
        "\n"
        "Rules:\n"
        "- Prefer taking actions with tools (read/write/edit/bash) over long prose.\n"
        "- Keep outputs terse. Use bullet lists / checklists when summarizing.\n"
        "- Never invent file paths. Ask via reads or list directories first if unsure.\n"
        "- For edits, choose the right tool: file_edit for single string replacements, multi_edit for multiple changes to same file or large edits, file_write for complete rewrites.\n"
        "- For large string edits (>2000 chars), prefer multi_edit tool or break into smaller chunks for better reliability.\n"
        "- Always read files before editing to establish freshness tracking.\n"
        "- For bash, avoid destructive or privileged commands; stay inside the workspace.\n"
        "- After finishing, summarize what changed and how to run or test."
    )

    def __post_init__(self):
        """Initialize the CodeAgent with thinking capabilities and optional state tracking."""
        super().__post_init__()
        self.conversation_history = []
        # Initialize auto-compact functionality
        self.auto_compact = AutoCompactCore(CompactConfig(
            context_window=128000,  # 128k tokens
            compact_threshold=0.92,  # 92%
            preserve_recent_messages=10,
            compression_ratio=0.5
        ))
    
    async def pre_step(self, input_data, kwargs):
        """Override pre_step to track iterations without todo usage and handle auto-compacting."""
        # Call parent pre_step first
        result = await super().pre_step(input_data, kwargs)
        
        # Initialize metadata if not exists
        if not hasattr(self.state, 'metadata'):
            self.state.metadata = {}
        if "iteration_without_todos" not in self.state.metadata:
            self.state.metadata["iteration_without_todos"] = 0
        
        # Increment iteration counter
        self.state.metadata["iteration_without_todos"] += 1
        
        # AUTO_COMPACT: Check if history needs compacting
        if hasattr(self.state, 'history') and self.state.history:
            # Convert history to list of dicts if needed
            history_messages = []
            for msg in self.state.history:
                if isinstance(msg, dict):
                    history_messages.append(msg)
                else:
                    # Handle other message formats if needed
                    content = getattr(msg, 'content', str(msg))
                    # Keep content in its original format (string or list)
                    history_messages.append({
                        'role': getattr(msg, 'role', 'unknown'),
                        'content': content
                    })
            
            # Check if compacting is needed
            if self.auto_compact.needs_compacting(history_messages):
                logger.info(f"AUTO_COMPACT: Compacting history from {len(history_messages)} messages")
                compacted_messages = self.auto_compact.compact_history(history_messages)
                
                # Update the history with compacted messages
                self.state.history.clear()
                for msg in compacted_messages:
                    self.state.history.append(msg)
                
                logger.info(f"AUTO_COMPACT: History compacted to {len(compacted_messages)} messages")
                
                # Log context stats
                stats = self.auto_compact.get_context_stats(compacted_messages)
                logger.info(f"AUTO_COMPACT: Context usage: {stats['usage_percentage']:.1%} "
                           f"({stats['total_tokens']}/{self.auto_compact.config.context_window} tokens)")
        
        # Add nag reminder if more than 10 iterations without todo usage
        if self.state.metadata["iteration_without_todos"] > 10:
            self.state.history.append({
                'role': 'user',
                'content': NAG_REMINDER
            })
            # Reset counter to avoid spamming reminders
            self.state.metadata["iteration_without_todos"] = 0
        
        return result
    
    @classmethod
    async def create(
        cls,
        name: str = "Minion Code Assistant",
        llm: str = "sonnet",
        llms: Optional[dict] = None,
        system_prompt: Optional[str] = None,
        workdir: Optional[Union[str, Path]] = None,
        additional_tools: Optional[List[Any]] = None,
        **kwargs
    ) -> "MinionCodeAgent":
        """
        Create a new MinionCodeAgent with all minion_code tools.
        
        Args:
            name: Agent name
            llm: Main LLM model to use (default for all tasks)
            llms: Optional dict with specialized LLMs: {'quick': 'haiku', 'task': 'sonnet', 'reasoning': 'o4-mini'}
                  If not provided, uses smart defaults based on main llm
            system_prompt: Custom system prompt (uses default if None)
            workdir: Working directory (uses current if None)
            additional_tools: Extra tools to add beyond minion_code tools
            **kwargs: Additional arguments passed to CodeAgent.create()
        
        Returns:
            Configured MinionCodeAgent instance
        """
        if workdir is None:
            workdir = Path.cwd()
        else:
            workdir = Path(workdir)
        
        # Set up specialized LLMs with fallback to main llm
        if llms is None:
            llms = {}
        
        llm_quick = llms.get('quick')
        llm_task = llms.get('task')
        llm_reasoning = llms.get('reasoning')
        
        if llm_quick is None:
            llm_quick = "haiku" if llm == "sonnet" else llm
        if llm_task is None:
            llm_task = "sonnet" if llm != "sonnet" else llm
        if llm_reasoning is None:
            llm_reasoning = "o4-mini" if llm not in ["o4-mini", "o1-mini"] else llm
        
        # Use default system prompt if none provided
        if system_prompt is None:
            system_prompt = cls.DEFAULT_SYSTEM_PROMPT.format(workdir=workdir)
        
        # Get all minion_code tools
        minion_tools = [
            FileReadTool(),
            FileWriteTool(),
            FileEditTool(),
            MultiEditTool(),
            BashTool(),
            GrepTool(),
            GlobTool(),
            LsTool(),
            PythonInterpreterTool(),
            UserInputTool(),
            TodoWriteTool(),
            TodoReadTool(),
        ]
        
        # Add TaskTool if available (avoid circular import)
        # try:
        #     from ..tools.task_tool import TaskTool
        #     minion_tools.append(TaskTool())
        # except ImportError:
        #     pass
        
        # Add any additional tools
        all_tools = minion_tools[:]
        if additional_tools:
            all_tools.extend(additional_tools)
        
        logger.info(f"Creating MinionCodeAgent with {len(all_tools)} tools")
        logger.info(f"LLM config - main: {llm}, quick: {llm_quick}, task: {llm_task}, reasoning: {llm_reasoning}")
        
        # Create the underlying CodeAgent
        agent = await super().create(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            tools=all_tools,
            **kwargs
        )
        
        # Store specialized LLM configurations in a dict
        agent.llms = {
            'main': agent.llm,  # The actual provider object
            'quick': llm_quick,
            'task': llm_task,
            'reasoning': llm_reasoning
        }
        
        # Initialize todo tracking metadata
        if not hasattr(agent.state, 'metadata'):
            agent.state.metadata = {}
        agent.state.metadata["iteration_without_todos"] = 0
        
        # Add initial todo reminder to history
        agent.state.history.append({
            'role': 'user',
            'content': INITIAL_REMINDER
        })
        
        return agent
    
    async def run_async(self, message: str, **kwargs) -> Any:
        """
        Run agent asynchronously and track conversation history.
        
        Args:
            message: User message
            **kwargs: Additional arguments passed to agent.run_async()
        
        Returns:
            Agent response
        """
        try:
            response = await super().run_async(message, **kwargs)
            
            # Track conversation history
            self.conversation_history.append({
                'user_message': message,
                'agent_response': response.answer if hasattr(response, 'answer') else str(response),
                'timestamp': asyncio.get_event_loop().time()
            })
            
            return response
            
        except Exception as e:
            logger.error(f"Error in run_async: {e}")
            traceback.print_exc()
            raise
    
    def run(self, message: str, **kwargs) -> Any:
        """
        Run agent synchronously.
        
        Args:
            message: User message
            **kwargs: Additional arguments
        
        Returns:
            Agent response
        """
        return asyncio.run(self.run_async(message, **kwargs))
    
    def get_conversation_history(self) -> List[dict]:
        """Get conversation history."""
        return self.conversation_history.copy()
    
    def clear_conversation_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
    
    def get_tools_info(self) -> List[dict]:
        """
        Get information about available tools.
        
        Returns:
            List of tool information dictionaries
        """
        tools_info = []
        for tool in self.tools:
            readonly_status = getattr(tool, "readonly", None)
            tools_info.append({
                'name': tool.name,
                'description': tool.description,
                'readonly': readonly_status,
                'type': type(tool).__name__
            })
        return tools_info
    
    def print_tools_summary(self):
        """Print a summary of available tools."""
        tools_info = self.get_tools_info()
        
        print(f"\n🛠️ Available Tools ({len(tools_info)} total):")
        
        # Group tools by category
        categories = {
            'File & Directory': ['file', 'read', 'write', 'grep', 'glob', 'ls'],
            'System & Execution': ['bash', 'python', 'calc', 'system'],
            'Web & Search': ['web', 'search', 'wikipedia', 'visit'],
            'Other': []
        }
        
        categorized_tools = {cat: [] for cat in categories}
        
        for tool in tools_info:
            categorized = False
            for category, keywords in categories.items():
                if category == 'Other':
                    continue
                if any(keyword in tool['name'].lower() for keyword in keywords):
                    categorized_tools[category].append(tool)
                    categorized = True
                    break
            
            if not categorized:
                categorized_tools['Other'].append(tool)
        
        # Print categorized tools
        for category, tools in categorized_tools.items():
            if tools:
                print(f"\n📁 {category} Tools:")
                for tool in tools:
                    readonly_icon = "🔒" if tool['readonly'] else "✏️"
                    print(f"  {readonly_icon} {tool['name']}: {tool['description']}")
        
        print(f"\n🔒 = readonly tool, ✏️ = read/write tool")
    
    def get_context_stats(self) -> dict:
        """Get current context usage statistics."""
        if not hasattr(self.state, 'history') or not self.state.history:
            return {
                'total_tokens': 0,
                'usage_percentage': 0.0,
                'needs_compacting': False,
                'remaining_tokens': self.auto_compact.config.context_window
            }
        
        # Convert history to list of dicts if needed
        history_messages = []
        for msg in self.state.history:
            if isinstance(msg, dict):
                history_messages.append(msg)
            else:
                content = getattr(msg, 'content', str(msg))
                # Keep content in its original format (string or list)
                history_messages.append({
                    'role': getattr(msg, 'role', 'unknown'),
                    'content': content
                })
        
        return self.auto_compact.get_context_stats(history_messages)
    
    def force_compact_history(self) -> bool:
        """Manually trigger history compaction. Returns True if compaction occurred."""
        if not hasattr(self.state, 'history') or not self.state.history:
            return False
        
        # Convert history to list of dicts if needed
        history_messages = []
        for msg in self.state.history:
            if isinstance(msg, dict):
                history_messages.append(msg)
            else:
                content = getattr(msg, 'content', str(msg))
                # Keep content in its original format (string or list)
                history_messages.append({
                    'role': getattr(msg, 'role', 'unknown'),
                    'content': content
                })
        
        original_count = len(history_messages)
        compacted_messages = self.auto_compact.compact_history(history_messages)
        
        if len(compacted_messages) < original_count:
            # Update the history with compacted messages
            self.state.history.clear()
            for msg in compacted_messages:
                self.state.history.append(msg)
            
            logger.info(f"Manual compaction: {original_count} -> {len(compacted_messages)} messages")
            return True
        
        return False
    
    def update_compact_config(self, **kwargs) -> None:
        """Update auto-compact configuration."""
        self.auto_compact.update_config(**kwargs)
        logger.info(f"Updated auto-compact config: {kwargs}")
    
    def get_llm_for_task(self, task_type: str = "main"):
        """
        Get the appropriate LLM for a specific task type.
        
        Args:
            task_type: Type of task - "main", "quick", "task", or "reasoning"
        
        Returns:
            LLM model name or provider for the specified task type
        """
        if not hasattr(self, 'llms'):
            return self.llm
        
        return self.llms.get(task_type, self.llm)
    
    def get_llm_config(self) -> dict:
        """
        Get all LLM configurations.
        
        Returns:
            Dictionary with all LLM configurations
        """
        if not hasattr(self, 'llms'):
            return {
                'main': self.llm,
                'quick': self.llm,
                'task': self.llm,
                'reasoning': self.llm
            }
        
        return self.llms.copy()
    
    def update_llm_config(self, **kwargs) -> None:
        """
        Update LLM configurations dynamically.
        
        Args:
            **kwargs: LLM configurations to update (quick, task, reasoning)
        
        Example:
            agent.update_llm_config(quick='haiku', reasoning='o1-mini')
        """
        if not hasattr(self, 'llms'):
            self.llms = {
                'main': self.llm,
                'quick': self.llm,
                'task': self.llm,
                'reasoning': self.llm
            }
        
        for key, value in kwargs.items():
            if key in ['quick', 'task', 'reasoning']:
                self.llms[key] = value
                logger.info(f"Updated LLM config: {key} = {value}")
            else:
                logger.warning(f"Invalid LLM config key: {key}. Valid keys: quick, task, reasoning")
    
    async def query_quick(
        self,
        user_prompt: str,
        system_prompt: Optional[Union[str, List[str]]] = None,
        assistant_prompt: Optional[str] = None,
        enable_prompt_caching: bool = False,
        llm: Optional[str] = None,
    ) -> str:
        """
        Quick query method for simple LLM interactions without agent overhead.
        
        This is a convenience wrapper around the query_quick function that uses
        this agent instance. It bypasses tool execution and complex routing.
        
        Args:
            user_prompt: The user's message/question
            system_prompt: Optional system prompt(s) - can be a string or list of strings
            assistant_prompt: Optional assistant prompt to prefill the response
            enable_prompt_caching: Whether to enable prompt caching (default: False)
            llm: Optional LLM model to use (defaults to agent's quick LLM)
        
        Returns:
            The LLM's response as a string
        
        Example:
            >>> agent = await MinionCodeAgent.create(name="Assistant", llm="sonnet")
            >>> response = await agent.query_quick(
            ...     user_prompt="What is 2+2?",
            ...     system_prompt="You are a helpful math assistant."
            ... )
            >>> print(response)
            "4"
        """
        return await query_quick(
            agent=self,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            assistant_prompt=assistant_prompt,
            enable_prompt_caching=enable_prompt_caching,
            llm=llm,
        )


# Convenience function for quick setup
async def create_minion_code_agent(
    name: str = "Minion Code Assistant",
    llm: str = "gpt-4o-mini",
    **kwargs
) -> MinionCodeAgent:
    """
    Convenience function to create a MinionCodeAgent.
    
    Args:
        name: Agent name
        llm: LLM model to use
        **kwargs: Additional arguments passed to MinionCodeAgent.create()
    
    Returns:
        Configured MinionCodeAgent instance
    """
    return await MinionCodeAgent.create(name=name, llm=llm, **kwargs)