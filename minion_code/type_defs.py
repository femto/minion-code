"""
Type definitions for minion_code
Shared types to avoid circular imports
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Union
import uuid
import time


class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    PROGRESS = "progress"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class InputMode(Enum):
    BASH = "bash"
    PROMPT = "prompt"
    KODING = "koding"


@dataclass
class MessageContent:
    """Represents message content - can be text or structured content"""

    content: Union[str, List[Dict[str, Any]]]
    type: str = "text"

    def __init__(
        self, content: Union[str, List[Dict[str, Any]]] = "", type: str = "text"
    ):
        self.content = content
        self.type = type


@dataclass
class Message:
    """Core message structure equivalent to TypeScript MessageType"""

    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.USER
    message: MessageContent = field(default_factory=lambda: MessageContent(""))
    timestamp: float = field(default_factory=time.time)
    options: Optional[Dict[str, Any]] = None


@dataclass
class ToolUseConfirm:
    """Tool use confirmation context"""

    tool_name: str
    parameters: Dict[str, Any]
    on_confirm: Any  # Callable[[], None]
    on_abort: Any  # Callable[[], None]


@dataclass
class BinaryFeedbackContext:
    """Binary feedback context for comparing two assistant messages"""

    m1: Message
    m2: Message
    resolve: Any  # Callable[[str], None]


@dataclass
class ToolJSXContext:
    """Tool JSX rendering context"""

    jsx: Optional[Any] = None
    should_hide_prompt_input: bool = False


@dataclass
class ModelInfo:
    """Model information display"""

    name: str
    provider: str
    context_length: int
    current_tokens: int
    id: Optional[str] = None


class REPLConfig:
    """Configuration equivalent to getGlobalConfig()"""

    def __init__(self):
        self.verbose: bool = False
        self.debug: bool = False
        self.safe_mode: bool = False
        self.has_acknowledged_cost_threshold: bool = False
        self.model_name: str = "claude-3-5-sonnet-20241022"

    def get_model_name(self, context: str = "main") -> str:
        return self.model_name
