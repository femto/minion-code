#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Minion CodeAgent Integration

Simple test script to verify that our tools work with CodeAgent.
"""

import asyncio
import sys
from pathlib import Path

# Add project root and minion framework to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, "/Users/femtozheng/python-project/minion1")

from minion.agents import CodeAgent
from minion_code.tools import FileReadTool, LsTool, PythonInterpreterTool


async def test_agent_integration():
    """Test CodeAgent with our tools."""
    print("🧪 Testing Minion CodeAgent Integration...")

    try:
        # Create tools - using only minion_code tools
        tools = [
            FileReadTool(),
            LsTool(),
            PythonInterpreterTool(),
        ]

        print(f"📦 Creating agent with {len(tools)} tools...")

        # Create agent
        agent = await CodeAgent.create(
            llm="gpt-4o-mini", tools=tools, name="Test Agent"
        )

        print(f"✅ Agent created with {len(agent.tools)} tools")

        # Test basic functionality
        print("\n🔍 Testing basic query...")
        response = await agent.run_async("List the files in the current directory")
        print(f"Response: {response.answer}")

        # Test Python code execution
        print("\n🧮 Testing Python code execution...")
        response = await agent.run_async("Execute Python code to calculate 15 + 27")
        print(f"Response: {response.answer}")

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agent_integration())
