#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
User input tool
"""

from typing import Optional
from minion.tools import BaseTool


class UserInputTool(BaseTool):
    """User input tool"""

    name = "user_input"
    description = "Ask user a specific question and get input"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "question": {"type": "string", "description": "Question to ask the user"},
        "default_value": {
            "type": "string",
            "description": "Default value (optional)",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, question: str, default_value: Optional[str] = None) -> str:
        """Ask user a question"""
        try:
            # Build prompt message
            prompt = f"Question: {question}"
            if default_value:
                prompt += f" (default: {default_value})"
            prompt += "\nPlease enter your answer: "

            # Get user input
            user_response = input(prompt).strip()

            # Use default value if user didn't input anything and default exists
            if not user_response and default_value:
                user_response = default_value

            result = f"User question: {question}\n"
            if default_value:
                result += f"Default value: {default_value}\n"
            result += f"User answer: {user_response}"

            return result

        except KeyboardInterrupt:
            return "User cancelled input"
        except Exception as e:
            return f"Error getting user input: {str(e)}"
