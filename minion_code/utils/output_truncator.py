#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Output truncation and size checking utilities for tools.

Handles:
- Built-in tool output truncation (400KB limit)
- MCP tool output checking (token limit)
- File size checking before read (with suggested tools for large files)
"""

from pathlib import Path
from typing import Optional

# ============ 配置常量 ============
MAX_OUTPUT_SIZE = 400 * 1024      # 400KB - 内置工具输出截断阈值
MAX_FILE_SIZE = 1_000_000         # 1MB - 文件读取大小阈值
MAX_TOKEN_LIMIT = 100_000         # MCP 工具 token 限制


# ============ 异常类 ============
class OutputTooLargeError(Exception):
    """内置工具输出过大"""
    pass


class MCPContentTooLargeError(Exception):
    """MCP 工具内容过大"""
    def __init__(self, message: str, token_count: Optional[int] = None):
        self.token_count = token_count
        super().__init__(message)


class FileTooLargeError(Exception):
    """文件过大，建议使用专用工具"""
    def __init__(
        self,
        message: str,
        file_path: str,
        file_size: int,
        suggested_tool: Optional[str] = None
    ):
        self.file_path = file_path
        self.file_size = file_size
        self.suggested_tool = suggested_tool
        super().__init__(message)


# ============ 执行前检查 ============
def check_file_size_before_read(
    file_path: str,
    max_size: int = MAX_FILE_SIZE
) -> None:
    """
    Read 工具执行前检查文件大小

    Args:
        file_path: 文件路径
        max_size: 最大允许大小（字节）

    Raises:
        FileTooLargeError: 文件过大时抛出，包含建议工具
    """
    path = Path(file_path)
    if not path.exists():
        return

    file_size = path.stat().st_size
    if file_size > max_size:
        size_mb = file_size / 1_000_000
        suffix = path.suffix.lower()

        # 根据文件类型建议专用工具
        tool_suggestions = {
            '.pdf': 'pdf 工具',
            '.xlsx': 'xlsx 工具',
            '.xls': 'xlsx 工具',
            '.docx': 'docx 工具',
            '.doc': 'docx 工具',
            '.pptx': 'pptx 工具',
        }
        suggested = tool_suggestions.get(suffix, '分页读取 (offset/limit 参数)')

        raise FileTooLargeError(
            f"文件过大 ({size_mb:.1f}MB > {max_size/1_000_000:.1f}MB)，请使用 {suggested}",
            file_path=str(path),
            file_size=file_size,
            suggested_tool=suggested
        )


# ============ 输出截断 ============
def truncate_output(
    output: str,
    max_size: int = MAX_OUTPUT_SIZE,
    tool_name: str = "",
) -> str:
    """
    截断内置工具输出（自动生效）

    Args:
        output: 原始输出
        max_size: 最大字节数，默认 400KB
        tool_name: 工具名，用于生成针对性提示

    Returns:
        截断后的输出（如果需要截断则添加提示）
    """
    output_bytes = output.encode('utf-8')
    if len(output_bytes) <= max_size:
        return output

    # 截断到 max_size 字节，确保不截断 UTF-8 字符
    truncated_bytes = output_bytes[:max_size]
    truncated = truncated_bytes.decode('utf-8', errors='ignore')

    total_size = len(output_bytes)
    hint = _get_tool_hint(tool_name)

    truncated += f"\n\n---\n⚠️ 输出被截断 (显示 {max_size/1024:.0f}KB / {total_size/1024:.0f}KB)\n{hint}"

    return truncated


def check_mcp_output(
    output: str,
    max_tokens: int = MAX_TOKEN_LIMIT
) -> str:
    """
    检查 MCP 工具输出，超过 token 限制则抛异常

    Args:
        output: MCP 工具输出
        max_tokens: 最大 token 数

    Returns:
        原始输出（如果未超限）

    Raises:
        MCPContentTooLargeError: 输出超过 token 限制
    """
    # 简单估算: 1 token ≈ 4 字符
    estimated_tokens = len(output) // 4

    if estimated_tokens > max_tokens:
        raise MCPContentTooLargeError(
            f"MCP 工具输出过大 (约 {estimated_tokens} tokens > {max_tokens} 限制)",
            token_count=estimated_tokens
        )

    return output


def _get_tool_hint(tool_name: str) -> str:
    """根据工具名返回获取完整内容的提示"""
    hints = {
        'bash': "提示: 使用 `| head -n N` 或 `| tail -n N` 限制输出行数",
        'grep': "提示: 使用 `head_limit` 参数，或更精确的搜索模式",
        'glob': "提示: 使用更具体的 pattern 缩小匹配范围",
        'ls': "提示: 避免递归模式，或指定更具体的子目录",
        'file_read': "提示: 使用 `offset` 和 `limit` 参数分页读取",
        'python': "提示: 在代码中控制 print 输出量",
    }
    return hints.get(tool_name, "提示: 使用更精确的参数缩小输出范围")
