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
        "You are a coding agent operating INSIDE the user's repository at {workdir}.\n"
        "Follow this loop strictly: plan briefly → use TOOLS to act directly on files/shell → report concise results.\n"
        "Rules:\n"
        "- Prefer taking actions with tools (read/write/edit/bash) over long prose.\n"
        "- Keep outputs terse. Use bullet lists / checklists when summarizing.\n"
        "- Never invent file paths. Ask via reads or list directories first if unsure.\n"
        "- For edits, choose the right tool: file_edit for single string replacements, multi_edit for multiple changes to same file or large edits, file_write for complete rewrites.\n"
        "- For large string edits (>2000 chars), prefer multi_edit tool or break into smaller chunks for better reliability.\n"
        "- Always read files before editing to establish freshness tracking.\n"
        "- For bash, avoid destructive or privileged commands; stay inside the workspace.\n"
        "- Use the Todo tool to maintain multi-step plans when needed.\n"
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
        system_prompt: Optional[str] = None,
        workdir: Optional[Union[str, Path]] = None,
        additional_tools: Optional[List[Any]] = None,
        **kwargs
    ) -> "MinionCodeAgent":
        """
        Create a new MinionCodeAgent with all minion_code tools.
        
        Args:
            name: Agent name
            llm: LLM model to use
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
        
        # Create the underlying CodeAgent
        agent = await super().create(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            tools=all_tools,
            **kwargs
        )
        
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