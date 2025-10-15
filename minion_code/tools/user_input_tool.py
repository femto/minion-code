#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户输入工具
"""

from typing import Optional
from minion.tools import BaseTool


class UserInputTool(BaseTool):
    """用户输入工具"""

    name = "user_input"
    description = "向用户询问特定问题并获取输入"
    readonly = True  # 只读工具，不会修改系统状态
    inputs = {
        "question": {"type": "string", "description": "要询问用户的问题"},
        "default_value": {
            "type": "string",
            "description": "默认值（可选）",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, question: str, default_value: Optional[str] = None) -> str:
        """向用户询问问题"""
        try:
            # 构建提示信息
            prompt = f"问题: {question}"
            if default_value:
                prompt += f" (默认: {default_value})"
            prompt += "\n请输入您的回答: "

            # 获取用户输入
            user_response = input(prompt).strip()

            # 如果用户没有输入且有默认值，使用默认值
            if not user_response and default_value:
                user_response = default_value

            result = f"用户问题: {question}\n"
            if default_value:
                result += f"默认值: {default_value}\n"
            result += f"用户回答: {user_response}"

            return result

        except KeyboardInterrupt:
            return "用户取消了输入"
        except Exception as e:
            return f"获取用户输入时出错：{str(e)}"
