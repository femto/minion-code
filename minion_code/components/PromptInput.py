"""
PromptInput Component - Python equivalent of React PromptInput
Handles user input with multiple modes (prompt, bash, memory)
"""

import os
from pathlib import Path

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

from ..utils.history import get_history

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
        max-height: 8;
        width: 1fr;
        border: none;
        background: transparent;
        padding: 0;
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
        # Handle Ctrl+Enter, Tab, and Ctrl+J - prevent default, let parent add newline manually
        if event.key in ["tab"]:
            self.post_message(self.KeyPressed(event.key))
            event.prevent_default()
            event.stop()
            return True
        if event.key in ["ctrl+enter", "ctrl+j"]:
            self.post_message(self.KeyPressed(event.key))
            return True  # Prevent TextArea from handling, parent will add newline

        # Handle Enter - prevent default and let parent handle
        if event.key == "enter":
            self.post_message(self.KeyPressed(event.key))
            event.prevent_default()
            event.stop()
            return True  # Prevent TextArea from handling

        if event.key == "up" and self.cursor_location[0] == 0:
            self.post_message(self.KeyPressed(event.key))
            event.prevent_default()
            event.stop()
            return True

        line_count = len(self.text.split("\n")) or 1
        if event.key == "down" and self.cursor_location[0] >= line_count - 1:
            self.post_message(self.KeyPressed(event.key))
            event.prevent_default()
            event.stop()
            return True

        # Post key event to parent for handling
        self.post_message(self.KeyPressed(event.key))

        # Let TextArea handle all other keys normally
        return False


@dataclass
class PromptSuggestion:
    """Represents one inline completion candidate."""

    kind: str
    value: str
    detail: str = ""


