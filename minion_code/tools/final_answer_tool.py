#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最终答案工具
"""

from typing import Optional
from minion.tools import BaseTool


class FinalAnswerTool(BaseTool):
    """最终答案工具"""

    name = "final_answer"
    description = "提供问题的最终答案"
    readonly = True  # 只读工具，不会修改系统状态
    inputs = {
        "answer": {"type": "string", "description": "最终答案内容"},
        "confidence": {
            "type": "number",
            "description": "答案的置信度（0-1）",
            "nullable": True,
        },
        "reasoning": {
            "type": "string",
            "description": "推理过程（可选）",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(
        self,
        answer: str,
        confidence: Optional[float] = None,
        reasoning: Optional[str] = None,
    ) -> str:
        """提供最终答案"""
        try:
            result = "=== 最终答案 ===\n\n"
            result += f"答案: {answer}\n"

            if confidence is not None:
                # 确保置信度在有效范围内
                confidence = max(0.0, min(1.0, confidence))
                result += f"置信度: {confidence:.2%}\n"

            if reasoning:
                result += f"\n推理过程:\n{reasoning}\n"

            result += "\n=== 答案结束 ==="
            return result

        except Exception as e:
            return f"生成最终答案时出错：{str(e)}"
