#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Resume command - Resume a previous session
"""

import os
from minion_code.commands import BaseCommand, CommandType
from minion_code.utils.session_storage import (
    list_sessions,
    load_session,
    get_latest_session_id,
    SessionMetadata
)


class ResumeCommand(BaseCommand):
    """Resume a previous conversation session."""

    name = "resume"
    description = "Resume a previous session or list available sessions"
    usage = "/resume [session_id] or /resume list"
    aliases = ["r"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        """Execute the resume command.

        Args:
            args: Optional session_id or 'list' to show available sessions
        """
        args = args.strip()
        current_project = os.getcwd()

        # /resume list - show available sessions
        if args.lower() == "list" or args.lower() == "ls":
            await self._list_sessions(current_project)
            return

        # /resume <session_id> - resume specific session
        if args:
            await self._resume_session(args)
            return

        # /resume (no args) - resume latest session for current project
        latest_id = get_latest_session_id(project_path=current_project)
        if latest_id:
            await self._resume_session(latest_id)
        else:
            self.output.panel(
                "No previous sessions found for this project.\n\n"
                "Use `/resume list` to see all available sessions.",
                title="No Sessions",
                border_style="yellow"
            )

    async def _list_sessions(self, project_path: str) -> None:
        """List available sessions."""
        # Get sessions for current project
        project_sessions = list_sessions(project_path=project_path, limit=10)

        # Get all sessions
        all_sessions = list_sessions(limit=20)

        if not all_sessions:
            self.output.panel(
                "No saved sessions found.\n\n"
                "Sessions are automatically saved during conversations.",
                title="No Sessions",
                border_style="yellow"
            )
            return

        # Build output
        lines = []

        # Current project sessions
        if project_sessions:
            lines.append("**This Project:**")
            lines.append("")
            for session in project_sessions[:5]:
                lines.append(self._format_session_line(session))
            lines.append("")

        # Other sessions
        other_sessions = [s for s in all_sessions if s.project_path != project_path]
        if other_sessions:
            lines.append("**Other Projects:**")
            lines.append("")
            for session in other_sessions[:5]:
                lines.append(self._format_session_line(session, show_path=True))
            lines.append("")

        lines.append("---")
        lines.append("Use `/resume <id>` to restore a session")
        lines.append("Use `/resume` to restore the latest session")

        self.output.panel(
            "\n".join(lines),
            title="Available Sessions",
            border_style="blue"
        )

    def _format_session_line(self, session: SessionMetadata, show_path: bool = False) -> str:
        """Format a session for display."""
        # Parse timestamp for display
        try:
            from datetime import datetime
            updated = datetime.fromisoformat(session.updated_at)
            time_str = updated.strftime("%m/%d %H:%M")
        except:
            time_str = session.updated_at[:16]

        title = session.title or "(no title)"
        if len(title) > 40:
            title = title[:40] + "..."

        line = f"  `{session.session_id}` - {title} ({session.message_count} msgs, {time_str})"

        if show_path:
            # Show shortened path
            path = session.project_path
            home = os.path.expanduser("~")
            if path.startswith(home):
                path = "~" + path[len(home):]
            if len(path) > 30:
                path = "..." + path[-27:]
            line += f"\n    {path}"

        return line

    async def _resume_session(self, session_id: str) -> None:
        """Resume a specific session."""
        session = load_session(session_id)

        if not session:
            self.output.panel(
                f"Session `{session_id}` not found.\n\n"
                "Use `/resume list` to see available sessions.",
                title="Session Not Found",
                border_style="red"
            )
            return

        # Check if agent supports session restoration
        if not self.agent:
            self.output.panel(
                "Agent not initialized. Cannot restore session.",
                title="Error",
                border_style="red"
            )
            return

        # Check if agent has restore_session method
        if not hasattr(self.agent, 'restore_session'):
            self.output.panel(
                "Session restoration not yet implemented in agent.\n\n"
                f"Session `{session_id}` has {len(session.messages)} messages:\n"
                f"Title: {session.metadata.title or '(none)'}\n"
                f"Project: {session.metadata.project_path}",
                title="Coming Soon",
                border_style="yellow"
            )
            return

        # Restore the session
        try:
            await self.agent.restore_session(session)

            self.output.panel(
                f"Restored session `{session_id}` with {len(session.messages)} messages.\n\n"
                f"Title: {session.metadata.title or '(none)'}\n"
                f"You can continue the conversation now.",
                title="Session Restored",
                border_style="green"
            )
        except Exception as e:
            self.output.panel(
                f"Failed to restore session: {e}",
                title="Error",
                border_style="red"
            )
