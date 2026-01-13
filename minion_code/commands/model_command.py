#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Model command - View and configure the LLM model
"""

import json
import yaml
from pathlib import Path
from typing import List, Optional
from minion_code.commands import BaseCommand, CommandType


class ModelCommand(BaseCommand):
    """View or set the default LLM model."""

    name = "model"
    description = "View or set the default LLM model"
    usage = "/model [model_name] or /model --clear or /model --list"
    aliases = ["llm"]
    command_type = CommandType.LOCAL

    # Config file path
    CONFIG_DIR = Path.home() / ".minion"
    CONFIG_FILE = CONFIG_DIR / "minion-code.json"
    MINION_CONFIG_FILE = CONFIG_DIR / "config.yaml"

    def _load_config(self) -> dict:
        """Load config from file."""
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self, config: dict) -> None:
        """Save config to file."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)

    def _get_available_models(self) -> List[str]:
        """Get list of available models from minion config.yaml.

        Uses the same logic as minion's load_config():
        1. First load user config (~/.minion/config.yaml)
        2. Then load base config (MINION_ROOT/config/config.yaml) which OVERWRITES user config
        """
        config_dict = {}

        # First load user config
        if self.MINION_CONFIG_FILE.exists():
            try:
                with open(self.MINION_CONFIG_FILE, 'r') as f:
                    config_dict = yaml.safe_load(f) or {}
            except Exception:
                pass

        # Then load base config (MINION_ROOT), which overwrites user config
        try:
            from minion.const import get_minion_root
            minion_root = get_minion_root()
            base_config_path = Path(minion_root) / "config" / "config.yaml"
            if base_config_path.exists():
                with open(base_config_path, 'r') as f:
                    base_config = yaml.safe_load(f) or {}
                config_dict.update(base_config)  # Overwrite, same as minion
        except Exception:
            pass

        models = list(config_dict.get('models', {}).keys())
        return sorted(models)

    def _update_agent_model(self, model_name: str) -> bool:
        """Update the agent's model at runtime."""
        if not self.agent:
            return False

        try:
            from minion.types.llm_types import create_llm_from_model
            # Create new LLM provider with the new model
            new_llm = create_llm_from_model(model_name)
            self.agent.llm = new_llm

            # Update llms dict if it exists
            if hasattr(self.agent, 'llms'):
                self.agent.llms['main'] = new_llm

            return True
        except Exception as e:
            self.output.warning(f"Could not update runtime model: {e}")
            return False

    def _set_model(self, model_name: str) -> None:
        """Set the model and update config."""
        config = self._load_config()
        config["model"] = model_name
        self._save_config(config)

        # Try to update the running agent's model
        runtime_updated = self._update_agent_model(model_name)

        if runtime_updated:
            self.output.success(f"Model changed to: {model_name}")
        else:
            self.output.success(f"Default model set to: {model_name}")
            self.output.warning("Restart session to use the new model.")

        self.output.info(f"Config saved to: {self.CONFIG_FILE}")

    async def execute(self, args: str) -> None:
        """Execute the model command."""
        args = args.strip()
        config = self._load_config()

        if args == "--clear" or args == "-c":
            # Clear model setting
            if "model" in config:
                del config["model"]
                self._save_config(config)
                self.output.success("Model setting cleared. Will use default model.")
            else:
                self.output.info("No model setting to clear.")

        elif args == "--list" or args == "-l":
            # List available models
            models = self._get_available_models()
            if models:
                self.output.info(f"Available models ({len(models)}):")
                for model in models:
                    self.output.text(f"  - {model}")
            else:
                self.output.warning("No models found in config.yaml")

        elif args:
            # Set model directly
            self._set_model(args)

        else:
            # Interactive mode: show current model and let user choose
            current_config_model = config.get("model")

            # Get current agent model
            current_agent_model = None
            if self.agent:
                current_agent_model = getattr(self.agent, 'llm', None)

            # Display current info
            headers = ["Setting", "Value"]
            rows = []

            if current_agent_model:
                rows.append(["Current Session Model", str(current_agent_model)])

            if current_config_model:
                rows.append(["Config File Model", current_config_model])
            else:
                rows.append(["Config File Model", "(not set - using default)"])

            self.output.table(headers, rows, title="Model Configuration")

            # Get available models and show selection
            models = self._get_available_models()
            if models:
                # Add current model indicator
                choices = []
                for model in models:
                    if model == current_config_model:
                        choices.append(f"{model} (current)")
                    else:
                        choices.append(model)

                # Ask user to select (returns index, -1 if cancelled)
                selected_index = await self.output.choice(
                    message="Select a model:",
                    choices=choices,
                    title="Available Models"
                )

                if selected_index >= 0 and selected_index < len(models):
                    # Get the model name from original models list (without " (current)" suffix)
                    model_name = models[selected_index]
                    if model_name != current_config_model:
                        self._set_model(model_name)
                    else:
                        self.output.info("Model unchanged.")
            else:
                # No models found, show usage hints
                self.output.info("\nUsage:")
                self.output.text("  /model <name>   - Set model (e.g., /model gpt-4o)")
                self.output.text("  /model --list   - List available models")
                self.output.text("  /model --clear  - Clear saved model setting")
