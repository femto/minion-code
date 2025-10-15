#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化的基础工具类，从 minion 框架提取的核心功能
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseTool(ABC):
    """工具基类，定义所有工具的基本接口"""

    name: str = "base_tool"
    description: str = "基础工具类，所有工具应继承此类"
    inputs: Dict[str, Dict[str, Any]] = {}
    output_type: str = "any"

    def __init__(self):
        """初始化工具"""
        self.is_initialized = False

    def __call__(self, *args, **kwargs) -> Any:
        """
        调用工具执行，这是工具的主入口

        Returns:
            工具执行结果
        """
        if not self.is_initialized:
            self.setup()

        # 处理传入单一字典的情况
        if len(args) == 1 and len(kwargs) == 0 and isinstance(args[0], dict):
            potential_kwargs = args[0]
            if all(key in self.inputs for key in potential_kwargs):
                args = ()
                kwargs = potential_kwargs

        return self.forward(*args, **kwargs)

    @abstractmethod
    def forward(self, *args, **kwargs) -> Any:
        """
        实际的工具执行逻辑，子类必须实现此方法

        Args:
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            工具执行结果
        """
        raise NotImplementedError("工具子类必须实现forward方法")

    def setup(self):
        """
        在首次使用前执行初始化操作
        用于执行耗时的初始化操作（如加载模型）
        """
        self.is_initialized = True


def tool(func):
    """
    装饰器，将函数转换为BaseTool实例
    """

    class FunctionTool(BaseTool):
        name = func.__name__
        description = func.__doc__ or ""

        def __init__(self):
            super().__init__()
            self.is_initialized = True

        def forward(self, *args, **kwargs):
            return func(*args, **kwargs)

    return FunctionTool()


class ToolCollection:
    """工具集合，用于管理多个工具"""

    def __init__(self, tools):
        self.tools = tools
