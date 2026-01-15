#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the skills system.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from minion_code.skills.skill import Skill
from minion_code.skills.skill_registry import (
    SkillRegistry,
    get_skill_registry,
    reset_skill_registry,
)
from minion_code.skills.skill_loader import SkillLoader


class TestSkill:
    """Tests for the Skill class."""

    def test_parse_frontmatter_basic(self):
        """Test parsing basic YAML frontmatter."""
        content = """---
name: test-skill
description: A test skill for testing purposes
---

# Test Skill Instructions

This is the skill content.
"""
        frontmatter, body = Skill._parse_frontmatter(content)

        assert frontmatter["name"] == "test-skill"
        assert frontmatter["description"] == "A test skill for testing purposes"
        assert "# Test Skill Instructions" in body

    def test_parse_frontmatter_with_optional_fields(self):
        """Test parsing frontmatter with optional fields."""
        content = """---
name: advanced-skill
description: An advanced skill
license: MIT
allowed-tools:
  - Bash
  - Read
metadata:
  author: test
  version: "1.0"
---

Instructions here.
"""
        frontmatter, body = Skill._parse_frontmatter(content)

        assert frontmatter["name"] == "advanced-skill"
        assert frontmatter["license"] == "MIT"
        assert frontmatter["allowed-tools"] == ["Bash", "Read"]
        assert frontmatter["metadata"]["author"] == "test"

    def test_parse_frontmatter_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "# Just regular markdown\n\nNo frontmatter here."
        frontmatter, body = Skill._parse_frontmatter(content)

        assert frontmatter == {}
        assert body == content

    def test_from_skill_md(self, tmp_path):
        """Test creating Skill from SKILL.md file."""
        # Create a temporary skill directory
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: my-skill
description: My custom skill for testing
---

# My Skill

Follow these instructions to use my skill.

## Steps
1. Do this
2. Then that
"""
        )

        skill = Skill.from_skill_md(skill_md, location="project")

        assert skill is not None
        assert skill.name == "my-skill"
        assert skill.description == "My custom skill for testing"
        assert skill.location == "project"
        assert "# My Skill" in skill.content
        assert skill.path == skill_dir

    def test_from_skill_md_missing_required_fields(self, tmp_path):
        """Test that skills without required fields return None."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: incomplete-skill
# Missing description!
---

Some content.
"""
        )

        skill = Skill.from_skill_md(skill_md)
        assert skill is None

    def test_to_xml(self):
        """Test XML output format."""
        skill = Skill(
            name="xml-test",
            description="Test XML output",
            content="Content here",
            path=Path("/tmp/test"),
            location="user",
        )

        xml = skill.to_xml()

        assert "<skill>" in xml
        assert "<name>xml-test</name>" in xml
        assert "<description>Test XML output</description>" in xml
        assert "<location>user</location>" in xml

    def test_get_prompt_includes_base_directory(self, tmp_path):
        """Test that get_prompt includes the base directory header."""
        skill_path = tmp_path / "my-skill"
        skill = Skill(
            name="test-skill",
            description="Test skill",
            content="# Instructions\n\nDo this.",
            path=skill_path,
            location="project",
        )

        prompt = skill.get_prompt()

        assert "Loading: test-skill" in prompt
        assert f"Base directory: {skill_path}" in prompt
        assert "# Instructions" in prompt
        assert "Do this." in prompt


class TestSkillRegistry:
    """Tests for the SkillRegistry class."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_skill_registry()

    def test_register_and_get(self):
        """Test registering and retrieving skills."""
        registry = SkillRegistry()

        skill = Skill(
            name="test",
            description="Test skill",
            content="Content",
            path=Path("/tmp"),
            location="project",
        )

        result = registry.register(skill)
        assert result is True
        assert registry.get("test") == skill

    def test_priority_project_over_user(self):
        """Test that project skills override user skills."""
        registry = SkillRegistry()

        user_skill = Skill(
            name="same-name",
            description="User version",
            content="User content",
            path=Path("/home/user"),
            location="user",
        )

        project_skill = Skill(
            name="same-name",
            description="Project version",
            content="Project content",
            path=Path("/project"),
            location="project",
        )

        # Register user skill first
        registry.register(user_skill)
        # Then register project skill - should override
        registry.register(project_skill)

        retrieved = registry.get("same-name")
        assert retrieved.description == "Project version"

    def test_priority_user_does_not_override_project(self):
        """Test that user skills don't override project skills."""
        registry = SkillRegistry()

        project_skill = Skill(
            name="same-name",
            description="Project version",
            content="Project content",
            path=Path("/project"),
            location="project",
        )

        user_skill = Skill(
            name="same-name",
            description="User version",
            content="User content",
            path=Path("/home/user"),
            location="user",
        )

        # Register project skill first
        registry.register(project_skill)
        # Try to register user skill - should be skipped
        result = registry.register(user_skill)

        assert result is False
        retrieved = registry.get("same-name")
        assert retrieved.description == "Project version"

    def test_list_all(self):
        """Test listing all skills."""
        registry = SkillRegistry()

        for i in range(3):
            skill = Skill(
                name=f"skill-{i}",
                description=f"Skill {i}",
                content="Content",
                path=Path("/tmp"),
                location="project",
            )
            registry.register(skill)

        all_skills = registry.list_all()
        assert len(all_skills) == 3

    def test_generate_skills_prompt(self):
        """Test generating skills prompt."""
        registry = SkillRegistry()

        skill = Skill(
            name="prompt-test",
            description="Test prompt generation",
            content="Content",
            path=Path("/tmp"),
            location="project",
        )
        registry.register(skill)

        prompt = registry.generate_skills_prompt()

        assert "<available_skills>" in prompt
        assert "<name>prompt-test</name>" in prompt

    def test_generate_skills_prompt_respects_budget(self):
        """Test that prompt generation respects character budget."""
        registry = SkillRegistry()

        # Add many skills
        for i in range(100):
            skill = Skill(
                name=f"skill-{i:03d}",
                description="A " * 50,  # Long description
                content="Content",
                path=Path("/tmp"),
                location="project",
            )
            registry.register(skill)

        # Small budget should limit output
        prompt = registry.generate_skills_prompt(char_budget=500)
        assert len(prompt) < 1000  # Should be limited


