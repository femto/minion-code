"""Tests for readonly tools functionality."""

import sys

# 添加 minion 框架路径
sys.path.insert(0, "/Users/femtozheng/python-project/minion1")

import pytest
from minion_code.tools import (
    FileReadTool,
    FileWriteTool,
    BashTool,
    GrepTool,
    GlobTool,
    LsTool,
    PythonInterpreterTool,
    WebSearchTool,
    WikipediaSearchTool,
    VisitWebpageTool,
    UserInputTool,

)


def test_readonly_tools():
    """测试只读工具的 readonly 属性"""
    readonly_tools = [
        FileReadTool(),
        GrepTool(),
        GlobTool(),
        LsTool(),
        WebSearchTool(),
        WikipediaSearchTool(),
        VisitWebpageTool(),
        UserInputTool(),
    ]

    for tool in readonly_tools:
        assert tool.readonly is True, f"{tool.__class__.__name__} 应该是只读工具"


def test_readwrite_tools():
    """测试读写工具的 readonly 属性"""
    readwrite_tools = [
        FileWriteTool(),
        BashTool(),
        PythonInterpreterTool(),
    ]

    for tool in readwrite_tools:
        assert tool.readonly is False, f"{tool.__class__.__name__} 应该是读写工具"


def test_web_search_tool():
    """测试网络搜索工具"""
    tool = WebSearchTool()
    result = tool.forward("Python")
    assert "搜索查询: Python" in result
    assert "找到" in result


def test_wikipedia_search_tool():
    """测试 Wikipedia 搜索工具"""
    tool = WikipediaSearchTool()
    result = tool.forward("Python", "zh")
    assert "Wikipedia 搜索结果" in result
    assert "Python" in result


def test_visit_webpage_tool():
    """测试网页访问工具"""
    tool = VisitWebpageTool()
    result = tool.forward("https://www.example.com")
    assert "网页访问结果" in result
    assert "https://www.example.com" in result



def test_tool_inheritance():
    """测试所有工具都正确继承了 BaseTool"""
    from minion.tools import BaseTool

    tools = [
        FileReadTool(),
        FileWriteTool(),
        BashTool(),
        GrepTool(),
        GlobTool(),
        LsTool(),
        PythonInterpreterTool(),
        WebSearchTool(),
        WikipediaSearchTool(),
        VisitWebpageTool(),
        UserInputTool(),
    ]

    for tool in tools:
        assert isinstance(tool, BaseTool)
        assert hasattr(tool, "readonly")
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "forward")
