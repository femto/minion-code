#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minion Code Tools Package
A collection of development tools for code analysis and manipulation.
"""

# Import base classes from minion framework
from minion.tools import BaseTool, tool, ToolCollection

# Import individual tools
from .file_read_tool import FileReadTool
from .file_write_tool import FileWriteTool
from .file_edit_tool import FileEditTool
from .multi_edit_tool import MultiEditTool
from .bash_tool import BashTool
from .grep_tool import GrepTool
from .glob_tool import GlobTool
from .ls_tool import LsTool
from .python_interpreter_tool import PythonInterpreterTool
from .user_input_tool import UserInputTool
from .task_tool import TaskTool
from .task_status_tool import TaskStatusTool
from .task_output_tool import TaskOutputTool
from .task_list_tool import TaskListTool
from .task_cancel_tool import TaskCancelTool

from .todo_write_tool import TodoWriteTool
from .todo_read_tool import TodoReadTool
from .skill_tool import SkillTool

# Tool mapping
TOOL_MAPPING = {
    tool_class.name: tool_class
    for tool_class in [
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
        TaskTool,
        TaskStatusTool,
        TaskOutputTool,
        TaskListTool,
        TaskCancelTool,
        TodoWriteTool,
        TodoReadTool,
        SkillTool,
    ]
}

__all__ = [
    # Base classes
    # File system tools
    "FileReadTool",
    "FileWriteTool",
    "FileEditTool",
    "FileEditToolNew",
    "MultiEditTool",
    "BashTool",
    "GrepTool",
    "GlobTool",
    "LsTool",
    # Execution tools
    "PythonInterpreterTool",
    # Task tools
    "TaskTool",
    "TaskStatusTool",
    "TaskOutputTool",
    "TaskListTool",
    "TaskCancelTool",
    # Web tools
    # Interactive tools
    "UserInputTool",
    # Todo tools
    "TodoWriteTool",
    "TodoReadTool",
    # Skill tools
    "SkillTool",
    # Utilities
    "TOOL_MAPPING",
]
