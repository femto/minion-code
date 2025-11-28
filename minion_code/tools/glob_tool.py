#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
File pattern matching tool
"""

import glob
from pathlib import Path
from typing import Any
from minion.tools import BaseTool
from ..utils.output_truncator import truncate_output


class GlobTool(BaseTool):
    """File pattern matching tool"""

    name = "glob"
    description = "Match files using glob patterns"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "pattern": {"type": "string", "description": "Glob pattern"},
        "path": {"type": "string", "description": "Search path", "nullable": True},
    }
    output_type = "string"

    def forward(self, pattern: str, path: str = ".") -> str:
        """Match files using glob pattern"""
        try:
            search_path = Path(path)
            if not search_path.exists():
                return f"Error: Path does not exist - {path}"

            # Build complete search pattern
            if search_path.is_dir():
                full_pattern = str(search_path / pattern)
            else:
                full_pattern = pattern

            matches = glob.glob(full_pattern, recursive=True)
            matches.sort()

            if not matches:
                return f"No files found matching pattern '{pattern}'"

            result = f"Files matching pattern '{pattern}':\n"
            for match in matches:
                path_obj = Path(match)
                if path_obj.is_file():
                    size = path_obj.stat().st_size
                    result += f"  File: {match} ({size} bytes)\n"
                elif path_obj.is_dir():
                    result += f"  Directory: {match}/\n"
                else:
                    result += f"  Other: {match}\n"

            result += f"\nTotal {len(matches)} matches found"
            return self.format_for_observation(result)

        except Exception as e:
            return f"Error during glob matching: {str(e)}"

    def format_for_observation(self, output: Any) -> str:
        """Format output, auto-truncate if too large"""
        if isinstance(output, str):
            return truncate_output(output, tool_name=self.name)
        return str(output)
