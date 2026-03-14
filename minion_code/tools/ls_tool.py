#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Lightweight directory listing tool."""

from collections import deque
from pathlib import Path
from typing import Any, Optional

from minion.tools import BaseTool

from ..utils.output_truncator import truncate_output
from ..utils.search_backend import DEFAULT_TOOL_RESULT_LIMIT
from ..utils.search_backend import should_skip_relative_path


class LsTool(BaseTool):
    """List a small, bounded slice of a directory tree."""

    name = "ls"
    description = "List directory contents with bounded output"
    readonly = True
    inputs = {
        "path": {
            "type": "string",
            "description": "File or directory path to inspect",
            "nullable": True,
        },
        "recursive": {
            "type": "boolean",
            "description": "If true, traverse a few levels deep instead of only the immediate directory",
            "nullable": True,
        },
    }
    output_type = "string"

    DEFAULT_DEPTH = 1
    RECURSIVE_DEPTH = 3

    def __init__(self, workdir: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workdir = Path(workdir) if workdir else None

    def _resolve_path(self, path: str) -> Path:
        """Resolve path using workdir if path is relative."""
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        if self.workdir:
            return self.workdir / candidate
        return candidate

    def forward(self, path: str = ".", recursive: bool = False) -> str:
        """List a file or directory with bounded output."""
        try:
            target_path = self._resolve_path(path)
            if not target_path.exists():
                return f"Error: Path does not exist - {path}"

            if target_path.is_file():
                size = target_path.stat().st_size
                return self.format_for_observation(
                    "\n".join(
                        [
                            f"Path: {path}",
                            f"Absolute path: {target_path}",
                            f"File: {target_path.name} ({size} bytes)",
                        ]
                    )
                )

            if not target_path.is_dir():
                return f"Error: Path is not a file or directory - {path}"

            depth = self.RECURSIVE_DEPTH if recursive else self.DEFAULT_DEPTH
            entries, truncated = self._collect_entries(target_path, depth=depth)
            result = [f"Directory contents: {path}", ""]
            if entries:
                result.extend(entries)
            else:
                result.append("(empty)")
            if truncated:
                result.extend(
                    [
                        "",
                        f"(Output limited to {DEFAULT_TOOL_RESULT_LIMIT} entries; use glob/grep for targeted discovery)",
                    ]
                )
            return self.format_for_observation("\n".join(result))
        except Exception as exc:
            return f"Error listing directory: {exc}"

    def _collect_entries(self, dir_path: Path, *, depth: int) -> tuple[list[str], bool]:
        """Collect a bounded breadth-first list of entries."""
        entries: list[str] = []
        queue = deque([(dir_path, Path("."), 1)])

        while queue and len(entries) < DEFAULT_TOOL_RESULT_LIMIT:
            current_dir, relative_prefix, current_depth = queue.popleft()
            children = []
            for child in current_dir.iterdir():
                relative_path = (
                    Path(child.name)
                    if relative_prefix == Path(".")
                    else relative_prefix / child.name
                )
                if should_skip_relative_path(relative_path):
                    continue
                children.append((child, relative_path))

            children.sort(key=lambda item: (item[0].is_file(), item[0].name.lower()))

            for child, relative_path in children:
                if len(entries) >= DEFAULT_TOOL_RESULT_LIMIT:
                    return entries, True
                if child.is_dir():
                    entries.append(f"  Directory: {relative_path.as_posix()}/")
                    if current_depth < depth:
                        queue.append((child, relative_path, current_depth + 1))
                elif child.is_file():
                    size = child.stat().st_size
                    entries.append(
                        f"  File: {relative_path.as_posix()} ({size} bytes)"
                    )
                else:
                    entries.append(f"  Other: {relative_path.as_posix()}")

        return entries, bool(queue)

    def format_for_observation(self, output: Any) -> str:
        """Format output with truncation safeguards."""
        if isinstance(output, str):
            return truncate_output(output, tool_name=self.name)
        return str(output)
