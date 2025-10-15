#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wikipedia search tool
"""

from typing import Optional
from minion.tools import BaseTool


class WikipediaSearchTool(BaseTool):
    """Wikipedia search tool"""

    name = "wikipedia_search"
    description = "Search Wikipedia and return topic summary"
    readonly = True  # Read-only tool, does not modify system state
    inputs = {
        "topic": {"type": "string", "description": "Topic to search for"},
        "language": {
            "type": "string",
            "description": "Language code (e.g., 'zh', 'en')",
            "nullable": True,
        },
    }
    output_type = "string"

    def forward(self, topic: str, language: Optional[str] = "zh") -> str:
        """Search Wikipedia"""
        try:
            # This is a mock implementation, should call Wikipedia API in practice
            result = f"""
Wikipedia Search Result

Topic: {topic}
Language: {language}

Summary:
This is the Wikipedia summary for '{topic}'. In actual implementation, this would contain real content retrieved from the Wikipedia API.

Related links:
- https://{language}.wikipedia.org/wiki/{topic.replace(' ', '_')}

Note: This is a mock implementation. For actual use, you need to install the wikipedia-api package and implement real search functionality.
"""
            return result.strip()

        except Exception as e:
            return f"Error during Wikipedia search: {str(e)}"
