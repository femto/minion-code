#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) Tools Loader

This module provides functionality to load MCP tools from configuration files
and integrate them with MinionCodeAgent.
"""

import json
import logging
import os
import asyncio
import time
from urllib.parse import urlparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from minion.tools import AsyncBaseTool

try:
    from minion.tools.mcp.mcp_toolset import (
        MCPToolset,
        SSEServerParameters,
        StdioServerParameters,
        StreamableHTTPServerParameters,
    )

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPToolset = None
    SSEServerParameters = None
    StdioServerParameters = None
    StreamableHTTPServerParameters = None

from minion_code.utils.output_truncator import (
    MAX_TOKEN_LIMIT,
    MCPContentTooLargeError,
    check_mcp_output,
    save_large_output,
)

logger = logging.getLogger(__name__)

DEFAULT_MCP_STARTUP_TIMEOUT = float(
    os.environ.get("MINION_MCP_STARTUP_TIMEOUT", "10")
)


def find_mcp_config(project_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Auto-discover MCP configuration file.

    Searches in the following order (first found wins):

    Project scope (current working directory or specified project_dir):
    1. .mcp.json
    2. .claude/mcp.json
    3. .minion/mcp.json

    User scope (home directory):
    4. ~/.minion.json
    5. ~/.claude/mcp.json
    6. ~/.claude-code/mcp.json
    7. ~/.minion-code/mcp.json
    8. ~/.config/minion-code/mcp.json (XDG standard)

    Args:
        project_dir: Project directory to search in (defaults to cwd)

    Returns:
        Path to config file if found, None otherwise
    """
    locations = get_mcp_config_locations(project_dir=project_dir)

    # Search project scope first
    for config_path in locations["project"]:
        if config_path.exists():
            logger.info(f"Found MCP config at project scope: {config_path}")
            return config_path

    # Then search user scope
    for config_path in locations["user"]:
        if config_path.exists():
            logger.info(f"Found MCP config at user scope: {config_path}")
            return config_path

    logger.debug("No MCP config file found in any standard location")
    return None


def get_mcp_config_locations(project_dir: Optional[Path] = None) -> Dict[str, List[Path]]:
    """
    Get all standard MCP config file locations.

    Returns:
        Dictionary with 'project' and 'user' scope locations
    """
    project_root = project_dir or Path.cwd()
    home = Path.home()
    xdg_config_home = Path(
        os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    )

    return {
        "project": [
            project_root / ".mcp.json",
            project_root / ".claude" / "mcp.json",
            project_root / ".minion" / "mcp.json",
        ],
        "user": [
            home / ".minion.json",
            home / ".claude" / "mcp.json",
            home / ".claude-code" / "mcp.json",
            home / ".minion-code" / "mcp.json",
            xdg_config_home / "minion-code" / "mcp.json",
        ],
    }


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    transport: str = "stdio"
    command: str = ""
    args: List[str] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    timeout: Optional[float] = None
    sse_read_timeout: Optional[float] = None
    disabled: bool = False
    auto_approve: List[str] = None

    def __post_init__(self):
        if self.args is None:
            self.args = []
        if self.auto_approve is None:
            self.auto_approve = []


@dataclass
class MCPServerRuntimeStatus:
    """Track runtime connection state for one configured MCP server."""

    name: str
    state: str = "pending"
    error: Optional[str] = None
    tool_count: int = 0
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    last_duration_ms: Optional[int] = None


class CachedMCPTool(AsyncBaseTool):
    """Wrap an MCP tool and materialize oversized output into a cache file."""

    def __init__(self, tool: Any, server_name: str):
        super().__init__()
        self._tool = tool
        self.server_name = server_name
        self.name = getattr(tool, "name", "mcp_tool")
        self.tool_name = getattr(tool, "tool_name", self.name)
        self.description = getattr(tool, "description", "")
        self.inputs = getattr(tool, "inputs", {})
        self.parameters = getattr(tool, "parameters", None)
        self.__name__ = getattr(tool, "__name__", self.name)
        self.__doc__ = getattr(tool, "__doc__", self.description)
        self.__input_schema__ = getattr(tool, "__input_schema__", None)

    async def forward(self, *args, **kwargs):
        result = await self._tool.forward(*args, **kwargs)
        output = _stringify_mcp_output(result)

        try:
            check_mcp_output(output)
            return result
        except MCPContentTooLargeError as exc:
            return _build_large_mcp_output_message(
                output=output,
                tool_name=self.tool_name,
                server_name=self.server_name,
                token_count=exc.token_count,
            )


