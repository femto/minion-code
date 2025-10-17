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

# Import all minion_code tools
from ..tools import (
    FileReadTool,
    FileWriteTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool,
    UserInputTool,
    FinalAnswerTool,
    TodoWriteTool,
    TodoReadTool,
    TOOL_MAPPING,
)

logger = logging.getLogger(__name__)

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
        "- For edits, apply the smallest change that satisfies the request.\n"
        "- For bash, avoid destructive or privileged commands; stay inside the workspace.\n"
        "- Use the Todo tool to maintain multi-step plans when needed.\n"
        "- After finishing, summarize what changed and how to run or test."
    )

    def __post_init__(self):
        """Initialize the CodeAgent with thinking capabilities and optional state tracking."""
        super().__post_init__()
        self.conversation_history = []
    
    @classmethod
    async def create(
        cls,
        name: str = "Minion Code Assistant",
        llm: str = "gpt-4o-mini",
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
            BashTool(),
            GrepTool(),
            GlobTool(),
            LsTool(),
            PythonInterpreterTool(),
            UserInputTool(),
            FinalAnswerTool(),
            TodoWriteTool(),
            TodoReadTool(),
        ]
        
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