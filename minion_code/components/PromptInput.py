"""
PromptInput Component - Python equivalent of React PromptInput
Handles user input with multiple modes (prompt, bash, koding)
"""

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Static, Button, TextArea
from textual.reactive import reactive, var
from textual import on, work
from textual.events import Key
from textual.message import Message
from rich.text import Text
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import time

# No logging in UI components to reduce noise

# Import shared types
from ..type_defs import (
    InputMode,
    Message as MinionMessage,
    MessageType,
    MessageContent,
    ModelInfo,
)


class CustomTextArea(TextArea):
    """Custom TextArea with adaptive height and key event posting"""

    DEFAULT_CSS = """
    CustomTextArea {
        height: auto;
        min-height: 1;
        max-height: 10;
        width: 1fr;
        border: solid white;
    }
    """

    # Inherit COMPONENT_CLASSES from TextArea
    COMPONENT_CLASSES = TextArea.COMPONENT_CLASSES

    class KeyPressed(Message):
        """Message posted when a key is pressed"""

        def __init__(self, key: str) -> None:
            super().__init__()
            self.key = key

    def on_key(self, event: Key) -> bool:
        """Handle key events and post to parent"""
        # Post key event to parent for handling
        self.post_message(self.KeyPressed(event.key))

        # Handle Ctrl+Enter, Tab, and Ctrl+J - prevent default, let parent add newline manually
        if event.key in ["tab"]:
            event.prevent_default()
            event.stop()
            return True
        if event.key in ["ctrl+enter", "ctrl+j"]:
            return True  # Prevent TextArea from handling, parent will add newline

        # Handle Enter - prevent default and let parent handle
        if event.key == "enter":
            event.prevent_default()
            event.stop()
            return True  # Prevent TextArea from handling

        # Let TextArea handle all other keys normally
        return False


