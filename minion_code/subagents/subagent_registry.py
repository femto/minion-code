#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subagent Registry - manages loaded subagent configurations and provides lookup functionality.
"""

from typing import Dict, Optional, List
from .subagent import SubagentConfig


class SubagentRegistry:
    """
    Registry for managing loaded subagent configurations.

    Subagents are organized by name and can be looked up for task execution.
    The registry handles subagent deduplication based on priority.
    Priority: builtin < user < project (project overrides all)
    """

    PRIORITY_ORDER = {"builtin": 2, "user": 1, "project": 0}

    def __init__(self):
        self._subagents: Dict[str, SubagentConfig] = {}
        self._subagents_by_location: Dict[str, List[SubagentConfig]] = {
            "builtin": [],
            "project": [],
            "user": [],
        }

    def register(self, subagent: SubagentConfig) -> bool:
        """
        Register a subagent in the registry.

        Project subagents take precedence over user subagents,
        which take precedence over builtin.

        Args:
            subagent: SubagentConfig instance to register

        Returns:
            True if the subagent was registered, False if it was skipped
        """
        existing = self._subagents.get(subagent.name)

        if existing:
            existing_priority = self.PRIORITY_ORDER.get(existing.location, 99)
            new_priority = self.PRIORITY_ORDER.get(subagent.location, 99)

            if new_priority >= existing_priority:
                # Skip - existing subagent has higher or equal priority
                return False

        self._subagents[subagent.name] = subagent
        self._subagents_by_location[subagent.location].append(subagent)
        return True

    def get(self, name: str) -> Optional[SubagentConfig]:
        """Get a subagent by name."""
        return self._subagents.get(name)

    def exists(self, name: str) -> bool:
        """Check if a subagent exists in the registry."""
        return name in self._subagents

    def list_all(self) -> List[SubagentConfig]:
        """Get all registered subagents."""
        return list(self._subagents.values())

    def list_names(self) -> List[str]:
        """Get all registered subagent names."""
        return list(self._subagents.keys())

    def list_by_location(self, location: str) -> List[SubagentConfig]:
        """Get subagents by location type."""
        return self._subagents_by_location.get(location, [])

    def clear(self):
        """Clear all registered subagents."""
        self._subagents.clear()
        for location in self._subagents_by_location:
            self._subagents_by_location[location].clear()

    def generate_subagents_prompt(self, char_budget: int = 10000) -> str:
        """
        Generate a prompt listing all available subagents in XML format.

        Args:
            char_budget: Maximum characters for subagents list

        Returns:
            Formatted subagents prompt in XML format
        """
        subagents = self.list_all()

        if not subagents:
            return ""

        entries = []
        total_chars = 0

        for subagent in subagents:
            entry = subagent.to_xml()
            if total_chars + len(entry) > char_budget:
                break
            entries.append(entry)
            total_chars += len(entry)

        if not entries:
            return ""

        subagents_xml = "\n".join(entries)
        return f"""<available_subagents>
{subagents_xml}
</available_subagents>"""

    def generate_tool_description_lines(self) -> str:
        """
        Generate description lines for the Task tool.

        Returns:
            Multi-line string with each subagent's prompt line
        """
        subagents = self.list_all()
        return "\n".join(s.to_prompt_line() for s in subagents)

    def __len__(self) -> int:
        return len(self._subagents)

    def __contains__(self, name: str) -> bool:
        return name in self._subagents

    def __iter__(self):
        return iter(self._subagents.values())


# Global subagent registry instance
_subagent_registry: Optional[SubagentRegistry] = None


def get_subagent_registry() -> SubagentRegistry:
    """Get the global subagent registry instance."""
    global _subagent_registry
    if _subagent_registry is None:
        _subagent_registry = SubagentRegistry()
    return _subagent_registry


def reset_subagent_registry():
    """Reset the global subagent registry."""
    global _subagent_registry
    _subagent_registry = None
