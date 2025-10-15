#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wikipedia 搜索工具
"""

from typing import Optional
from minion.tools import BaseTool


class WikipediaSearchTool(BaseTool):
    """Wikipedia 搜索工具"""

    name = "wikipedia_search"
    description = "搜索 Wikipedia 并返回主题摘要"
    readonly = True  # 只读工具，不会修改系统状态
    inputs = {
        "topic": {"type": "string", "description": "要搜索的主题"},
        "language": {
            "type": "string",
            "description": "语言代码（如 'zh', 'en'）",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, topic: str, language: Optional[str] = "zh") -> str:
        """搜索 Wikipedia"""
        try:
            # 这里是一个模拟实现，实际应该调用 Wikipedia API
            result = f"""
Wikipedia 搜索结果

主题: {topic}
语言: {language}

摘要:
这是关于 '{topic}' 的 Wikipedia 摘要。实际实现中，这里会包含从 Wikipedia API 获取的真实内容。

相关链接:
- https://{language}.wikipedia.org/wiki/{topic.replace(' ', '_')}

注意: 这是一个模拟实现，实际使用时需要安装 wikipedia-api 包并实现真实的搜索功能。
"""
            return result.strip()

        except Exception as e:
            return f"Wikipedia 搜索时出错：{str(e)}"
