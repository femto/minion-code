#!/usr/bin/env python3
"""Shared helpers for filesystem search tools."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Sequence


RG_TIMEOUT_SECONDS = 30
DEFAULT_TOOL_RESULT_LIMIT = 200
NOISY_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        ".pytest_cache",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "target",
        "venv",
    }
)


def find_rg() -> Optional[str]:
    """Return the path to rg if available."""
    return shutil.which("rg")


def run_rg(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run rg with consistent defaults."""
    return subprocess.run(
        [find_rg() or "rg", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=RG_TIMEOUT_SECONDS,
        check=False,
    )


def collect_rg_lines(
    args: list[str], cwd: Path, *, max_results: int
) -> tuple[list[str], bool]:
    """Collect at most max_results + 1 lines from rg and indicate truncation."""
    process = subprocess.Popen(
        [find_rg() or "rg", *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None

    lines: list[str] = []
    truncated = False
    try:
        for raw_line in process.stdout:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            if len(lines) >= max_results:
                truncated = True
                process.terminate()
                break
            lines.append(line)
        stdout_tail, stderr_text = process.communicate(timeout=RG_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError("rg timed out")

    if process.returncode not in (0, 1, -15):
        message = (stderr_text or stdout_tail or "").strip()
        raise RuntimeError(message or "rg failed")

    return lines, truncated


def build_rg_exclude_args() -> list[str]:
    """Return default rg glob exclusions for noisy directories."""
    args: list[str] = []
    for name in sorted(NOISY_DIRECTORY_NAMES):
        args.extend(["-g", f"!**/{name}/**"])
    return args


def build_extra_ignore_args(ignore_patterns: Sequence[str]) -> list[str]:
    """Return rg exclude globs for caller-provided ignore patterns."""
    args: list[str] = []
    for pattern in ignore_patterns:
        cleaned = pattern.strip()
        if not cleaned:
            continue
        if cleaned.startswith("!"):
            cleaned = cleaned[1:]
        args.extend(["-g", f"!{cleaned}"])
    return args


def normalize_ignore_patterns(
    ignore: Optional[Sequence[str] | str],
) -> list[str]:
    """Normalize ignore input into a list of non-empty glob patterns."""
    if ignore is None:
        return []
    if isinstance(ignore, str):
        raw_parts = ignore.replace("\n", ",").split(",")
        return [part.strip() for part in raw_parts if part.strip()]
    return [part.strip() for part in ignore if part and part.strip()]


def is_hidden_name(name: str) -> bool:
    """Return True if the path component is hidden."""
    return name.startswith(".")


def should_skip_relative_path(
    relative_path: Path, *, include_hidden: bool = False
) -> bool:
    """Return True if the path should be skipped by fallback filesystem scans."""
    for part in relative_path.parts:
        if part in NOISY_DIRECTORY_NAMES:
            return True
        if not include_hidden and is_hidden_name(part):
            return True
    return False


def iter_visible_children(
    dir_path: Path, *, include_hidden: bool = False
) -> Iterable[Path]:
    """Yield visible child paths from a directory."""
    for child in dir_path.iterdir():
        relative_path = Path(child.name)
        if should_skip_relative_path(
            relative_path, include_hidden=include_hidden
        ):
            continue
        yield child
