#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件写入工具
"""

from pathlib import Path
from minion.tools import BaseTool


class FileWriteTool(BaseTool):
    """文件写入工具"""

    name = "file_write"
    description = "写入内容到文件"
    readonly = False  # 写入工具，会修改系统状态
    inputs = {
        "file_path": {"type": "string", "description": "要写入的文件路径"},
        "content": {"type": "string", "description": "要写入的内容"},
    }
    output_type = "string"

    def forward(self, file_path: str, content: str) -> str:
        """写入文件内容"""
        try:
            path = Path(file_path)
            # 创建目录（如果不存在）
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"成功写入文件：{file_path}（{len(content)} 字符）"

        except Exception as e:
            return f"写入文件时出错：{str(e)}"
