#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件模式匹配工具
"""

import glob
from pathlib import Path
from minion.tools import BaseTool


class GlobTool(BaseTool):
    """文件模式匹配工具"""

    name = "glob"
    description = "使用glob模式匹配文件"
    inputs = {
        "pattern": {"type": "string", "description": "glob模式"},
        "path": {"type": "string", "description": "搜索路径", "nullable": True},
    }
    output_type = "string"

    def forward(self, pattern: str, path: str = ".") -> str:
        """使用glob模式匹配文件"""
        try:
            search_path = Path(path)
            if not search_path.exists():
                return f"错误：路径不存在 - {path}"

            # 构建完整的搜索模式
            if search_path.is_dir():
                full_pattern = str(search_path / pattern)
            else:
                full_pattern = pattern

            matches = glob.glob(full_pattern, recursive=True)
            matches.sort()

            if not matches:
                return f"未找到匹配模式 '{pattern}' 的文件"

            result = f"匹配模式 '{pattern}' 的文件：\n"
            for match in matches:
                path_obj = Path(match)
                if path_obj.is_file():
                    size = path_obj.stat().st_size
                    result += f"  文件：{match} ({size} 字节)\n"
                elif path_obj.is_dir():
                    result += f"  目录：{match}/\n"
                else:
                    result += f"  其他：{match}\n"

            result += f"\n总共找到 {len(matches)} 个匹配项"
            return result

        except Exception as e:
            return f"glob匹配时出错：{str(e)}"
