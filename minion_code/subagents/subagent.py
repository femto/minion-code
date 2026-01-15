#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subagent configuration dataclass representing a loaded subagent type.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml


@dataclass
class SubagentConfig:
    """Represents a configured subagent type with its metadata and settings."""

    name: str  # Unique identifier (e.g., "Explore", "Plan")
    description: str  # Short description of what the agent does
    when_to_use: str  # When the user should use this agent
    tools: List[str] = field(default_factory=lambda: ["*"])  # Tool filter: ["*"] = all
    system_prompt: Optional[str] = None  # Custom system prompt for this agent type
    model_name: str = "inherit"  # "inherit" = use parent, or specific model name

    # Additional metadata
    path: Optional[Path] = None  # Path to config file (for file-based configs)
    location: str = "builtin"  # builtin, project, user
    readonly: bool = False  # If True, agent only gets read-only tools
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml(
        cls, yaml_path: Path, location: str = "project"
    ) -> Optional["SubagentConfig"]:
        """
        Parse a SUBAGENT.yaml file and create a SubagentConfig instance.

        Args:
            yaml_path: Path to the SUBAGENT.yaml file
            location: Where the subagent was found (project, user)

        Returns:
            SubagentConfig instance or None if parsing fails
        """
        if not yaml_path.exists():
            return None

        try:
            content = yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
        except (yaml.YAMLError, IOError):
            return None

        if not data:
            return None

        name = data.get("name")
        description = data.get("description")
        when_to_use = data.get("when_to_use")

        if not name or not description or not when_to_use:
            return None

        # Load system_prompt from separate file if specified
        system_prompt = data.get("system_prompt")
        if (
            system_prompt
            and isinstance(system_prompt, str)
            and system_prompt.startswith("file:")
        ):
            prompt_file = yaml_path.parent / system_prompt[5:]
            if prompt_file.exists():
                system_prompt = prompt_file.read_text(encoding="utf-8")
            else:
                system_prompt = None

        return cls(
            name=name,
            description=description,
            when_to_use=when_to_use,
            tools=data.get("tools", ["*"]),
            system_prompt=system_prompt,
            model_name=data.get("model_name", "inherit"),
            path=yaml_path.parent,
            location=location,
            readonly=data.get("readonly", False),
            metadata=data.get("metadata", {}),
        )

    def to_xml(self) -> str:
        """
        Format subagent as XML for inclusion in prompts.

        Returns:
            XML formatted subagent entry
        """
        tools_str = ", ".join(self.tools) if self.tools != ["*"] else "All tools"
        return f"""<subagent>
<name>{self.name}</name>
<description>{self.description}</description>
<when_to_use>{self.when_to_use}</when_to_use>
<tools>{tools_str}</tools>
<location>{self.location}</location>
</subagent>"""

    def to_prompt_line(self) -> str:
        """
        Format subagent as a single line for tool description.

        Returns:
            Formatted prompt line like: "- Explore: Fast codebase exploration... (Tools: glob, grep)"
        """
        tools_str = ", ".join(self.tools) if self.tools != ["*"] else "All tools"
        return f"- {self.name}: {self.description} (Tools: {tools_str})"

    def __repr__(self) -> str:
        return f"SubagentConfig(name={self.name!r}, location={self.location!r})"
