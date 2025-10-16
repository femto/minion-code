#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Status command - Show system status and information
"""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import sys
import platform
from datetime import datetime
from minion_code.commands import BaseCommand


class StatusCommand(BaseCommand):
    """Show system status and information."""
    
    name = "status"
    description = "Show system status, agent info, and statistics"
    usage = "/status"
    aliases = ["info", "stat"]
    
    async def execute(self, args: str) -> None:
        """Execute the status command."""
        # Create status table
        status_table = Table(
            title="📊 System Status", 
            show_header=True, 
            header_style="bold blue"
        )
        status_table.add_column("Component", style="cyan", no_wrap=True)
        status_table.add_column("Status", style="white")
        status_table.add_column("Details", style="yellow")
        
        # System info
        status_table.add_row(
            "System",
            "✅ Running",
            f"{platform.system()} {platform.release()}"
        )
        
        status_table.add_row(
            "Python",
            "✅ Active",
            f"{sys.version.split()[0]}"
        )
        
        # Agent info
        if self.agent:
            history = self.agent.get_conversation_history()
            tools_count = len(self.agent.tools) if self.agent.tools else 0
            
            status_table.add_row(
                "Agent",
                "✅ Ready",
                f"{tools_count} tools loaded"
            )
            
            status_table.add_row(
                "Conversation",
                "📝 Active" if history else "📝 Empty",
                f"{len(history)} messages" if history else "No messages"
            )
        else:
            status_table.add_row(
                "Agent",
                "❌ Not Ready",
                "Not initialized"
            )
        
        # Memory info (basic)
        try:
            import psutil
            memory = psutil.virtual_memory()
            status_table.add_row(
                "Memory",
                "📊 Monitored",
                f"{memory.percent}% used ({memory.available // (1024**3)} GB free)"
            )
        except ImportError:
            status_table.add_row(
                "Memory",
                "❌ Not Available",
                "psutil not installed"
            )
        
        self.console.print(status_table)
        
        # Additional info panel
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        info_text = Text()
        info_text.append("🕒 Current Time: ", style="bold")
        info_text.append(f"{current_time}\n", style="white")
        
        if self.agent:
            info_text.append("🤖 Agent Model: ", style="bold")
            info_text.append(f"{getattr(self.agent, 'llm', 'Unknown')}\n", style="white")
            
            info_text.append("🛠️ Available Tools: ", style="bold")
            if self.agent.tools:
                tool_names = [tool.name for tool in self.agent.tools[:5]]
                if len(self.agent.tools) > 5:
                    tool_names.append(f"... and {len(self.agent.tools) - 5} more")
                info_text.append(", ".join(tool_names), style="white")
            else:
                info_text.append("None", style="red")
        
        info_panel = Panel(
            info_text,
            title="[bold green]Additional Information[/bold green]",
            border_style="green"
        )
        self.console.print(info_panel)