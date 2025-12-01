#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Start Script for MinionCodeAgent

This script provides a unified way to start any interface of MinionCodeAgent.
It automatically detects the best available interface and provides fallbacks.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_tui_available():
    """Check if TUI dependencies are available"""
    try:
        import textual
        import rich
        return True
    except ImportError:
        return False

def show_interface_menu():
    """Show interface selection menu"""
    print("🤖 MinionCodeAgent - Choose Interface")
    print("=" * 40)
    print("1. 🖥️  Modern TUI REPL (Recommended)")
    print("2. 🖥️  Console CLI (Traditional)")
    print("3. ❓ Auto-detect best interface")
    print("4. 🚪 Exit")
    print()
    
    while True:
        try:
            choice = input("Select interface (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            sys.exit(0)

def start_tui_repl():
    """Start TUI REPL interface"""
    print("🚀 Starting TUI REPL interface...")
    try:
        from minion_code.screens.REPL import run
        run()
    except ImportError as e:
        print(f"❌ TUI dependencies not available: {e}")
        print("💡 Install with: pip install textual rich")
        return False
    except Exception as e:
        print(f"❌ Error starting TUI REPL: {e}")
        return False
    return True

def start_console_cli():
    """Start console CLI interface"""
    print("🚀 Starting console CLI interface...")
    try:
        from minion_code.cli_simple import InterruptibleCLI
        import asyncio
        cli = InterruptibleCLI()
        asyncio.run(cli.run())
    except Exception as e:
        print(f"❌ Error starting console CLI: {e}")
        return False
    return True

def auto_detect_interface():
    """Auto-detect and start the best available interface"""
    print("🔍 Auto-detecting best interface...")
    
    if check_tui_available():
        print("✅ TUI dependencies available - starting TUI REPL")
        return start_tui_repl()
    else:
        print("⚠️  TUI dependencies not available - starting console CLI")
        return start_console_cli()

def main():
    """Main entry point"""
    print("🤖 MinionCodeAgent Universal Launcher")
    print("=" * 50)
    
    # Check if command line arguments are provided
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['repl', 'tui', 'r']:
            if not start_tui_repl():
                print("🔄 Falling back to console CLI...")
                start_console_cli()
        elif arg in ['console', 'cli', 'c']:
            start_console_cli()
        elif arg in ['auto', 'a']:
            auto_detect_interface()
        elif arg in ['help', 'h', '--help', '-h']:
            print_help()
        else:
            print(f"❌ Unknown argument: {arg}")
            print_help()
            sys.exit(1)
    else:
        # Interactive mode
        choice = show_interface_menu()
        
        if choice == '1':
            if not start_tui_repl():
                print("🔄 Falling back to console CLI...")
                start_console_cli()
        elif choice == '2':
            start_console_cli()
        elif choice == '3':
            auto_detect_interface()
        elif choice == '4':
            print("👋 Goodbye!")
            sys.exit(0)

def print_help():
    """Print help information"""
    print("""
Usage: python examples/start.py [INTERFACE]

Interfaces:
  repl, tui, r     Start TUI REPL interface (recommended)
  console, cli, c  Start console CLI interface
  auto, a          Auto-detect best interface
  help, h          Show this help

Examples:
  python examples/start.py repl
  python examples/start.py console
  python examples/start.py auto
  python examples/start.py

If no interface is specified, an interactive menu will be shown.

Dependencies:
  TUI REPL requires: textual, rich
  Console CLI requires: typer, rich (basic)

Install TUI dependencies:
  pip install textual rich
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)