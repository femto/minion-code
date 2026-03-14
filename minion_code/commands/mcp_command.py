#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP command - inspect and reconnect MCP servers.
"""

from __future__ import annotations

from minion_code.commands import BaseCommand, CommandType


class MCPCommand(BaseCommand):
    """Inspect MCP server status and retry failed connections."""

    name = "mcp"
    description = "Show MCP server status and reload/retry MCP connections"
    usage = "/mcp [status|reload|retry <server>|verify <server>]"
    aliases = ["mcp-status"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        """Handle `/mcp` status and reconnect flows."""
        host = self.host
        if host is None or not hasattr(host, "get_mcp_status"):
            self.output.error("MCP management is not available in this interface.")
            return

        raw_args = args.strip()
        if not raw_args:
            self._render_status()
            return

        parts = raw_args.split(None, 1)
        action = parts[0].lower()
        target = parts[1].strip() if len(parts) > 1 else ""

        if action in {"status", "list"}:
            self._render_status()
            return

        if action == "reload":
            self.output.info(
                "Reloading all MCP servers..."
                if not target
                else f"Reloading MCP server `{target}`..."
            )
            try:
                await host.reload_mcp(target or None)
            except KeyError as exc:
                self.output.error(str(exc))
                return
            self._render_status()
            return

        if action in {"retry", "verify", "reconnect"}:
            if not target:
                self.output.error("Usage: /mcp retry <server>")
                return
            self.output.info(f"Retrying MCP server `{target}`...")
            try:
                await host.reload_mcp(target)
            except KeyError as exc:
                self.output.error(str(exc))
                return
            self._render_status()
            return

        self.output.error(
            "Unknown /mcp action. Use `/mcp`, `/mcp reload`, or `/mcp retry <server>`."
        )

    def _render_status(self) -> None:
        """Render MCP config path and per-server runtime status."""
        host = self.host
        status_map = host.get_mcp_status()
        config_path = host.get_mcp_config_path()

        if not status_map:
            location = str(config_path) if config_path else "No MCP config discovered"
            self.output.panel(
                location,
                title="MCP Status",
                border_style="yellow",
            )
            return

        rows = []
        for name, info in sorted(status_map.items()):
            target = info.get("url") or self._format_command_target(info)
            detail = target
            if info.get("error"):
                detail = f"{detail}\n{info['error']}" if detail else str(info["error"])
            duration = info.get("last_duration_ms")
            duration_label = f"{duration} ms" if duration is not None else "-"
            rows.append(
                [
                    name,
                    info.get("status", "unknown"),
                    str(info.get("tool_count", 0)),
                    info.get("transport", "-"),
                    duration_label,
                    detail or "-",
                ]
            )

        title = "MCP Status"
        if config_path:
            title = f"MCP Status ({config_path})"
        self.output.table(
            ["Server", "Status", "Tools", "Transport", "Last Load", "Details"],
            rows,
            title=title,
        )

    @staticmethod
    def _format_command_target(info) -> str:
        command = info.get("command") or ""
        args = info.get("args") or []
        parts = [command, *args]
        return " ".join(part for part in parts if part)
