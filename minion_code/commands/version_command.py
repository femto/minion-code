#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version command - Show version information
"""

import sys
from minion_code.commands import BaseCommand


class VersionCommand(BaseCommand):
    """Show version information."""

    name = "version"
    description = "Show version information for MinionCode and dependencies"
    usage = "/version"
    aliases = ["v", "ver"]

    async def execute(self, args: str) -> None:
        """Execute the version command."""
        # Prepare version data
        headers = ["Component", "Version", "Status"]
        rows = []

        # MinionCode version
        rows.append(["MinionCode", "0.1.0", "✅ Active"])

        # Python version
        rows.append(["Python", sys.version.split()[0], "✅ Compatible"])

        # Rich version
        try:
            import rich
            version = getattr(rich, '__version__', 'Unknown')
            rows.append(["Rich", version, "✅ Loaded"])
        except ImportError:
            rows.append(["Rich", "Not installed", "❌ Missing"])

        # Textual version
        try:
            import textual
            version = getattr(textual, '__version__', 'Unknown')
            rows.append(["Textual", version, "✅ Available"])
        except ImportError:
            rows.append(["Textual", "Not installed", "⚠️ Optional"])

        # Minion version
        try:
            import minion
            rows.append(["Minion", getattr(minion, '__version__', 'Unknown'), "✅ Core"])
        except ImportError:
            rows.append(["Minion", "Not found", "❌ Required"])

        self.output.table(headers, rows, title="📦 Version Information")

        # Additional info
        self.output.panel(
            "🚀 MinionCode TUI - Advanced AI-powered development assistant\n"
            "🔗 Built with Rich for beautiful terminal interfaces\n"
            "🤖 Powered by Minion framework for AI agent capabilities",
            title="About",
            border_style="green"
        )