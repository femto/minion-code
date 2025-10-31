"""
Messages Component - Python equivalent of React Messages component
Renders a list of messages in the REPL interface
"""

from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import Static
from textual.reactive import reactive, var
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

# Import shared types and components
from ..types import Message as MessageType, MessageContent, InputMode
from .Message import Message, UserMessage, AssistantMessage, ToolUseMessage


class Messages(ScrollableContainer):
    """
    Messages container component equivalent to React Messages component
    Renders a list of messages with proper scrolling and layout
    """
    
    DEFAULT_CSS = """
    Messages {
        height: 1fr;
        width: 100%;
        margin: 1;
        padding: 1;
        scrollbar-background: $surface-lighten-1;
        scrollbar-color: $primary;
    }
    
    .messages-container {
        width: 100%;
        height: auto;
    }
    
    .empty-state {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
        text-style: dim;
    }
    
    .message-item {
        width: 100%;
        margin-bottom: 1;
    }
    """
    
    # Reactive properties
    messages = reactive(list, recompose=True)  # List[MessageType]
    #messages = vars(list)  # List[MessageType]
    
    def __init__(self,
                 messages: List[MessageType] = None,
                 tools: List[Any] = None,
                 verbose: bool = False,
                 debug: bool = False,
                 errored_tool_use_ids: Set[str] = None,
                 in_progress_tool_use_ids: Set[str] = None,
                 unresolved_tool_use_ids: Set[str] = None,
                 should_animate: bool = False,
                 auto_scroll: bool = True,
                 **kwargs):
        super().__init__(**kwargs)
        
        # Props equivalent to TypeScript Props interface
        self._initial_messages = messages or []
        print(f"DEBUG: Messages component initialized with {len(self._initial_messages)} initial messages")
        self.tools = tools or []
        self.verbose = verbose
        self.debug = debug
        self.errored_tool_use_ids = errored_tool_use_ids or set()
        self.in_progress_tool_use_ids = in_progress_tool_use_ids or set()
        self.unresolved_tool_use_ids = unresolved_tool_use_ids or set()
        self.should_animate = should_animate
        self.auto_scroll = auto_scroll
        
        # Internal state
        self._last_message_count = 0
        self._is_mounted = False
        
        # Set messages after initialization to avoid watch_messages being called too early
        if self._initial_messages:
            self.messages = self._initial_messages.copy()
    
    def compose(self):
        """Compose the messages interface - equivalent to React render method"""
        print(f"DEBUG: Messages.compose() called with {len(self.messages)} messages")
        if not self.messages:
            # Empty state - equivalent to showing placeholder when no messages
            print("DEBUG: Showing empty state")
            yield Static(
                "💬 Start a conversation by typing a message below...",
                classes="empty-state"
            )
        else:
            # Messages container
            print(f"DEBUG: Rendering {len(self.messages)} messages")
            with Vertical(classes="messages-container"):
                for i, message in enumerate(self.messages):
                    print(f"DEBUG: Creating message widget {i}: {message.type}")
                    yield self._create_message_widget(message, i)
    
    def on_mount(self):
        """Called when the widget is mounted"""
        self._is_mounted = True
        # Now it's safe to update the display if needed
        if self.messages != self._initial_messages:
            self._update_display()
    
    def _create_message_widget(self, message: MessageType, index: int) -> Message:
        """Create a message widget based on message type"""
        
        # Common props for all message types
        message_props = {
            "message": message,
            "messages": self.messages,
            "tools": self.tools,
            "verbose": self.verbose,
            "debug": self.debug,
            "errored_tool_use_ids": self.errored_tool_use_ids,
            "in_progress_tool_use_ids": self.in_progress_tool_use_ids,
            "unresolved_tool_use_ids": self.unresolved_tool_use_ids,
            "should_animate": self.should_animate,
            "classes": "message-item",
            "id": f"message_{index}"
        }
        
        # Create appropriate message component based on type
        if message.type.value == "user":
            return UserMessage(**message_props)
        elif message.type.value == "assistant":
            # Check if this is a tool use message
            if self._is_tool_use_message(message):
                return ToolUseMessage(**message_props)
            else:
                return AssistantMessage(**message_props)
        else:
            # Default to generic Message component
            return Message(**message_props)
    
    def _is_tool_use_message(self, message: MessageType) -> bool:
        """Check if message contains tool use content"""
        content = message.message.content
        if isinstance(content, list):
            return any(
                isinstance(item, dict) and item.get('type') == 'tool_use'
                for item in content
            )
        return False
    
    def add_message(self, message: MessageType):
        """Add a new message to the list"""
        self.messages.append(message)
        self.mutate_reactive(Messages.messages)
        
        if self.auto_scroll:
            self.call_later(self._scroll_to_bottom)
    
    def update_messages(self, messages: List[MessageType]):
        """Update the entire messages list"""
        # Clear and replace all messages
        self.messages = messages
        self.mutate_reactive(Messages.messages)

        
        # Auto-scroll if new messages were added
        if len(messages) > self._last_message_count and self.auto_scroll:
            self.call_later(self._scroll_to_bottom)
        
        self._last_message_count = len(messages)
    
    def update_streaming_message(self, message_index: int, new_content: str):
        """Update a streaming message at specific index"""
        if 0 <= message_index < len(self.messages):
            # Update the message content
            self.messages[message_index].message.content = new_content
            
            # Find and update the corresponding widget
            try:
                message_widget = self.query_one(f"#message_{message_index}")
                if hasattr(message_widget, 'update_streaming_content'):
                    message_widget.update_streaming_content(new_content)
            except Exception:
                pass  # Widget might not exist yet
    
    def finalize_streaming_message(self, message_index: int, final_content: str):
        """Finalize a streaming message with final content"""
        if 0 <= message_index < len(self.messages):
            # Update the message content and remove streaming flag
            message = self.messages[message_index]
            message.message.content = final_content
            if message.options:
                message.options.pop("streaming", None)
            
            # Find and update the corresponding widget
            try:
                message_widget = self.query_one(f"#message_{message_index}")
                if hasattr(message_widget, 'finalize_streaming'):
                    message_widget.finalize_streaming(final_content)
            except Exception:
                pass  # Widget might not exist yet
    
    def clear_messages(self):
        """Clear all messages"""
        self.messages = []
        self.mutate_reactive(Messages.messages)
    
    def _update_display(self):
        """Update the display when messages change"""
        # Use recompose to rebuild the entire widget tree
        self.recompose()
    
    def _scroll_to_bottom(self):
        """Scroll to the bottom of the messages container"""
        try:
            self.scroll_end(animate=True)
        except Exception:
            pass  # Silently handle scroll errors
    
    def get_message_count(self) -> int:
        """Get the current number of messages"""
        return len(self.messages)
    
    def get_last_message(self) -> Optional[MessageType]:
        """Get the last message in the list"""
        return self.messages[-1] if self.messages else None
    
    def get_messages_by_type(self, message_type: str) -> List[MessageType]:
        """Get all messages of a specific type"""
        return [msg for msg in self.messages if msg.type.value == message_type]
    
    def find_message_by_id(self, message_id: str) -> Optional[MessageType]:
        """Find a message by its ID"""
        for message in self.messages:
            if hasattr(message, 'id') and message.id == message_id:
                return message
        return None
    
    # Reactive property watchers
    def watch_messages(self, messages: List[MessageType]):
        """Watch for changes to the messages list"""
        # Only update display if the widget is mounted
        if self._is_mounted:
            self._update_display()
            
            # Auto-scroll if new messages were added
            if len(messages) > self._last_message_count and self.auto_scroll:
                self.call_later(self._scroll_to_bottom)
        
        self._last_message_count = len(messages)


