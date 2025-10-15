"""Tests for minion-code tools."""

import sys
import tempfile
import os
from pathlib import Path

# 添加 minion 框架路径
sys.path.insert(0, "/Users/femtozheng/python-project/minion1")

import pytest
from minion_code.tools import FileReadTool, FileWriteTool, BashTool, TOOL_MAPPING


def test_tool_mapping():
    """测试工具映射是否正确"""
    assert "file_read" in TOOL_MAPPING
    assert "file_write" in TOOL_MAPPING
    assert "bash" in TOOL_MAPPING
    assert len(TOOL_MAPPING) == 7  # 应该有7个工具


def test_file_read_tool():
    """测试文件读取工具"""
    tool = FileReadTool()

    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Hello\nWorld\nTest")
        temp_file = f.name

    try:
        # 测试读取文件
        result = tool.forward(temp_file)
        assert "Hello" in result
        assert "World" in result
        assert "Test" in result
        assert "总行数：3" in result
    finally:
        os.unlink(temp_file)


def test_file_write_tool():
    """测试文件写入工具"""
    tool = FileWriteTool()

    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = Path(temp_dir) / "test.txt"
        content = "Hello, World!"

        # 测试写入文件
        result = tool.forward(str(test_file), content)
        assert "成功写入文件" in result
        assert str(test_file) in result

        # 验证文件内容
        assert test_file.exists()
        assert test_file.read_text() == content


def test_bash_tool():
    """测试 Bash 工具"""
    tool = BashTool()

    # 测试简单命令
    result = tool.forward("echo 'Hello World'")
    assert "Hello World" in result
    assert "退出码：0" in result

    # 测试危险命令被阻止
    result = tool.forward("rm -rf /")
    assert "错误：禁止执行危险命令" in result


def test_tool_inheritance():
    """测试工具是否正确继承了 BaseTool"""
    from minion.tools import BaseTool

    tool = FileReadTool()
    assert isinstance(tool, BaseTool)
    assert hasattr(tool, "forward")
    assert hasattr(tool, "name")
    assert hasattr(tool, "description")