class TestSkillLoader:
    """Tests for the SkillLoader class."""

    def test_get_search_paths(self, tmp_path):
        """Test search path generation."""
        loader = SkillLoader(project_root=tmp_path)
        paths = loader.get_search_paths()

        # Should have project and user paths
        locations = [loc for _, loc in paths]
        assert "project" in locations
        assert "user" in locations

    def test_discover_skills(self, tmp_path):
        """Test skill discovery in directory."""
        # Create skills directory structure
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        # Create two skill directories
        for name in ["skill-a", "skill-b"]:
            skill_dir = skills_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"""---
name: {name}
description: Test skill {name}
---

Instructions for {name}.
"""
            )

        loader = SkillLoader(project_root=tmp_path)
        skill_files = loader.discover_skills(skills_dir)

        assert len(skill_files) == 2
        names = [f.parent.name for f in skill_files]
        assert "skill-a" in names
        assert "skill-b" in names

    def test_discover_nested_skills(self, tmp_path):
        """Test discovery of nested skills (like document-skills/pdf)."""
        skills_dir = tmp_path / ".claude" / "skills"
        nested_dir = skills_dir / "document-skills" / "pdf"
        nested_dir.mkdir(parents=True)

        (nested_dir / "SKILL.md").write_text(
            """---
name: pdf
description: PDF processing skill
---

PDF instructions.
"""
        )

        loader = SkillLoader(project_root=tmp_path)
        skill_files = loader.discover_skills(skills_dir)

        assert len(skill_files) == 1
        assert skill_files[0].parent.name == "pdf"

    def test_load_all(self, tmp_path):
        """Test loading all skills."""
        # Create skills directory
        skills_dir = tmp_path / ".claude" / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)

        (skills_dir / "SKILL.md").write_text(
            """---
name: test-skill
description: A test skill
---

Test instructions.
"""
        )

        reset_skill_registry()
        loader = SkillLoader(project_root=tmp_path)
        registry = loader.load_all()

        assert len(registry) >= 1
        assert registry.exists("test-skill")


class TestIntegration:
    """Integration tests for the skills system."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow from skill file to execution."""
        # Setup
        reset_skill_registry()

        # Create skill
        skills_dir = tmp_path / ".minion" / "skills" / "my-workflow"
        skills_dir.mkdir(parents=True)

        (skills_dir / "SKILL.md").write_text(
            """---
name: my-workflow
description: Custom workflow for data processing
allowed-tools:
  - Bash
  - Read
---

# My Workflow

This skill helps you process data efficiently.

## Steps

1. Read the input file
2. Process the data
3. Write the output

## Example

```bash
cat input.txt | process | tee output.txt
```
"""
        )

        # Load
        loader = SkillLoader(project_root=tmp_path)
        registry = loader.load_all()

        # Verify
        skill = registry.get("my-workflow")
        assert skill is not None
        assert skill.name == "my-workflow"
        assert "Bash" in skill.allowed_tools
        assert "# My Workflow" in skill.get_prompt()

        # Test XML output
        xml = skill.to_xml()
        assert "my-workflow" in xml

        # Test prompt generation
        prompt = registry.generate_skills_prompt()
        assert "my-workflow" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
