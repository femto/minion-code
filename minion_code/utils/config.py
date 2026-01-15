"""Configuration management utilities for minion-code.

This module provides configuration management functionality similar to the TypeScript
config.ts file, adapted for Python and the minion-code project structure.
"""

import json
import os
import secrets
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)

# Type definitions
McpStdioServerConfig = TypedDict(
    "McpStdioServerConfig",
    {
        "type": Optional[str],  # Optional for backwards compatibility
        "command": str,
        "args": List[str],
        "env": Optional[Dict[str, str]],
    },
)

McpSSEServerConfig = TypedDict(
    "McpSSEServerConfig", {"type": Literal["sse"], "url": str}
)

McpServerConfig = Union[McpStdioServerConfig, McpSSEServerConfig]

AutoUpdaterStatus = Literal["disabled", "enabled", "no_permissions", "not_configured"]
NotificationChannel = Literal[
    "iterm2", "terminal_bell", "iterm2_with_bell", "notifications_disabled"
]
ProviderType = Literal[
    "anthropic",
    "openai",
    "mistral",
    "deepseek",
    "kimi",
    "qwen",
    "glm",
    "minimax",
    "baidu-qianfan",
    "siliconflow",
    "bigdream",
    "opendev",
    "xai",
    "groq",
    "gemini",
    "ollama",
    "azure",
    "custom",
    "custom-openai",
]

ReasoningEffort = Literal["low", "medium", "high", "minimal"]
ModelPointerType = Literal["main", "task", "reasoning", "quick"]
ValidationStatus = Literal["valid", "needs_repair", "auto_repaired"]


@dataclass
class ModelProfile:
    """Model profile configuration."""

    name: str  # User-friendly name
    provider: ProviderType  # Provider type
    model_name: str  # Primary key - actual model identifier
    api_key: str
    max_tokens: int  # Output token limit
    context_length: int  # Context window size
    is_active: bool = True  # Whether profile is enabled
    created_at: int = field(default_factory=lambda: int(os.time.time() * 1000))
    base_url: Optional[str] = None  # Custom endpoint
    reasoning_effort: Optional[ReasoningEffort] = None
    last_used: Optional[int] = None  # Last usage timestamp
    is_gpt5: Optional[bool] = None  # Auto-detected GPT-5 model flag
    validation_status: Optional[ValidationStatus] = None  # Configuration status
    last_validation: Optional[int] = None  # Last validation timestamp


@dataclass
class ModelPointers:
    """Model pointer system."""

    main: str = ""  # Main dialog model ID
    task: str = ""  # Task tool model ID
    reasoning: str = ""  # Reasoning model ID
    quick: str = ""  # Quick model ID


@dataclass
class AccountInfo:
    """Account information."""

    account_uuid: str
    email_address: str
    organization_uuid: Optional[str] = None


@dataclass
class ProjectConfig:
    """Project-specific configuration."""

    allowed_tools: List[str] = field(default_factory=list)
    context: Dict[str, str] = field(default_factory=dict)
    context_files: Optional[List[str]] = None
    history: List[str] = field(default_factory=list)
    dont_crawl_directory: bool = False
    enable_architect_tool: bool = False
    mcp_context_uris: List[str] = field(default_factory=list)
    mcp_servers: Optional[Dict[str, McpServerConfig]] = field(default_factory=dict)
    approved_mcprc_servers: Optional[List[str]] = field(default_factory=list)
    rejected_mcprc_servers: Optional[List[str]] = field(default_factory=list)
    last_api_duration: Optional[float] = None
    last_cost: Optional[float] = None
    last_duration: Optional[float] = None
    last_session_id: Optional[str] = None
    example_files: Optional[List[str]] = None
    example_files_generated_at: Optional[int] = None
    has_trust_dialog_accepted: bool = False
    has_completed_project_onboarding: bool = False


@dataclass
class GlobalConfig:
    """Global configuration."""

    num_startups: int = 0
    auto_updater_status: AutoUpdaterStatus = "not_configured"
    user_id: Optional[str] = None
    theme: str = "dark"
    has_completed_onboarding: Optional[bool] = None
    last_onboarding_version: Optional[str] = None
    last_release_notes_seen: Optional[str] = None
    mcp_servers: Optional[Dict[str, McpServerConfig]] = field(default_factory=dict)
    preferred_notif_channel: NotificationChannel = "iterm2"
    verbose: bool = False
    custom_api_key_responses: Optional[Dict[str, List[str]]] = field(
        default_factory=lambda: {"approved": [], "rejected": []}
    )
    primary_provider: ProviderType = "anthropic"
    max_tokens: Optional[int] = None
    has_acknowledged_cost_threshold: Optional[bool] = None
    oauth_account: Optional[AccountInfo] = None
    iterm2_key_binding_installed: Optional[bool] = None  # Legacy
    shift_enter_key_binding_installed: Optional[bool] = None
    proxy: Optional[str] = None
    stream: bool = True
    projects: Optional[Dict[str, ProjectConfig]] = field(default_factory=dict)

    # New model system
    model_profiles: Optional[List[ModelProfile]] = field(default_factory=list)
    model_pointers: Optional[ModelPointers] = field(default_factory=ModelPointers)
    default_model_name: Optional[str] = None
    last_dismissed_update_version: Optional[str] = None


