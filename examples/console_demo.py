#!/usr/bin/env python3
"""
Console UI Demo with Minion Code Tools

This script demonstrates a simple console interface using the minion_code.tools system.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minion_code.tools import (
    FileReadTool, FileWriteTool, BashTool, GrepTool, 
    GlobTool, LsTool, PythonInterpreterTool, TOOL_MAPPING
)

class MinionCodeToolsConsole:
    """Simple console interface for Minion Code Tools."""
    
    def __init__(self):
        """Initialize the console with available tools."""
        self.tools = {
            'read': FileReadTool(),
            'write': FileWriteTool(),
            'bash': BashTool(),
            'grep': GrepTool(),
            'glob': GlobTool(),
            'ls': LsTool(),
            'python': PythonInterpreterTool()
        }
        self.running = True
    
    def show_help(self):
        """Show available commands."""
        print("\n📚 Available Commands:")
        print("  help                    - Show this help message")
        print("  quit/exit              - Exit the application")
        print("  tools                  - List all available tools")
        print("  <tool> <args>          - Execute a tool with arguments")
        print("\n🛠️ Available Tools:")
        for name, tool in self.tools.items():
            print(f"  {name:<10} - {tool.description}")
        print("\n💡 Examples:")
        print("  ls .")
        print("  read README.md")
        print("  write test.txt 'Hello World'")
        print("  bash echo 'Hello from bash'")
        print("  grep 'import' . '*.py'")
        print("  glob '*.py'")
        print("  python 'print(2 + 2)'")
        print()
    
    def list_tools(self):
        """List all available tools with descriptions."""
        print("\n🛠️ Available Tools:")
        for name, tool in self.tools.items():
            print(f"  {name:<15} - {tool.description}")
            print(f"  {'Input:':<15} {tool.inputs}")
            print(f"  {'Output:':<15} {tool.output_type}")
            print()
    
    def execute_tool(self, tool_name: str, args: list) -> str:
        """Execute a tool with given arguments."""
        if tool_name not in self.tools:
            return f"❌ Unknown tool: {tool_name}. Type 'tools' to see available tools."
        
        try:
            tool = self.tools[tool_name]
            
            # Handle different tools with their specific argument patterns
            if tool_name == 'read':
                file_path = args[0] if args else None
                offset = int(args[1]) if len(args) > 1 else None
                limit = int(args[2]) if len(args) > 2 else None
                if not file_path:
                    return "❌ Usage: read <file_path> [offset] [limit]"
                return tool(file_path, offset, limit)
            
            elif tool_name == 'write':
                if len(args) < 2:
                    return "❌ Usage: write <file_path> <content>"
                file_path = args[0]
                content = ' '.join(args[1:])
                return tool(file_path, content)
            
            elif tool_name == 'bash':
                if not args:
                    return "❌ Usage: bash <command>"
                command = ' '.join(args)
                return tool(command)
            
            elif tool_name == 'grep':
                if len(args) < 2:
                    return "❌ Usage: grep <pattern> <path> [include]"
                pattern = args[0]
                path = args[1]
                include = args[2] if len(args) > 2 else None
                return tool(pattern, path, include)
            
            elif tool_name == 'glob':
                if not args:
                    return "❌ Usage: glob <pattern> [path]"
                pattern = args[0]
                path = args[1] if len(args) > 1 else '.'
                return tool(pattern, path)
            
            elif tool_name == 'ls':
                path = args[0] if args else '.'
                recursive = len(args) > 1 and args[1].lower() in ['true', '1', 'yes', 'recursive']
                return tool(path, recursive)
            
            elif tool_name == 'python':
                if not args:
                    return "❌ Usage: python <code>"
                code = ' '.join(args)
                return tool(code)
            
            else:
                # Generic tool execution
                return tool(*args)
        
        except Exception as e:
            return f"❌ Error executing {tool_name}: {str(e)}"
    
    def process_input(self, user_input: str):
        """Process user input and execute commands."""
        if not user_input.strip():
            return
        
        parts = user_input.strip().split()
        command = parts[0].lower()
        args = parts[1:]
        
        if command in ['quit', 'exit']:
            self.running = False
            print("👋 Goodbye!")
        elif command == 'help':
            self.show_help()
        elif command == 'tools':
            self.list_tools()
        elif command in self.tools:
            result = self.execute_tool(command, args)
            print(result)
        else:
            print(f"❌ Unknown command: {command}")
            print("💡 Type 'help' for available commands or 'tools' to see available tools")
    
    def run(self):
        """Run the console interface."""
        print("🚀 Starting Minion Code Tools Console...")
        print("📝 This demo uses the minion_code.tools system")
        print("💡 Type 'help' for available commands")
        print("🛑 Press Ctrl+C or type 'quit' to exit")
        print()
        
        try:
            while self.running:
                try:
                    user_input = input("minion-console> ").strip()
                    if user_input:
                        self.process_input(user_input)
                except EOFError:
                    break
                except KeyboardInterrupt:
                    print("\n👋 Shutting down gracefully...")
                    break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main function to launch the console interface."""
    console = MinionCodeToolsConsole()
    console.run()

if __name__ == "__main__":
    main()