def _stringify_mcp_output(result: Any) -> str:
    """Convert MCP tool output into text for size checks and caching."""
    if isinstance(result, str):
        return result
    if result is None:
        return ""
    if isinstance(result, (int, float, bool)):
        return str(result)
    try:
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        return str(result)


def _build_large_mcp_output_message(
    output: str,
    tool_name: str,
    server_name: str,
    token_count: Optional[int],
) -> str:
    """Persist oversized MCP output and return a file_read-oriented fallback."""
    preview_limit = 4_000
    preview = output[:preview_limit]
    if len(output) > preview_limit:
        preview += "\n...[truncated preview]..."

    try:
        cache_tool_name = f"mcp-{server_name}-{tool_name}".replace("/", "-")
        saved_path = save_large_output(output, cache_tool_name)
    except Exception as exc:
        logger.warning("Failed to save oversized MCP output: %s", exc)
        saved_path = None

    lines = [
        (
            "MCP tool output too large to inline "
            f"(approx {token_count or 'unknown'} tokens > {MAX_TOKEN_LIMIT} limit)."
        ),
    ]
    if preview:
        lines.extend(["Preview:", preview])
    if saved_path:
        lines.append(f"Full output saved to: {saved_path}")
        lines.append("Use file_read with offset/limit to inspect the cached result.")
    else:
        lines.append("Full output could not be cached; narrow the MCP query and retry.")
    return "\n".join(lines)


