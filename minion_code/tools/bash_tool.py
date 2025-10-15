#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bash命令执行工具
"""

import os
import subprocess
from typing import Optional
from minion.tools import BaseTool


class BashTool(BaseTool):
    """Bash命令执行工具"""

    name = "bash"
    description = "执行bash命令"
    inputs = {
        "command": {"type": "string", "description": "要执行的bash命令"},
        "timeout": {
            "type": "integer",
            "description": "超时时间（秒）",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, command: str, timeout: Optional[int] = 30) -> str:
        """执行bash命令"""
        try:
            # 安全检查：禁止危险命令
            dangerous_commands = ["rm -rf", "sudo", "su", "chmod 777", "mkfs", "dd if="]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return f"错误：禁止执行危险命令 - {command}"

            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd(),
            )

            output = ""
            if result.stdout:
                output += f"标准输出：\n{result.stdout}\n"
            if result.stderr:
                output += f"标准错误：\n{result.stderr}\n"
            output += f"退出码：{result.returncode}"

            return output

        except subprocess.TimeoutExpired:
            return f"命令执行超时（{timeout}秒）"
        except Exception as e:
            return f"执行命令时出错：{str(e)}"
