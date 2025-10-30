"""
REPL Screen Implementation using Textual UI Components
Python equivalent of /Users/femtozheng/web-project/Kode/src/screens/REPL.tsx
Simulates React-like component structure as documented in AGENTS.md
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Input, RichLog, Button, Static, Header, Footer, Label, TextArea
from textual.reactive import reactive, var
from textual import on, work
from textual.screen import Screen
from rich.text import Text
from rich.syntax import Syntax
from rich.console import Console
import asyncio
from typing import List, Dict, Any, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
import time
from pathlib import Path

# Setup TUI-friendly logging - removes console output to prevent UI interference
from ..utils.logs import setup_tui_logging
logger = setup_tui_logging()


# Import shared types
from ..types import (
    MessageType, InputMode, MessageContent, Message, 
    ToolUseConfirm, BinaryFeedbackContext, ToolJSXContext, 
    REPLConfig, ModelInfo
)


class Logo(Static):
    """Logo component equivalent to React Logo component"""
    
    def __init__(self, mcp_clients=None, is_default_model=True, update_banner_version=None, **kwargs):
        super().__init__(**kwargs)
        self.mcp_clients = mcp_clients or []
        self.is_default_model = is_default_model
        self.update_banner_version = update_banner_version
    
    def render(self) -> str:
        logo_text = "🤖 Minion Code Assistant"
        if self.update_banner_version:
            logo_text += f" (Update available: {self.update_banner_version})"
        return logo_text

class ModeIndicator(Static):
    """Mode indicator component"""
    
    def __init__(self, mode: InputMode = InputMode.PROMPT, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
    
    def render(self) -> str:
        return f"Mode: {self.mode.value.upper()}"

class Spinner(Static):
    """Loading spinner component"""
    
    def __init__(self, **kwargs):
        super().__init__("⠋ Loading...", **kwargs)
        self.auto_refresh = 0.1
        self.spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        self.spinner_index = 0
    
    def on_mount(self):
        self.set_interval(0.1, self.update_spinner)
    
    def update_spinner(self):
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
        self.update(f"{self.spinner_chars[self.spinner_index]} Loading...")

class MessageWidget(Container):
    """Individual message display widget with streaming support"""
    
    def __init__(self, message: Message, verbose: bool = False, debug: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.verbose = verbose
        self.debug = debug
        self.is_streaming = message.options.get("streaming", False) if message.options else False
        self.is_error = message.options.get("error", False) if message.options else False
    
    def compose(self) -> ComposeResult:
        content_text = self._get_content_text()
        
        if self.message.type == MessageType.USER:
            yield Static(f"👤 User:", classes="user-label")
            yield Static(content_text, classes="user-message")
        elif self.message.type == MessageType.ASSISTANT:
            if self.is_streaming:
                yield Static(f"🤖 Assistant: ⠋ Thinking...", classes="assistant-streaming")
            elif self.is_error:
                yield Static(f"❌ Assistant:", classes="assistant-error-label")
                yield Static(content_text, classes="assistant-error")
            else:
                yield Static(f"🤖 Assistant:", classes="assistant-label")
                # Handle markdown content
                if "```" in content_text or content_text.startswith("#"):
                    from rich.markdown import Markdown
                    yield Static(Markdown(content_text), classes="assistant-message")
                else:
                    yield Static(content_text, classes="assistant-message")
        elif self.message.type == MessageType.PROGRESS:
            yield Static(f"⚙️ Progress:", classes="progress-label")
            yield Static(content_text, classes="progress-message")
    
    def _get_content_text(self) -> str:
        if isinstance(self.message.message.content, str):
            return self.message.message.content
        elif isinstance(self.message.message.content, list):
            # Extract text from structured content
            text_parts = []
            for block in self.message.message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "\n".join(text_parts)
        return str(self.message.message.content)
    
    def update_streaming_content(self, new_content: str):
        """Update streaming message content"""
        if self.is_streaming:
            try:
                # Update the message content
                self.message.message.content = new_content
                # Find and update the static widget
                static_widgets = self.query("Static")
                if len(static_widgets) > 1:
                    static_widgets[1].update(new_content)
            except Exception as e:
                logger.warning(f"Failed to update streaming content: {e}")
    
    def finalize_streaming(self, final_content: str):
        """Finalize streaming message with final content"""
        if self.is_streaming:
            self.is_streaming = False
            self.message.options["streaming"] = False
            self.message.message.content = final_content
            # Refresh the entire widget
            self.refresh()


# PromptInput moved to components/PromptInput.py
from ..components.PromptInput import PromptInput

class CostThresholdDialog(Container):
    """Cost threshold warning dialog"""
    
    def compose(self) -> ComposeResult:
        yield Static("⚠️ Cost Threshold Warning", classes="dialog-title")
        yield Static("You have exceeded $5 in API costs. Please be mindful of usage.")
        yield Button("Acknowledge", id="acknowledge_btn", variant="primary")

class PermissionRequest(Container):
    """Permission request dialog for tool usage"""
    
    def __init__(self, tool_use_confirm: ToolUseConfirm, **kwargs):
        super().__init__(**kwargs)
        self.tool_use_confirm = tool_use_confirm
    
    def compose(self) -> ComposeResult:
        yield Static(f"🔧 Tool Permission Request", classes="dialog-title")
        yield Static(f"Tool: {self.tool_use_confirm.tool_name}")
        yield Static(f"Parameters: {self.tool_use_confirm.parameters}")
        with Horizontal():
            yield Button("Allow", id="allow_btn", variant="success")
            yield Button("Deny", id="deny_btn", variant="error")
    
    @on(Button.Pressed, "#allow_btn")
    def allow_tool(self):
        self.tool_use_confirm.on_confirm()
    
    @on(Button.Pressed, "#deny_btn")
    def deny_tool(self):
        self.tool_use_confirm.on_abort()


class MessageSelector(Container):
    """Message selector for conversation forking"""
    
    def __init__(self, messages: List[Message], **kwargs):
        super().__init__(**kwargs)
        self.messages = messages
    
    def compose(self) -> ComposeResult:
        yield Static("📝 Select Message to Fork From", classes="dialog-title")
        with ScrollableContainer():
            for i, message in enumerate(self.messages[-10:]):  # Show last 10 messages
                content = self._get_message_preview(message)
                yield Button(f"{i}: {content[:50]}...", id=f"msg_{i}")
        yield Button("Cancel", id="cancel_selector", variant="error")
    
    def _get_message_preview(self, message: Message) -> str:
        if isinstance(message.message.content, str):
            return message.message.content
        return str(message.message.content)[:50]


class REPL(Container):
    """
    Main REPL Component - Python equivalent of React REPL component
    Manages the entire conversation interface with AI assistant
    """
    
    # Reactive properties equivalent to React useState
    fork_number = reactive(0)
    is_loading = reactive(False)
    messages = var(list)  # List[Message]
    input_value = reactive("")
    input_mode = reactive(InputMode.PROMPT)
    submit_count = reactive(0)
    is_message_selector_visible = reactive(False)
    show_cost_dialog = reactive(False)
    have_shown_cost_dialog = reactive(False)
    
    def __init__(self, 
                 commands=None,
                 safe_mode=False,
                 debug=False,
                 initial_fork_number=0,
                 initial_prompt=None,
                 message_log_name="default",
                 should_show_prompt_input=True,
                 tools=None,
                 verbose=False,
                 initial_messages=None,
                 mcp_clients=None,
                 is_default_model=True,
                 initial_update_version=None,
                 initial_update_commands=None,
                 agent=None,  # Agent passed from app level
                 **kwargs):
        super().__init__(**kwargs)
        
        # Props equivalent to TypeScript Props interface
        self.commands = commands or []
        self.safe_mode = safe_mode
        self.debug = debug
        self.initial_fork_number = initial_fork_number
        self.initial_prompt = initial_prompt
        self.message_log_name = message_log_name
        self.should_show_prompt_input = should_show_prompt_input
        self.tools = tools or []
        self.verbose = verbose
        self.mcp_clients = mcp_clients or []
        self.is_default_model = is_default_model
        self.initial_update_version = initial_update_version
        self.initial_update_commands = initial_update_commands
        
        # Initialize state
        self.messages = initial_messages or []
        self.fork_number = initial_fork_number
        
        # Agent from app level
        self.agent = agent
        
        # Internal state
        self.config = REPLConfig()
        self.abort_controller: Optional[asyncio.Task] = None
        self.tool_jsx: Optional[ToolJSXContext] = None
        self.tool_use_confirm: Optional[ToolUseConfirm] = None
        self.binary_feedback_context: Optional[BinaryFeedbackContext] = None
        self.read_file_timestamps: Dict[str, float] = {}
        self.fork_convo_with_messages_on_next_render: Optional[List[Message]] = None
        
        logger.info(f"REPL initialized with {len(self.messages)} initial messages")
    
    def compose(self) -> ComposeResult:
        """Compose the REPL interface - equivalent to React render method"""
        # Static header section (equivalent to Static items in React)
        with Vertical():
            yield Logo(
                mcp_clients=self.mcp_clients,
                is_default_model=self.is_default_model,
                update_banner_version=self.initial_update_version
            )
            # ModeIndicator removed - mode is shown in PromptInput prefix
            
            # Messages container (equivalent to messagesJSX mapping)
            with ScrollableContainer(id="messages_container"):
                for message in self.messages:
                    yield MessageWidget(
                        message=message,
                        verbose=self.verbose,
                        debug=self.debug
                    )
            
            # Dynamic content area (equivalent to conditional rendering in React)
            with Container(id="dynamic_content"):
                # Spinner (equivalent to {!toolJSX && !toolUseConfirm && !binaryFeedbackContext && isLoading && <Spinner />})
                if self.is_loading and not self.tool_jsx and not self.tool_use_confirm and not self.binary_feedback_context:
                    yield Spinner()
                
                # Tool JSX (equivalent to {toolJSX ? toolJSX.jsx : null})
                if self.tool_jsx and self.tool_jsx.jsx:
                    yield self.tool_jsx.jsx
                
                # Binary feedback (equivalent to BinaryFeedback component)
                if self.binary_feedback_context and not self.is_message_selector_visible:
                    yield Static("🔄 Binary feedback component would render here")
                
                # Permission request (equivalent to PermissionRequest component)
                if self.tool_use_confirm and not self.is_message_selector_visible and not self.binary_feedback_context:
                    yield PermissionRequest(self.tool_use_confirm)
                
                # Cost dialog (equivalent to CostThresholdDialog component)
                if self.show_cost_dialog and not self.is_loading:
                    yield CostThresholdDialog()
                
                # PromptInput component (now working)
                if True:  # Always show for now
                    prompt_input = PromptInput(
                        commands=self.commands,
                        fork_number=self.fork_number,
                        message_log_name=self.message_log_name,
                        is_disabled=False,
                        is_loading=self.is_loading,
                        debug=self.debug,
                        verbose=self.verbose,
                        messages=self.messages,
                        tools=self.tools,
                        input_value=self.input_value,
                        mode=self.input_mode,
                        submit_count=self.submit_count,
                        read_file_timestamps=self.read_file_timestamps,
                        abort_controller=self.abort_controller
                    )
                    
                    # Set up callbacks
                    prompt_input.on_query = self.on_query_from_prompt
                    prompt_input.on_input_change = self.on_input_change_from_prompt
                    prompt_input.on_mode_change = self.on_mode_change_from_prompt
                    prompt_input.on_submit_count_change = self.on_submit_count_change_from_prompt
                    prompt_input.set_is_loading = self.set_loading_from_prompt
                    prompt_input.set_abort_controller = self.set_abort_controller_from_prompt
                    prompt_input.on_show_message_selector = self.show_message_selector
                    prompt_input.set_fork_convo_with_messages = self.set_fork_convo_messages
                    prompt_input.on_model_change = self.on_model_change_from_prompt
                    prompt_input.set_tool_jsx = self.set_tool_jsx_from_prompt
                    
                    yield prompt_input
            
            # Message selector (equivalent to {isMessageSelectorVisible && <MessageSelector />})
            if self.is_message_selector_visible:
                yield MessageSelector(messages=self.messages)
    
    def on_mount(self):
        """Component lifecycle - equivalent to React useEffect(() => { onInit() }, [])"""
        logger.info("REPL mounted, starting initialization")
        self.call_later(self.on_init)
        # Set focus to the input after a short delay to ensure it's mounted
        self.set_timer(0.1, self._set_focus_to_input)
    
    def _set_focus_to_input(self):
        """Set focus to the main input widget"""
        try:
            # Try to find the main TextArea input
            input_widget = self.query_one("#main_input", expect_type=TextArea)
            input_widget.focus()
            logger.info("Focus set to main TextArea input from REPL")
        except Exception as e:
            logger.warning(f"Could not set focus to main input: {e}")
            # If that fails, try to focus any TextArea or Input widget
            try:
                text_areas = self.query("TextArea")
                if text_areas:
                    text_areas[0].focus()
                    logger.info("Focus set to first available TextArea")
                else:
                    inputs = self.query("Input")
                    if inputs:
                        inputs[0].focus()
                        logger.info("Focus set to first available Input")
            except Exception as e2:
                logger.warning(f"Could not set focus to any input: {e2}")
    
    async def on_init(self):
        """Initialize REPL - equivalent to React onInit function"""
        logger.info("REPL initialization started")
        
        if not self.initial_prompt:
            logger.info("No initial prompt provided")
            return
        
        self.is_loading = True
        
        try:
            # Process initial prompt (equivalent to processUserInput)
            new_messages = await self.process_user_input(
                self.initial_prompt,
                self.input_mode
            )
            
            if new_messages:
                # Add to history (equivalent to addToHistory)
                self.add_to_history(self.initial_prompt)
                
                # Update messages (equivalent to setMessages)
                self.messages = [*self.messages, *new_messages]
                
                # Query API if needed (equivalent to query function)
                await self.query_api(new_messages)
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
        finally:
            self.is_loading = False
            logger.info("REPL initialization completed")
    
    async def process_user_input(self, input_text: str, mode: InputMode) -> List[Message]:
        """Process user input - equivalent to processUserInput function"""
        logger.info(f"Processing user input: {input_text[:50]}... (mode: {mode.value})")
        
        # Create user message
        user_message = Message(
            type=MessageType.USER,
            message=MessageContent(input_text),
            options={"isKodingRequest": mode == InputMode.KODING}
        )
        
        # Handle different input modes
        if mode == InputMode.BASH:
            # Handle bash command
            result = await self.execute_bash_command(input_text)
            assistant_message = Message(
                type=MessageType.ASSISTANT,
                message=MessageContent(result)
            )
            return [user_message, assistant_message]
        elif mode == InputMode.KODING:
            # Handle koding request
            return [user_message]
        else:
            # Handle regular prompt
            return [user_message]
    
    async def execute_bash_command(self, command: str) -> str:
        """Execute bash command - simplified version"""
        try:
            import subprocess
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout or "Command executed successfully"
            else:
                return f"Error: {result.stderr}"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def set_agent(self, agent):
        """Set agent from app level"""
        self.agent = agent
        logger.info("Agent set from app level")
    
    async def query_api(self, new_messages: List[Message]):
        """Query the AI API with streaming support - equivalent to query function"""
        logger.info("Querying AI API with streaming")
        
        if not new_messages or new_messages[-1].type != MessageType.USER:
            return
        
        user_content = new_messages[-1].message.content
        if not isinstance(user_content, str):
            return
        
        # Check if agent is available
        if not self.agent:
            error_message = Message(
                type=MessageType.ASSISTANT,
                message=MessageContent("❌ Agent not initialized yet. Please wait..."),
                options={"error": True}
            )
            self.messages = [*self.messages, error_message]
            return
        
        try:
            # Set loading state
            self.is_loading = True
            
            # Create streaming response container
            streaming_message = Message(
                type=MessageType.ASSISTANT,
                message=MessageContent("⠋ Thinking..."),
                options={"streaming": True}
            )
            self.messages = [*self.messages, streaming_message]
            
            # Refresh UI to show streaming message
            self.refresh()
            
            # Process with agent - check if it supports streaming
            try:
                # Try to use streaming if available
                if hasattr(self.agent, 'run_async') and hasattr(self.agent.run_async, '__code__'):
                    # Check if run_async supports stream parameter
                    import inspect
                    sig = inspect.signature(self.agent.run_async)
                    if 'stream' in sig.parameters:
                        # Use streaming
                        accumulated_response = ""
                        async for chunk in self.agent.run_async(user_content, stream=True):
                            if hasattr(chunk, 'answer'):
                                accumulated_response += chunk.answer
                            elif isinstance(chunk, str):
                                accumulated_response += chunk
                            
                            # Update streaming message
                            streaming_message.message.content = accumulated_response
                            self.refresh()
                        
                        # Finalize with accumulated response
                        final_content = accumulated_response
                    else:
                        # No streaming support, use regular call
                        response = await self.agent.run_async(user_content)
                        final_content = response.answer if hasattr(response, 'answer') else str(response)
                else:
                    # Fallback to regular call
                    response = await self.agent.run_async(user_content)
                    final_content = response.answer if hasattr(response, 'answer') else str(response)
                
                # Update the streaming message with final response
                final_message = Message(
                    type=MessageType.ASSISTANT,
                    message=MessageContent(final_content),
                    options={"streaming": False}
                )
                
                # Replace the streaming message with final message
                self.messages = [*self.messages[:-1], final_message]
                
                # Handle Koding mode special case
                if (new_messages[-1].options and 
                    new_messages[-1].options.get("isKodingRequest")):
                    await self.handle_koding_response(final_message)
                    
            except Exception as e:
                logger.error(f"Agent processing error: {e}")
                
                # Format error message for UI display
                error_text = self._format_error_for_ui(e)
                
                error_message = Message(
                    type=MessageType.ASSISTANT,
                    message=MessageContent(error_text),
                    options={"error": True}
                )
                # Replace streaming message with error
                self.messages = [*self.messages[:-1], error_message]
                
        except Exception as e:
            logger.error(f"Query API error: {e}")
            
            # Show error message to user
            error_text = self._format_error_for_ui(e)
            error_message = Message(
                type=MessageType.ASSISTANT,
                message=MessageContent(error_text),
                options={"error": True}
            )
            
            # Replace streaming message with error or add new error message
            if self.messages and self.messages[-1].options.get("streaming"):
                self.messages = [*self.messages[:-1], error_message]
            else:
                self.messages = [*self.messages, error_message]
                
        finally:
            self.is_loading = False
    
    async def handle_koding_response(self, assistant_message: Message):
        """Handle Koding mode response - equivalent to handleHashCommand"""
        logger.info("Handling Koding response")
        
        content = assistant_message.message.content
        if isinstance(content, str) and content.strip():
            # Save to AGENTS.md (equivalent to handleHashCommand)
            try:
                agents_md_path = Path("AGENTS.md")
                if agents_md_path.exists():
                    with open(agents_md_path, "a") as f:
                        f.write(f"\n\n## Koding Response - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(content)
                        f.write("\n")
                    logger.info("Saved Koding response to AGENTS.md")
            except Exception as e:
                logger.error(f"Error saving to AGENTS.md: {e}")
    
    def add_to_history(self, command: str):
        """Add command to history - equivalent to addToHistory"""
        # This would integrate with the history system
        logger.info(f"Added to history: {command[:50]}...")
    
    def on_cancel(self):
        """Cancel current operation - equivalent to onCancel function"""
        if not self.is_loading:
            return
        
        self.is_loading = False
        
        if self.tool_use_confirm:
            self.tool_use_confirm.on_abort()
        elif self.abort_controller:
            self.abort_controller.cancel()
        
        logger.info("Operation cancelled")
    
    # Callback methods for PromptInput component
    async def on_query_from_prompt(self, messages: List[Message], abort_controller=None):
        """Handle query from PromptInput - equivalent to onQuery prop"""
        logger.info(f"Received query from PromptInput with {len(messages)} messages")
        
        # Use passed AbortController or create new one
        controller_to_use = abort_controller or asyncio.create_task(asyncio.sleep(0))
        if not abort_controller:
            self.abort_controller = controller_to_use
        
        # Update messages
        self.messages = [*self.messages, *messages]
        
        # Query API
        await self.query_api(messages)
    
    def on_input_change_from_prompt(self, value: str):
        """Handle input change from PromptInput"""
        self.input_value = value
    
    def on_mode_change_from_prompt(self, mode: InputMode):
        """Handle mode change from PromptInput"""
        self.input_mode = mode
    
    def on_submit_count_change_from_prompt(self, updater):
        """Handle submit count change from PromptInput"""
        if callable(updater):
            self.submit_count = updater(self.submit_count)
        else:
            self.submit_count = updater
    
    def set_loading_from_prompt(self, is_loading: bool):
        """Set loading state from PromptInput"""
        self.is_loading = is_loading
    
    def set_abort_controller_from_prompt(self, controller):
        """Set abort controller from PromptInput"""
        self.abort_controller = controller
    
    def show_message_selector(self):
        """Show message selector from PromptInput"""
        self.is_message_selector_visible = True
    
    def set_fork_convo_messages(self, messages: List[Message]):
        """Set fork conversation messages from PromptInput"""
        self.fork_convo_with_messages_on_next_render = messages
    
    def on_model_change_from_prompt(self):
        """Handle model change from PromptInput"""
        self.fork_number += 1
        logger.info("Model changed, incrementing fork number")
    
    def set_tool_jsx_from_prompt(self, tool_jsx):
        """Set tool JSX from PromptInput"""
        self.tool_jsx = tool_jsx
    
    @on(Button.Pressed, "#acknowledge_btn")
    def acknowledge_cost_dialog(self):
        """Acknowledge cost threshold dialog"""
        self.show_cost_dialog = False
        self.have_shown_cost_dialog = True
        self.config.has_acknowledged_cost_threshold = True
        logger.info("Cost threshold acknowledged")
    
    def normalize_messages(self) -> List[Message]:
        """Normalize messages - equivalent to normalizeMessages function"""
        # Filter out empty messages and normalize structure
        return [msg for msg in self.messages if self.is_not_empty_message(msg)]
    
    def is_not_empty_message(self, message: Message) -> bool:
        """Check if message is not empty - equivalent to isNotEmptyMessage"""
        if isinstance(message.message.content, str):
            return bool(message.message.content.strip())
        return bool(message.message.content)
    
    def get_unresolved_tool_use_ids(self) -> Set[str]:
        """Get unresolved tool use IDs - equivalent to getUnresolvedToolUseIDs"""
        # This would analyze messages for unresolved tool uses
        return set()
    
    def get_in_progress_tool_use_ids(self) -> Set[str]:
        """Get in-progress tool use IDs - equivalent to getInProgressToolUseIDs"""
        # This would analyze messages for in-progress tool uses
        return set()
    
    def get_errored_tool_use_ids(self) -> Set[str]:
        """Get errored tool use IDs - equivalent to getErroredToolUseMessages"""
        # This would analyze messages for errored tool uses
        return set()
    
    def _format_error_for_ui(self, error: Exception) -> str:
        """Format error message for UI display with appropriate context"""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Handle common error types with user-friendly messages
        if "ImportError" in error_type or "ModuleNotFoundError" in error_type:
            return f"❌ Module Error: {error_msg}\n💡 Try installing missing dependencies or check your environment setup."
        
        elif "ConnectionError" in error_type or "TimeoutError" in error_type:
            return f"❌ Connection Error: {error_msg}\n💡 Check your internet connection or API configuration."
        
        elif "PermissionError" in error_type:
            return f"❌ Permission Error: {error_msg}\n💡 Check file permissions or run with appropriate privileges."
        
        elif "FileNotFoundError" in error_type:
            return f"❌ File Not Found: {error_msg}\n💡 Verify the file path exists and is accessible."
        
        elif "ValueError" in error_type or "TypeError" in error_type:
            return f"❌ Input Error: {error_msg}\n💡 Please check your input format and try again."
        
        else:
            # Generic error with helpful context
            return f"❌ {error_type}: {error_msg}\n💡 If this error persists, please check the logs for more details."
    
    # Reactive property watchers (equivalent to React useEffect)
    def watch_fork_number(self, fork_number: int):
        """Watch fork number changes"""
        logger.info(f"Fork number changed to: {fork_number}")
    
    def watch_is_loading(self, is_loading: bool):
        """Watch loading state changes"""
        logger.info(f"Loading state changed to: {is_loading}")
    
    def watch_messages(self, messages: List[Message]):
        """Watch messages changes - equivalent to useEffect([messages], ...)"""
        logger.info(f"Messages updated, count: {len(messages)}")
        
        # Check cost threshold (equivalent to cost threshold useEffect)
        total_cost = self.get_total_cost()
        if (total_cost >= 5.0 and 
            not self.show_cost_dialog and 
            not self.have_shown_cost_dialog):
            self.show_cost_dialog = True
    
    def get_total_cost(self) -> float:
        """Get total API cost - equivalent to getTotalCost"""
        # This would calculate actual API costs
        return len(self.messages) * 0.01  # Mock cost calculation
    
    def _get_mode_prefix(self) -> str:
        """Get the mode prefix character"""
        if self.input_mode == InputMode.BASH:
            return "!"
        elif self.input_mode == InputMode.KODING:
            return "#"
        else:
            return ">"
    
    # Simplified event handlers for debugging
    @on(Input.Changed, "#simple_input")
    def on_simple_input_changed(self, event):
        """Handle simple input changes"""
        self.input_value = event.value
        logger.info(f"Input changed: {event.value}")
    
    @on(Input.Submitted, "#simple_input")
    @on(Button.Pressed, "#simple_send")
    async def on_simple_submit(self, event):
        """Handle simple input submission"""
        input_widget = self.query_one("#simple_input", expect_type=Input)
        input_text = input_widget.value.strip()
        
        if not input_text:
            return
        
        logger.info(f"Submitting: {input_text}")
        
        # Add user message to display
        user_message = Message(
            type=MessageType.USER,
            message=MessageContent(input_text),
            options={"mode": self.input_mode.value}
        )
        self.messages = [*self.messages, user_message]
        
        # Create simple response
        response_text = f"Received: {input_text} (mode: {self.input_mode.value})"
        assistant_message = Message(
            type=MessageType.ASSISTANT,
            message=MessageContent(response_text)
        )
        self.messages = [*self.messages, assistant_message]
        
        # Clear input
        input_widget.value = ""
        self.input_value = ""
        
        # Keep focus
        input_widget.focus()
    
    @on(Button.Pressed, "#simple_mode")
    def on_simple_mode_change(self):
        """Handle mode change"""
        modes = list(InputMode)
        current_index = modes.index(self.input_mode)
        self.input_mode = modes[(current_index + 1) % len(modes)]
        
        # Update mode indicator
        try:
            mode_indicator = self.query_one("#mode_indicator", expect_type=Static)
            mode_indicator.update(f" {self._get_mode_prefix()} ")
            
            # Update input placeholder
            input_widget = self.query_one("#simple_input", expect_type=Input)
            input_widget.placeholder = f"Enter {self.input_mode.value} command..."
        except:
            pass
        
        logger.info(f"Mode changed to: {self.input_mode.value}")


class REPLApp(App):
    """
    Main REPL Application - equivalent to the main App wrapper in React
    Provides the application context, agent management, and styling
    """
    
    CSS = """
    /* Message styling */
    .user-label {
        text-style: bold;
        color: blue;
        margin-top: 1;
        margin-bottom: 0;
    }
    
    .user-message {
        background: blue 20%;
        color: white;
        margin: 1;
        margin-top: 0;
        padding: 1;
        border-left: solid blue;
    }
    
    .assistant-label {
        text-style: bold;
        color: green;
        margin-top: 1;
        margin-bottom: 0;
    }
    
    .assistant-message {
        background: green 20%;
        color: white;
        margin: 1;
        margin-top: 0;
        padding: 1;
        border-left: solid green;
    }
    
    .assistant-streaming {
        background: yellow 20%;
        color: black;
        margin: 1;
        padding: 1;
        border-left: solid yellow;
        text-style: italic;
    }
    
    .assistant-error-label {
        text-style: bold;
        color: red;
        margin-top: 1;
        margin-bottom: 0;
    }
    
    .assistant-error {
        background: red 20%;
        color: white;
        margin: 1;
        margin-top: 0;
        padding: 1;
        border-left: solid red;
    }
    
    .progress-label {
        text-style: bold;
        color: yellow;
        margin-top: 1;
        margin-bottom: 0;
    }
    
    .progress-message {
        background: yellow 20%;
        color: black;
        margin: 1;
        margin-top: 0;
        padding: 1;
        border-left: solid yellow;
    }
    
    .dialog-title {
        text-style: bold;
        content-align: center middle;
        margin: 1;
        background: cyan 30%;
        color: black;
    }
    
    #messages_container {
        height: 1fr;
        margin: 1;
        scrollbar-background: gray 50%;
        scrollbar-color: white;
    }
    
    #dynamic_content {
        dock: bottom;
        height: auto;
        margin: 1;
    }
    
    #main_input {
        width: 1fr;
        margin-right: 1;
        border: solid white;
    }
    
    #simple_input_area {
        dock: bottom;
        height: 3;
        margin: 1;
    }
    
    #mode_indicator {
        width: 3;
        content-align: center middle;
        text-style: bold;
        background: gray 20%;
    }
    
    #simple_input {
        width: 1fr;
        margin-right: 1;
    }
    
    /* PromptInput component styles */
    .model-info {
        dock: top;
        height: 1;
        content-align: right middle;
        color: white;
        margin-bottom: 1;
    }
    
    #input_container {
        margin: 1;
        padding: 1;
    }
    
    #mode_prefix {
        width: 3;
        content-align: center middle;
        text-style: bold;
    }
    
    .mode-bash #mode_prefix {
        color: yellow;
    }
    
    .mode-koding #mode_prefix {
        color: cyan;
    }
    
    #status_area {
        dock: bottom;
        height: 2;
        margin: 1;
    }
    
    .status-message {
        color: white;
        text-style: dim;
    }
    
    .model-switch-message {
        color: green;
        text-style: bold;
    }
    
    .help-text {
        margin-right: 2;
    }
    
    .help-text.active {
        color: white;
        text-style: bold;
    }
    
    .help-text.inactive {
        color: gray;
        text-style: dim;
    }
    
    Button {
        margin: 1;
    }
    
    Input {
        border: solid white;
    }
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize with default props (equivalent to React props)
        self.repl_props = {
            "commands": [],
            "safe_mode": False,
            "debug": False,
            "initial_fork_number": 0,
            "initial_prompt": None,
            "message_log_name": "default",
            "should_show_prompt_input": True,
            "tools": [],
            "verbose": False,
            "initial_messages": [],
            "mcp_clients": [],
            "is_default_model": True,
            "initial_update_version": None,
            "initial_update_commands": None
        }
        
        # App-level agent management
        self.agent = None
        self.agent_ready = False
    
    def compose(self) -> ComposeResult:
        """Compose the main application - equivalent to React App render"""
        yield Header(show_clock=False)
        # Pass agent to REPL component
        repl_props_with_agent = {**self.repl_props, "agent": self.agent}
        yield REPL(**repl_props_with_agent)
        yield Footer()
    
    def on_mount(self):
        """Application mount lifecycle"""
        self.title = "Minion Code Assistant"
        logger.info("REPL Application started")
        # Initialize agent at app level
        self.run_worker(self._initialize_agent())
    
    async def _initialize_agent(self):
        """Initialize the MinionCodeAgent at app level"""
        try:
            from minion_code import MinionCodeAgent
            self.agent = await MinionCodeAgent.create(
                name="REPL Assistant",
                llm="sonnet"
            )
            self.agent_ready = True
            logger.info("App-level agent initialized successfully")
            
            # Update REPL component with agent
            try:
                repl_component = self.query_one(REPL)
                repl_component.set_agent(self.agent)
            except:
                pass  # REPL might not be mounted yet
                
        except Exception as e:
            logger.error(f"Failed to initialize app-level agent: {e}")
            self.agent_ready = False