class PromptInput(Container):
    """
    Main input component equivalent to React PromptInput
    Handles user input with mode switching and command processing
    """

    DEFAULT_CSS = """
    PromptInput {
        dock: bottom;
        height: auto;
        max-height: 15;
        margin: 0 1 1 1;
        padding: 1;
    }
    
    .mode-bash PromptInput {
        border: solid yellow;
    }
    
    .mode-koding PromptInput {
        border: solid cyan;
    }
    
    .input-row {
        height: auto;
        width: 1fr;
    }
    
    #mode_prefix {
        width: 4;
        min-width: 4;
        max-width: 4;
        content-align: center middle;
        text-style: bold;
        margin-right: 1;
    }
    
    .help-text {
        color: gray;
        text-style: dim;
        margin-bottom: 1;
    }
    
    .model-info {
        height: 1;
        content-align: right middle;
        background: gray 10%;
        color: white;
    }
    
    CustomTextArea {
        width: 1fr;
        height: auto;
        min-height: 1;
        max-height: 10;
    }
    """

    # Reactive properties equivalent to React useState
    mode = reactive(InputMode.PROMPT)
    input_value = reactive("")
    is_disabled = reactive(False)
    is_loading = reactive(False)
    submit_count = reactive(0)
    cursor_offset = reactive(0)

    # State for messages and UI feedback
    exit_message = var(dict)  # {"show": bool, "key": str}
    message = var(dict)  # {"show": bool, "text": str}
    model_switch_message = var(dict)  # {"show": bool, "text": str}
    pasted_image = var(None)  # Optional[str]
    pasted_text = var(None)  # Optional[str]
    placeholder = reactive("")

    def __init__(
        self,
        commands=None,
        fork_number=0,
        message_log_name="default",
        is_disabled=False,
        is_loading=False,
        debug=False,
        verbose=False,
        messages=None,
        tools=None,
        input_value="",
        mode=InputMode.PROMPT,
        submit_count=0,
        read_file_timestamps=None,
        abort_controller=None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        # Props equivalent to TypeScript Props interface
        self.commands = commands or []
        self.fork_number = fork_number
        self.message_log_name = message_log_name
        self.debug = debug
        self.verbose = verbose
        self.messages = messages or []
        self.tools = tools or []
        self.read_file_timestamps = read_file_timestamps or {}
        self.abort_controller = abort_controller

        # Initialize reactive state
        self.mode = mode
        self.input_value = input_value
        self.is_disabled = is_disabled
        self.is_loading = is_loading
        self.submit_count = submit_count
        self.cursor_offset = len(input_value)

        # Initialize state variables
        self.exit_message = {"show": False, "key": ""}
        self.message = {"show": False, "text": ""}
        self.model_switch_message = {"show": False, "text": ""}
        self.pasted_image = None
        self.pasted_text = None
        self.placeholder = ""

        # Callbacks (would be passed as props in React)
        self.on_query: Optional[Callable] = None
        self.on_add_user_message: Optional[Callable] = (
            None  # New callback for immediate message display
        )
        self.on_input_change: Optional[Callable] = None
        self.on_mode_change: Optional[Callable] = None
        self.on_submit_count_change: Optional[Callable] = None
        self.set_is_loading: Optional[Callable] = None
        self.set_abort_controller: Optional[Callable] = None
        self.on_show_message_selector: Optional[Callable] = None
        self.set_fork_convo_with_messages: Optional[Callable] = None
        self.on_model_change: Optional[Callable] = None
        self.set_tool_jsx: Optional[Callable] = None
        self.on_execute_command: Optional[Callable] = (
            None  # Callback for executing / commands
        )

    def on_mount(self):
        """Set focus to input when component mounts"""
        try:
            input_widget = self.query_one("#main_input", expect_type=CustomTextArea)
            input_widget.focus()
        except Exception:
            pass  # Silently handle focus errors

    def compose(self):
        """Compose the PromptInput interface with loading indicator"""
        # Loading indicator - replaces "BEFORE TextArea - Ready"
        if self.is_loading:
            yield Static(
                "⠋ Assistant is thinking...",
                id="loading_status",
                classes="loading-status",
            )

        # Input area with mode prefix in horizontal layout
        with Horizontal(classes="input-row"):
            yield Static(self._get_mode_prefix(), id="mode_prefix")
            yield CustomTextArea(
                text=self.input_value,
                id="main_input",
                disabled=self.is_disabled or self.is_loading,
                show_line_numbers=False,
            )

        yield Static(
            "Enter to submit · Ctrl+Enter/Ctrl+J/Tab for new line · ! for bash · # for AGENTS.md",
            classes="help-text",
        )

    def _render_model_info(self) -> Static:
        """Render model information - equivalent to model info display"""
        model_info = self._get_model_info()
        if model_info:
            info_text = f"[{model_info.provider}] {model_info.name}: {model_info.current_tokens//1000}k / {model_info.context_length//1000}k"
            return Static(info_text, id="model_info", classes="model-info")
        return Static("", id="model_info")

    # _render_status_area method removed - content moved to compose method

    def _get_mode_prefix(self) -> str:
        """Get the mode prefix character"""
        if self.mode == InputMode.BASH:
            return " ! "
        elif self.mode == InputMode.KODING:
            return " # "
        else:
            return " > "

    def _get_placeholder(self) -> str:
        """Get placeholder text based on current mode"""
        if self.placeholder:
            return self.placeholder

        if self.mode == InputMode.BASH:
            return "Enter bash command..."
        elif self.mode == InputMode.KODING:
            return "Enter note for AGENTS.md..."
        else:
            return "Enter your message..."

    def _get_model_info(self) -> Optional[ModelInfo]:
        """Get current model information - equivalent to modelInfo useMemo"""
        # This would integrate with the actual model manager
        # For now, return mock data
        return ModelInfo(
            name="claude-3-5-sonnet-20241022",
            provider="anthropic",
            context_length=200000,
            current_tokens=len(str(self.messages)) * 4,  # Rough token estimate
            id="claude-3-5-sonnet",
        )

    # Event handlers
    @on(TextArea.Changed, "#main_input")
    def on_textarea_changed(self, event: TextArea.Changed):
        """Handle TextArea content changes"""
        value = event.text_area.text

        # Handle mode switching based on input prefix
        if value.startswith("!"):
            if self.mode != InputMode.BASH:
                self.mode = InputMode.BASH
                if self.on_mode_change:
                    self.on_mode_change(InputMode.BASH)
        elif value.startswith("#"):
            if self.mode != InputMode.KODING:
                self.mode = InputMode.KODING
                if self.on_mode_change:
                    self.on_mode_change(InputMode.KODING)

        self.input_value = value
        if self.on_input_change:
            self.on_input_change(value)

    @on(CustomTextArea.KeyPressed)
    def on_custom_textarea_key(self, event: CustomTextArea.KeyPressed):
        """Handle key events from CustomTextArea"""
        key = event.key

        if key == "enter":
            # Regular Enter - submit
            self.run_worker(self._handle_submit(), exclusive=True)
        elif key in ["ctrl+enter", "ctrl+j"]:
            # Ctrl+Enter, Tab, or Ctrl+J - manually add newline
            self._insert_newline()
        elif key in ["backspace", "delete"]:
            # Handle mode reset on empty input
            if self.mode == InputMode.BASH and not self.input_value:
                self.mode = InputMode.PROMPT
                if self.on_mode_change:
                    self.on_mode_change(InputMode.PROMPT)
            elif self.mode == InputMode.KODING and not self.input_value:
                self.mode = InputMode.PROMPT
                if self.on_mode_change:
                    self.on_mode_change(InputMode.PROMPT)
        elif key == "escape":
            # Handle escape key
            if not self.input_value and not self.is_loading and len(self.messages) > 0:
                if self.on_show_message_selector:
                    self.on_show_message_selector()
            else:
                self.mode = InputMode.PROMPT
                if self.on_mode_change:
                    self.on_mode_change(InputMode.PROMPT)
        elif key == "shift+m":
            # Handle model switching
            self._handle_quick_model_switch()
        elif key == "shift+tab":
            # Handle mode cycling
            self._cycle_mode()

    async def _handle_submit(self):
        """Handle input submission with immediate UI feedback"""
        try:
            text_area = self.query_one("#main_input", expect_type=CustomTextArea)
            input_text = text_area.text.strip()
        except:
            return

        if not input_text:
            return

        if self.is_disabled or self.is_loading:
            return

        # Handle exit commands
        if input_text.lower() in ["exit", "quit", ":q", ":q!", ":wq", ":wq!"]:
            self._handle_exit()
            return

        # Handle slash commands (e.g., /clear, /help, /tools)
        if input_text.startswith("/"):
            # Clear input immediately
            with text_area.prevent(TextArea.Changed):
                text_area.text = ""
            self.input_value = ""

            # Execute command (no AI processing, no "Thinking..." message)
            await self._handle_command_input(input_text)

            # Update history
            self._add_to_history(input_text)
            return

        # 1. 立即清空输入框并重置模式 - 提供即时反馈
        original_mode = self.mode

        with text_area.prevent(TextArea.Changed):
            text_area.text = ""
        self.input_value = ""
        self.mode = InputMode.PROMPT

        if self.on_mode_change:
            self.on_mode_change(InputMode.PROMPT)

        # 2. 根据模式处理输入
        if original_mode == InputMode.KODING:
            # Koding 模式：直接处理笔记，不走 AI query
            await self._handle_koding_input(input_text)
        elif original_mode == InputMode.BASH:
            # Bash 模式：执行命令
            await self._handle_bash_input(input_text)
        else:
            # Prompt 模式：正常的 AI 对话
            # 2a. 立即创建用户消息
            user_message = self._create_user_message(input_text, original_mode)

            # 2b. 立即显示用户消息（同步操作，不等待网络）
            if self.on_add_user_message:
                self.on_add_user_message(user_message)

            # 2c. 启动后台AI处理 - 让父组件管理 worker
            if self.on_query:
                # 直接调用父组件的回调，让父组件管理 worker
                await self.on_query([user_message])

        # 3. 更新提交计数和历史记录
        self.submit_count += 1
        if self.on_submit_count_change:
            self.on_submit_count_change(lambda x: x + 1)

        self._add_to_history(input_text)

    async def _handle_command_input(self, input_text: str):
        """
        Handle slash command input (e.g., /clear, /help, /tools).
        Commands are executed directly without AI processing.
        """
        # Parse command: /command_name args
        command_input = input_text[1:] if input_text.startswith("/") else input_text
        parts = command_input.split(" ", 1)
        command_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Delegate to REPL for command execution
        if self.on_execute_command:
            await self.on_execute_command(command_name, args)
        else:
            # Fallback: show error if no handler is set
            self._show_temporary_message(
                f"❌ Command handler not available for /{command_name}", duration=3.0
            )

    async def _handle_koding_input(self, input_text: str):
        """Handle koding mode input - equivalent to koding mode handling"""

        # Strip # prefix if present
        content = input_text[1:].strip() if input_text.startswith("#") else input_text

        # Check if this is an action prompt (put, create, generate, etc.)
        if any(
            word in content.lower()
            for word in ["put", "create", "generate", "write", "give", "provide"]
        ):
            # Handle as AI request for AGENTS.md content
            await self._handle_koding_ai_request(content)
        else:
            # Handle as direct note to AGENTS.md
            await self._handle_koding_note(content)

        # Add to history
        self._add_to_history(
            f"#{input_text}" if not input_text.startswith("#") else input_text
        )

    async def _handle_bash_input(self, input_text: str):
        """Handle bash mode input - equivalent to bash command processing"""

        # Strip ! prefix if present
        command = input_text[1:].strip() if input_text.startswith("!") else input_text

        try:
            # Execute bash command (simplified version)
            import subprocess

            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )

            # Create assistant message with result
            if result.returncode == 0:
                response = result.stdout or "Command executed successfully"
            else:
                response = f"Error: {result.stderr}"

            # This would typically be handled by the parent REPL component
            pass

        except Exception:
            pass  # Silently handle bash command errors

        # Add to history
        self._add_to_history(
            f"!{input_text}" if not input_text.startswith("!") else input_text
        )

    def _create_user_message(self, input_text: str, mode: InputMode):
        """Create user message for immediate display"""
        from ..type_defs import Message as MinionMessage, MessageType, MessageContent

        return MinionMessage(
            type=MessageType.USER,
            message=MessageContent(input_text),
            options={"mode": mode.value},
        )

    async def _handle_prompt_response(self, input_text: str):
        """Handle AI response for regular prompt input"""

        if self.set_is_loading:
            self.set_is_loading(True)

        # Create new abort controller
        if self.set_abort_controller:
            new_controller = asyncio.create_task(asyncio.sleep(0))  # Mock controller
            self.set_abort_controller(new_controller)

        # 这里不再创建用户消息，因为已经在 _handle_submit 中创建并显示了
        # 直接触发 AI 响应处理

    async def _handle_prompt_input(self, input_text: str):
        """Handle regular prompt input - equivalent to normal message processing (deprecated)"""
        # 这个方法现在被 _handle_prompt_response 替代
        await self._handle_prompt_response(input_text)

    async def _handle_koding_ai_request(self, content: str):
        """Handle AI request for koding mode"""

        # This would integrate with the AI system to generate content for AGENTS.md
        # For now, just log the request
        koding_context = (
            "The user is using Koding mode. Format your response as a comprehensive, "
            "well-structured document suitable for adding to AGENTS.md. Use proper "
            "markdown formatting with headings, lists, code blocks, etc."
        )

        # This would be processed by the main query system
        if self.on_query:
            user_message = MinionMessage(
                type=MessageType.USER,
                message=MessageContent(content),
                options={"isKodingRequest": True, "kodingContext": koding_context},
            )
            await self.on_query([user_message])

    async def _handle_koding_note(self, content: str):
        """Handle direct note to AGENTS.md"""

        # Show processing message
        self._show_temporary_message("🤔 Formatting note with AI...", duration=30.0)

        # Interpret and format the note using AI
        try:
            self._handle_hash_command(content)
        except Exception as e:
            pass

    async def _interpret_hash_command(self, content: str) -> str:
        """
        Interpret hash command using AI - equivalent to interpretHashCommand.

        Uses the AI to transform raw notes into well-structured content for AGENTS.md.
        Adds appropriate markdown formatting, headings, bullet points, etc.

        Args:
            content: Raw note content from user

        Returns:
            Formatted markdown content ready for AGENTS.md
        """
        try:
            # Import query_quick for AI interpretation
            from ..agents.code_agent import query_quick

            # Get agent from parent REPL component if available
            agent = None
            try:
                # Try to get agent from parent
                parent = self.parent
                while parent and not hasattr(parent, "agent"):
                    parent = parent.parent
                if parent and hasattr(parent, "agent"):
                    agent = parent.agent
            except:
                pass

            # If no agent available, fall back to simple formatting
            if not agent:
                return f"# {content}\n\n_Added on {time.strftime('%m/%d/%Y, %I:%M:%S %p')}_"

            # Create system prompt for note interpretation
            system_prompt = [
                "You're helping the user structure notes that will be added to their AGENTS.md file.",
                "Format the user's input into a well-structured note that will be useful for later reference.",
                "Add appropriate markdown formatting, headings, bullet points, or other structural elements as needed.",
                "The goal is to transform the raw note into something that will be more useful when reviewed later.",
                "You should keep the original meaning but make the structure clear.",
            ]

            # Send request to AI using query_quick
            result = await query_quick(
                agent=agent,
                user_prompt=f"Transform this note for AGENTS.md: {content}",
                system_prompt=system_prompt,
            )

            # Extract content from response
            if isinstance(result, str):
                formatted_content = result
            else:
                # Handle other response formats
                formatted_content = str(result)

            # Add timestamp
            timestamp = time.strftime("%m/%d/%Y, %I:%M:%S %p")
            if "_Added on" not in formatted_content:
                formatted_content += f"\n\n_Added on {timestamp}_"

            return formatted_content

        except Exception as e:
            # If interpretation fails, return input with minimal formatting
            timestamp = time.strftime("%m/%d/%Y, %I:%M:%S %p")
            return f"# {content}\n\n_Added on {timestamp}_"

    def _handle_hash_command(self, content: str):
        """Handle hash command - equivalent to handleHashCommand"""
        try:
            from pathlib import Path

            agents_md = Path("AGENTS.md")

            # Create file if it doesn't exist
            if not agents_md.exists():
                with open(agents_md, "w", encoding="utf-8") as f:
                    f.write("# Agent Development Guidelines\n\n")

            # Append the formatted content
            with open(agents_md, "a", encoding="utf-8") as f:
                f.write(f"\n\n{content}\n")

            # Show success message to user
            self._show_temporary_message(f"✅ Note added to AGENTS.md", duration=3.0)

        except Exception as e:
            # Show error message to user
            self._show_temporary_message(
                f"❌ Failed to write to AGENTS.md: {e}", duration=5.0
            )

    def _show_temporary_message(self, text: str, duration: float = 3.0):
        """Show a temporary message to the user"""
        self.message = {"show": True, "text": text}
        self.set_timer(
            duration, lambda: setattr(self, "message", {"show": False, "text": ""})
        )

    async def _process_user_input(
        self, input_text: str, mode: InputMode
    ) -> List[MinionMessage]:
        """Process user input - equivalent to processUserInput"""
        user_message = MinionMessage(
            type=MessageType.USER,
            message=MessageContent(input_text),
            options={"mode": mode.value},
        )
        return [user_message]

    def _add_to_history(self, input_text: str):
        from minion_code.utils.history import add_to_history

        add_to_history(input_text)

    def _handle_exit(self):
        """Handle exit command"""
        # This would typically exit the application
        # For now, just show exit message
        self.exit_message = {"show": True, "key": "Ctrl+C"}
        self.set_timer(
            3.0, lambda: setattr(self, "exit_message", {"show": False, "key": ""})
        )

    def _handle_quick_model_switch(self):
        """Handle quick model switching - equivalent to handleQuickModelSwitch"""

        # This would integrate with the model manager
        # For now, show a mock message
        self.model_switch_message = {
            "show": True,
            "text": "✅ Model switching would happen here",
        }

        # Clear message after 3 seconds
        self.set_timer(
            3.0,
            lambda: setattr(self, "model_switch_message", {"show": False, "text": ""}),
        )

        if self.on_model_change:
            self.on_model_change()

    def _insert_newline(self):
        """Insert newline at current cursor position"""
        try:
            text_area = self.query_one("#main_input", expect_type=CustomTextArea)

            # Get current cursor position
            cursor_row, cursor_col = text_area.cursor_location

            # Get current text
            current_text = text_area.text

            # Split text into lines
            lines = current_text.split("\n")

            # Insert newline at cursor position
            if cursor_row < len(lines):
                line = lines[cursor_row]
                # Split the current line at cursor position
                before_cursor = line[:cursor_col]
                after_cursor = line[cursor_col:]

                # Replace current line with split lines
                lines[cursor_row] = before_cursor
                lines.insert(cursor_row + 1, after_cursor)
            else:
                # Cursor is beyond existing lines, just add a new line
                lines.append("")

            # Update text area with new content
            new_text = "\n".join(lines)
            text_area.text = new_text

            # Move cursor to next line
            text_area.cursor_location = (cursor_row + 1, 0)

            # Update input value
            self.input_value = new_text
            if self.on_input_change:
                self.on_input_change(new_text)

        except Exception:
            pass  # Silently handle newline insertion errors

    def _cycle_mode(self):
        """Cycle through input modes"""
        modes = list(InputMode)
        current_index = modes.index(self.mode)
        new_mode = modes[(current_index + 1) % len(modes)]
        self.mode = new_mode

        if self.on_mode_change:
            self.on_mode_change(new_mode)

    # Reactive property watchers
    def watch_mode(self, mode: InputMode):
        """Watch mode changes and update UI"""
        try:
            # Update mode prefix
            prefix_widget = self.query_one("#mode_prefix", expect_type=Static)
            prefix_widget.update(self._get_mode_prefix())

            # Update input placeholder
            input_widget = self.query_one("#main_input", expect_type=Input)
            input_widget.placeholder = self._get_placeholder()

            # Update container classes
            container = self.query_one("#input_container")
            container.remove_class("mode-prompt", "mode-bash", "mode-koding")
            container.add_class(f"mode-{mode.value}")
        except:
            pass  # Widgets might not be mounted yet

    def watch_is_loading(self, is_loading: bool):
        """Watch loading state changes"""
        try:
            input_widget = self.query_one("#main_input", expect_type=CustomTextArea)
            input_widget.disabled = self.is_disabled or is_loading
        except:
            pass

    def watch_input_value(self, value: str):
        """Watch input value changes"""
        try:
            input_widget = self.query_one("#main_input", expect_type=CustomTextArea)
            if input_widget.text != value:
                input_widget.text = value
        except:
            pass
