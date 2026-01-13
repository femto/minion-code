#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subagent Loader - discovers and loads subagent configurations from standard directories.
"""

import logging
from pathlib import Path
from typing import List, Optional

from .subagent import SubagentConfig
from .subagent_registry import SubagentRegistry, get_subagent_registry
from .builtin import get_all_builtin_subagents

logger = logging.getLogger(__name__)


class SubagentLoader:
    """
    Discovers and loads subagent configurations.

    Search paths (in priority order - lower priority registered first):
    1. builtin (code-defined)
    2. ~/.claude/subagents or ~/.minion/subagents (user-level)
    3. .claude/subagents or .minion/subagents (project-level)

    Project-level overrides user-level, which overrides builtin.
    """

    SUBAGENT_DIRS = [
        ".claude/agents",      # Claude Code compatible
        ".minion/agents",      # Minion compatible
        ".claude/subagents",   # Legacy/alternative
        ".minion/subagents",   # Legacy/alternative
    ]

    SUBAGENT_FILE = "SUBAGENT.yaml"

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the subagent loader."""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.home_dir = Path.home()

    def get_search_paths(self) -> List[tuple[Path, str]]:
        """
        Get all subagent search paths with their location type.
        Returns paths in priority order (lowest priority first).
        """
        paths = []

        # User-level paths (lower priority than project)
        for subagent_dir in self.SUBAGENT_DIRS:
            user_path = self.home_dir / subagent_dir
            paths.append((user_path, "user"))

        # Project-level paths (highest priority)
        for subagent_dir in self.SUBAGENT_DIRS:
            project_path = self.project_root / subagent_dir
            paths.append((project_path, "project"))

        return paths

    def discover_subagents(self, subagents_dir: Path) -> List[Path]:
        """
        Discover all subagent directories within a subagents directory.
        A subagent directory must contain a SUBAGENT.yaml file.
        """
        if not subagents_dir.exists() or not subagents_dir.is_dir():
            return []

        subagent_files = []

        for item in subagents_dir.iterdir():
            if item.is_dir():
                subagent_yaml = item / self.SUBAGENT_FILE
                if subagent_yaml.exists():
                    subagent_files.append(subagent_yaml)

        return subagent_files

    def load_subagent(self, yaml_path: Path, location: str) -> Optional[SubagentConfig]:
        """Load a single subagent from its SUBAGENT.yaml file."""
        try:
            subagent = SubagentConfig.from_yaml(yaml_path, location)
            if subagent:
                logger.debug(f"Loaded subagent: {subagent.name} from {yaml_path}")
            else:
                logger.warning(f"Failed to parse subagent: {yaml_path}")
            return subagent
        except Exception as e:
            logger.error(f"Error loading subagent from {yaml_path}: {e}")
            return None

    def load_all(self, registry: Optional[SubagentRegistry] = None) -> SubagentRegistry:
        """
        Load all subagents (builtin + custom) into the registry.
        Builtin is registered first (lowest priority), then user, then project.
        """
        if registry is None:
            registry = get_subagent_registry()

        # 1. Register builtin subagents first (lowest priority)
        for subagent in get_all_builtin_subagents():
            registered = registry.register(subagent)
            if registered:
                logger.debug(f"Registered builtin subagent: {subagent.name}")

        # 2. Load from file system (user then project)
        for search_path, location in self.get_search_paths():
            subagent_files = self.discover_subagents(search_path)

            for yaml_path in subagent_files:
                subagent = self.load_subagent(yaml_path, location)
                if subagent:
                    registered = registry.register(subagent)
                    if registered:
                        logger.debug(f"Registered {location} subagent: {subagent.name}")
                    else:
                        logger.debug(
                            f"Skipped subagent {subagent.name} - already registered from higher priority"
                        )

        return registry

    def reload(self, registry: Optional[SubagentRegistry] = None) -> SubagentRegistry:
        """Reload all subagents, clearing the existing registry first."""
        if registry is None:
            registry = get_subagent_registry()

        registry.clear()
        return self.load_all(registry)


def load_subagents(project_root: Optional[Path] = None) -> SubagentRegistry:
    """Convenience function to load all subagents."""
    loader = SubagentLoader(project_root)
    return loader.load_all()


def get_available_subagents() -> List[SubagentConfig]:
    """Get list of all available subagents."""
    registry = get_subagent_registry()

    if len(registry) == 0:
        load_subagents()

    return registry.list_all()
