#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Permission store for persistent tool permissions.

Stores user's "always allow" and "always reject" preferences
per project in ~/.minion/sessions/<project>-<hash>/permissions.json
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional, Set, Dict

logger = logging.getLogger(__name__)


class PermissionStore:
    """
    Manages persistent tool permission preferences per project.

    Stores permissions in ~/.minion/sessions/<project-name>-<hash>/permissions.json
    """

    def __init__(self, cwd: str):
        """
        Initialize permission store for a specific project.

        Args:
            cwd: The working directory (project root) for this session
        """
        cwd_hash = hashlib.md5(cwd.encode()).hexdigest()[:8]
        project_name = Path(cwd).name
        self.config_dir = (
            Path.home() / ".minion" / "sessions" / f"{project_name}-{cwd_hash}"
        )
        self.permissions_file = self.config_dir / "permissions.json"

        # Permission sets
        self._allow_always: Set[str] = set()
        self._reject_always: Set[str] = set()

        # Load existing permissions
        self._load()

    def is_allowed(self, tool_name: str) -> Optional[bool]:
        """
        Check if tool has persistent permission.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if always allowed, False if always rejected, None if not set
        """
        if tool_name in self._allow_always:
            return True
        if tool_name in self._reject_always:
            return False
        return None

    def set_permission(self, tool_name: str, always_allow: bool) -> None:
        """
        Set persistent permission for a tool.

        Args:
            tool_name: Name of the tool
            always_allow: True to always allow, False to always reject
        """
        if always_allow:
            self._allow_always.add(tool_name)
            self._reject_always.discard(tool_name)
            logger.info(f"Set permission: always allow '{tool_name}'")
        else:
            self._reject_always.add(tool_name)
            self._allow_always.discard(tool_name)
            logger.info(f"Set permission: always reject '{tool_name}'")

        self._save()

    def clear_permission(self, tool_name: str) -> None:
        """
        Clear permission for a tool (reset to ask every time).

        Args:
            tool_name: Name of the tool
        """
        self._allow_always.discard(tool_name)
        self._reject_always.discard(tool_name)
        self._save()
        logger.info(f"Cleared permission for '{tool_name}'")

    def clear_all(self) -> None:
        """Clear all permissions."""
        self._allow_always.clear()
        self._reject_always.clear()
        self._save()
        logger.info("Cleared all permissions")

    def get_all(self) -> Dict[str, list]:
        """Get all permissions as a dict."""
        return {
            "allow_always": sorted(self._allow_always),
            "reject_always": sorted(self._reject_always),
        }

    def _load(self) -> None:
        """Load permissions from file."""
        if not self.permissions_file.exists():
            return

        try:
            with open(self.permissions_file, "r") as f:
                data = json.load(f)

            self._allow_always = set(data.get("allow_always", []))
            self._reject_always = set(data.get("reject_always", []))
            logger.debug(f"Loaded permissions from {self.permissions_file}")
        except Exception as e:
            logger.warning(f"Failed to load permissions: {e}")

    def _save(self) -> None:
        """Save permissions to file."""
        try:
            # Ensure directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            data = {
                "allow_always": sorted(self._allow_always),
                "reject_always": sorted(self._reject_always),
            }

            with open(self.permissions_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved permissions to {self.permissions_file}")
        except Exception as e:
            logger.error(f"Failed to save permissions: {e}")


__all__ = ["PermissionStore"]
