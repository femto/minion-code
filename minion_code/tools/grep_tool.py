#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文本搜索工具
"""

import re
from pathlib import Path
from typing import List, Optional
from .base_tool import BaseTool


class GrepTool(BaseTool):
    """文本搜索工具"""

    name = "grep"
    description = "在文件中搜索文本模式"
    inputs = {
        "pattern": {"type": "string", "description": "要搜索的正则表达式模式"},
        "path": {"type": "string", "description": "搜索路径（文件或目录）"},
        "include": {
            "type": "string",
            "description": "包含的文件模式（可选）",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self, pattern: str, path: str = ".", include: Optional[str] = None
    ) -> str:
        """搜索文本模式"""
        try:
            search_path = Path(path)
            if not search_path.exists():
                return f"错误：路径不存在 - {path}"

            matches = []

            if search_path.is_file():
                # 搜索单个文件
                matches.extend(self._search_file(search_path, pattern))
            else:
                # 搜索目录
                if include:
                    # 使用文件模式过滤
                    for file_path in search_path.rglob(include):
                        if file_path.is_file():
                            matches.extend(self._search_file(file_path, pattern))
                else:
                    # 搜索所有文本文件
                    for file_path in search_path.rglob("*"):
                        if file_path.is_file() and self._is_text_file(file_path):
                            matches.extend(self._search_file(file_path, pattern))

            if not matches:
                return f"未找到匹配模式 '{pattern}' 的内容"

            # 按文件分组显示结果
            result = f"搜索模式 '{pattern}' 的结果：\n\n"
            current_file = None
            for file_path, line_num, line_content in matches:
                if file_path != current_file:
                    result += f"文件：{file_path}\n"
                    current_file = file_path
                result += f"  行 {line_num}: {line_content.strip()}\n"

            result += f"\n总共找到 {len(matches)} 个匹配项"
            return result

        except Exception as e:
            return f"搜索时出错：{str(e)}"

    def _search_file(self, file_path: Path, pattern: str) -> List[tuple]:
        """在单个文件中搜索模式"""
        matches = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append((str(file_path), line_num, line))
        except Exception:
            # 忽略无法读取的文件
            pass
        return matches

    def _is_text_file(self, file_path: Path) -> bool:
        """检查是否为文本文件"""
        text_extensions = {
            ".txt",
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".md",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
            ".conf",
        }
        return file_path.suffix.lower() in text_extensions
