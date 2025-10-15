#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件读取工具
"""

from pathlib import Path
from typing import Optional
from minion.tools import BaseTool


class FileReadTool(BaseTool):
    """文件读取工具"""

    name = "file_read"
    description = "读取文件内容，支持文本文件和图片文件"
    readonly = True  # 只读工具，不会修改系统状态
    inputs = {
        "file_path": {"type": "string", "description": "要读取的文件路径"},
        "offset": {
            "type": "integer",
            "description": "起始行号（可选）",
            "nullable": True,
        },
        "limit": {
            "type": "integer",
            "description": "读取行数限制（可选）",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None
    ) -> str:
        """读取文件内容"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"错误：文件不存在 - {file_path}"

            if not path.is_file():
                return f"错误：路径不是文件 - {file_path}"

            # 检查是否为图片文件
            image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
            if path.suffix.lower() in image_extensions:
                return f"图片文件：{file_path}（大小：{path.stat().st_size} 字节）"

            # 读取文本文件
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)

            # 应用偏移和限制
            if offset is not None:
                lines = lines[offset:]
            if limit is not None:
                lines = lines[:limit]

            content = "".join(lines)

            result = f"文件：{file_path}\n"
            result += f"总行数：{total_lines}\n"
            if offset is not None or limit is not None:
                result += f"显示行数：{len(lines)}\n"
            result += f"内容：\n{content}"

            return result

        except Exception as e:
            return f"读取文件时出错：{str(e)}"