# Utility functions equivalent to TypeScript utility functions
def should_render_statically(
    message: Message,
    messages: List[Message],
    unresolved_tool_use_ids: Set[str]
) -> bool:
    """
    Determine if message should render statically
    Equivalent to shouldRenderStatically function in TypeScript
    """
    if message.type in [MessageType.USER, MessageType.ASSISTANT]:
        # For now, render all user and assistant messages statically
        return True
    elif message.type == MessageType.PROGRESS:
        # Progress messages depend on tool use resolution
        return len(unresolved_tool_use_ids) == 0
    return True

def intersects(set_a: Set[str], set_b: Set[str]) -> bool:
    """Check if two sets intersect - equivalent to intersects function"""
    return len(set_a & set_b) > 0


# Factory function to create REPL with specific configuration
def create_repl(
    commands=None,
    safe_mode=False,
    debug=False,
    initial_prompt=None,
    verbose=False,
    **kwargs
) -> REPLApp:
    """
    Create a configured REPL application
    Equivalent to calling REPL component with props in React
    """
    app = REPLApp()
    app.repl_props.update({
        "commands": commands or [],
        "safe_mode": safe_mode,
        "debug": debug,
        "initial_prompt": initial_prompt,
        "verbose": verbose,
        **kwargs
    })
    return app


def run(initial_prompt=None, debug=False, verbose=False):
    """Run the REPL application with optional configuration"""
    app = create_repl(
        initial_prompt=initial_prompt,
        debug=debug,
        verbose=verbose
    )
    app.run()


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments (basic implementation)
    initial_prompt = None
    debug = False
    verbose = False
    
    if len(sys.argv) > 1:
        if "--debug" in sys.argv:
            debug = True
        if "--verbose" in sys.argv:
            verbose = True
        if "--prompt" in sys.argv:
            prompt_index = sys.argv.index("--prompt")
            if prompt_index + 1 < len(sys.argv):
                initial_prompt = sys.argv[prompt_index + 1]
    
    run(initial_prompt=initial_prompt, debug=debug, verbose=verbose)