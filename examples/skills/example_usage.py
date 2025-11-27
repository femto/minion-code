#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: How to use the Skills system in minion-code.

This script demonstrates:
1. Loading skills from directories
2. Querying the skill registry
3. Using skills as commands
4. Generating skill prompts for LLM
"""

from pathlib import Path
from minion_code.skills import Skill, SkillRegistry, SkillLoader
from minion_code.skills.skill_registry import get_skill_registry, reset_skill_registry
from minion_code.tools.skill_tool import SkillTool, generate_skill_tool_prompt


def example_1_basic_skill_parsing():
    """Example 1: Parse a SKILL.md file directly."""
    print("=" * 60)
    print("Example 1: Basic Skill Parsing")
    print("=" * 60)

    # Parse the example skill
    skill_path = Path(__file__).parent / "hello-world" / "SKILL.md"

    if skill_path.exists():
        skill = Skill.from_skill_md(skill_path, location="project")

        if skill:
            print(f"Name: {skill.name}")
            print(f"Description: {skill.description}")
            print(f"Location: {skill.location}")
            print(f"Allowed Tools: {skill.allowed_tools}")
            print(f"License: {skill.license}")
            print(f"\nContent Preview (first 200 chars):")
            print(skill.content[:200] + "...")
    else:
        print(f"Skill not found at {skill_path}")

    print()


def example_2_skill_registry():
    """Example 2: Use the SkillRegistry to manage skills."""
    print("=" * 60)
    print("Example 2: Skill Registry")
    print("=" * 60)

    # Create a fresh registry
    registry = SkillRegistry()

    # Manually add skills
    skill1 = Skill(
        name="custom-skill-1",
        description="A custom skill added programmatically",
        content="# Custom Skill 1\n\nInstructions here.",
        path=Path("/tmp/custom"),
        location="project"
    )

    skill2 = Skill(
        name="custom-skill-2",
        description="Another custom skill",
        content="# Custom Skill 2\n\nMore instructions.",
        path=Path("/tmp/custom"),
        location="user"
    )

    registry.register(skill1)
    registry.register(skill2)

    print(f"Registered {len(registry)} skills")
    print("\nAll skills:")
    for skill in registry.list_all():
        print(f"  - {skill.name} ({skill.location})")

    # Lookup a skill
    found = registry.get("custom-skill-1")
    print(f"\nFound skill: {found}")

    print()


def example_3_skill_loader():
    """Example 3: Load skills from directories."""
    print("=" * 60)
    print("Example 3: Skill Loader")
    print("=" * 60)

    # Reset global registry
    reset_skill_registry()

    # Create loader for current project
    loader = SkillLoader()

    print("Search paths:")
    for path, location in loader.get_search_paths():
        exists = "✓" if path.exists() else "✗"
        print(f"  [{exists}] {location}: {path}")

    # Load all skills
    registry = loader.load_all()

    print(f"\nLoaded {len(registry)} skills:")
    for skill in registry.list_all():
        print(f"  - {skill.name}: {skill.description[:50]}...")

    print()


def example_4_skill_tool():
    """Example 4: Use the SkillTool."""
    print("=" * 60)
    print("Example 4: Skill Tool")
    print("=" * 60)

    # Create skill tool
    tool = SkillTool()

    # List available skills
    skills = tool.registry.list_all()
    print(f"Available skills: {len(skills)}")

    # Validate a skill
    if skills:
        skill_name = skills[0].name
        is_valid, error = tool.validate_skill(skill_name)
        print(f"\nValidating '{skill_name}': {'Valid' if is_valid else error}")

    # Validate non-existent skill
    is_valid, error = tool.validate_skill("non-existent-skill")
    print(f"Validating 'non-existent-skill': {'Valid' if is_valid else error}")

    print()


def example_5_generate_prompt():
    """Example 5: Generate skill prompt for LLM."""
    print("=" * 60)
    print("Example 5: Generate Skill Prompt")
    print("=" * 60)

    prompt = generate_skill_tool_prompt()

    print(f"Generated prompt ({len(prompt)} characters):")
    print("-" * 40)
    # Show first 1000 chars
    print(prompt[:1000])
    if len(prompt) > 1000:
        print("...")
        print(f"[Truncated - full prompt is {len(prompt)} chars]")

    print()


def example_6_skill_as_command():
    """Example 6: Use skills as slash commands."""
    print("=" * 60)
    print("Example 6: Skills as Commands")
    print("=" * 60)

    from minion_code.commands import command_registry

    # List skill commands
    skills = command_registry.list_skills()
    print(f"Available skill commands: {len(skills)}")

    for name, cmd_class in list(skills.items())[:5]:
        print(f"  /{name} - {cmd_class.description[:40]}...")

    # Get a specific skill command
    if skills:
        skill_name = list(skills.keys())[0]
        cmd_class = command_registry.get_command(skill_name)
        print(f"\nCommand type for /{skill_name}: {cmd_class.command_type}")
        print(f"Is skill: {cmd_class.is_skill}")

    print()


def example_7_xml_output():
    """Example 7: XML format for prompts."""
    print("=" * 60)
    print("Example 7: XML Output Format")
    print("=" * 60)

    skill = Skill(
        name="example-skill",
        description="An example skill showing XML output",
        content="Instructions",
        path=Path("/tmp"),
        location="project"
    )

    print("Single skill XML:")
    print(skill.to_xml())

    # Registry XML
    registry = SkillRegistry()
    registry.register(skill)
    registry.register(Skill(
        name="another-skill",
        description="Another skill",
        content="More instructions",
        path=Path("/tmp"),
        location="user"
    ))

    print("\nRegistry XML output:")
    print(registry.generate_skills_prompt())

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("MINION-CODE SKILLS SYSTEM EXAMPLES")
    print("=" * 60 + "\n")

    example_1_basic_skill_parsing()
    example_2_skill_registry()
    example_3_skill_loader()
    example_4_skill_tool()
    example_5_generate_prompt()
    example_6_skill_as_command()
    example_7_xml_output()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
