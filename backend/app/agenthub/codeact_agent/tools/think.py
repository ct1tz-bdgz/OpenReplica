"""
Think tool for CodeAct agent matching OpenHands exactly
"""
from litellm import ChatCompletionToolParam


class ThinkTool:
    """Tool for agent to express thoughts"""
    
    def to_tool_param(self) -> ChatCompletionToolParam:
        """Convert to tool parameter format"""
        return {
            "type": "function",
            "function": {
                "name": "think",
                "description": "Use this tool to express your thoughts or reasoning before taking action. This helps in planning and explaining your approach.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "thought": {
                            "type": "string",
                            "description": "Your thought or reasoning"
                        }
                    },
                    "required": ["thought"]
                }
            }
        }
