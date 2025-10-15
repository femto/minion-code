#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web search tool
"""

from typing import Optional
from minion.tools import BaseTool


class WebSearchTool(BaseTool):
    """Web search tool"""

    name = "web_search"
    description = "Perform web search and return search results"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "query": {"type": "string", "description": "Search query"},
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, query: str, max_results: Optional[int] = 5) -> str:
        """Perform web search"""
        try:
            # This is a mock implementation, should call search API in practice
            results = [
                f"Search result {i+1}: Information about '{query}'..."
                for i in range(min(max_results, 3))
            ]

            result_text = f"Search query: {query}\n\n"
            for i, result in enumerate(results, 1):
                result_text += f"{i}. {result}\n"

            result_text += f"\nFound {len(results)} results"
            return result_text

        except Exception as e:
            return f"Error during search: {str(e)}"
