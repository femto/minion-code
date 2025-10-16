#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
History command - Show conversation history
"""

from rich.panel import Panel
from rich.table import Table
from minion_code.commands import BaseCommand


class HistoryCommand(BaseCommand):
    """Show conversation history."""
    
    name = "history"
    description = "Show conversation history with the agent"
    usage = "/history [count]"
    aliases = ["hist", "h"]
    
    async def execute(self, args: str) -> None:
        """Execute the history command."""
        if not self.agent:
            error_panel = Panel(
                "❌ [bold red]Agent not initialized[/bold red]",
                title="[bold red]Error[/bold red]",
                border_style="red"
            )
            self.console.print(error_panel)
            return
        
        # Parse count argument
        count = 5  # default
        if args.strip():
            try:
                count = int(args.strip())
                if count <= 0:
                    count = 5
            except ValueError:
                error_panel = Panel(
                    f"❌ [bold red]Invalid count: '{args.strip()}'. Using default (5)[/bold red]",
                    title="[bold red]Warning[/bold red]",
                    border_style="yellow"
                )
                self.console.print(error_panel)
        
        history = self.agent.get_conversation_history()
        if not history:
            no_history_panel = Panel(
                "📝 [italic]No conversation history yet.[/italic]",
                title="[bold blue]History[/bold blue]",
                border_style="blue"
            )
            self.console.print(no_history_panel)
            return
        
        # Show header
        header_panel = Panel(
            f"📝 [bold blue]Conversation History (showing last {min(count, len(history))} of {len(history)} messages)[/bold blue]",
            border_style="blue"
        )
        self.console.print(header_panel)
        
        # Show recent messages
        recent_history = history[-count:] if count < len(history) else history
        
        for i, entry in enumerate(recent_history, 1):
            message_num = len(history) - len(recent_history) + i
            
            # User message
            user_msg = entry['user_message']
            if len(user_msg) > 150:
                user_msg = user_msg[:150] + "..."
            
            user_panel = Panel(
                user_msg,
                title=f"👤 [bold cyan]You (#{message_num})[/bold cyan]",
                border_style="cyan"
            )
            self.console.print(user_panel)
            
            # Agent response
            agent_msg = entry['agent_response']
            if len(agent_msg) > 200:
                agent_msg = agent_msg[:200] + "..."
            
            agent_panel = Panel(
                agent_msg,
                title="🤖 [bold green]Agent[/bold green]",
                border_style="green"
            )
            self.console.print(agent_panel)
            
            if i < len(recent_history):  # Don't add spacing after last message
                self.console.print()
        
        # Show summary if there are more messages
        if len(history) > count:
            summary_panel = Panel(
                f"💡 [italic]Showing {count} most recent messages. "
                f"Use '/history {len(history)}' to see all {len(history)} messages.[/italic]",
                title="[bold yellow]Note[/bold yellow]",
                border_style="yellow"
            )
            self.console.print(summary_panel)