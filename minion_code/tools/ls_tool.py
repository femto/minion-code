#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directory listing tool
"""

from pathlib import Path
from typing import Any, Optional
from minion.tools import BaseTool
from ..utils.output_truncator import truncate_output


class LsTool(BaseTool):
    """Directory listing tool"""

    name = "ls"
    description = "List directory contents"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "path": {"type": "string", "description": "Directory path to list", "nullable": True},
        "recursive": {
            "type": "boolean",
            "description": "Whether to list recursively",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workdir = Path(workdir) if workdir else None

    def _resolve_path(self, path: str) -> Path:
        """Resolve path using workdir if path is relative."""
        p = Path(path)
        if p.is_absolute():
            return p
        if self.workdir:
            return self.workdir / p
        return p  # Relative to cwd (backward compatible)

    def forward(self, path: str = ".", recursive: bool = False) -> str:
        """List directory contents"""
        try:
            dir_path = self._resolve_path(path)
            if not dir_path.exists():
                return f"Error: Path does not exist - {path}"

            if not dir_path.is_dir():
                return f"Error: Path is not a directory - {path}"

            result = f"Directory contents: {path}\n\n"

            if recursive:
                # List recursively
                for item in sorted(dir_path.rglob("*")):
                    relative_path = item.relative_to(dir_path)
                    if item.is_file():
                        size = item.stat().st_size
                        result += f"  File: {relative_path} ({size} bytes)\n"
                    elif item.is_dir():
                        result += f"  Directory: {relative_path}/\n"
            else:
                # List current directory only
                items = list(dir_path.iterdir())
                items.sort(key=lambda x: (x.is_file(), x.name.lower()))

                for item in items:
                    if item.is_file():
                        size = item.stat().st_size
                        result += f"  File: {item.name} ({size} bytes)\n"
                    elif item.is_dir():
                        result += f"  Directory: {item.name}/\n"
                    else:
                        result += f"  Other: {item.name}\n"

            return self.format_for_observation(result)

        except Exception as e:
            return f"Error listing directory: {str(e)}"

    def format_for_observation(self, output: Any) -> str:
        """格式化输出，自动截断过大内容"""
        if isinstance(output, str):
            return truncate_output(output, tool_name=self.name)
        return str(output)
