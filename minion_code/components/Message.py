"""
Message Component - Python equivalent of React Message component
Handles rendering of user and assistant messages with different content types
"""

from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, RichLog
from textual.reactive import reactive
from rich.text import Text
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from typing import List, Dict, Any, Optional, Set
import json

# Import shared types
from ..types import Message as MessageType, MessageContent, InputMode


class Message(Container):
    """
    Main message component equivalent to React Message
    Handles rendering of both user and assistant messages
    """
    
    DEFAULT_CSS = """
    Message {
        width: 80%;
        height: auto;
        margin-bottom: 1;
    }
    
    .user-message {
        border-left: thick blue;
        padding-left: 1;
        height: auto;
    }
    
    .assistant-message {
        border-left: thick green;
        padding-left: 1;
        height: auto;
    }
    
    .tool-use-message {
        border-left: thick yellow;
        padding-left: 1;
        background: $surface-lighten-1;
        height: auto;
    }
    
    .error-message {
        border-left: thick red;
        padding-left: 1;
        background: $error 10%;
        height: auto;
    }
    
    .message-content {
        width: 100%;
        height: auto;
        padding: 1;
    }
    
    .message-meta {
        color: $text-muted;
        text-style: dim;
        height: 1;
    }
    """
    
    def __init__(self,
                 message: MessageType,
                 messages: List[MessageType] = None,
                 add_margin: bool = True,
                 tools: List[Any] = None,
                 verbose: bool = False,
                 debug: bool = False,
                 errored_tool_use_ids: Set[str] = None,
                 in_progress_tool_use_ids: Set[str] = None,
                 unresolved_tool_use_ids: Set[str] = None,
                 should_animate: bool = False,
                 should_show_dot: bool = False,
                 width: Optional[int] = None,
                 **kwargs):
        super().__init__(**kwargs)
        
        self.message = message
        self.messages = messages or []
        self.add_margin = add_margin
        self.tools = tools or []
        self.verbose = verbose
        self.debug = debug
        self.errored_tool_use_ids = errored_tool_use_ids or set()
        self.in_progress_tool_use_ids = in_progress_tool_use_ids or set()
        self.unresolved_tool_use_ids = unresolved_tool_use_ids or set()
        self.should_animate = should_animate
        self.should_show_dot = should_show_dot
        self.width = width
    
    def compose(self):
        """Compose the message interface"""
        if self.message.type.value == "assistant":
            yield from self._render_assistant_message()
        else:
            yield from self._render_user_message()
    
    def _render_user_message(self):
        """Render user message - equivalent to UserMessage component"""
        with Vertical(classes="user-message"):
            # Message metadata
            if self.verbose or self.debug:
                yield Static(
                    f"User • {self._format_timestamp()}",
                    classes="message-meta"
                )
            
            # Message content
            content = self.message.message.content
            if isinstance(content, str):
                yield from self._render_text_content(content)
            elif isinstance(content, list):
                for item in content:
                    yield from self._render_content_block(item)
    
    def _render_assistant_message(self):
        """Render assistant message - equivalent to AssistantMessage component"""
        with Vertical(classes="assistant-message"):
            # Message metadata
            if self.verbose or self.debug:
                meta_text = f"Assistant • {self._format_timestamp()}"
                if hasattr(self.message, 'cost_usd') and self.message.cost_usd:
                    meta_text += f" • ${self.message.cost_usd:.4f}"
                if hasattr(self.message, 'duration_ms') and self.message.duration_ms:
                    meta_text += f" • {self.message.duration_ms}ms"
                
                yield Static(meta_text, classes="message-meta")
            
            # Message content
            content = self.message.message.content
            if isinstance(content, str):
                yield from self._render_text_content(content)
            elif isinstance(content, list):
                for item in content:
                    yield from self._render_content_block(item)
    
    def _render_content_block(self, block: Dict[str, Any]):
        """Render individual content blocks based on type"""
        block_type = block.get('type', 'text')
        
        if block_type == 'text':
            yield from self._render_text_content(block.get('text', ''))
        elif block_type == 'tool_use':
            yield from self._render_tool_use_block(block)
        elif block_type == 'tool_result':
            yield from self._render_tool_result_block(block)
        elif block_type == 'thinking':
            yield from self._render_thinking_block(block)
        elif block_type == 'redacted_thinking':
            yield from self._render_redacted_thinking_block()
        else:
            # Unknown block type
            yield Static(f"[Unknown content type: {block_type}]", classes="error-message")
    
    def _render_text_content(self, text: str):
        """Render text content with markdown support"""
        if not text.strip():
            return
        
        try:
            # For now, just render as plain text to avoid compose-time issues
            # TODO: Implement proper markdown rendering with RichLog after mount
            yield Static(text, classes="message-content")
        except Exception:
            yield Static(text, classes="message-content")
    
    def _render_tool_use_block(self, block: Dict[str, Any]):
        """Render tool use block - equivalent to AssistantToolUseMessage"""
        tool_name = block.get('name', 'unknown')
        tool_id = block.get('id', '')
        parameters = block.get('input', {})
        
        # Determine status
        status = "completed"
        if tool_id in self.in_progress_tool_use_ids:
            status = "in_progress"
        elif tool_id in self.errored_tool_use_ids:
            status = "error"
        elif tool_id in self.unresolved_tool_use_ids:
            status = "unresolved"
        
        with Vertical(classes="tool-use-message"):
            # Tool header
            status_icon = {
                "completed": "✅",
                "in_progress": "⏳",
                "error": "❌",
                "unresolved": "⏸️"
            }.get(status, "🔧")
            
            yield Static(
                f"{status_icon} Tool: {tool_name}",
                classes="message-meta"
            )
            
            # Tool parameters (if verbose)
            if self.verbose and parameters:
                try:
                    params_json = json.dumps(parameters, indent=2)
                    # For now, render as plain text to avoid compose-time issues
                    yield Static(params_json, classes="message-content")
                except Exception:
                    yield Static(str(parameters), classes="message-content")
    
    def _render_tool_result_block(self, block: Dict[str, Any]):
        """Render tool result block - equivalent to UserToolResultMessage"""
        tool_use_id = block.get('tool_use_id', '')
        content = block.get('content', '')
        is_error = block.get('is_error', False)
        
        classes = "error-message" if is_error else "message-content"
        
        with Vertical():
            # Result header
            icon = "❌" if is_error else "📤"
            yield Static(
                f"{icon} Tool Result",
                classes="message-meta"
            )
            
            # Result content
            if isinstance(content, str):
                yield Static(content, classes=classes)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        yield Static(item.get('text', ''), classes=classes)
                    else:
                        yield Static(str(item), classes=classes)
    
    def _render_thinking_block(self, block: Dict[str, Any]):
        """Render thinking block - equivalent to AssistantThinkingMessage"""
        if not self.debug:
            return  # Only show in debug mode
        
        thinking_content = block.get('content', '')
        
        with Vertical():
            yield Static("🤔 Thinking...", classes="message-meta")
            yield Static(thinking_content, classes="message-content")
    
    def _render_redacted_thinking_block(self):
        """Render redacted thinking block"""
        if not self.debug:
            return
        
        yield Static("🤔 [Thinking content redacted]", classes="message-meta")
    
    def _format_timestamp(self) -> str:
        """Format message timestamp"""
        import datetime
        dt = datetime.datetime.fromtimestamp(self.message.timestamp)
        return dt.strftime("%H:%M:%S")


class UserMessage(Message):
    """Specialized component for user messages"""
    
    def __init__(self, message: MessageType, **kwargs):
        super().__init__(message, **kwargs)
    
    def compose(self):
        """Compose user message with specific styling"""
        yield from self._render_user_message()


class AssistantMessage(Message):
    """Specialized component for assistant messages"""
    
    def __init__(self, message: MessageType, **kwargs):
        super().__init__(message, **kwargs)
    
    def compose(self):
        """Compose assistant message with specific styling"""
        yield from self._render_assistant_message()


class ToolUseMessage(Message):
    """Specialized component for tool use messages"""
    
    def __init__(self, message: MessageType, **kwargs):
        super().__init__(message, **kwargs)
    
    def compose(self):
        """Compose tool use message with specific styling"""
        content = self.message.message.content
        if isinstance(content, list):
            for item in content:
                if item.get('type') == 'tool_use':
                    yield from self._render_tool_use_block(item)