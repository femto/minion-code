#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Version command - Show version information
"""

from rich.panel import Panel
from rich.table import Table
from minion_code.commands import BaseCommand


class VersionCommand(BaseCommand):
    """Show version information."""
    
    name = "version"
    description = "Show version information for MinionCode and dependencies"
    usage = "/version"
    aliases = ["v", "ver"]
    
    async def execute(self, args: str) -> None:
        """Execute the version command."""
        # Create version table
        version_table = Table(
            title="📦 Version Information", 
            show_header=True, 
            header_style="bold blue"
        )
        version_table.add_column("Component", style="cyan", no_wrap=True)
        version_table.add_column("Version", style="white")
        version_table.add_column("Status", style="green")
        
        # MinionCode version
        version_table.add_row(
            "MinionCode",
            "0.1.0",
            "✅ Active"
        )
        
        # Python version
        import sys
        version_table.add_row(
            "Python",
            f"{sys.version.split()[0]}",
            "✅ Compatible"
        )
        
        # Rich version
        try:
            import rich
            version = getattr(rich, '__version__', 'Unknown')
            version_table.add_row(
                "Rich",
                version,
                "✅ Loaded"
            )
        except ImportError:
            version_table.add_row(
                "Rich",
                "Not installed",
                "❌ Missing"
            )
        
        # Textual version
        try:
            import textual
            version = getattr(textual, '__version__', 'Unknown')
            version_table.add_row(
                "Textual",
                version,
                "✅ Available"
            )
        except ImportError:
            version_table.add_row(
                "Textual",
                "Not installed",
                "⚠️ Optional"
            )
        
        # Minion version
        try:
            import minion
            version_table.add_row(
                "Minion",
                getattr(minion, '__version__', 'Unknown'),
                "✅ Core"
            )
        except ImportError:
            version_table.add_row(
                "Minion",
                "Not found",
                "❌ Required"
            )
        
        self.console.print(version_table)
        
        # Additional info
        info_panel = Panel(
            "🚀 [bold blue]MinionCode TUI[/bold blue] - Advanced AI-powered development assistant\n"
            "🔗 Built with Rich for beautiful terminal interfaces\n"
            "🤖 Powered by Minion framework for AI agent capabilities",
            title="[bold green]About[/bold green]",
            border_style="green"
        )
        self.console.print(info_panel)