#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minion Code Tools Package
A collection of development tools for code analysis and manipulation.
"""

# Import base classes from local implementation
from .base_tool import BaseTool, tool, ToolCollection

# Import individual tools
from .file_read_tool import FileReadTool
from .file_write_tool import FileWriteTool
from .bash_tool import BashTool
from .grep_tool import GrepTool
from .glob_tool import GlobTool
from .ls_tool import LsTool
from .python_interpreter_tool import PythonInterpreterTool

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
    ]
}

__all__ = [
    # Base classes
    "BaseTool",
    "tool",
    "ToolCollection",
    # Concrete tools
    "FileReadTool",
    "FileWriteTool",
    "BashTool",
    "GrepTool",
    "GlobTool",
    "LsTool",
    "PythonInterpreterTool",
    # Utilities
    "TOOL_MAPPING",
]
