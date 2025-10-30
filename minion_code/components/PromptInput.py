"""
PromptInput Component - Python equivalent of React PromptInput
Handles user input with multiple modes (prompt, bash, koding)
"""

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Input, Static, Button, TextArea
from textual.reactive import reactive, var
from textual import on, work
from textual.events import Key
from rich.text import Text
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
import time

# Simple logging setup for TUI - disable to prevent screen interference
import logging
logger = logging.getLogger(__name__)
logger.disabled = True

# Import shared types
from ..types import (
    InputMode, Message, MessageType, MessageContent, ModelInfo
)


class PromptInput(Container):
    """
    Main input component equivalent to React PromptInput
    Handles user input with mode switching and command processing
    """
    
    # Working CSS
    CSS = """
    PromptInput {
        dock: bottom;
        height: auto;
        min-height: 6;
        max-height: 15;
        margin: 1;
        border: solid white;
        padding: 1;
    }
    
    .mode-bash PromptInput {
        border: solid yellow;
    }
    
    .mode-koding PromptInput {
        border: solid cyan;
    }
    
    #mode_prefix {
        width: 3;
        content-align: center middle;
        text-style: bold;
    }
    
    #main_input {
        width: 1fr;
        height: auto;
        min-height: 1;
        max-height: 10;
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
    
    def __init__(self,
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
                 **kwargs):
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
        self.on_input_change: Optional[Callable] = None
        self.on_mode_change: Optional[Callable] = None
        self.on_submit_count_change: Optional[Callable] = None
        self.set_is_loading: Optional[Callable] = None
        self.set_abort_controller: Optional[Callable] = None
        self.on_show_message_selector: Optional[Callable] = None
        self.set_fork_convo_with_messages: Optional[Callable] = None
        self.on_model_change: Optional[Callable] = None
        self.set_tool_jsx: Optional[Callable] = None
        
        logger.info(f"PromptInput initialized in {mode.value} mode")
    
    def on_mount(self):
        """Set focus to input when component mounts"""
        try:
            input_widget = self.query_one("#main_input", expect_type=TextArea)
            input_widget.focus()
            logger.info("Focus set to main TextArea input")
        except Exception as e:
            logger.warning(f"Could not set focus to TextArea input: {e}")
    
    def compose(self):
        """Compose the PromptInput interface - working version"""
        # Model info at top
        yield self._render_model_info()
        
        # Help text
        yield Static("Enter to submit · Ctrl+Enter for new line · ! for bash · # for AGENTS.md", classes="help-text")
        
        # Input area with mode prefix
        with Horizontal():
            yield Static(self._get_mode_prefix(), id="mode_prefix")
            yield TextArea(
                text=self.input_value,
                id="main_input",
                disabled=self.is_disabled or self.is_loading,
                show_line_numbers=False
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
            id="claude-3-5-sonnet"
        )
    
    # Event handlers
    @on(TextArea.Changed, "#main_input")
    def on_textarea_changed(self, event: TextArea.Changed):
        """Handle TextArea content changes"""
        value = event.text_area.text
        
        # Handle mode switching based on input prefix
        if value.startswith('!'):
            if self.mode != InputMode.BASH:
                self.mode = InputMode.BASH
                if self.on_mode_change:
                    self.on_mode_change(InputMode.BASH)
        elif value.startswith('#'):
            if self.mode != InputMode.KODING:
                self.mode = InputMode.KODING
                if self.on_mode_change:
                    self.on_mode_change(InputMode.KODING)
        
        self.input_value = value
        if self.on_input_change:
            self.on_input_change(value)
    
    def on_key(self, event: Key) -> bool:
        """Handle key events - Ctrl+Enter for newline, Enter for submit"""
        # Only handle keys when the TextArea has focus
        try:
            text_area = self.query_one("#main_input", expect_type=TextArea)
            if not text_area.has_focus:
                return False
        except:
            return False
        
        if event.key == "enter":
            # Regular Enter - submit (prevent default TextArea behavior)
            self.run_worker(self._handle_submit())
            return True
        elif event.key == "ctrl+enter":
            # Ctrl+Enter - insert newline (let TextArea handle it naturally)
            return False
        
        # Handle other special keys
        if event.key in ["backspace", "delete"]:
            if self.mode == InputMode.BASH and not self.input_value:
                self.mode = InputMode.PROMPT
                if self.on_mode_change:
                    self.on_mode_change(InputMode.PROMPT)
                return True
            elif self.mode == InputMode.KODING and not self.input_value:
                self.mode = InputMode.PROMPT
                if self.on_mode_change:
                    self.on_mode_change(InputMode.PROMPT)
                return True
        
        # Handle escape key
        if event.key == "escape":
            if not self.input_value and not self.is_loading and len(self.messages) > 0:
                if self.on_show_message_selector:
                    self.on_show_message_selector()
                return True
            else:
                self.mode = InputMode.PROMPT
                if self.on_mode_change:
                    self.on_mode_change(InputMode.PROMPT)
                return True
        
        # Handle Shift+M for model switching
        if event.key == "shift+m":
            self._handle_quick_model_switch()
            return True
        
        # Handle Shift+Tab for mode cycling
        if event.key == "shift+tab":
            self._cycle_mode()
            return True
        
        return False

    async def _handle_submit(self):
        """Handle input submission - equivalent to onSubmit function"""
        try:
            text_area = self.query_one("#main_input", expect_type=TextArea)
            input_text = text_area.text.strip()
        except:
            return
        
        if not input_text:
            return
        
        if self.is_disabled or self.is_loading:
            return
        
        logger.info(f"Submitting input: {input_text[:50]}... (mode: {self.mode.value})")
        
        # Handle exit commands
        if input_text.lower() in ['exit', 'quit', ':q', ':q!', ':wq', ':wq!']:
            self._handle_exit()
            return
        
        # Handle different modes
        if self.mode == InputMode.KODING or input_text.startswith('#'):
            await self._handle_koding_input(input_text)
        elif self.mode == InputMode.BASH or input_text.startswith('!'):
            await self._handle_bash_input(input_text)
        else:
            await self._handle_prompt_input(input_text)
        
        # Clear input and reset mode
        text_area.text = ""
        self.input_value = ""
        self.mode = InputMode.PROMPT
        if self.on_mode_change:
            self.on_mode_change(InputMode.PROMPT)
        
        # Update submit count
        self.submit_count += 1
        if self.on_submit_count_change:
            self.on_submit_count_change(lambda x: x + 1)
    
    async def _handle_koding_input(self, input_text: str):
        """Handle koding mode input - equivalent to koding mode handling"""
        logger.info(f"Processing koding input: {input_text}")
        
        # Strip # prefix if present
        content = input_text[1:].strip() if input_text.startswith('#') else input_text
        
        # Check if this is an action prompt (put, create, generate, etc.)
        if any(word in content.lower() for word in ['put', 'create', 'generate', 'write', 'give', 'provide']):
            # Handle as AI request for AGENTS.md content
            await self._handle_koding_ai_request(content)
        else:
            # Handle as direct note to AGENTS.md
            await self._handle_koding_note(content)
        
        # Add to history
        self._add_to_history(f"#{input_text}" if not input_text.startswith('#') else input_text)
    
    async def _handle_bash_input(self, input_text: str):
        """Handle bash mode input - equivalent to bash command processing"""
        logger.info(f"Processing bash input: {input_text}")
        
        # Strip ! prefix if present
        command = input_text[1:].strip() if input_text.startswith('!') else input_text
        
        try:
            # Execute bash command (simplified version)
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Create assistant message with result
            if result.returncode == 0:
                response = result.stdout or "Command executed successfully"
            else:
                response = f"Error: {result.stderr}"
            
            # This would typically be handled by the parent REPL component
            logger.info(f"Bash command result: {response[:100]}...")
            
        except Exception as e:
            logger.error(f"Error executing bash command: {e}")
        
        # Add to history
        self._add_to_history(f"!{input_text}" if not input_text.startswith('!') else input_text)
    
    async def _handle_prompt_input(self, input_text: str):
        """Handle regular prompt input - equivalent to normal message processing"""
        logger.info(f"Processing prompt input: {input_text}")
        
        if self.set_is_loading:
            self.set_is_loading(True)
        
        # Create new abort controller
        if self.set_abort_controller:
            new_controller = asyncio.create_task(asyncio.sleep(0))  # Mock controller
            self.set_abort_controller(new_controller)
        
        # Process user input (this would integrate with the actual message processing)
        messages = await self._process_user_input(input_text, self.mode)
        
        if messages and self.on_query:
            await self.on_query(messages)
        
        # Add to history
        self._add_to_history(input_text)
    
    async def _handle_koding_ai_request(self, content: str):
        """Handle AI request for koding mode"""
        logger.info(f"Processing koding AI request: {content}")
        
        # This would integrate with the AI system to generate content for AGENTS.md
        # For now, just log the request
        koding_context = (
            "The user is using Koding mode. Format your response as a comprehensive, "
            "well-structured document suitable for adding to AGENTS.md. Use proper "
            "markdown formatting with headings, lists, code blocks, etc."
        )
        
        # This would be processed by the main query system
        if self.on_query:
            user_message = Message(
                type=MessageType.USER,
                message=MessageContent(content),
                options={"isKodingRequest": True, "kodingContext": koding_context}
            )
            await self.on_query([user_message])
    
    async def _handle_koding_note(self, content: str):
        """Handle direct note to AGENTS.md"""
        logger.info(f"Adding note to AGENTS.md: {content}")
        
        # Interpret and format the note using AI (simplified version)
        try:
            interpreted_content = await self._interpret_hash_command(content)
            self._handle_hash_command(interpreted_content)
        except Exception as e:
            logger.error(f"Error interpreting hash command: {e}")
            # Fallback to simple formatting
            formatted_content = f"# {content}\n\n_Added on {time.strftime('%Y-%m-%d %H:%M:%S')}_"
            self._handle_hash_command(formatted_content)
    
    async def _interpret_hash_command(self, content: str) -> str:
        """Interpret hash command using AI - equivalent to interpretHashCommand"""
        # This would integrate with the AI system
        # For now, return simple formatting
        return f"# {content}\n\n_Added on {time.strftime('%Y-%m-%d %H:%M:%S')}_"
    
    def _handle_hash_command(self, content: str):
        """Handle hash command - equivalent to handleHashCommand"""
        try:
            from pathlib import Path
            agents_md = Path("AGENTS.md")
            
            if agents_md.exists():
                with open(agents_md, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{content}\n")
                logger.info("Added content to AGENTS.md")
            else:
                logger.warning("AGENTS.md not found")
        except Exception as e:
            logger.error(f"Error writing to AGENTS.md: {e}")
    
    async def _process_user_input(self, input_text: str, mode: InputMode) -> List[Message]:
        """Process user input - equivalent to processUserInput"""
        user_message = Message(
            type=MessageType.USER,
            message=MessageContent(input_text),
            options={"mode": mode.value}
        )
        return [user_message]
    
    def _add_to_history(self, input_text: str):
        """Add input to history - equivalent to addToHistory"""
        logger.info(f"Added to history: {input_text[:50]}...")
    
    def _handle_exit(self):
        """Handle exit command"""
        logger.info("Exit command received")
        # This would typically exit the application
        # For now, just show exit message
        self.exit_message = {"show": True, "key": "Ctrl+C"}
        self.set_timer(3.0, lambda: setattr(self, 'exit_message', {"show": False, "key": ""}))
    

    
    def _handle_quick_model_switch(self):
        """Handle quick model switching - equivalent to handleQuickModelSwitch"""
        logger.info("Model switch requested")
        
        # This would integrate with the model manager
        # For now, show a mock message
        self.model_switch_message = {
            "show": True,
            "text": "✅ Model switching would happen here"
        }
        
        # Clear message after 3 seconds
        self.set_timer(3.0, lambda: setattr(self, 'model_switch_message', {"show": False, "text": ""}))
        
        if self.on_model_change:
            self.on_model_change()
    
    def _cycle_mode(self):
        """Cycle through input modes"""
        modes = list(InputMode)
        current_index = modes.index(self.mode)
        new_mode = modes[(current_index + 1) % len(modes)]
        self.mode = new_mode
        
        if self.on_mode_change:
            self.on_mode_change(new_mode)
        
        logger.info(f"Cycled to mode: {new_mode.value}")
    
    # Reactive property watchers
    def watch_mode(self, mode: InputMode):
        """Watch mode changes and update UI"""
        logger.info(f"Mode changed to: {mode.value}")
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
            input_widget = self.query_one("#main_input", expect_type=TextArea)
            input_widget.disabled = self.is_disabled or is_loading
        except:
            pass
    
    def watch_input_value(self, value: str):
        """Watch input value changes"""
        try:
            input_widget = self.query_one("#main_input", expect_type=TextArea)
            if input_widget.text != value:
                input_widget.text = value
        except:
            pass