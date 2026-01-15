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

    DEFAULT_CSS = """
    MessageResponse {
        height: auto;
        width: 100%;
    }
    
    .message-response-container {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0;
        layers: first second;
    }
    
    .response-indicator {
        height: 1;
        width: auto;
        color: $text-muted;
        text-style: dim;
        margin: 0;
        padding: 0;
    }
    
    .response-content {
        width: 100%;
        height: auto;
        margin-left: 4;
        margin-top: 0;
        margin-bottom: 0;
        padding: 0;
    }
    
    .response-content > * {
        margin: 0;
        padding: 0;
        height: auto;
    }
    
    /* 移除Vertical容器的默认间距 */
    .response-content Vertical {
        margin: 0;
        padding: 0;
    }
    """

    def __init__(
        self,
        children: Optional[Union[Widget, List[Widget]]] = None,
        content: Optional[str] = None,
        **kwargs,
    ):
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
        from textual.containers import Vertical

        # 使用Vertical多层布局
        with Horizontal(classes="message-response-container"):
            # yield (Static("  ⎿", classes="response-indicator"))
            if self.children_widgets:

                for child in self.children_widgets:
                    yield child

    # def on_mount(self):
    #     print("mounting")
    #     pass
    def mount_child(self, widget: Widget):
        """
        Mount a child widget to the content area
        Equivalent to React's children mounting
        """
        content_area = self.query_one("#content-area", Container)
        content_area.mount(widget)

    def mount_children(self, widgets: List[Widget]):
        """Mount multiple child widgets"""
        for widget in widgets:
            self.mount_child(widget)

    def clear_children(self):
        """Clear all child widgets from content area"""
        content_area = self.query_one("#content-area", Container)
        for child in list(content_area.children):
            child.remove()


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
            "thinking": "🤔",
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
