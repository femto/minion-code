#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills system for MinionCode

Skills are folders of instructions, scripts, and resources that are loaded
dynamically to improve performance on specialized tasks. Each skill has a
SKILL.md file with YAML frontmatter containing name and description.

Skill search paths (in order):
- .claude/skills (project-level)
- ~/.claude/skills (user-level)
- .minion/skills (project-level)
- ~/.minion/skills (user-level)
"""

from .skill import Skill
from .skill_registry import SkillRegistry
from .skill_loader import SkillLoader

__all__ = [
    "Skill",
    "SkillRegistry",
    "SkillLoader",
]
