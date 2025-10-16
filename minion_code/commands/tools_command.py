#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tools command - Show available tools
"""

from rich.table import Table
from rich.panel import Panel
from minion_code.commands import BaseCommand


class ToolsCommand(BaseCommand):
    """Show available tools."""
    
    name = "tools"
    description = "List all available tools and their descriptions"
    usage = "/tools [filter]"
    aliases = ["t"]
    
    async def execute(self, args: str) -> None:
        """Execute the tools command."""
        if not self.agent or not self.agent.tools:
            error_panel = Panel(
                "❌ [bold red]No tools available or agent not initialized[/bold red]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)
            return
        
        filter_text = args.strip().lower()
        tools = self.agent.tools
        
        # Filter tools if filter text provided
        if filter_text:
            tools = [tool for tool in tools 
                    if filter_text in tool.name.lower() or 
                       filter_text in tool.description.lower()]
        
        if not tools:
            no_tools_panel = Panel(
                f"❌ [bold yellow]No tools found matching '{filter_text}'[/bold yellow]",
                title="[bold yellow]No Results[/bold yellow]",
                border_style="yellow"
            )
            self.console.print(no_tools_panel)
            return
        
        # Create tools table
        tools_table = Table(
            title=f"🛠️ Available Tools{f' (filtered: {filter_text})' if filter_text else ''}", 
            show_header=True, 
            header_style="bold magenta"
        )
        tools_table.add_column("Tool Name", style="cyan", no_wrap=True)
        tools_table.add_column("Description", style="white")
        tools_table.add_column("Type", style="yellow")
        tools_table.add_column("Inputs", style="green")
        
        for tool in tools:
            tool_type = "Read-only" if getattr(tool, 'readonly', False) else "Read-write"
            
            # Get input parameters
            inputs = getattr(tool, 'inputs', {})
            input_names = list(inputs.keys()) if inputs else []
            input_str = ", ".join(input_names[:3])  # Show first 3 inputs
            if len(input_names) > 3:
                input_str += f" (+{len(input_names) - 3} more)"
            
            tools_table.add_row(
                tool.name,
                tool.description[:50] + "..." if len(tool.description) > 50 else tool.description,
                tool_type,
                input_str or "-"
            )
        
        self.console.print(tools_table)
        
        # Show summary
        summary_panel = Panel(
            f"📊 [bold blue]Total: {len(tools)} tools[/bold blue]"
            f"{f' (filtered from {len(self.agent.tools)} total)' if filter_text else ''}",
            title="[bold green]Summary[/bold green]",
            border_style="green"
        )
        self.console.print(summary_panel)