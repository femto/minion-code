#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Final answer tool
"""

from typing import Optional
from minion.tools import BaseTool


class FinalAnswerTool(BaseTool):
    """Final answer tool"""

    name = "final_answer"
    description = "Provide the final answer to a question"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "answer": {"type": "string", "description": "Final answer content"},
        "confidence": {
            "type": "number",
            "description": "Confidence level of the answer (0-1)",
            "nullable": True,
        },
        "reasoning": {
            "type": "string",
            "description": "Reasoning process (optional)",
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
        """Provide final answer"""
        try:
            result = "=== Final Answer ===\n\n"
            result += f"Answer: {answer}\n"

            if confidence is not None:
                # Ensure confidence is within valid range
                confidence = max(0.0, min(1.0, confidence))
                result += f"Confidence: {confidence:.2%}\n"

            if reasoning:
                result += f"\nReasoning:\n{reasoning}\n"

            result += "\n=== End of Answer ==="
            return result

        except Exception as e:
            return f"Error generating final answer: {str(e)}"
