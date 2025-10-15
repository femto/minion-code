#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minion CodeAgent TUI Demo

This example demonstrates:
1. How to integrate minion_code tools with a minion CodeAgent
2. How to create an interactive TUI using the CodeAgent
3. How to use raw Python functions alongside existing tools
4. Automatic conversion of raw functions to BaseTool during agent setup

Key features shown:
- minion_code tools integration
- Raw sync/async function auto-conversion
- Interactive TUI with CodeAgent
- Seamless integration of all tool types
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Union, Optional
import traceback

# Add project root and minion framework to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, "/Users/femtozheng/python-project/minion1")

from minion.agents import CodeAgent
from minion.providers.openai_provider import OpenAIProvider

# Import our custom tools
from minion_code.tools import (
    FileReadTool,
    FileWriteTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool,
    WebSearchTool,
    WikipediaSearchTool,
    VisitWebpageTool,
    UserInputTool,
    FinalAnswerTool,
    TOOL_MAPPING,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Using only minion_code tools - no additional raw functions needed


class MinionCodeAgentTUI:
    """Interactive TUI using Minion CodeAgent with minion_code tools."""

    def __init__(self):
        """Initialize the TUI application."""
        self.agent: Optional[CodeAgent] = None
        self.running = True
        self.conversation_history = []

    async def setup_agent(self):
        """Set up the CodeAgent with all available tools."""
        try:
            print("🔧 Setting up Minion CodeAgent...")

            # Get all our custom tools (already BaseTool instances)
            custom_tools = [
                FileReadTool(),
                FileWriteTool(),
                BashTool(),
                GrepTool(),
                GlobTool(),
                LsTool(),
                PythonInterpreterTool(),
                WebSearchTool(),
                WikipediaSearchTool(),
                VisitWebpageTool(),
                UserInputTool(),
                FinalAnswerTool(),
            ]

            # Use only our custom tools
            all_tools = custom_tools

            print(f"📦 Total tools before setup: {len(all_tools)}")
            print(f"   - minion_code tools: {len(custom_tools)}")

            # Create agent with all tools
            self.agent = await CodeAgent.create(
                name="Minion Code Assistant",
                llm="gpt-4o-mini",  # Using mini for faster responses
                tools=all_tools,
            )

            print(f"✅ Agent setup complete! Final tool count: {len(self.agent.tools)}")
            print("\n📋 Available tools:")
            for tool in self.agent.tools:
                readonly_status = (
                    "🔒 readonly" if getattr(tool, "readonly", None) else "✏️ read/write"
                )
                print(f"  - {tool.name}: {readonly_status}")
                print(f"    {tool.description}")
            print()

        except Exception as e:
            print(f"❌ Error setting up agent: {e}")
            logger.exception("Agent setup error:")
            raise

    def show_help(self):
        """Show available commands and usage information."""
        print(
            """
📚 Minion CodeAgent TUI Help

🤖 Chat Commands:
  Just type your message and press Enter to chat with the AI agent.
  The agent has access to various tools and can help you with:
  
  📁 File Operations:
    - "Read the contents of README.md"
    - "Write 'Hello World' to test.txt"
    - "List files in the current directory"
    - "Search for 'import' in all Python files"
  
  💻 System Operations:
    - "Execute 'ls -la' command"
    - "Run Python code: print(2 + 2)"
  
  🌐 Web Operations:
    - "Search the web for Python tutorials"
    - "Look up 'machine learning' on Wikipedia"
    - "Visit https://example.com and summarize"

🎛️ Control Commands:
  help     - Show this help message
  history  - Show conversation history
  clear    - Clear conversation history
  tools    - List all available tools
  quit     - Exit the application

💡 Tips:
  - Be specific about what you want to accomplish
  - The agent will choose the best tools for your task
  - You can ask follow-up questions about previous results
  - Use natural language - no need for specific command syntax
"""
        )

    def show_tools(self):
        """Show all available tools with details."""
        if not self.agent:
            print("❌ Agent not initialized")
            return

        print(f"\n🛠️ Available Tools ({len(self.agent.tools)} total):")

        # Group tools by category
        file_tools = []
        system_tools = []
        web_tools = []
        other_tools = []

        for tool in self.agent.tools:
            readonly_status = "🔒" if getattr(tool, "readonly", None) else "✏️"
            tool_info = f"{readonly_status} {tool.name}: {tool.description}"

            if any(
                keyword in tool.name
                for keyword in ["file", "read", "write", "grep", "glob", "ls"]
            ):
                file_tools.append(tool_info)
            elif any(
                keyword in tool.name for keyword in ["bash", "python", "calc", "system"]
            ):
                system_tools.append(tool_info)
            elif any(
                keyword in tool.name
                for keyword in ["web", "search", "wikipedia", "visit"]
            ):
                web_tools.append(tool_info)
            else:
                other_tools.append(tool_info)

        if file_tools:
            print("\n📁 File & Directory Tools:")
            for tool in file_tools:
                print(f"  {tool}")

        if system_tools:
            print("\n💻 System & Execution Tools:")
            for tool in system_tools:
                print(f"  {tool}")

        if web_tools:
            print("\n🌐 Web & Search Tools:")
            for tool in web_tools:
                print(f"  {tool}")

        if other_tools:
            print("\n🔧 Other Tools:")
            for tool in other_tools:
                print(f"  {tool}")

        print(f"\n🔒 = readonly tool, ✏️ = read/write tool")

    def show_history(self):
        """Show conversation history."""
        if not self.conversation_history:
            print("📝 No conversation history yet.")
            return

        print(f"\n📝 Conversation History ({len(self.conversation_history)} messages):")
        for i, (user_msg, agent_response) in enumerate(self.conversation_history, 1):
            print(f"\n--- Message {i} ---")
            print(f"👤 You: {user_msg}")
            print(f"🤖 Agent: {agent_response}")

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        print("🗑️ Conversation history cleared.")

    async def process_user_input(self, user_input: str):
        """Process user input and get agent response."""
        if not user_input.strip():
            return

        command = user_input.strip().lower()

        # Handle control commands
        if command in ["quit", "exit"]:
            self.running = False
            print("👋 Goodbye!")
            return
        elif command == "help":
            self.show_help()
            return
        elif command == "tools":
            self.show_tools()
            return
        elif command == "history":
            self.show_history()
            return
        elif command == "clear":
            self.clear_history()
            return

        # Process with agent
        if not self.agent:
            print("❌ Agent not initialized. Please restart the application.")
            return

        try:
            print(f"🤖 Processing: {user_input}")
            print("⏳ Thinking...")

            # Get response from agent
            response = await self.agent.run_async(user_input)

            print(f"\n🤖 Agent: {response.answer}")

            # Add to history
            self.conversation_history.append((user_input, response.answer))

        except Exception as e:
            error_msg = f"❌ Error processing request: {str(e)}"
            print(error_msg)
            logger.exception("Error processing user input:")

    async def run(self):
        """Run the interactive TUI."""
        print("🚀 Starting Minion CodeAgent TUI...")
        print("📝 This demo integrates minion_code tools with a Minion CodeAgent")

        try:
            # Setup agent
            await self.setup_agent()

            print("💡 Type 'help' for available commands")
            print("🛑 Press Ctrl+C or type 'quit' to exit")
            print("🤖 Start chatting with the AI agent!\n")

            # Main interaction loop
            while self.running:
                try:
                    user_input = input("👤 You: ").strip()
                    if user_input:
                        await self.process_user_input(user_input)
                        print()  # Add spacing between interactions
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n👋 Shutting down gracefully...")
                    break

        except Exception as e:
            print(f"❌ Application error: {e}")
            logger.exception("Application error:")


async def main():
    """Main function to launch the TUI."""
    try:
        tui = MinionCodeAgentTUI()
        await tui.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Startup error: {e}")
        traceback.print_exc()


def run():
    """Synchronous entry point for the TUI."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
