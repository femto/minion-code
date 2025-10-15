#!/usr/bin/env python3
"""
Textual UI Demo with Minion Code Tools

This script demonstrates how to create a terminal interface using textual
with the minion_code.tools system for code analysis and manipulation.
"""

import asyncio
import sys
import os
import threading
import queue
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minion_code.tools import (
    FileReadTool,
    FileWriteTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool,
    TOOL_MAPPING,
)


class MinionCodeToolsApp:
    """Simple terminal application using Minion Code Tools."""

    def __init__(self):
        """Initialize the application with available tools."""
        self.tools = {
            "read": FileReadTool(),
            "write": FileWriteTool(),
            "bash": BashTool(),
            "grep": GrepTool(),
            "glob": GlobTool(),
            "ls": LsTool(),
            "python": PythonInterpreterTool(),
        }
        self.running = True

    def show_help(self):
        """Show available commands."""
        print("\n📚 Available Commands:")
        print("  help                    - Show this help message")
        print("  quit/exit              - Exit the application")
        print("  ls [path]              - List directory contents")
        print("  read <file> [offset] [limit] - Read file content")
        print("  write <file> <content> - Write content to file")
        print("  bash <command>         - Execute bash command")
        print("  grep <pattern> <path> [include] - Search for text pattern")
        print("  glob <pattern> [path]  - Find files matching pattern")
        print("  python <code>          - Execute Python code")
        print("\n💡 Examples:")
        print("  ls .")
        print("  read README.md")
        print("  write test.txt 'Hello World'")
        print("  bash echo 'Hello from bash'")
        print("  grep 'import' . '*.py'")
        print("  glob '*.py'")
        print("  python 'print(2 + 2)'")
        print()

    def process_command(self, command_line: str):
        """Process a command line input."""
        if not command_line.strip():
            return

        parts = command_line.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd in ["quit", "exit"]:
                self.running = False
                print("👋 Goodbye!")
                return
            elif cmd == "help":
                self.show_help()
                return
            elif cmd == "ls":
                path = args[0] if args else "."
                result = self.tools["ls"](path)
                print(result)
            elif cmd == "read":
                if not args:
                    print("❌ Usage: read <file> [offset] [limit]")
                    return
                file_path = args[0]
                offset = int(args[1]) if len(args) > 1 else None
                limit = int(args[2]) if len(args) > 2 else None
                result = self.tools["read"](file_path, offset, limit)
                print(result)
            elif cmd == "write":
                if len(args) < 2:
                    print("❌ Usage: write <file> <content>")
                    return
                file_path = args[0]
                content = " ".join(args[1:])
                result = self.tools["write"](file_path, content)
                print(result)
            elif cmd == "bash":
                if not args:
                    print("❌ Usage: bash <command>")
                    return
                command = " ".join(args)
                result = self.tools["bash"](command)
                print(result)
            elif cmd == "grep":
                if len(args) < 2:
                    print("❌ Usage: grep <pattern> <path> [include]")
                    return
                pattern = args[0]
                path = args[1]
                include = args[2] if len(args) > 2 else None
                result = self.tools["grep"](pattern, path, include)
                print(result)
            elif cmd == "glob":
                if not args:
                    print("❌ Usage: glob <pattern> [path]")
                    return
                pattern = args[0]
                path = args[1] if len(args) > 1 else "."
                result = self.tools["glob"](pattern, path)
                print(result)
            elif cmd == "python":
                if not args:
                    print("❌ Usage: python <code>")
                    return
                code = " ".join(args)
                result = self.tools["python"](code)
                print(result)
            else:
                print(f"❌ Unknown command: {cmd}")
                print("💡 Type 'help' for available commands")

        except Exception as e:
            print(f"❌ Error executing command: {e}")

    def run(self):
        """Run the interactive terminal application."""
        print("🚀 Starting Minion Code Tools Terminal...")
        print("📝 This demo uses the minion_code.tools system")
        print("💡 Type 'help' for available commands")
        print("🛑 Press Ctrl+C or type 'quit' to exit")
        print()

        try:
            while self.running:
                try:
                    command = input("minion-tools> ").strip()
                    if command:
                        self.process_command(command)
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
    """Main function to launch the terminal application."""
    app = MinionCodeToolsApp()
    app.run()


def run():
    """Run the main function."""
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Startup error: {e}")


if __name__ == "__main__":
    run()
