#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网络搜索工具
"""

from typing import Optional
from minion.tools import BaseTool


class WebSearchTool(BaseTool):
    """网络搜索工具"""

    name = "web_search"
    description = "执行网络搜索并返回搜索结果"
    readonly = True  # 只读工具，不会修改系统状态
    inputs = {
        "query": {"type": "string", "description": "搜索查询"},
        "max_results": {
            "type": "integer",
            "description": "最大结果数量",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, query: str, max_results: Optional[int] = 5) -> str:
        """执行网络搜索"""
        try:
            # 这里是一个模拟实现，实际应该调用搜索 API
            results = [
                f"搜索结果 {i+1}: 关于 '{query}' 的信息..."
                for i in range(min(max_results, 3))
            ]

            result_text = f"搜索查询: {query}\n\n"
            for i, result in enumerate(results, 1):
                result_text += f"{i}. {result}\n"

            result_text += f"\n找到 {len(results)} 个结果"
            return result_text

        except Exception as e:
            return f"搜索时出错：{str(e)}"
