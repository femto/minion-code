#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: MinionCodeAgent with Skill Tool

This script demonstrates using MinionCodeAgent with the built-in SkillTool.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from minion_code.agents.code_agent import MinionCodeAgent


async def main():
    """Demonstrate MinionCodeAgent with skill tool."""
    print("=" * 60)
    print("MinionCodeAgent with Skill Tool Example")
    print("=" * 60 + "\n")

    # Create agent - SkillTool is included by default
    print("Creating MinionCodeAgent...")
    agent = await MinionCodeAgent.create(
        name="Skill Demo Agent",
        llm="sonnet"
    )
    print("✓ Agent created with SkillTool\n")

    # Show available tools (including SkillTool)
    print("Available tools:")
    tools_info = agent.get_tools_info()
    for tool in tools_info:
        if 'skill' in tool['name'].lower():
            print(f"  ★ {tool['name']}: {tool['description']}")
        else:
            print(f"  - {tool['name']}")
    print()

    # Ask agent to list available skills
    print("Asking agent to list available skills...")
    print("-" * 40)

    response = await agent.run_async(
        "Please read Titans.pdf and give a summary"
    )

    print(f"\nAgent response:\n{response.answer if hasattr(response, 'answer') else response}")
    print()

    print("=" * 60)
    print("Example completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
