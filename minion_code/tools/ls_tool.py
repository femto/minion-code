#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Directory listing tool
"""

from pathlib import Path
from minion.tools import BaseTool


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

    def forward(self, path: str = ".", recursive: bool = False) -> str:
        """List directory contents"""
        try:
            dir_path = Path(path)
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

            return result

        except Exception as e:
            return f"Error listing directory: {str(e)}"