# Configuration keys that can be modified
GLOBAL_CONFIG_KEYS = [
    "auto_updater_status",
    "theme",
    "has_completed_onboarding",
    "last_onboarding_version",
    "last_release_notes_seen",
    "verbose",
    "custom_api_key_responses",
    "primary_provider",
    "preferred_notif_channel",
    "shift_enter_key_binding_installed",
    "max_tokens",
]

PROJECT_CONFIG_KEYS = [
    "dont_crawl_directory",
    "enable_architect_tool",
    "has_trust_dialog_accepted",
    "has_completed_project_onboarding",
]


class ConfigParseError(Exception):
    """Configuration parsing error."""

    def __init__(self, message: str, file_path: str, default_config: Any):
        super().__init__(message)
        self.file_path = file_path
        self.default_config = default_config


class ConfigManager:
    """Configuration manager for minion-code."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_dir: Directory for configuration files. Defaults to ~/.minion-code
        """
        if config_dir is None:
            config_dir = Path.home() / ".minion-code"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.global_config_file = self.config_dir / "config.json"

        # Test configurations for testing environment
        self._test_global_config: Optional[GlobalConfig] = None
        self._test_project_config: Optional[ProjectConfig] = None

    def _is_test_env(self) -> bool:
        """Check if running in test environment."""
        return (
            os.getenv("PYTHON_ENV") == "test"
            or os.getenv("PYTEST_CURRENT_TEST") is not None
        )

    def _get_current_project_path(self) -> str:
        """Get current project path."""
        return os.getcwd()

    def _default_project_config(self, project_path: str) -> ProjectConfig:
        """Get default configuration for a project."""
        config = ProjectConfig()
        if project_path == str(Path.home()):
            config.dont_crawl_directory = True
        return config

    def _safe_parse_json(self, content: str) -> Any:
        """Safely parse JSON content."""
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return None

    def _save_config(self, file_path: Path, config: Any, default_config: Any) -> None:
        """Save configuration to file."""
        # Convert dataclass to dict if needed
        if hasattr(config, "__dataclass_fields__"):
            config_dict = asdict(config)
        else:
            config_dict = config

        if hasattr(default_config, "__dataclass_fields__"):
            default_dict = asdict(default_config)
        else:
            default_dict = default_config

        # Filter out values that match defaults
        filtered_config = {}
        for key, value in config_dict.items():
            if key in default_dict:
                if json.dumps(value, sort_keys=True) != json.dumps(
                    default_dict[key], sort_keys=True
                ):
                    filtered_config[key] = value
            else:
                filtered_config[key] = value

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(filtered_config, f, indent=2, ensure_ascii=False)
        except (PermissionError, OSError) as e:
            logger.warning(f"Could not save config to {file_path}: {e}")

    def _load_config(
        self, file_path: Path, default_config: Any, throw_on_invalid: bool = False
    ) -> Any:
        """Load configuration from file."""
        logger.debug(f"Loading config from {file_path}")

        if not file_path.exists():
            logger.debug(f"Config file {file_path} does not exist, using defaults")
            return deepcopy(default_config)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            parsed_config = self._safe_parse_json(content)
            if parsed_config is None:
                if throw_on_invalid:
                    raise ConfigParseError(
                        f"Invalid JSON in {file_path}", str(file_path), default_config
                    )
                logger.warning(f"Invalid JSON in {file_path}, using defaults")
                return deepcopy(default_config)

            # Merge with defaults
            if hasattr(default_config, "__dataclass_fields__"):
                # Handle dataclass
                default_dict = asdict(default_config)
                merged_dict = {**default_dict, **parsed_config}
                # Convert back to dataclass
                return type(default_config)(**merged_dict)
            else:
                # Handle regular dict
                return {**deepcopy(default_config), **parsed_config}

        except Exception as e:
            if throw_on_invalid:
                raise ConfigParseError(str(e), str(file_path), default_config)
            logger.warning(
                f"Error loading config from {file_path}: {e}, using defaults"
            )
            return deepcopy(default_config)

    def get_global_config(self) -> GlobalConfig:
        """Get global configuration."""
        if self._is_test_env() and self._test_global_config is not None:
            return self._test_global_config

        config = self._load_config(self.global_config_file, GlobalConfig())
        return self._migrate_model_profiles_remove_id(config)

    def save_global_config(self, config: GlobalConfig) -> None:
        """Save global configuration."""
        if self._is_test_env():
            self._test_global_config = config
            return

        # Preserve projects when saving global config
        current_config = self._load_config(self.global_config_file, GlobalConfig())
        config.projects = current_config.projects

        self._save_config(self.global_config_file, config, GlobalConfig())

    def get_current_project_config(self) -> ProjectConfig:
        """Get current project configuration."""
        if self._is_test_env() and self._test_project_config is not None:
            return self._test_project_config

        project_path = self._get_current_project_path()
        global_config = self.get_global_config()

        if not global_config.projects:
            return self._default_project_config(project_path)

        project_config_data = global_config.projects.get(project_path)
        if project_config_data is None:
            return self._default_project_config(project_path)

        # Convert dict to ProjectConfig instance if needed
        if isinstance(project_config_data, dict):
            # Handle legacy string format for allowed_tools
            if isinstance(project_config_data.get("allowed_tools"), str):
                try:
                    project_config_data["allowed_tools"] = json.loads(
                        project_config_data["allowed_tools"]
                    )
                except json.JSONDecodeError:
                    project_config_data["allowed_tools"] = []

            # Create ProjectConfig instance from dict
            project_config = ProjectConfig(**project_config_data)
        else:
            # Already a ProjectConfig instance
            project_config = project_config_data
            # Handle legacy string format for allowed_tools
            if isinstance(project_config.allowed_tools, str):
                try:
                    project_config.allowed_tools = json.loads(
                        project_config.allowed_tools
                    )
                except json.JSONDecodeError:
                    project_config.allowed_tools = []

        return project_config

    def save_current_project_config(self, project_config: ProjectConfig) -> None:
        """Save current project configuration."""
        if self._is_test_env():
            self._test_project_config = project_config
            return

        project_path = self._get_current_project_path()
        global_config = self.get_global_config()

        if global_config.projects is None:
            global_config.projects = {}

        global_config.projects[project_path] = project_config
        self._save_config(self.global_config_file, global_config, GlobalConfig())

    def get_anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from environment."""
        return os.getenv("ANTHROPIC_API_KEY")

    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment."""
        return os.getenv("OPENAI_API_KEY")

    def normalize_api_key_for_config(self, api_key: str) -> str:
        """Normalize API key for configuration storage."""
        return api_key[-20:] if api_key else ""

    def get_custom_api_key_status(
        self, truncated_api_key: str
    ) -> Literal["approved", "rejected", "new"]:
        """Get custom API key status."""
        config = self.get_global_config()
        responses = config.custom_api_key_responses or {"approved": [], "rejected": []}

        if truncated_api_key in responses.get("approved", []):
            return "approved"
        if truncated_api_key in responses.get("rejected", []):
            return "rejected"
        return "new"

    def get_or_create_user_id(self) -> str:
        """Get or create user ID."""
        config = self.get_global_config()
        if config.user_id:
            return config.user_id

        user_id = secrets.token_hex(32)
        config.user_id = user_id
        self.save_global_config(config)
        return user_id

    def check_has_trust_dialog_accepted(self) -> bool:
        """Check if trust dialog has been accepted for current or parent directories."""
        current_path = Path(self._get_current_project_path())
        config = self.get_global_config()

        # Check current and parent directories
        for path in [current_path] + list(current_path.parents):
            path_str = str(path)
            project_config = config.projects.get(path_str) if config.projects else None
            if project_config and project_config.has_trust_dialog_accepted:
                return True

        return False

    def _migrate_model_profiles_remove_id(self, config: GlobalConfig) -> GlobalConfig:
        """Migrate model profiles to remove ID field and update pointers."""
        if not config.model_profiles:
            return config

        # Build ID to model_name mapping and remove id field
        id_to_model_name = {}
        migrated_profiles = []

        for profile in config.model_profiles:
            profile_dict = (
                asdict(profile) if hasattr(profile, "__dataclass_fields__") else profile
            )

            # Build mapping before removing id field
            if "id" in profile_dict and "model_name" in profile_dict:
                id_to_model_name[profile_dict["id"]] = profile_dict["model_name"]

            # Remove id field
            profile_dict.pop("id", None)
            migrated_profiles.append(ModelProfile(**profile_dict))

        # Migrate model pointers
        migrated_pointers = ModelPointers()
        if config.model_pointers:
            pointers_dict = (
                asdict(config.model_pointers)
                if hasattr(config.model_pointers, "__dataclass_fields__")
                else config.model_pointers
            )
            for pointer, value in pointers_dict.items():
                if value:
                    model_name = id_to_model_name.get(value, value)
                    setattr(migrated_pointers, pointer, model_name)

        # Migrate legacy fields
        default_model_name = config.default_model_name
        if hasattr(config, "default_model_id"):
            default_model_name = id_to_model_name.get(
                getattr(config, "default_model_id"), getattr(config, "default_model_id")
            )

        config.model_profiles = migrated_profiles
        config.model_pointers = migrated_pointers
        config.default_model_name = default_model_name

        return config

    # GPT-5 specific functions
    def is_gpt5_model_name(self, model_name: str) -> bool:
        """Check if a model name represents a GPT-5 model."""
        if not model_name or not isinstance(model_name, str):
            return False
        return "gpt-5" in model_name.lower()

    def validate_and_repair_gpt5_profile(self, profile: ModelProfile) -> ModelProfile:
        """Validate and auto-repair GPT-5 model configuration."""
        is_gpt5 = self.is_gpt5_model_name(profile.model_name)
        now = int(os.time.time() * 1000)

        # Create working copy
        repaired_profile = deepcopy(profile)
        was_repaired = False

        # Set GPT-5 detection flag
        if is_gpt5 != profile.is_gpt5:
            repaired_profile.is_gpt5 = is_gpt5
            was_repaired = True

        if is_gpt5:
            # GPT-5 parameter validation and repair
            valid_reasoning_efforts = ["minimal", "low", "medium", "high"]
            if (
                not profile.reasoning_effort
                or profile.reasoning_effort not in valid_reasoning_efforts
            ):
                repaired_profile.reasoning_effort = "medium"
                was_repaired = True
                logger.info(
                    f"🔧 GPT-5 Config: Set reasoning effort to 'medium' for {profile.model_name}"
                )

            # Context length validation
            if profile.context_length < 128000:
                repaired_profile.context_length = 128000
                was_repaired = True
                logger.info(
                    f"🔧 GPT-5 Config: Updated context length to 128k for {profile.model_name}"
                )

            # Output tokens validation
            if profile.max_tokens < 4000:
                repaired_profile.max_tokens = 8192
                was_repaired = True
                logger.info(
                    f"🔧 GPT-5 Config: Updated max tokens to 8192 for {profile.model_name}"
                )

            # Base URL validation
            if "gpt-5" in profile.model_name and not profile.base_url:
                repaired_profile.base_url = "https://api.openai.com/v1"
                was_repaired = True
                logger.info(
                    f"🔧 GPT-5 Config: Set default base URL for {profile.model_name}"
                )

        # Update validation metadata
        repaired_profile.validation_status = (
            "auto_repaired" if was_repaired else "valid"
        )
        repaired_profile.last_validation = now

        if was_repaired:
            logger.info(
                f"✅ GPT-5 Config: Auto-repaired configuration for {profile.model_name}"
            )

        return repaired_profile

    def set_model_pointer(self, pointer: ModelPointerType, model_name: str) -> None:
        """Set a model pointer to a specific model."""
        config = self.get_global_config()
        if config.model_pointers is None:
            config.model_pointers = ModelPointers()

        setattr(config.model_pointers, pointer, model_name)
        self.save_global_config(config)

    def set_all_pointers_to_model(self, model_name: str) -> None:
        """Set all model pointers to the same model."""
        config = self.get_global_config()
        config.model_pointers = ModelPointers(
            main=model_name, task=model_name, reasoning=model_name, quick=model_name
        )
        config.default_model_name = model_name
        self.save_global_config(config)


# Global instance
config_manager = ConfigManager()


# Convenience functions
def get_global_config() -> GlobalConfig:
    """Get global configuration."""
    return config_manager.get_global_config()


def save_global_config(config: GlobalConfig) -> None:
    """Save global configuration."""
    config_manager.save_global_config(config)


def get_current_project_config() -> ProjectConfig:
    """Get current project configuration."""
    return config_manager.get_current_project_config()


def save_current_project_config(config: ProjectConfig) -> None:
    """Save current project configuration."""
    config_manager.save_current_project_config(config)


def get_anthropic_api_key() -> Optional[str]:
    """Get Anthropic API key."""
    return config_manager.get_anthropic_api_key()


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key."""
    return config_manager.get_openai_api_key()