class MessagesWithStatus(Container):
    """
    Messages container with status indicators
    Equivalent to a more advanced Messages component with loading states
    """
    
    DEFAULT_CSS = """
    MessagesWithStatus {
        height: 1fr;
        width: 100%;
    }
    
    .status-bar {
        dock: bottom;
        height: 1;
        background: $surface-lighten-1;
        content-align: center middle;
        color: $text-muted;
    }
    
    .typing-indicator {
        color: $primary;
        text-style: italic;
    }
    
    .error-indicator {
        color: $error;
        text-style: bold;
    }
    """
    
    def __init__(self,
                 messages: List[MessageType] = None,
                 is_loading: bool = False,
                 error_message: Optional[str] = None,
                 typing_indicator: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        
        self.messages = messages or []
        self.is_loading = is_loading
        self.error_message = error_message
        self.typing_indicator = typing_indicator
    
    def compose(self):
        """Compose messages with status bar"""
        # Main messages component
        yield Messages(
            messages=self.messages,
            id="main_messages"
        )
        
        # Status bar
        yield self._render_status_bar()
    
    def _render_status_bar(self) -> Static:
        """Render the status bar based on current state"""
        if self.error_message:
            return Static(
                f"❌ {self.error_message}",
                classes="status-bar error-indicator"
            )
        elif self.is_loading:
            return Static(
                "⠋ Assistant is thinking...",
                classes="status-bar typing-indicator"
            )
        elif self.typing_indicator:
            return Static(
                f"⌨️ {self.typing_indicator}",
                classes="status-bar typing-indicator"
            )
        else:
            return Static("", classes="status-bar")
    
    def update_status(self, is_loading: bool = None, error_message: str = None, typing_indicator: str = None):
        """Update the status indicators"""
        if is_loading is not None:
            self.is_loading = is_loading
        if error_message is not None:
            self.error_message = error_message
        if typing_indicator is not None:
            self.typing_indicator = typing_indicator
        
        # Update status bar
        try:
            status_bar = self.query_one(".status-bar")
            new_status_bar = self._render_status_bar()
            status_bar.update(new_status_bar.renderable)
        except Exception:
            pass  # Status bar might not be mounted yet