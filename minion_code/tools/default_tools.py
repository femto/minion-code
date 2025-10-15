#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2024
@Author  : femto Zheng
@File    : default_tools.py
"""

import os
import subprocess
import glob
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from .base_tool import BaseTool


class FileReadTool(BaseTool):
    """文件读取工具"""
    
    name = "file_read"
    description = "读取文件内容，支持文本文件和图片文件"
    inputs = {
        "file_path": {"type": "string", "description": "要读取的文件路径"},
        "offset": {"type": "integer", "description": "起始行号（可选）", "nullable": True},
        "limit": {"type": "integer", "description": "读取行数限制（可选）", "nullable": True}
    }
    output_type = "string"
    
    def forward(self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
        """读取文件内容"""
        try:
            path = Path(file_path)
            if not path.exists():
                return f"错误：文件不存在 - {file_path}"
            
            if not path.is_file():
                return f"错误：路径不是文件 - {file_path}"
            
            # 检查是否为图片文件
            image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
            if path.suffix.lower() in image_extensions:
                return f"图片文件：{file_path}（大小：{path.stat().st_size} 字节）"
            
            # 读取文本文件
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            # 应用偏移和限制
            if offset is not None:
                lines = lines[offset:]
            if limit is not None:
                lines = lines[:limit]
            
            content = ''.join(lines)
            
            result = f"文件：{file_path}\n"
            result += f"总行数：{total_lines}\n"
            if offset is not None or limit is not None:
                result += f"显示行数：{len(lines)}\n"
            result += f"内容：\n{content}"
            
            return result
            
        except Exception as e:
            return f"读取文件时出错：{str(e)}"


class FileWriteTool(BaseTool):
    """文件写入工具"""
    
    name = "file_write"
    description = "写入内容到文件"
    inputs = {
        "file_path": {"type": "string", "description": "要写入的文件路径"},
        "content": {"type": "string", "description": "要写入的内容"}
    }
    output_type = "string"
    
    def forward(self, file_path: str, content: str) -> str:
        """写入文件内容"""
        try:
            path = Path(file_path)
            # 创建目录（如果不存在）
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"成功写入文件：{file_path}（{len(content)} 字符）"
            
        except Exception as e:
            return f"写入文件时出错：{str(e)}"


class BashTool(BaseTool):
    """Bash命令执行工具"""
    
    name = "bash"
    description = "执行bash命令"
    inputs = {
        "command": {"type": "string", "description": "要执行的bash命令"},
        "timeout": {"type": "integer", "description": "超时时间（秒）", "nullable": True}
    }
    output_type = "string"
    
    def forward(self, command: str, timeout: Optional[int] = 30) -> str:
        """执行bash命令"""
        try:
            # 安全检查：禁止危险命令
            dangerous_commands = ['rm -rf', 'sudo', 'su', 'chmod 777', 'mkfs', 'dd if=']
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return f"错误：禁止执行危险命令 - {command}"
            
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.getcwd()
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


class GrepTool(BaseTool):
    """文本搜索工具"""
    
    name = "grep"
    description = "在文件中搜索文本模式"
    inputs = {
        "pattern": {"type": "string", "description": "要搜索的正则表达式模式"},
        "path": {"type": "string", "description": "搜索路径（文件或目录）"},
        "include": {"type": "string", "description": "包含的文件模式（可选）", "nullable": True}
    }
    output_type = "string"
    
    def forward(self, pattern: str, path: str = ".", include: Optional[str] = None) -> str:
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
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append((str(file_path), line_num, line))
        except Exception:
            # 忽略无法读取的文件
            pass
        return matches
    
    def _is_text_file(self, file_path: Path) -> bool:
        """检查是否为文本文件"""
        text_extensions = {'.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md', '.yml', '.yaml', '.ini', '.cfg', '.conf'}
        return file_path.suffix.lower() in text_extensions


class GlobTool(BaseTool):
    """文件模式匹配工具"""
    
    name = "glob"
    description = "使用glob模式匹配文件"
    inputs = {
        "pattern": {"type": "string", "description": "glob模式"},
        "path": {"type": "string", "description": "搜索路径", "nullable": True}
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


class LsTool(BaseTool):
    """目录列表工具"""
    
    name = "ls"
    description = "列出目录内容"
    inputs = {
        "path": {"type": "string", "description": "要列出的目录路径", "nullable": True},
        "recursive": {"type": "boolean", "description": "是否递归列出", "nullable": True}
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


class PythonInterpreterTool(BaseTool):
    """Python代码执行工具"""
    
    name = "python_interpreter"
    description = "执行Python代码"
    inputs = {
        "code": {"type": "string", "description": "要执行的Python代码"}
    }
    output_type = "string"
    
    def __init__(self, authorized_imports=None):
        super().__init__()
        if authorized_imports is None:
            self.authorized_imports = [
                'math', 'random', 'datetime', 'json', 're', 'os', 'sys',
                'collections', 'itertools', 'functools', 'operator'
            ]
        else:
            self.authorized_imports = list(set(['math', 'random', 'datetime', 'json', 're', 'os', 'sys']) | set(authorized_imports))
    
    def forward(self, code: str) -> str:
        """执行Python代码"""
        import sys
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        # 创建受限的全局环境
        restricted_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'any': any,
                'all': all,
                '__import__': __import__,  # 添加 __import__ 函数
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


# 工具映射
TOOL_MAPPING = {
    tool_class.name: tool_class
    for tool_class in [
        FileReadTool,
        FileWriteTool,
        BashTool,
        GrepTool,
        GlobTool,
        LsTool,
        PythonInterpreterTool,
    ]
}

__all__ = [
    "FileReadTool",
    "FileWriteTool", 
    "BashTool",
    "GrepTool",
    "GlobTool",
    "LsTool",
    "PythonInterpreterTool",
    "TOOL_MAPPING"
]