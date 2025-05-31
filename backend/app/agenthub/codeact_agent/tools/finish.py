"""
Finish tool for CodeAct agent matching OpenHands exactly
"""
from litellm import ChatCompletionToolParam


class FinishTool:
    """Tool for agent to finish a task"""
    
    def to_tool_param(self) -> ChatCompletionToolParam:
        """Convert to tool parameter format"""
        return {
            "type": "function",
            "function": {
                "name": "finish",
                "description": "Use this tool when you have completed the task. Provide a summary of what was accomplished and any relevant outputs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "A summary of what was accomplished"
                        },
                        "outputs": {
                            "type": "object",
                            "description": "Any relevant outputs or results from the task",
                            "additionalProperties": True
                        }
                    },
                    "required": ["summary"]
                }
            }
        }
