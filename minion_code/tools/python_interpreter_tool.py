#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python code execution tool
"""

import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from minion.tools import BaseTool


class PythonInterpreterTool(BaseTool):
    """Python code execution tool"""

    name = "python_interpreter"
    description = "Execute Python code"
    readonly = False  # Code execution may modify system state
    inputs = {"code": {"type": "string", "description": "Python code to execute"}}
    output_type = "string"

    def __init__(self, authorized_imports=None):
        super().__init__()
        if authorized_imports is None:
            self.authorized_imports = [
                "math",
                "random",
                "datetime",
                "json",
                "re",
                "os",
                "sys",
                "collections",
                "itertools",
                "functools",
                "operator",
            ]
        else:
            self.authorized_imports = list(
                set(["math", "random", "datetime", "json", "re", "os", "sys"])
                | set(authorized_imports)
            )

    def forward(self, code: str) -> str:
        """Execute Python code"""
        # Create restricted global environment
        restricted_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "sum": sum,
                "max": max,
                "min": min,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "reversed": reversed,
                "any": any,
                "all": all,
                "__import__": __import__,  # Add __import__ function
            }
        }

        # Add authorized imports
        for module_name in self.authorized_imports:
            try:
                restricted_globals[module_name] = __import__(module_name)
            except ImportError:
                pass

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, restricted_globals)

            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            output_parts = []
            if stdout_content:
                output_parts.append(f"Standard output:\n{stdout_content}")
            if stderr_content:
                output_parts.append(f"Standard error:\n{stderr_content}")

            if not output_parts:
                output_parts.append("Code executed successfully, no output.")

            return "\n".join(output_parts)

        except Exception as e:
            return f"Error executing code: {str(e)}"
