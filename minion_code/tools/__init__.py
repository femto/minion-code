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
from .bash_tool import BashTool
from .grep_tool import GrepTool
from .glob_tool import GlobTool
from .ls_tool import LsTool
from .python_interpreter_tool import PythonInterpreterTool
from .user_input_tool import UserInputTool
from .final_answer_tool import FinalAnswerTool
from .todo_write_tool import TodoWriteTool
from .todo_read_tool import TodoReadTool

# Tool mapping
TOOL_MAPPING = {
    tool_class.name: tool_class
    for tool_class in [
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
    ]
}

__all__ = [
    # Base classes
    # File system tools
    "FileReadTool",
    "FileWriteTool",
    "BashTool",
    "GrepTool",
    "GlobTool",
    "LsTool",
    # Execution tools
    "PythonInterpreterTool",
    # Web tools
    # Interactive tools
    "UserInputTool",
    "FinalAnswerTool",
    # Todo tools
    "TodoWriteTool",
    "TodoReadTool",
    # Utilities
    "TOOL_MAPPING",
]
