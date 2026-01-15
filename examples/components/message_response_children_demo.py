#!/usr/bin/env python3
"""
Demo showing MessageResponse with children usage
Equivalent to React's <MessageResponse><Message /></MessageResponse> pattern
"""

import asyncio
import time
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Static

# Import the components
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from minion_code.components import Message, MessageResponse
from minion_code.type_defs import (
    Message as MessageType,
    MessageContent,
    MessageType as MsgType,
)


class MessageResponseChildrenDemo(App):
    """Demo showing MessageResponse children usage like React"""

    CSS = """
    Screen {
        background: $surface;
    }
    
    .demo-container {
        padding: 1;
        height: 100%;
    }
    
    .messages-container {
        height: 1fr;
        border: solid $primary;
        padding: 1;
        margin-bottom: 1;
    }
    
    .controls {
        height: auto;
        dock: bottom;
        padding: 1;
        background: $surface-lighten-1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the demo interface"""
        yield Header()

        with Container(classes="demo-container"):
            with ScrollableContainer(classes="messages-container", id="messages"):
                # Show examples of different usage patterns
                yield from self._create_usage_examples()

            # with Container(classes="controls"):
            #     yield Button("Add Tool Progress", id="add_tool_progress", variant="primary")
            #     yield Button("Add Nested Response", id="add_nested", variant="success")
            #     yield Button("Add Multiple Children", id="add_multiple", variant="warning")
            #     yield Button("Add Dynamic Mount", id="add_dynamic", variant="default")
            #     yield Button("Clear", id="clear", variant="error")

        yield Footer()
        self.log(self.tree)

    def _create_usage_examples(self):
        """Create examples showing different MessageResponse usage patterns"""
        child_msg = MessageType(
            type=MsgType.ASSISTANT,
            message=MessageContent("This message is wrapped in MessageResponse"),
            timestamp=time.time(),
        )
        yield Message(child_msg, classes="example-header")
        yield Static(
            "\n2. Single child message (React-like):", classes="example-header"
        )

        # This is equivalent to: <MessageResponse><Message /></MessageResponse>

        yield MessageResponse(children=[Message(child_msg, classes="example-header")])

        # Example 3: Tool execution progress
        yield Static("\n3. Tool execution progress:", classes="example-header")
        tool_msg = MessageType(
            type=MsgType.TOOL_USE,
            message=MessageContent(
                [
                    {
                        "type": "tool_use",
                        "id": "tool_demo",
                        "name": "file_editor",
                        "input": {"path": "demo.py", "content": "print('Hello')"},
                    }
                ]
            ),
            timestamp=time.time(),
        )
        yield MessageResponse(children=[Message(tool_msg, verbose=True)])

        # Example 4: Multiple children (using initialization)
        yield Static("\n4. Multiple children:", classes="example-header")

        # Add multiple children to demonstrate flexibility
        status_msg = MessageType(
            type=MsgType.ASSISTANT,
            message=MessageContent("Step 1: Analyzing code..."),
            timestamp=time.time(),
        )
        progress_msg = MessageType(
            type=MsgType.ASSISTANT,
            message=MessageContent("Step 2: Applying changes..."),
            timestamp=time.time(),
        )

        # Create with children during initialization
        yield MessageResponse(children=[Message(status_msg), Message(progress_msg)])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        messages_container = self.query_one("#messages", ScrollableContainer)

        if event.button.id == "add_tool_progress":
            self._add_tool_progress(messages_container)
        elif event.button.id == "add_nested":
            self._add_nested_response(messages_container)
        elif event.button.id == "add_multiple":
            self._add_multiple_children(messages_container)
        elif event.button.id == "add_dynamic":
            self._add_dynamic_mount(messages_container)
        elif event.button.id == "clear":
            self._clear_messages(messages_container)

    def _add_tool_progress(self, container):
        """Add tool execution progress using MessageResponse + Message"""
        # Simulate tool execution progress
        tool_msg = MessageType(
            type=MsgType.ASSISTANT,
            message=MessageContent("🔧 Executing file operation..."),
            timestamp=time.time(),
        )

        # Create MessageResponse with child during initialization
        response = MessageResponse(children=[Message(tool_msg)])

        container.mount(response)
        container.scroll_end()

    def _add_nested_response(self, container):
        """Add nested MessageResponse (response within response)"""
        # Create outer message
        outer_msg = MessageType(
            type=MsgType.ASSISTANT,
            message=MessageContent("Starting complex operation..."),
            timestamp=time.time(),
        )

        # Create inner message for sub-operation
        inner_msg = MessageType(
            type=MsgType.ASSISTANT,
            message=MessageContent("  └─ Sub-operation in progress..."),
            timestamp=time.time(),
        )

        # Create nested structure with initialization
        inner_response = MessageResponse(children=[Message(inner_msg)])
        outer_response = MessageResponse(children=[Message(outer_msg), inner_response])

        container.mount(outer_response)
        container.scroll_end()

    def _add_multiple_children(self, container):
        """Add MessageResponse with multiple child messages"""
        # Create multiple related messages
        messages = [
            MessageType(
                type=MsgType.ASSISTANT,
                message=MessageContent(f"Processing step {i+1}/3..."),
                timestamp=time.time(),
            )
            for i in range(3)
        ]

        # Create MessageResponse with multiple children during initialization
        message_widgets = [Message(msg) for msg in messages]
        response = MessageResponse(children=message_widgets)

        container.mount(response)
        container.scroll_end()

    def _add_dynamic_mount(self, container):
        """Add MessageResponse and then dynamically mount children after it's mounted"""
        # Create empty MessageResponse first
        response = MessageResponse(content="Dynamic mounting example:")

        # Mount it to the container
        container.mount(response)

        # Use call_after_refresh to mount children after the component is fully mounted
        def mount_children_after():
            msg = MessageType(
                type=MsgType.ASSISTANT,
                message=MessageContent("This was added dynamically after mounting!"),
                timestamp=time.time(),
            )
            response.mount_child(Message(msg))

        # Schedule the dynamic mounting
        self.call_after_refresh(mount_children_after)
        container.scroll_end()

    def _clear_messages(self, container):
        """Clear all messages except headers"""
        for child in list(container.children)[2:]:  # Keep title and subtitle
            child.remove()


def main():
    """Run the demo application"""
    app = MessageResponseChildrenDemo()
    app.run()


if __name__ == "__main__":
    main()