class MCPToolsLoader:
    """Loader for MCP tools from configuration files."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        auto_discover: bool = True,
        project_dir: Optional[Path] = None,
    ):
        """
        Initialize MCP tools loader.

        Args:
            config_path: Path to MCP configuration file. If None and auto_discover=True,
                        will search standard locations.
            auto_discover: If True and config_path is None, automatically search for
                          config in standard locations (.mcp.json, .claude/, .minion/, etc.)
        """
        self.project_dir = (project_dir or Path.cwd()).resolve()

        if config_path:
            self.config_path = Path(config_path).expanduser().resolve()
        elif auto_discover:
            self.config_path = find_mcp_config(project_dir=self.project_dir)
        else:
            self.config_path = None

        self.servers: Dict[str, MCPServerConfig] = {}
        self.loaded_tools = []
        self.toolsets: List[Any] = []  # Store MCPToolset instances for cleanup
        self.toolsets_by_server: Dict[str, Any] = {}
        self.tools_by_server: Dict[str, List[Any]] = {}
        self.server_statuses: Dict[str, MCPServerRuntimeStatus] = {}

    def load_config(
        self, config_path: Optional[Path] = None
    ) -> Dict[str, MCPServerConfig]:
        """
        Load MCP configuration from JSON file.

        Args:
            config_path: Path to configuration file

        Returns:
            Dictionary of server configurations
        """
        if config_path:
            self.config_path = Path(config_path).expanduser().resolve()

        if not self.config_path or not self.config_path.exists():
            logger.warning(f"MCP config file not found: {self.config_path}")
            self.servers = {}
            self.server_statuses = {}
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            previous_statuses = self.server_statuses
            self.servers = {}
            servers_config = self._extract_servers_config(config_data)

            for server_name, server_data in servers_config.items():
                parsed = self._parse_server_config(server_name, server_data)
                if parsed is not None:
                    self.servers[server_name] = parsed

            self.server_statuses = {}
            for name, config in self.servers.items():
                preserved = previous_statuses.get(name)
                if preserved is not None and not config.disabled:
                    self.server_statuses[name] = preserved
                    continue
                self.server_statuses[name] = MCPServerRuntimeStatus(
                    name=name,
                    state="disabled" if config.disabled else "pending",
                )

            logger.info(f"Loaded {len(self.servers)} MCP server configurations")
            return self.servers

        except Exception as e:
            logger.error(f"Failed to load MCP config from {self.config_path}: {e}")
            self.servers = {}
            self.server_statuses = {}
            return {}

    async def load_tools_from_server(self, server_config: MCPServerConfig) -> List[Any]:
        """
        Load tools from an MCP server.

        Args:
            server_config: Server configuration

        Returns:
            List of loaded tools
        """
        if server_config.disabled:
            logger.info(f"Skipping disabled MCP server: {server_config.name}")
            await self._close_server_toolset(server_config.name)
            self._update_server_status(server_config.name, state="disabled")
            return []

        if not MCP_AVAILABLE:
            logger.warning("MCP framework not available, skipping MCP server loading")
            self._update_server_status(
                server_config.name,
                state="failed",
                error="MCP framework not available",
            )
            return []

        timeout_seconds = self._resolve_startup_timeout(server_config)

        try:
            logger.info(f"Loading tools from MCP server: {server_config.name}")
            logger.info(self._describe_server(server_config))
            self._update_server_status(server_config.name, state="loading")

            create_coro = MCPToolset.create(
                connection_params=self._build_connection_params(server_config),
                name=server_config.name,
                structured_output=False,  # Set to False as requested
            )
            if timeout_seconds and timeout_seconds > 0:
                toolset = await asyncio.wait_for(create_coro, timeout=timeout_seconds)
            else:
                toolset = await create_coro

            tools = []
            if hasattr(toolset, "tools"):
                tools = [
                    CachedMCPTool(tool, server_config.name) for tool in toolset.tools
                ]
                toolset.tools = tools

            await self._replace_server_toolset(server_config.name, toolset, tools)
            self._update_server_status(
                server_config.name,
                state="connected",
                error=None,
                tool_count=len(tools),
            )

            logger.info(
                f"Successfully loaded {len(tools)} tools from {server_config.name}"
            )
            return tools

        except TimeoutError:
            message = (
                f"MCP startup timed out after {timeout_seconds:.1f}s"
                if timeout_seconds
                else "MCP startup timed out"
            )
            self._update_server_status(
                server_config.name,
                state="timed_out",
                error=message,
            )
            logger.error("%s: %s", server_config.name, message)
            return []
        except asyncio.CancelledError as e:
            logger.error(
                "MCP server %s setup cancelled during initialization: %s",
                server_config.name,
                e,
            )
            self._update_server_status(
                server_config.name,
                state="failed",
                error=f"setup cancelled: {e}",
            )
            return []
        except Exception as e:
            logger.error(
                f"Failed to load tools from MCP server {server_config.name}: {e}"
            )
            self._update_server_status(
                server_config.name,
                state="failed",
                error=str(e),
            )
            return []

    def _resolve_startup_timeout(self, server_config: MCPServerConfig) -> Optional[float]:
        """Return per-server startup timeout, falling back to a sane default."""
        if server_config.timeout and server_config.timeout > 0:
            return float(server_config.timeout)
        if DEFAULT_MCP_STARTUP_TIMEOUT <= 0:
            return None
        return DEFAULT_MCP_STARTUP_TIMEOUT

    def _update_server_status(
        self,
        server_name: str,
        *,
        state: str,
        error: Optional[str] = None,
        tool_count: Optional[int] = None,
    ) -> None:
        """Update per-server runtime status, including simple timing data."""
        status = self.server_statuses.get(server_name)
        if status is None:
            status = MCPServerRuntimeStatus(name=server_name)
            self.server_statuses[server_name] = status

        now = time.time()
        if state == "loading":
            status.started_at = now
            status.finished_at = None
            status.last_duration_ms = None
            status.tool_count = 0
            status.error = None
        else:
            if status.started_at is None:
                status.started_at = now
            status.finished_at = now
            status.last_duration_ms = int((now - status.started_at) * 1000)
            if tool_count is not None:
                status.tool_count = tool_count
            elif state in {"failed", "timed_out", "disabled"}:
                status.tool_count = 0
            status.error = error

        status.state = state

    async def _replace_server_toolset(
        self, server_name: str, toolset: Any, tools: List[Any]
    ) -> None:
        """Swap in a freshly connected toolset without leaking the old one."""
        await self._close_server_toolset(server_name)

        self.toolsets_by_server[server_name] = toolset
        self.tools_by_server[server_name] = list(tools)
        if toolset not in self.toolsets:
            self.toolsets.append(toolset)

    async def _close_server_toolset(self, server_name: str) -> None:
        """Close and forget one server's active toolset, if present."""
        old_toolset = self.toolsets_by_server.pop(server_name, None)
        if old_toolset is None:
            self.tools_by_server.pop(server_name, None)
            return

        try:
            await old_toolset.close()
        except Exception as exc:
            logger.error(
                "Error closing previous MCP toolset for %s: %s",
                server_name,
                exc,
            )
        try:
            self.toolsets.remove(old_toolset)
        except ValueError:
            pass
        self.tools_by_server.pop(server_name, None)

    def _extract_servers_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract effective mcpServers from root config and matched Claude project blocks."""
        effective_servers: Dict[str, Any] = {}

        root_servers = config_data.get("mcpServers", {})
        if isinstance(root_servers, dict):
            effective_servers.update(root_servers)

        matching_project = self._find_matching_project_config(config_data)
        if matching_project:
            project_servers = matching_project.get("mcpServers", {})
            if isinstance(project_servers, dict):
                effective_servers.update(project_servers)

        return effective_servers

    def _find_matching_project_config(
        self, config_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Return the closest matching Claude-style per-project config block."""
        projects = config_data.get("projects")
        if not isinstance(projects, dict):
            return None

        current = self.project_dir
        matches: List[tuple[int, Dict[str, Any]]] = []
        for raw_path, project_config in projects.items():
            if not isinstance(project_config, dict):
                continue
            try:
                candidate = Path(raw_path).expanduser().resolve()
            except Exception:
                continue

            if candidate == current or candidate in current.parents:
                matches.append((len(str(candidate)), project_config))

        if not matches:
            return None

        matches.sort(key=lambda item: item[0], reverse=True)
        return matches[0][1]

    def _parse_server_config(
        self, server_name: str, server_data: Any
    ) -> Optional[MCPServerConfig]:
        """Parse one MCP server entry from Claude-style or legacy config JSON."""
        if not isinstance(server_data, dict):
            logger.warning("Skipping MCP server %s with invalid config", server_name)
            return None

        transport = str(server_data.get("type") or "").strip().lower()
        if not transport:
            transport = "stdio" if server_data.get("command") else "http"
        if transport == "streamable_http":
            transport = "streamable-http"
        transport = self._normalize_transport(
            transport=transport,
            url=server_data.get("url"),
        )

        return MCPServerConfig(
            name=server_name,
            transport=transport,
            command=str(server_data.get("command", "")),
            args=[str(arg) for arg in server_data.get("args", [])],
            env={
                str(key): str(value)
                for key, value in (server_data.get("env") or {}).items()
            },
            cwd=server_data.get("cwd"),
            url=server_data.get("url"),
            headers=server_data.get("headers"),
            timeout=server_data.get("timeout"),
            sse_read_timeout=server_data.get("sse_read_timeout"),
            disabled=server_data.get("disabled", False),
            auto_approve=server_data.get("autoApprove", []),
        )

    def _normalize_transport(self, transport: str, url: Optional[str]) -> str:
        """Fix common MCP config mismatches like `type=http` pointing at `/sse`."""
        if not url:
            return transport

        path = urlparse(url).path.lower()
        if transport in {"http", "streamable-http"} and path.endswith("/sse"):
            logger.info(
                "Treating MCP URL %s as SSE despite transport=%s",
                url,
                transport,
            )
            return "sse"

        return transport

    def _build_connection_params(self, server_config: MCPServerConfig) -> Any:
        """Build minion MCP connection params for stdio, SSE, or streamable HTTP."""
        if server_config.transport == "stdio":
            return StdioServerParameters(
                command=server_config.command,
                args=server_config.args,
                env=server_config.env or {},
                cwd=server_config.cwd,
            )

        if server_config.transport == "sse":
            return SSEServerParameters(
                url=server_config.url or "",
                headers=server_config.headers or {},
                timeout=server_config.timeout,
                sse_read_timeout=server_config.sse_read_timeout,
            )

        if server_config.transport in {"http", "streamable-http"}:
            return StreamableHTTPServerParameters(
                url=server_config.url or "",
                headers=server_config.headers or {},
                timeout=server_config.timeout,
                sse_read_timeout=server_config.sse_read_timeout,
            )

        raise ValueError(
            f"Unsupported MCP transport '{server_config.transport}' for {server_config.name}"
        )

    def _describe_server(self, server_config: MCPServerConfig) -> str:
        """Return a concise human-readable server description for logs."""
        if server_config.transport == "stdio":
            return f"Command: {server_config.command} {' '.join(server_config.args)}"
        return (
            f"Transport: {server_config.transport} "
            f"URL: {server_config.url or '<missing>'}"
        )

    async def load_all_tools(
        self, server_names: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Load tools from all configured MCP servers.

        Returns:
            List of all loaded MCP tools
        """
        target_names = server_names or list(self.servers.keys())
        for server_name in target_names:
            if server_name not in self.servers:
                raise KeyError(f"Unknown MCP server: {server_name}")

        load_tasks = []
        for server_name in target_names:
            server_config = self.servers[server_name]
            if server_config.disabled:
                await self._close_server_toolset(server_name)
                continue
            load_tasks.append(self.load_tools_from_server(server_config))

        if load_tasks:
            await asyncio.gather(*load_tasks)

        all_tools: List[Any] = []
        for server_name in self.servers:
            all_tools.extend(self.tools_by_server.get(server_name, []))
        self.loaded_tools = all_tools
        logger.info(f"Total MCP tools loaded: {len(all_tools)}")
        return all_tools

    async def reload_all_tools(self) -> List[Any]:
        """Reload MCP configuration and reconnect all configured servers."""
        await self.close()
        self.tools_by_server.clear()
        self.toolsets_by_server.clear()
        self.loaded_tools = []
        self.load_config()
        return await self.load_all_tools()

    async def reload_server_tools(self, server_name: str) -> List[Any]:
        """Reconnect a single MCP server and refresh the flattened tool list."""
        self.load_config()
        if server_name not in self.servers:
            raise KeyError(f"Unknown MCP server: {server_name}")
        await self.load_all_tools(server_names=[server_name])
        return self.loaded_tools

    def get_server_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about configured servers.

        Returns:
            Dictionary with server information
        """
        info = {}
        for name, config in self.servers.items():
            status = self.server_statuses.get(name)
            info[name] = {
                "transport": config.transport,
                "command": config.command,
                "args": config.args,
                "url": config.url,
                "disabled": config.disabled,
                "auto_approve_count": len(config.auto_approve),
                "status": status.state if status else "unknown",
                "error": status.error if status else None,
                "tool_count": status.tool_count if status else 0,
                "last_duration_ms": status.last_duration_ms if status else None,
            }
        return info

    def get_server_statuses(self) -> Dict[str, MCPServerRuntimeStatus]:
        """Return runtime status objects keyed by server name."""
        return dict(self.server_statuses)

    async def close(self):
        """
        Close all MCP toolsets and clean up resources.
        """
        logger.info(f"Closing {len(self.toolsets)} MCP toolsets...")

        for toolset in self.toolsets:
            try:
                await toolset.close()
                logger.debug(f"Closed toolset: {getattr(toolset, 'name', 'unknown')}")
            except Exception as e:
                logger.error(f"Error closing toolset: {e}")

        self.toolsets.clear()
        self.toolsets_by_server.clear()
        self.tools_by_server.clear()
        logger.info("All MCP toolsets closed")


# Convenience function
async def load_mcp_tools(config_path: Path) -> List[Any]:
    """
    Convenience function to load MCP tools from a configuration file.

    Args:
        config_path: Path to MCP configuration file

    Returns:
        List of loaded MCP tools
    """
    loader = MCPToolsLoader(config_path)
    loader.load_config()
    return await loader.load_all_tools()
