#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
目录列表工具
"""

from pathlib import Path
from .base_tool import BaseTool


class LsTool(BaseTool):
    """目录列表工具"""

    name = "ls"
    description = "列出目录内容"
    inputs = {
        "path": {"type": "string", "description": "要列出的目录路径", "nullable": True},
        "recursive": {
            "type": "boolean",
            "description": "是否递归列出",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, path: str = ".", recursive: bool = False) -> str:
        """列出目录内容"""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return f"错误：路径不存在 - {path}"

            if not dir_path.is_dir():
                return f"错误：路径不是目录 - {path}"

            result = f"目录内容：{path}\n\n"

            if recursive:
                # 递归列出
                for item in sorted(dir_path.rglob("*")):
                    relative_path = item.relative_to(dir_path)
                    if item.is_file():
                        size = item.stat().st_size
                        result += f"  文件：{relative_path} ({size} 字节)\n"
                    elif item.is_dir():
                        result += f"  目录：{relative_path}/\n"
            else:
                # 只列出当前目录
                items = list(dir_path.iterdir())
                items.sort(key=lambda x: (x.is_file(), x.name.lower()))

                for item in items:
                    if item.is_file():
                        size = item.stat().st_size
                        result += f"  文件：{item.name} ({size} 字节)\n"
                    elif item.is_dir():
                        result += f"  目录：{item.name}/\n"
                    else:
                        result += f"  其他：{item.name}\n"

            return result

        except Exception as e:
            return f"列出目录时出错：{str(e)}"
