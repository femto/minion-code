# OutputAdapter Implementation

## Overview

The OutputAdapter pattern decouples command business logic from UI rendering, allowing commands to work seamlessly in both CLI (Rich) and TUI (Textual) environments.

## Architecture

```
Command Layer (Business Logic)
    ↓
OutputAdapter (Abstract Interface)
    ↓
├─→ RichOutputAdapter (CLI mode - blocking)
└─→ TextualOutputAdapter (TUI mode - async non-blocking)
```

## Key Components

### 1. Output Adapters

**Location**: `minion_code/adapters/`

- **`output_adapter.py`**: Abstract base class defining the interface
- **`rich_adapter.py`**: CLI implementation using Rich Console (blocking I/O)
- **`textual_adapter.py`**: TUI implementation using asyncio.Future (non-blocking)

### 2. TUI Dialog Components

**Location**: `minion_code/components/ConfirmDialog.py`

- `ConfirmDialog`: Yes/No confirmation dialogs
- `ChoiceDialog`: Multiple choice selection
- `InputDialog`: Text input prompts

### 3. Updated Commands

**Location**: `minion_code/commands/`

All commands now use `self.output` instead of `self.console`:

- `clear_command.py`: Uses `await self.output.confirm()` for user confirmation
- `history_command.py`: Uses `self.output.panel()` for display
- `status_command.py`: Uses `self.output.table()` for tabular data

## Usage Examples

### In Commands

```python
from minion_code.commands import BaseCommand

class MyCommand(BaseCommand):
    name = "my_command"
    description = "Example command"

    async def execute(self, args: str) -> None:
        # Display info
        self.output.panel("Info message", title="Info", border_style="blue")

        # Ask for confirmation
        confirmed = await self.output.confirm(
            "Are you sure?",
            title="Confirm Action",
            ok_text="Yes",
            cancel_text="No"
        )

        if confirmed:
            # Do something
            self.output.panel("Action completed!", border_style="green")
        else:
            self.output.panel("Action cancelled", border_style="yellow")
```

### In CLI Mode

```python
from minion_code.adapters import RichOutputAdapter
from minion_code.commands import command_registry
from rich.console import Console

# Create Rich adapter
console = Console()
adapter = RichOutputAdapter(console)

# Create command with adapter
cmd_class = command_registry.get_command("clear")
command = cmd_class(adapter, agent)

# Execute (blocks on user interaction)
await command.execute("")
```

### In TUI Mode

```python
from minion_code.adapters import TextualOutputAdapter

class REPL(Container):
    def __init__(self):
        super().__init__()

        # Create adapter with callback
        self.output_adapter = TextualOutputAdapter(
            on_output=self.handle_command_output
        )

        # Dialog tracking
        self.active_dialog = None

    def handle_command_output(self, output_type: str, data: dict):
        """Route output to appropriate handler"""
        if output_type == "confirm":
            self.show_confirm_dialog(data)
        elif output_type == "panel":
            self.display_panel_output(data)
        # ... etc

    def show_confirm_dialog(self, data: dict):
        """Display confirmation dialog"""
        dialog = ConfirmDialog(
            interaction_id=data["interaction_id"],
            message=data["message"],
            title=data.get("title", "Confirm"),
            on_result=self.handle_confirm_result
        )
        self.mount(dialog)

    def handle_confirm_result(self, interaction_id: str, result: bool):
        """User clicked Yes/No"""
        # Resolve the waiting Future in adapter
        self.output_adapter.resolve_interaction(interaction_id, result)
```

## Execution Flow (User Confirmation)

### CLI Mode (Blocking)
```
1. Command: await output.confirm("Clear history?")
2. RichAdapter: Confirm.ask() - blocks terminal
3. User types 'y' or 'n'
4. Returns True/False immediately
5. Command continues
```

### TUI Mode (Non-blocking)
```
1. Command: await output.confirm("Clear history?")
2. TextualAdapter:
   - Creates asyncio.Future
   - Calls on_output("confirm", {...})
   - await future (suspends)
3. REPL.handle_command_output():
   - Receives "confirm" event
   - Shows ConfirmDialog
4. User clicks "Yes" button
5. ConfirmDialog.on_ok():
   - Calls on_result callback
6. REPL.handle_confirm_result():
   - Calls adapter.resolve_interaction(id, True)
7. TextualAdapter:
   - Sets future.set_result(True)
8. Command resumes from await
9. Command continues with result
```

## Agent Tool Confirmation (Advanced)

For agent tools that need user confirmation (e.g., dangerous bash commands):

```python
# In tool implementation
class BashTool:
    async def __call__(self, command: str):
        if self.is_dangerous(command):
            confirmed = await self.request_confirmation({
                "tool_name": "bash",
                "action": f"Execute: {command}",
                "message": f"⚠️ Execute dangerous command?\n\n`{command}`"
            })

            if not confirmed:
                return "❌ Command cancelled by user"

        return await self._execute(command)

# Agent binds adapter to tools
agent.set_output_adapter(repl.output_adapter)
```

## Benefits

✅ **Unified API**: Commands work identically in CLI and TUI
✅ **Async Support**: Non-blocking user interactions in TUI
✅ **Type Safety**: Abstract interface ensures consistent implementation
✅ **Backward Compatible**: CLI mode unchanged, Rich console still accessible
✅ **Extensible**: Easy to add new interaction types (choice, input, etc.)
✅ **Agent Integration**: Tools can request user confirmation mid-execution

## Testing

### Test CLI Mode
```bash
# Run any command with Rich adapter
python -m minion_code.cli
/clear
# Should show Rich confirmation dialog
```

### Test TUI Mode
```bash
# Run TUI
python -m minion_code.screens.REPL
# Execute /clear command
# Should show Textual dialog with buttons
```

## Migration Guide

To update existing commands:

1. Replace `self.console.print(Panel(...))` with `self.output.panel(...)`
2. Replace `Confirm.ask()` with `await self.output.confirm(...)`
3. Replace `Table` creation with `self.output.table(headers, rows)`
4. Make command `execute()` method `async` if not already

**Before:**
```python
def execute(self, args: str):
    panel = Panel("Message", title="Title")
    self.console.print(panel)

    if Confirm.ask("Sure?", console=self.console):
        # do something
        pass
```

**After:**
```python
async def execute(self, args: str):
    self.output.panel("Message", title="Title")

    if await self.output.confirm("Sure?"):
        # do something
        pass
```

## Files Created/Modified

### New Files
- `minion_code/adapters/__init__.py`
- `minion_code/adapters/output_adapter.py`
- `minion_code/adapters/rich_adapter.py`
- `minion_code/adapters/textual_adapter.py`
- `minion_code/components/ConfirmDialog.py`

### Modified Files
- `minion_code/commands/__init__.py` - BaseCommand now takes `output` parameter
- `minion_code/commands/clear_command.py` - Uses adapter
- `minion_code/commands/history_command.py` - Uses adapter
- `minion_code/commands/status_command.py` - Uses adapter
- `minion_code/components/__init__.py` - Exports dialog components
- `minion_code/screens/REPL.py` - Integrates TextualAdapter

## Future Enhancements

- Add `ProgressDialog` for long-running operations
- Support for multi-select in `ChoiceDialog`
- Rich formatting preservation in TUI mode
- Auto-dismiss dialogs after timeout
- Dialog stacking/queuing for multiple interactions
