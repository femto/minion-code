#!/usr/bin/env python3
"""
Gradio UI Demo with Minion Code Tools

This script demonstrates how to create a web interface using Gradio
with the minion_code.tools system for code analysis and manipulation.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from minion_code.tools import (
    FileReadTool,
    FileWriteTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool,
    TOOL_MAPPING,
)


class MinionCodeToolsGradio:
    """Gradio web interface for Minion Code Tools."""

    def __init__(self):
        """Initialize the Gradio interface with available tools."""
        self.tools = {
            "read": FileReadTool(),
            "write": FileWriteTool(),
            "bash": BashTool(),
            "grep": GrepTool(),
            "glob": GlobTool(),
            "ls": LsTool(),
            "python": PythonInterpreterTool(),
        }

    def process_tool_request(self, tool_name: str, *args) -> str:
        """Process a tool request and return the result."""
        try:
            if tool_name not in self.tools:
                return f"❌ Unknown tool: {tool_name}"

            tool = self.tools[tool_name]
            result = tool(*args)
            return str(result)
        except Exception as e:
            return f"❌ Error executing {tool_name}: {str(e)}"

    def create_interface(self):
        """Create and return the Gradio interface."""
        try:
            import gradio as gr
        except ImportError:
            print("❌ Gradio is not installed. Please install it with:")
            print("   pip install gradio")
            sys.exit(1)

        with gr.Blocks(title="Minion Code Tools", theme=gr.themes.Soft()) as interface:
            gr.Markdown("# 🛠️ Minion Code Tools")
            gr.Markdown(
                "A powerful collection of development tools for code analysis and manipulation."
            )

            with gr.Tabs():
                # File Operations Tab
                with gr.TabItem("📁 File Operations"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Read File")
                            read_file_path = gr.Textbox(
                                label="File Path", placeholder="path/to/file.txt"
                            )
                            read_offset = gr.Number(
                                label="Offset (optional)", value=None, precision=0
                            )
                            read_limit = gr.Number(
                                label="Limit (optional)", value=None, precision=0
                            )
                            read_btn = gr.Button("Read File", variant="primary")
                            read_output = gr.Textbox(
                                label="Output", lines=10, max_lines=20
                            )

                        with gr.Column():
                            gr.Markdown("### Write File")
                            write_file_path = gr.Textbox(
                                label="File Path", placeholder="path/to/file.txt"
                            )
                            write_content = gr.Textbox(
                                label="Content", lines=5, placeholder="File content..."
                            )
                            write_btn = gr.Button("Write File", variant="primary")
                            write_output = gr.Textbox(label="Output", lines=3)

                # Directory Operations Tab
                with gr.TabItem("📂 Directory Operations"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### List Directory")
                            ls_path = gr.Textbox(
                                label="Directory Path", value=".", placeholder="."
                            )
                            ls_recursive = gr.Checkbox(label="Recursive", value=False)
                            ls_btn = gr.Button("List Directory", variant="primary")
                            ls_output = gr.Textbox(
                                label="Output", lines=15, max_lines=25
                            )

                        with gr.Column():
                            gr.Markdown("### Find Files (Glob)")
                            glob_pattern = gr.Textbox(
                                label="Pattern", placeholder="*.py"
                            )
                            glob_path = gr.Textbox(
                                label="Search Path", value=".", placeholder="."
                            )
                            glob_btn = gr.Button("Find Files", variant="primary")
                            glob_output = gr.Textbox(
                                label="Output", lines=15, max_lines=25
                            )

                # Search Tab
                with gr.TabItem("🔍 Search"):
                    gr.Markdown("### Search Text in Files (Grep)")
                    with gr.Row():
                        grep_pattern = gr.Textbox(
                            label="Search Pattern", placeholder="import"
                        )
                        grep_path = gr.Textbox(
                            label="Search Path", value=".", placeholder="."
                        )
                        grep_include = gr.Textbox(
                            label="File Pattern (optional)", placeholder="*.py"
                        )
                    grep_btn = gr.Button("Search", variant="primary")
                    grep_output = gr.Textbox(
                        label="Search Results", lines=15, max_lines=30
                    )

                # Code Execution Tab
                with gr.TabItem("🐍 Python Execution"):
                    gr.Markdown("### Execute Python Code")
                    python_code = gr.Code(
                        label="Python Code", language="python", lines=10
                    )
                    python_btn = gr.Button("Execute Code", variant="primary")
                    python_output = gr.Textbox(label="Output", lines=10, max_lines=20)

                # Bash Tab
                with gr.TabItem("💻 Bash Commands"):
                    gr.Markdown("### Execute Bash Commands")
                    gr.Markdown(
                        "⚠️ **Warning**: Only safe commands are allowed. Dangerous commands are blocked."
                    )
                    bash_command = gr.Textbox(
                        label="Command", placeholder="echo 'Hello World'"
                    )
                    bash_timeout = gr.Number(
                        label="Timeout (seconds)", value=30, precision=0
                    )
                    bash_btn = gr.Button("Execute Command", variant="primary")
                    bash_output = gr.Textbox(label="Output", lines=10, max_lines=20)

            # Event handlers
            read_btn.click(
                fn=lambda path, offset, limit: self.process_tool_request(
                    "read", path, offset, limit
                ),
                inputs=[read_file_path, read_offset, read_limit],
                outputs=read_output,
            )

            write_btn.click(
                fn=lambda path, content: self.process_tool_request(
                    "write", path, content
                ),
                inputs=[write_file_path, write_content],
                outputs=write_output,
            )

            ls_btn.click(
                fn=lambda path, recursive: self.process_tool_request(
                    "ls", path, recursive
                ),
                inputs=[ls_path, ls_recursive],
                outputs=ls_output,
            )

            glob_btn.click(
                fn=lambda pattern, path: self.process_tool_request(
                    "glob", pattern, path
                ),
                inputs=[glob_pattern, glob_path],
                outputs=glob_output,
            )

            grep_btn.click(
                fn=lambda pattern, path, include: self.process_tool_request(
                    "grep", pattern, path, include if include else None
                ),
                inputs=[grep_pattern, grep_path, grep_include],
                outputs=grep_output,
            )

            python_btn.click(
                fn=lambda code: self.process_tool_request("python", code),
                inputs=[python_code],
                outputs=python_output,
            )

            bash_btn.click(
                fn=lambda command, timeout: self.process_tool_request(
                    "bash", command, timeout
                ),
                inputs=[bash_command, bash_timeout],
                outputs=bash_output,
            )

        return interface


def setup():
    """Set up the Gradio interface."""
    print("🚀 Starting Minion Code Tools Gradio Demo...")
    print("📝 This demo uses the minion_code.tools system")

    # Check if gradio is available
    try:
        import gradio as gr

        print(f"✅ Gradio {gr.__version__} is available")
    except ImportError:
        print("❌ Gradio is not installed. Please install it with:")
        print("   pip install gradio")
        sys.exit(1)

    # Create the Gradio interface
    print("🎨 Creating Gradio interface...")
    gradio_app = MinionCodeToolsGradio()
    interface = gradio_app.create_interface()
    print("✅ Gradio interface created successfully!")

    return interface


def run():
    """Run the Gradio application."""
    try:
        interface = setup()

        print("🌐 Launching web interface...")
        print("📝 You can use the tools to:")
        print("   - Read and write files")
        print("   - Execute Python code")
        print("   - Run bash commands")
        print("   - Search text in files")
        print("   - Find files with patterns")
        print("   - List directory contents")
        print("   - And much more!")
        print()
        print("🛑 Press Ctrl+C to stop the server")

        # Launch the interface
        interface.launch(
            share=False,  # Set to True to create a public link
            debug=False,  # Set to True for debug mode
            server_port=None,  # Let Gradio auto-select an available port
        )

    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run()
