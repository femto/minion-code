#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""File pattern matching tool."""

import glob
from pathlib import Path
from typing import Any, Optional, Sequence

from minion.tools import BaseTool

from ..utils.output_truncator import truncate_output
from ..utils.search_backend import DEFAULT_TOOL_RESULT_LIMIT
from ..utils.search_backend import build_extra_ignore_args
from ..utils.search_backend import build_rg_exclude_args
from ..utils.search_backend import collect_rg_lines
from ..utils.search_backend import find_rg
from ..utils.search_backend import normalize_ignore_patterns
from ..utils.search_backend import should_skip_relative_path


class GlobTool(BaseTool):
    """Match files using glob patterns."""

    name = "glob"
    description = "Match file paths using glob patterns"
    readonly = True
    inputs = {
        "pattern": {"type": "string", "description": "Glob pattern"},
        "path": {"type": "string", "description": "Search path", "nullable": True},
        "ignore": {
            "type": "array",
            "description": "Optional glob patterns to exclude from this search",
            "items": {"type": "string"},
            "nullable": True,
        },
    }
    output_type = "string"

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

    def forward(
        self,
        pattern: str,
        path: str = ".",
        ignore: Optional[Sequence[str] | str] = None,
    ) -> str:
        """Match files using a glob pattern."""
        try:
            search_path = self._resolve_path(path)
            if not search_path.exists():
                return f"Error: Path does not exist - {path}"

            ignore_patterns = normalize_ignore_patterns(ignore)
            matches, truncated = self._find_matches(
                pattern,
                search_path,
                ignore_patterns=ignore_patterns,
            )

            if not matches:
                return f"No files found matching pattern '{pattern}'"

            result = [f"Files matching pattern '{pattern}':", ""]
            for match in matches:
                path_obj = Path(match)
                size = path_obj.stat().st_size
                result.append(f"  File: {match} ({size} bytes)")
            if truncated:
                result.extend(
                    [
                        "",
                        f"(Output limited to {DEFAULT_TOOL_RESULT_LIMIT} matches; refine the pattern or add ignore globs)",
                    ]
                )
            result.extend(["", f"Total {len(matches)} matches found"])
            return self.format_for_observation("\n".join(result))
        except Exception as exc:
            return f"Error during glob matching: {exc}"

    def _find_matches(
        self,
        pattern: str,
        search_path: Path,
        *,
        ignore_patterns: list[str],
    ) -> tuple[list[str], bool]:
        rg_path = find_rg()
        if rg_path and search_path.is_dir():
            return self._find_matches_with_rg(
                search_path,
                pattern,
                ignore_patterns=ignore_patterns,
            )
        return self._find_matches_with_python(
            pattern,
            search_path,
            ignore_patterns=ignore_patterns,
        )

    def _find_matches_with_rg(
        self,
        search_path: Path,
        pattern: str,
        *,
        ignore_patterns: list[str],
    ) -> tuple[list[str], bool]:
        args = ["--files"]
        args.extend(build_rg_exclude_args())
        args.extend(build_extra_ignore_args(ignore_patterns))
        args.extend(["-g", pattern, "."])
        lines, truncated = collect_rg_lines(
            args,
            search_path,
            max_results=DEFAULT_TOOL_RESULT_LIMIT,
        )
        return [str((search_path / line).resolve()) for line in lines], truncated

    def _find_matches_with_python(
        self,
        pattern: str,
        search_path: Path,
        *,
        ignore_patterns: list[str],
    ) -> tuple[list[str], bool]:
        if search_path.is_file():
            if search_path.match(pattern):
                return [str(search_path.resolve())], False
            return [], False

        matches: list[str] = []
        for raw_match in sorted(glob.glob(str(search_path / pattern), recursive=True)):
            path_obj = Path(raw_match)
            try:
                relative_path = path_obj.relative_to(search_path)
            except ValueError:
                relative_path = Path(path_obj.name)
            if not path_obj.is_file():
                continue
            if should_skip_relative_path(relative_path):
                continue
            if any(path_obj.match(ignore_pattern) for ignore_pattern in ignore_patterns):
                continue
            matches.append(str(path_obj.resolve()))
            if len(matches) >= DEFAULT_TOOL_RESULT_LIMIT:
                return matches, True
        return matches, False

    def format_for_observation(self, output: Any) -> str:
        """Format output with truncation safeguards."""
        if isinstance(output, str):
            return truncate_output(output, tool_name=self.name)
        return str(output)
