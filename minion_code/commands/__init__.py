#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command system for MinionCode TUI

This module provides a command system similar to Claude Code or Gemini CLI,
where commands are prefixed with '/' and each command is implemented in a separate file.
"""

import importlib
import pkgutil
from typing import Dict, Type, Optional, Union
from abc import ABC, abstractmethod


class BaseCommand(ABC):
    """Base class for all commands."""

    name: str = ""
    description: str = ""
    usage: str = ""
    aliases: list = []

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
        if hasattr(output, 'console'):
            self.console = output.console

    @abstractmethod
    async def execute(self, args: str) -> None:
        """Execute the command with given arguments."""
        pass

    def get_help(self) -> str:
        """Get help text for this command."""
        return f"**/{self.name}** - {self.description}\n\nUsage: {self.usage}"


class CommandRegistry:
    """Registry for managing commands."""
    
    def __init__(self):
        self.commands: Dict[str, Type[BaseCommand]] = {}
        self._load_commands()
    
    def _load_commands(self):
        """Dynamically load all command modules."""
        import os
        commands_dir = os.path.dirname(__file__)
        
        for filename in os.listdir(commands_dir):
            if filename.endswith('_command.py') and not filename.startswith('_'):
                modname = filename[:-3]  # Remove .py extension
                try:
                    module = importlib.import_module(f'minion_code.commands.{modname}')
                    
                    # Look for command classes in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseCommand) and 
                            attr != BaseCommand and
                            hasattr(attr, 'name') and attr.name):
                            
                            self.commands[attr.name] = attr
                            
                            # Register aliases
                            for alias in getattr(attr, 'aliases', []):
                                self.commands[alias] = attr
                                
                except ImportError as e:
                    print(f"Failed to load command module {modname}: {e}")
    
    def get_command(self, name: str) -> Optional[Type[BaseCommand]]:
        """Get a command class by name."""
        return self.commands.get(name)
    
    def list_commands(self) -> Dict[str, Type[BaseCommand]]:
        """List all available commands."""
        # Return only primary commands (not aliases)
        return {name: cmd for name, cmd in self.commands.items() 
                if cmd.name == name}
    
    def reload_commands(self):
        """Reload all commands."""
        self.commands.clear()
        self._load_commands()


# Global command registry
command_registry = CommandRegistry()