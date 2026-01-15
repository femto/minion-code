#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Entry Point

This is the main entry point that provides access to all CLI interfaces:
- Modern TUI REPL (default)
- Traditional console CLI
- Direct command execution
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run():
    """Main CLI entry point"""
    try:
        from minion_code.cli import app

        app()
    except Exception as e:
        print(f"❌ Error starting CLI: {e}")
        sys.exit(1)


def run_repl():
    """Direct REPL entry point"""
    try:
        from minion_code.screens.REPL import run as run_repl_func

        run_repl_func()
    except ImportError as e:
        print(f"❌ TUI dependencies not available: {e}")
        print("💡 Install with: pip install textual rich")
        # Fallback to console
        from minion_code.cli_simple import app

        app()
    except Exception as e:
        print(f"❌ Error starting REPL: {e}")
        sys.exit(1)


def run_console():
    """Direct console CLI entry point"""
    try:
        from minion_code.cli_simple import app

        app()
    except Exception as e:
        print(f"❌ Error starting console CLI: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
