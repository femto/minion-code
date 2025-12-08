#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File writing tool
"""

from pathlib import Path
from typing import Optional
from minion.tools import BaseTool


class FileWriteTool(BaseTool):
    """File writing tool"""

    name = "file_write"
    description = "Write content to file"
    readonly = False  # Writing tool, modifies system state
    inputs = {
        "file_path": {"type": "string", "description": "File path to write to"},
        "content": {"type": "string", "description": "Content to write"},
    }
    output_type = "string"

    def __init__(self, workdir: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workdir = Path(workdir) if workdir else None

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve path using workdir if path is relative."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        if self.workdir:
            return self.workdir / path
        return path  # Relative to cwd (backward compatible)

    def forward(self, file_path: str, content: str) -> str:
        """Write file content"""
        try:
            path = self._resolve_path(file_path)
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Successfully wrote to file: {path} ({len(content)} characters)"

        except Exception as e:
            return f"Error writing file: {str(e)}"
