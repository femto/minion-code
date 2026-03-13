#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mode command - inspect or switch session operational mode."""

from minion_code.commands import BaseCommand, CommandType


class ModeCommand(BaseCommand):
    """View or switch the current session mode."""

    name = "mode"
    description = "View or switch the current session mode"
    usage = "/mode [mode_name]"
    aliases = ["modes"]
    command_type = CommandType.LOCAL

    async def execute(self, args: str) -> None:
        controller = self._get_mode_controller()
        if controller is None:
            self.output.error("Session mode controller is not available.")
            return

        requested = args.strip()
        if requested:
            await self._set_mode(controller, requested)
            return

        await self._choose_mode(controller)

    def _get_mode_controller(self):
        if not self.agent:
            return None
        metadata = getattr(getattr(self.agent, "state", None), "metadata", {}) or {}
        return metadata.get("mode_controller")

    async def _set_mode(self, controller, raw_value: str) -> None:
        spec = controller.resolve_mode(raw_value)
        if spec is None:
            self.output.error(f"Unknown mode: {raw_value}")
            await self._show_mode_table(controller)
            return

        previous_mode = controller.current_mode
        await controller.set_mode(spec.id)

        tool_count = len(controller.agent.tools) if controller.agent and controller.agent.tools else 0
        if previous_mode.id == spec.id:
            self.output.info(f"Already in {spec.name}.")
        else:
            self.output.success(f"Switched to {spec.name}.")
        self.output.text(f"{spec.description}\nTools available: {tool_count}")

    async def _choose_mode(self, controller) -> None:
        specs = controller.list_modes()
        current_mode = controller.current_mode
        choices = [
            f"{spec.name} ({spec.id}) - {spec.description}"
            for spec in specs
        ]
        default_index = next(
            (index for index, spec in enumerate(specs) if spec.id == current_mode.id),
            0,
        )
        selected_index = await self.output.choice(
            message=f"Current mode: {current_mode.name}",
            choices=choices,
            title="Session Mode",
            default_index=default_index,
        )
        if selected_index < 0:
            return

        await self._set_mode(controller, specs[selected_index].id)

    async def _show_mode_table(self, controller) -> None:
        headers = ["Mode", "ID", "Behavior"]
        rows = [
            [spec.name, spec.id, spec.description]
            for spec in controller.list_modes()
        ]
        self.output.table(headers, rows, title="Available Session Modes")
