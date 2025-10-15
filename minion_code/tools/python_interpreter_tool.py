#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python代码执行工具
"""

import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from minion.tools import BaseTool


class PythonInterpreterTool(BaseTool):
    """Python代码执行工具"""

    name = "python_interpreter"
    description = "执行Python代码"
    readonly = False  # 执行代码可能会修改系统状态
    inputs = {"code": {"type": "string", "description": "要执行的Python代码"}}
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
        """执行Python代码"""
        # 创建受限的全局环境
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
                "__import__": __import__,  # 添加 __import__ 函数
            }
        }

        # 添加授权的导入
        for module_name in self.authorized_imports:
            try:
                restricted_globals[module_name] = __import__(module_name)
            except ImportError:
                pass

        # 捕获输出
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, restricted_globals)

            stdout_content = stdout_capture.getvalue()
            stderr_content = stderr_capture.getvalue()

            output_parts = []
            if stdout_content:
                output_parts.append(f"标准输出：\n{stdout_content}")
            if stderr_content:
                output_parts.append(f"标准错误：\n{stderr_content}")

            if not output_parts:
                output_parts.append("代码执行成功，无输出。")

            return "\n".join(output_parts)

        except Exception as e:
            return f"执行代码时出错：{str(e)}"
