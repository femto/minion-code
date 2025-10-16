#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple TUI using MinionCodeAgent

This example shows how the new MinionCodeAgent class simplifies
the TUI implementation by handling all the tool setup internally.

Compare this with minion_agent_tui.py to see the reduction in boilerplate code.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minion_code import MinionCodeAgent


class SimpleTUI:
    """Simplified TUI using MinionCodeAgent."""
    
    def __init__(self):
        self.agent = None
        self.running = True
    
    async def setup(self):
        """Setup the agent."""
        print("🔧 Setting up MinionCodeAgent...")
        
        # Much simpler setup - no manual tool configuration needed
        self.agent = await MinionCodeAgent.create(
            name="Simple Code Assistant",
            llm="gpt-4o-mini"
        )
        
        print(f"✅ Agent ready with {len(self.agent.tools)} tools!")
    
    def show_help(self):
        """Show help information."""
        print("""
📚 Simple TUI Help

Commands:
  help     - Show this help
  tools    - List available tools  
  history  - Show conversation history
  clear    - Clear history
  quit     - Exit

Just type your message to chat with the AI agent!
        """)
    
    async def process_input(self, user_input: str):
        """Process user input."""
        command = user_input.strip().lower()
        
        if command in ["quit", "exit"]:
            self.running = False
            print("👋 Goodbye!")
            return
        elif command == "help":
            self.show_help()
            return
        elif command == "tools":
            self.agent.print_tools_summary()
            return
        elif command == "history":
            history = self.agent.get_conversation_history()
            if not history:
                print("📝 No conversation history yet.")
            else:
                print(f"\n📝 Conversation History ({len(history)} messages):")
                for i, entry in enumerate(history, 1):
                    print(f"\n--- Message {i} ---")
                    print(f"👤 You: {entry['user_message']}")
                    print(f"🤖 Agent: {entry['agent_response']}")
            return
        elif command == "clear":
            self.agent.clear_conversation_history()
            print("🗑️ History cleared.")
            return
        
        # Process with agent
        try:
            print("🤖 Processing...")
            response = await self.agent.run_async(user_input)
            print(f"\n🤖 Agent: {response.answer}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def run(self):
        """Run the TUI."""
        print("🚀 Simple MinionCodeAgent TUI")
        
        await self.setup()
        
        print("\n💡 Type 'help' for commands or just chat with the agent!")
        print("🛑 Type 'quit' to exit\n")
        
        while self.running:
            try:
                user_input = input("👤 You: ").strip()
                if user_input:
                    await self.process_input(user_input)
                    print()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                break


async def main():
    """Main function."""
    tui = SimpleTUI()
    await tui.run()


def run():
    """Synchronous entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    run()