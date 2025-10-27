"""
MessageResponse Component - Python equivalent of React MessageResponse component
Provides visual indentation for tool execution progress messages
"""

from textual.containers import Container, Horizontal
from textual.widgets import Static
from textual.widget import Widget
from rich.text import Text
from typing import Any, Optional, List, Union


class MessageResponse(Container):
    """
    MessageResponse component equivalent to React MessageResponse
    Provides visual indentation with "⎿" indicator for children widgets
    
    Usage:
        # With direct content
        response = MessageResponse(content="Operation completed")
        
        # With child widgets (like React children)
        response = MessageResponse()
        response.mount(Message(...))  # Mount child widgets
        
        # Or pass children during initialization
        response = MessageResponse(children=[message_widget, status_widget])
    """
    
    CSS = """
    MessageResponse {
        height: auto;
        width: 100%;
        overflow: hidden;
    }
    
    .response-indicator {
        width: auto;
        color: $text-muted;
        text-style: dim;
        dock: left;
    }
    
    .response-content {
        width: 1fr;
        margin-left: 1;
    }
    """
    
    def __init__(self, 
                 children: Optional[Union[Widget, List[Widget]]] = None,
                 content: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.children_widgets = []
        self.content = content
        
        # Handle children parameter
        if children:
            if isinstance(children, list):
                self.children_widgets = children
            else:
                self.children_widgets = [children]
    
    def compose(self):
        """Compose the MessageResponse interface"""
        with Horizontal():
            # Response indicator - equivalent to "  ⎿ &nbsp;"
            yield Static("  ⎿ ", classes="response-indicator")
            
            # Content container
            with Container(classes="response-content", id="content-area"):
                # If we have direct content, show it
                if self.content:
                    yield Static(self.content)
                
                # Mount any children widgets passed during initialization
                for child in self.children_widgets:
                    yield child
    
    def mount_child(self, widget: Widget):
        """
        Mount a child widget to the content area
        Equivalent to React's children mounting
        """
        try:
            content_area = self.query_one("#content-area", Container)
            content_area.mount(widget)
        except Exception:
            # If content area doesn't exist yet, add to pending children
            if not hasattr(self, '_pending_children'):
                self._pending_children = []
            self._pending_children.append(widget)
    
    def mount_children(self, widgets: List[Widget]):
        """Mount multiple child widgets"""
        for widget in widgets:
            self.mount_child(widget)
    
    def clear_children(self):
        """Clear all child widgets from content area"""
        try:
            content_area = self.query_one("#content-area", Container)
            for child in list(content_area.children):
                child.remove()
        except Exception:
            # If content area doesn't exist, clear pending children
            if hasattr(self, '_pending_children'):
                self._pending_children.clear()
    
    def on_mount(self):
        """Handle mounting of pending children when component is mounted"""
        if hasattr(self, '_pending_children') and self._pending_children:
            try:
                content_area = self.query_one("#content-area", Container)
                for widget in self._pending_children:
                    content_area.mount(widget)
                self._pending_children.clear()
            except Exception:
                pass  # Will try again later


class MessageResponseText(MessageResponse):
    """Specialized MessageResponse for text content"""
    
    def __init__(self, text: str, **kwargs):
        super().__init__(content=text, **kwargs)


class MessageResponseStatus(MessageResponse):
    """Specialized MessageResponse for status messages"""
    
    def __init__(self, status: str, message: str = "", **kwargs):
        status_icons = {
            "loading": "⏳",
            "success": "✅", 
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "thinking": "🤔"
        }
        
        icon = status_icons.get(status, "•")
        content = f"{icon} {message}" if message else icon
        
        super().__init__(content=content, **kwargs)


class MessageResponseProgress(MessageResponse):
    """Specialized MessageResponse for progress indicators"""
    
    def __init__(self, current: int, total: int, message: str = "", **kwargs):
        progress_text = f"[{current}/{total}]"
        if message:
            progress_text += f" {message}"
        
        super().__init__(content=progress_text, **kwargs)


class MessageResponseTyping(MessageResponse):
    """Specialized MessageResponse for typing indicators"""
    
    def __init__(self, **kwargs):
        super().__init__(content="typing...", **kwargs)
        
    def on_mount(self):
        """Start typing animation when mounted"""
        self._animate_typing()
    
    def _animate_typing(self):
        """Simple typing animation"""
        # This could be enhanced with actual animation
        # For now, just show static typing indicator
        pass


class MessageResponseWithChildren(MessageResponse):
    """
    Specialized MessageResponse that demonstrates children usage
    Equivalent to React's <MessageResponse><Message /></MessageResponse>
    """
    
    def __init__(self, message_widget: Widget, **kwargs):
        # Pass the message widget as a child
        super().__init__(children=[message_widget], **kwargs)