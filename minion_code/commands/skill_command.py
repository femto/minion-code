#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skill command - wrapper to execute skills as slash commands.
"""

from . import BaseCommand, CommandType


class SkillCommand(BaseCommand):
    """
    Command wrapper for executing skills.

    Skills are dynamically loaded and can be executed like /skill-name.
    This is a PROMPT type command - the skill content is expanded
    and sent to the LLM.
    """

    name: str = ""  # Set dynamically
    description: str = ""  # Set dynamically
    usage: str = ""  # Set dynamically
    command_type: CommandType = CommandType.PROMPT
    is_skill: bool = True

    def __init__(self, output, agent=None, skill=None):
        """
        Initialize the skill command.

        Args:
            output: OutputAdapter instance
            agent: Optional agent instance
            skill: Skill object to wrap
        """
        super().__init__(output, agent)
        self.skill = skill

        if skill:
            self.name = skill.name
            self.description = skill.description
            self.usage = f"/{skill.name}"

    async def execute(self, args: str) -> None:
        """
        Execute is not used for PROMPT commands.
        The get_prompt method is used instead.
        """
        pass

    async def get_prompt(self, args: str) -> str:
        """
        Get the expanded prompt for this skill.

        Args:
            args: Command arguments (usually ignored for skills)

        Returns:
            Expanded prompt string containing skill instructions
        """
        if not self.skill:
            return f"Error: Skill not found"

        # Build the skill activation message
        header = f'<command-message>The "{self.skill.name}" skill is loading</command-message>'
        skill_content = self.skill.get_prompt()

        return f"{header}\n\n{skill_content}"


def create_skill_command(skill) -> type:
    """
    Dynamically create a SkillCommand class for a specific skill.

    Args:
        skill: Skill object

    Returns:
        SkillCommand subclass configured for the skill
    """

    class DynamicSkillCommand(SkillCommand):
        name = skill.name
        description = skill.description
        usage = f"/{skill.name}"

        def __init__(self, output, agent=None):
            super().__init__(output, agent, skill=skill)

    DynamicSkillCommand.__name__ = f"{skill.name.replace('-', '_').title()}SkillCommand"
    return DynamicSkillCommand