class PromptInput(Container):
    """
    Main input component equivalent to React PromptInput
    Handles user input with mode switching and command processing
    """

    DEFAULT_CSS = """
    PromptInput {
        dock: bottom;
        height: auto;
        max-height: 12;
        margin: 0 1 1 1;
        padding: 0;
    }
    
    .mode-bash PromptInput {
        border: solid yellow;
    }
    
    .mode-memory PromptInput {
        border: solid cyan;
    }
    
    .input-row {
        height: auto;
        width: 1fr;
        background: $surface-lighten-1;
        padding: 0 1;
    }
    
    #mode_prefix {
        width: 3;
        min-width: 3;
        max-width: 3;
        content-align: center middle;
        text-style: bold;
        margin-right: 0;
        color: #7f8599;
    }
    
    .help-text {
        color: gray;
        text-style: dim;
        margin-top: 0;
        margin-bottom: 0;
    }

    .suggestions {
        color: $text-muted;
        margin-top: 0;
        margin-bottom: 0;
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
        max-height: 8;
    }
    """

    # Reactive properties equivalent to React useState
    mode = reactive(InputMode.PROMPT)
    input_value = reactive("")
    is_disabled = reactive(False)
    is_loading = reactive(False)
    interrupt_armed = reactive(False)
    history_position = reactive(-1)
    submit_count = reactive(0)
    cursor_offset = reactive(0)

    # State for messages and UI feedback
    exit_message = var(dict)  # {"show": bool, "key": str}
    message = var(dict)  # {"show": bool, "text": str}
    model_switch_message = var(dict)  # {"show": bool, "text": str}
    pasted_image = var(None)  # Optional[str]
    pasted_text = var(None)  # Optional[str]
    placeholder = reactive("")
    suggestions = var(list)
    suggestion_index = reactive(0)

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
        self.suggestions = []
        self.suggestion_index = 0

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
        self.on_interrupt: Optional[Callable] = None
        self.on_execute_command: Optional[Callable] = (
            None  # Callback for executing / commands
        )
        self._interrupt_deadline = 0.0
        self._interrupt_reset_timer = None
        self._history_draft = ""
        self._applying_history = False
        self._prefix_triggered_mode: Optional[InputMode] = None
        self._file_candidates: Optional[List[str]] = None

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
        with Horizontal(classes="input-row", id="input_container"):
            yield Static(self._get_mode_prefix(), id="mode_prefix")
            yield CustomTextArea(
                text=self.input_value,
                id="main_input",
                disabled=self.is_disabled,
                show_line_numbers=False,
            )

        yield Static(
            self._get_suggestions_text() if self.suggestions else "",
            id="suggestions_text",
            classes="suggestions",
        )

        yield Static(
            self._get_help_text(),
            id="help_text",
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
        elif self.mode == InputMode.MEMORY:
            return " # "
        else:
            return " > "

    def _get_placeholder(self) -> str:
        """Get placeholder text based on current mode"""
        if self.placeholder:
            return self.placeholder

        if self.mode == InputMode.BASH:
            return "Enter bash command..."
        elif self.mode == InputMode.MEMORY:
            return "Enter memory for AGENTS.md..."
        else:
            return "Enter your message..."

    def _get_help_text(self) -> str:
        """Get contextual footer help text."""
        if self.interrupt_armed:
            return "Press Esc again to interrupt current task"
        if self.suggestions:
            return "Tab accept · Up/Down navigate · Enter send · Ctrl+Enter/Ctrl+J newline"
        return "Enter send · Ctrl+Enter/Ctrl+J/Tab newline · ! bash · # memory · Shift+S mode"

    def _get_suggestions_text(self) -> str:
        """Render the active suggestion list in one compact line."""
        rendered = []
        for index, suggestion in enumerate(self.suggestions[:5]):
            prefix = "›" if index == self.suggestion_index else "·"
            detail = f" ({suggestion.detail})" if suggestion.detail else ""
            rendered.append(f"{prefix} {suggestion.value}{detail}")
        return "  ".join(rendered)

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
        self._sync_mode_from_text(value)
        self._refresh_suggestions(value)

        self.input_value = value
        if self.history_position == -1 and not self._applying_history:
            self._history_draft = value
        if self.on_input_change:
            self.on_input_change(value)

    def _set_mode(self, mode: InputMode) -> None:
        """Update mode and notify listeners only when it changes."""
        if self.mode == mode:
            return

        self.mode = mode
        if self.on_mode_change:
            self.on_mode_change(mode)

    def _sync_mode_from_text(self, value: str) -> None:
        """Track prefix-triggered modes and exit them once the prefix is removed."""
        if value.startswith("!"):
            self._prefix_triggered_mode = InputMode.BASH
            self._set_mode(InputMode.BASH)
            return

        if value.startswith("#"):
            self._prefix_triggered_mode = InputMode.MEMORY
            self._set_mode(InputMode.MEMORY)
            return

        if self._prefix_triggered_mode is not None:
            self._prefix_triggered_mode = None
            self._set_mode(InputMode.PROMPT)

    def _load_file_candidates(self, limit: int = 500) -> List[str]:
        """Build a bounded list of repo-relative file paths for `@` suggestions."""
        if self._file_candidates is not None:
            return self._file_candidates

        ignored_dirs = {
            ".git",
            ".venv",
            "node_modules",
            "__pycache__",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".idea",
            ".vscode",
            "dist",
            "build",
        }
        candidates: List[str] = []
        root = Path.cwd()

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name
                for name in dirnames
                if name not in ignored_dirs and not name.startswith(".DS_Store")
            ]
            rel_dir = Path(dirpath).relative_to(root)
            for filename in filenames:
                if filename.startswith("."):
                    continue
                rel_path = (rel_dir / filename).as_posix()
                candidates.append(rel_path)
                if len(candidates) >= limit:
                    self._file_candidates = sorted(candidates)
                    return self._file_candidates

        self._file_candidates = sorted(candidates)
        return self._file_candidates

    def _get_slash_suggestions(self, prefix: str) -> List[PromptSuggestion]:
        """Return slash-command suggestions for the current prefix."""
        from minion_code.commands import command_registry

        suggestions: List[PromptSuggestion] = []
        for name, command_class in sorted(command_registry.list_all().items()):
            if prefix and not name.startswith(prefix):
                continue
            suggestions.append(
                PromptSuggestion(
                    kind="command",
                    value=f"/{name}",
                    detail=getattr(command_class, "description", ""),
                )
            )
            if len(suggestions) >= 8:
                break
        return suggestions

    def _get_at_suggestions(self, prefix: str) -> List[PromptSuggestion]:
        """Return `@` suggestions from files and subagents."""
        suggestions: List[PromptSuggestion] = []
        normalized = prefix.lower()

        for file_path in self._load_file_candidates():
            if normalized and normalized not in file_path.lower():
                continue
            suggestions.append(
                PromptSuggestion(kind="file", value=f"@{file_path}", detail="file")
            )
            if len(suggestions) >= 6:
                return suggestions

        try:
            from minion_code.subagents import get_available_subagents

            for subagent in get_available_subagents():
                name = subagent.name
                if normalized and normalized not in name.lower():
                    continue
                suggestions.append(
                    PromptSuggestion(
                        kind="subagent",
                        value=f"@{name}",
                        detail="subagent",
                    )
                )
                if len(suggestions) >= 8:
                    break
        except Exception:
            pass

        return suggestions

    def _get_completion_context(self, value: str) -> tuple[Optional[str], str]:
        """Extract the active `/` or `@` token near the end of the current input."""
        token = value.split()[-1] if value.split() else ""
        if token.startswith("/") and "\n" not in token:
            return "/", token[1:]
        if token.startswith("@") and "\n" not in token:
            return "@", token[1:]
        return None, ""

    def _refresh_suggestions(self, value: str) -> None:
        """Recompute inline suggestions for `/` and `@` triggers."""
        trigger, prefix = self._get_completion_context(value)
        if trigger == "/":
            self.suggestions = self._get_slash_suggestions(prefix)
        elif trigger == "@":
            self.suggestions = self._get_at_suggestions(prefix)
        else:
            self.suggestions = []
        self.suggestion_index = 0

    def _move_suggestion_selection(self, delta: int) -> None:
        """Move the active suggestion selection up or down."""
        if not self.suggestions:
            return
        self.suggestion_index = (self.suggestion_index + delta) % len(self.suggestions)

    def _apply_active_suggestion(self) -> bool:
        """Replace the current `/` or `@` token with the selected suggestion."""
        if not self.suggestions:
            return False

        try:
            text_area = self.query_one("#main_input", expect_type=CustomTextArea)
        except Exception:
            return False

        current_text = text_area.text
        stripped = current_text.rstrip()
        trigger, _prefix = self._get_completion_context(stripped)
        if trigger is None:
            return False

        token_start = len(stripped) - len(stripped.split()[-1])
        replacement = self.suggestions[self.suggestion_index].value
        new_text = f"{stripped[:token_start]}{replacement} "

        with text_area.prevent(TextArea.Changed):
            text_area.text = new_text
            lines = new_text.split("\n") or [""]
            text_area.cursor_location = (len(lines) - 1, len(lines[-1]))

        self.input_value = new_text
        self.suggestions = []
        self.suggestion_index = 0
        if self.on_input_change:
            self.on_input_change(new_text)
        return True

    @on(CustomTextArea.KeyPressed)
    def on_custom_textarea_key(self, event: CustomTextArea.KeyPressed):
        """Handle key events from CustomTextArea"""
        key = event.key

        if key != "escape" and self.interrupt_armed:
            self._disarm_interrupt()

        if key == "enter":
            # Regular Enter - submit
            self.run_worker(self._handle_submit(), exclusive=True)
        elif key == "tab":
            if not self._apply_active_suggestion():
                self._insert_newline()
        elif key in ["ctrl+enter", "ctrl+j"]:
            # Ctrl+Enter or Ctrl+J - manually add newline
            self._insert_newline()
        elif key == "up":
            if self.suggestions:
                self._move_suggestion_selection(-1)
            else:
                self._history_previous()
        elif key == "down":
            if self.suggestions:
                self._move_suggestion_selection(1)
            else:
                self._history_next()
        elif key == "escape":
            if self.is_loading:
                self._handle_loading_escape()
            elif not self.input_value and len(self.messages) > 0:
                if self.on_show_message_selector:
                    self.on_show_message_selector()
            else:
                self.suggestions = []
                self._prefix_triggered_mode = None
                self._set_mode(InputMode.PROMPT)
        elif key == "shift+m":
            # Handle model switching
            self._handle_quick_model_switch()
        elif key == "shift+s":
            self.run_worker(self._handle_session_mode_switch(), exclusive=False)
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

        if self.is_disabled:
            return

        # Handle exit commands
        if input_text.lower() in ["exit", "quit", ":q", ":q!", ":wq", ":wq!"]:
            self._handle_exit()
            return

        # Handle slash commands (e.g., /clear, /help, /tools)
        if input_text.startswith("/"):
            if self.is_loading:
                return
            # Clear input immediately
            with text_area.prevent(TextArea.Changed):
                text_area.text = ""
            self.input_value = ""

            # Execute command (no AI processing, no "Thinking..." message)
            await self._handle_command_input(input_text)

            # Update history
            self._add_to_history(input_text)
            self._reset_history_navigation()
            return

        # 1. 立即清空输入框并重置模式 - 提供即时反馈
        original_mode = self.mode

        with text_area.prevent(TextArea.Changed):
            text_area.text = ""
        self.input_value = ""
        self._prefix_triggered_mode = None
        self._set_mode(InputMode.PROMPT)

        # 2. 统一创建用户消息并交给 REPL 处理
        user_message = self._create_user_message(input_text, original_mode)

        # 2a. 立即显示用户消息（同步操作，不等待网络）
        if self.on_add_user_message:
            self.on_add_user_message(user_message)

        # 2b. 让父组件统一处理 prompt/bash/memory
        if self.on_query:
            await self.on_query([user_message])

        # 3. 更新提交计数和历史记录
        self.submit_count += 1
        if self.on_submit_count_change:
            self.on_submit_count_change(lambda x: x + 1)

        self._add_to_history(input_text)
        self._reset_history_navigation()

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

    async def _handle_memory_input(self, input_text: str):
        """Handle memory mode input - equivalent to memory mode handling"""

        # Strip # prefix if present
        content = input_text[1:].strip() if input_text.startswith("#") else input_text

        # Check if this is an action prompt (put, create, generate, etc.)
        if any(
            word in content.lower()
            for word in ["put", "create", "generate", "write", "give", "provide"]
        ):
            # Handle as AI request for AGENTS.md content
            await self._handle_memory_ai_request(content)
        else:
            # Handle as direct note to AGENTS.md
            await self._handle_memory_note(content)

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

    async def _handle_memory_ai_request(self, content: str):
        """Handle AI request for memory mode"""

        # This would integrate with the AI system to generate content for AGENTS.md
        # For now, just log the request
        memory_context = (
            "The user is using Memory mode. Format your response as a comprehensive, "
            "well-structured document suitable for adding to AGENTS.md. Use proper "
            "markdown formatting with headings, lists, code blocks, etc."
        )

        # This would be processed by the main query system
        if self.on_query:
            user_message = MinionMessage(
                type=MessageType.USER,
                message=MessageContent(content),
                options={"isMemoryRequest": True, "memoryContext": memory_context},
            )
            await self.on_query([user_message])

    async def _handle_memory_note(self, content: str):
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

    def _handle_loading_escape(self) -> None:
        """Require a double-Esc gesture before interrupting active work."""
        now = time.monotonic()
        if self.interrupt_armed and now <= self._interrupt_deadline:
            self._disarm_interrupt()
            if self.on_interrupt:
                self.on_interrupt()
            return

        self.interrupt_armed = True
        self._interrupt_deadline = now + 1.5
        if self._interrupt_reset_timer is not None:
            self._interrupt_reset_timer.stop()
        self._interrupt_reset_timer = self.set_timer(1.5, self._disarm_interrupt)

    def _disarm_interrupt(self) -> None:
        """Clear the pending double-Esc interrupt gesture."""
        self.interrupt_armed = False
        self._interrupt_deadline = 0.0
        if self._interrupt_reset_timer is not None:
            self._interrupt_reset_timer.stop()
            self._interrupt_reset_timer = None

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

    def _apply_history_value(self, value: str) -> None:
        """Replace the input text with a history entry and move the cursor to the end."""
        try:
            text_area = self.query_one("#main_input", expect_type=CustomTextArea)
        except Exception:
            return

        self._applying_history = True
        try:
            with text_area.prevent(TextArea.Changed):
                text_area.text = value
                lines = value.split("\n") or [""]
                text_area.cursor_location = (len(lines) - 1, len(lines[-1]))
            self.input_value = value
            if self.on_input_change:
                self.on_input_change(value)
        finally:
            self._applying_history = False

    def _reset_history_navigation(self, clear_draft: bool = True) -> None:
        """Reset prompt history navigation state."""
        self.history_position = -1
        if clear_draft:
            self._history_draft = ""

    def _history_previous(self) -> None:
        """Load the previous prompt from persistent project history."""
        history = get_history()
        if not history:
            return

        try:
            text_area = self.query_one("#main_input", expect_type=CustomTextArea)
        except Exception:
            return

        if self.history_position == -1:
            self._history_draft = text_area.text
            next_position = 0
        else:
            next_position = min(self.history_position + 1, len(history) - 1)

        if next_position == self.history_position:
            return

        self.history_position = next_position
        self._apply_history_value(history[self.history_position])

    def _history_next(self) -> None:
        """Load the next prompt from persistent project history or restore the draft."""
        if self.history_position == -1:
            return

        history = get_history()
        if not history:
            self._reset_history_navigation()
            return

        if self.history_position <= 0:
            draft = self._history_draft
            self._reset_history_navigation(clear_draft=True)
            self._apply_history_value(draft)
            return

        self.history_position -= 1
        self._apply_history_value(history[self.history_position])

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

    async def _handle_session_mode_switch(self):
        """Open the session mode selector via the shared /mode command."""
        if self.on_execute_command:
            await self.on_execute_command("mode", "")
        else:
            self._show_temporary_message(
                "❌ Session mode selector is not available", duration=3.0
            )

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
        self._prefix_triggered_mode = None
        modes = list(InputMode)
        current_index = modes.index(self.mode)
        new_mode = modes[(current_index + 1) % len(modes)]
        self._set_mode(new_mode)

    # Reactive property watchers
    def watch_mode(self, mode: InputMode):
        """Watch mode changes and update UI"""
        try:
            # Update mode prefix
            prefix_widget = self.query_one("#mode_prefix", expect_type=Static)
            prefix_widget.update(self._get_mode_prefix())

            # Update input placeholder
            input_widget = self.query_one("#main_input", expect_type=CustomTextArea)
            if hasattr(input_widget, "placeholder"):
                input_widget.placeholder = self._get_placeholder()

            # Update container classes
            container = self.query_one("#input_container", expect_type=Horizontal)
            container.remove_class("mode-prompt", "mode-bash", "mode-memory")
            container.add_class(f"mode-{mode.value}")
        except:
            pass  # Widgets might not be mounted yet

    def watch_is_disabled(self, is_disabled: bool):
        """Keep the underlying text area disabled state in sync."""
        try:
            input_widget = self.query_one("#main_input", expect_type=CustomTextArea)
            input_widget.disabled = is_disabled
            if not is_disabled:
                input_widget.focus()
        except Exception:
            pass

    def watch_is_loading(self, is_loading: bool):
        """Watch loading state changes"""
        if not is_loading and self.interrupt_armed:
            self._disarm_interrupt()

    def watch_interrupt_armed(self, interrupt_armed: bool):
        """Update contextual footer text for the double-Esc gesture."""
        try:
            help_widget = self.query_one("#help_text", expect_type=Static)
            help_widget.update(self._get_help_text())
        except Exception:
            pass

    def watch_suggestions(self, suggestions: List[PromptSuggestion]):
        """Refresh the suggestions footer and contextual help."""
        try:
            help_widget = self.query_one("#help_text", expect_type=Static)
            help_widget.update(self._get_help_text())
        except Exception:
            pass

        try:
            widget = self.query_one("#suggestions_text", expect_type=Static)
            widget.update(self._get_suggestions_text() if suggestions else "")
        except Exception:
            pass

        self.refresh()

    def watch_suggestion_index(self, suggestion_index: int):
        """Update the rendered suggestions when the active row changes."""
        del suggestion_index
        if not self.suggestions:
            return
        try:
            widget = self.query_one("#suggestions_text", expect_type=Static)
            widget.update(self._get_suggestions_text())
        except Exception:
            self.refresh()

    def watch_input_value(self, value: str):
        """Watch input value changes"""
        try:
            input_widget = self.query_one("#main_input", expect_type=CustomTextArea)
            if input_widget.text != value:
                with input_widget.prevent(TextArea.Changed):
                    input_widget.text = value
        except:
            pass

    def watch_history_position(self, history_position: int):
        """Keep the draft in sync while the user is not browsing history."""
        if history_position == -1 and not self._applying_history:
            try:
                input_widget = self.query_one("#main_input", expect_type=CustomTextArea)
                self._history_draft = input_widget.text
            except Exception:
                self._history_draft = self.input_value
