"""
Browser tool for CodeAct agent matching OpenHands exactly
"""
from litellm import ChatCompletionToolParam


class BrowserTool:
    """Tool for browser interactions"""
    
    def to_tool_param(self) -> ChatCompletionToolParam:
        """Convert to tool parameter format"""
        return {
            "type": "function",
            "function": {
                "name": "browser",
                "description": "Browse the web by navigating to URLs or interacting with web pages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["navigate", "interact"],
                            "description": "The browser action to take"
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to (required when action is 'navigate')"
                        },
                        "coordinate": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Coordinates [x, y] to click on (required when action is 'interact')"
                        }
                    },
                    "required": ["action"]
                }
            }
        }
