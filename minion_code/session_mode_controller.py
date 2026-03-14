#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Shared local session mode controller for console and TUI frontends."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from .acp_server.session_modes import (
    SessionModeSpec,
    get_session_mode_spec,
    SESSION_MODE_SPECS,
)


BuildAgentFn = Callable[[SessionModeSpec], Awaitable[Any]]
AgentSwapFn = Callable[[Any], None]


class LocalSessionModeController:
    """Rebuild local agents when switching operational modes."""

    def __init__(
        self,
        initial_mode_id: str,
        build_agent: BuildAgentFn,
        on_agent_swapped: Optional[AgentSwapFn] = None,
    ) -> None:
        self.current_mode_id = initial_mode_id
        self._build_agent = build_agent
        self._on_agent_swapped = on_agent_swapped
        self.agent: Optional[Any] = None

    @property
    def current_mode(self) -> SessionModeSpec:
        return get_session_mode_spec(self.current_mode_id)

    def list_modes(self) -> list[SessionModeSpec]:
        return list(SESSION_MODE_SPECS.values())

    def resolve_mode(self, raw_value: str) -> Optional[SessionModeSpec]:
        """Resolve a user-supplied mode token to a known mode."""
        normalized = raw_value.strip().lower()
        if not normalized:
            return None

        for spec in self.list_modes():
            if normalized in {
                spec.id.lower(),
                spec.name.lower(),
                spec.name.lower().replace(" ", "-"),
            }:
                return spec
        return None

    async def initialize(self) -> Any:
        """Build the initial agent for the current mode."""
        self.agent = await self._build_agent(self.current_mode)
        self._annotate_agent(self.agent)
        self._notify_agent_swap(self.agent)
        return self.agent

    async def set_mode(self, mode_id: str) -> Any:
        """Switch modes, preserving history and runtime metadata."""
        target_mode = get_session_mode_spec(mode_id)
        if self.agent is not None and target_mode.id == self.current_mode_id:
            return self.agent
        return await self._rebuild_mode(target_mode)

    async def rebuild_current(self) -> Any:
        """Rebuild the current mode's agent, preserving conversation state."""
        return await self._rebuild_mode(get_session_mode_spec(self.current_mode_id))

    async def _rebuild_mode(self, target_mode: SessionModeSpec) -> Any:
        """Rebuild an agent for the target mode while preserving runtime state."""
        if self.agent is not None and target_mode.id != self.current_mode_id:
            self.current_mode_id = target_mode.id

        old_history = None
        old_conversation_history = None
        old_metadata = None
        if self.agent is not None:
            old_history = self.agent.state.history.copy()
            old_conversation_history = self.agent.get_conversation_history()
            old_metadata = dict(getattr(self.agent.state, "metadata", {}) or {})

        self.current_mode_id = target_mode.id
        self.agent = await self._build_agent(target_mode)

        if old_history is not None:
            self.agent.state.history.clear()
            self.agent.state.history.extend(old_history.to_list())
        if old_conversation_history is not None:
            self.agent.conversation_history = old_conversation_history
        if old_metadata is not None:
            self.agent.state.metadata.update(old_metadata)

        self._annotate_agent(self.agent)
        self._notify_agent_swap(self.agent)
        return self.agent

    def _annotate_agent(self, agent: Any) -> None:
        if not hasattr(agent.state, "metadata") or agent.state.metadata is None:
            agent.state.metadata = {}
        agent.state.metadata["mode_controller"] = self
        agent.state.metadata["session_mode_id"] = self.current_mode.id
        agent.state.metadata["session_mode_name"] = self.current_mode.name
        agent.state.metadata["session_mode_description"] = self.current_mode.description
        if agent.state and not getattr(agent.state, "agent", None):
            agent.state.agent = agent

    def _notify_agent_swap(self, agent: Any) -> None:
        if self._on_agent_swapped is not None:
            self._on_agent_swapped(agent)
