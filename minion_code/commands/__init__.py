#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command system for MinionCode TUI

This module provides a command system similar to Claude Code or Gemini CLI,
where commands are prefixed with '/' and each command is implemented in a separate file.

Command Types:
- LOCAL: Direct execution, returns result immediately (e.g., /clear, /help)
- LOCAL_JSX: Requires UI interaction, returns a component (e.g., /config, /model)
- PROMPT: Replaces user input and sends to LLM (e.g., /bug, custom .md commands)
"""

import importlib
import pkgutil
from typing import Dict, Type, Optional, Union
from abc import ABC, abstractmethod
from enum import Enum


class CommandType(Enum):
    """Types of commands based on execution flow."""

    LOCAL = "local"  # Direct execution, returns result
    LOCAL_JSX = "local_jsx"  # Requires UI interaction
    PROMPT = "prompt"  # Replaces user input, sends to LLM


class BaseCommand(ABC):
    """Base class for all commands."""

    name: str = ""
    description: str = ""
    usage: str = ""
    aliases: list = []
    command_type: CommandType = CommandType.LOCAL  # Default to LOCAL
    is_skill: bool = False  # Whether this is a skill (affects display)

    def __init__(self, output, agent=None):
        """
        Initialize command.

        Args:
            output: OutputAdapter instance for UI output (RichAdapter or TextualAdapter)
            agent: Optional agent instance
        """
        self.output = output
        self.agent = agent

        # Backward compatibility: expose console attribute for Rich adapter
        # This allows old code using self.console to still work
        if hasattr(output, "console"):
            self.console = output.console

    @abstractmethod
    async def execute(self, args: str) -> None:
        """Execute the command with given arguments."""
        pass

    async def get_prompt(self, args: str) -> str:
        """
        Get the expanded prompt for PROMPT type commands.
        Override this method for PROMPT type commands.

        Args:
            args: Command arguments from user input

        Returns:
            Expanded prompt string to send to LLM
        """
        # Default implementation just returns the args
        return args

    def get_help(self) -> str:
        """Get help text for this command."""
        return f"**/{self.name}** - {self.description}\n\nUsage: {self.usage}"


class CommandRegistry:
    """Registry for managing commands."""

    def __init__(self):
        self.commands: Dict[str, Type[BaseCommand]] = {}
        self._skills_loaded = False
        self._load_commands()

    def _load_commands(self):
        """Dynamically load all command modules."""
        import os

        commands_dir = os.path.dirname(__file__)

        for filename in os.listdir(commands_dir):
            if filename.endswith("_command.py") and not filename.startswith("_"):
                # Skip skill_command.py as it's loaded dynamically
                if filename == "skill_command.py":
                    continue

                modname = filename[:-3]  # Remove .py extension
                try:
                    module = importlib.import_module(f"minion_code.commands.{modname}")

                    # Look for command classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseCommand)
                            and attr != BaseCommand
                            and hasattr(attr, "name")
                            and attr.name
                        ):

                            self.commands[attr.name] = attr

                            # Register aliases
                            for alias in getattr(attr, "aliases", []):
                                self.commands[alias] = attr

                except ImportError as e:
                    print(f"Failed to load command module {modname}: {e}")

    def _load_skills(self):
        """Load skills as commands."""
        if self._skills_loaded:
            return

        try:
            from minion_code.skills.skill_loader import load_skills
            from minion_code.commands.skill_command import create_skill_command

            registry = load_skills()
            for skill in registry.list_all():
                # Create a command class for each skill
                skill_cmd_class = create_skill_command(skill)
                self.commands[skill.name] = skill_cmd_class

            self._skills_loaded = True
        except ImportError as e:
            print(f"Failed to load skills: {e}")

    def get_command(self, name: str) -> Optional[Type[BaseCommand]]:
        """Get a command class by name."""
        # Try to load skills if command not found
        if name not in self.commands and not self._skills_loaded:
            self._load_skills()
        return self.commands.get(name)

    def list_commands(self) -> Dict[str, Type[BaseCommand]]:
        """List all available commands (excluding skills)."""
        # Return only primary commands (not aliases, not skills)
        return {
            name: cmd
            for name, cmd in self.commands.items()
            if cmd.name == name and not getattr(cmd, "is_skill", False)
        }

    def list_skills(self) -> Dict[str, Type[BaseCommand]]:
        """List all available skills as commands."""
        # Ensure skills are loaded
        if not self._skills_loaded:
            self._load_skills()
        return {
            name: cmd
            for name, cmd in self.commands.items()
            if cmd.name == name and getattr(cmd, "is_skill", False)
        }

    def list_all(self) -> Dict[str, Type[BaseCommand]]:
        """List all available commands and skills."""
        if not self._skills_loaded:
            self._load_skills()
        return {name: cmd for name, cmd in self.commands.items() if cmd.name == name}

    def reload_commands(self):
        """Reload all commands."""
        self.commands.clear()
        self._skills_loaded = False
        self._load_commands()

    def reload_skills(self):
        """Reload skills only."""
        # Remove existing skill commands
        skills_to_remove = [
            name
            for name, cmd in self.commands.items()
            if getattr(cmd, "is_skill", False)
        ]
        for name in skills_to_remove:
            del self.commands[name]
        self._skills_loaded = False
        self._load_skills()


# Global command registry
command_registry = CommandRegistry()
