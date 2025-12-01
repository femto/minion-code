#!/usr/bin/env python3
"""
Test script for the Messages component
Verifies that the Messages component can render a list of messages correctly
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Header, Footer, Button
from textual import on

# Import the components we want to test
from minion_code.components.Messages import Messages
from minion_code.type_defs import Message, MessageType, MessageContent


class TestMessagesApp(App):
    """Test application for Messages component"""
    
    CSS = """
    TestMessagesApp {
        background: $surface;
    }
    
    #test_container {
        height: 1fr;
        margin: 1;
    }
    
    #controls {
        dock: bottom;
        height: auto;
        margin: 1;
        
    }
    
    Button {
        margin: 1;
        min-width: 20;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.test_messages = []
        self._create_test_messages()
    
    def _create_test_messages(self):
        """Create some test messages"""
        import time
        
        # User message
        self.test_messages.append(Message(
            type=MessageType.USER,
            message=MessageContent("Hello, can you help me with Python?"),
            timestamp=time.time() - 60,
            options={}
        ))
        
        # Assistant message
        self.test_messages.append(Message(
            type=MessageType.ASSISTANT,
            message=MessageContent("Of course! I'd be happy to help you with Python. What specific topic or problem would you like assistance with?"),
            timestamp=time.time() - 50,
            options={}
        ))
        
        # User message with code
        self.test_messages.append(Message(
            type=MessageType.USER,
            message=MessageContent("How do I create a list comprehension?"),
            timestamp=time.time() - 40,
            options={}
        ))
        
        # Assistant message with code example
        self.test_messages.append(Message(
            type=MessageType.ASSISTANT,
            message=MessageContent("""List comprehensions are a concise way to create lists in Python. Here's the basic syntax:

```python
# Basic syntax: [expression for item in iterable]
numbers = [1, 2, 3, 4, 5]
squares = [x**2 for x in numbers]
print(squares)  # [1, 4, 9, 16, 25]

# With condition: [expression for item in iterable if condition]
even_squares = [x**2 for x in numbers if x % 2 == 0]
print(even_squares)  # [4, 16]
```

List comprehensions are more readable and often faster than traditional for loops for creating lists."""),
            timestamp=time.time() - 30,
            options={}
        ))
    
    def compose(self) -> ComposeResult:
        """Compose the test application"""
        yield Header(show_clock=True)
        
        with Container(id="test_container"):
            yield Messages(
                messages=self.test_messages,
                verbose=True,
                debug=True,
                id="test_messages"
            )
        
        with Horizontal(id="controls"):
            yield Button("Add User Message", id="add_user", variant="primary")
            yield Button("Add Assistant Message", id="add_assistant", variant="success")
            yield Button("Clear Messages", id="clear", variant="error")
        
        yield Footer()
    
    def on_mount(self):
        """Set up the application"""
        self.title = "Messages Component Test"
    
    @on(Button.Pressed, "#add_user")
    def add_user_message(self):
        """Add a test user message"""
        import time
        
        self.notify("Add User button clicked!")  # Debug
        
        new_message = Message(
            type=MessageType.USER,
            message=MessageContent(f"Test user message at {time.strftime('%H:%M:%S')}"),
            timestamp=time.time(),
            options={}
        )
        
        self.test_messages.append(new_message)
        self.notify(f"Added message, total: {len(self.test_messages)}")  # Debug
        
        # Update the Messages component using add_message method
        try:
            messages_component = self.query_one("#test_messages", expect_type=Messages)
            self.notify(f"Found messages component: {messages_component}")  # Debug
            # Use add_message method which uses mutate_reactive
            messages_component.add_message(new_message)
            self.notify("Messages updated successfully!")  # Debug
        except Exception as e:
            self.notify(f"Error updating messages: {e}")
    
    @on(Button.Pressed, "#add_assistant")
    def add_assistant_message(self):
        """Add a test assistant message"""
        import time
        
        new_message = Message(
            type=MessageType.ASSISTANT,
            message=MessageContent(f"Test assistant response at {time.strftime('%H:%M:%S')}. This is a longer message to test how the component handles different message lengths and formatting."),
            timestamp=time.time(),
            options={}
        )
        
        self.test_messages.append(new_message)
        
        # Update the Messages component using add_message method
        try:
            messages_component = self.query_one("#test_messages", expect_type=Messages)
            # Use add_message method which uses mutate_reactive
            messages_component.add_message(new_message)
        except Exception as e:
            self.notify(f"Error updating messages: {e}")
    
    @on(Button.Pressed, "#clear")
    def clear_messages(self):
        """Clear all messages"""
        self.test_messages = []
        
        # Update the Messages component using clear_messages method
        try:
            messages_component = self.query_one("#test_messages", expect_type=Messages)
            # Use clear_messages method which uses mutate_reactive
            messages_component.clear_messages()
        except Exception as e:
            self.notify(f"Error clearing messages: {e}")


if __name__ == "__main__":
    app = TestMessagesApp()
    app.run()