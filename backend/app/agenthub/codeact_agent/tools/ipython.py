"""
IPython tool for CodeAct agent matching OpenHands exactly
"""
from litellm import ChatCompletionToolParam


class IPythonTool:
    """IPython code execution tool"""
    
    def to_tool_param(self) -> ChatCompletionToolParam:
        """Convert to tool parameter format"""
        return {
            "type": "function",
            "function": {
                "name": "ipython",
                "description": "Execute Python code in an interactive IPython environment. Use this for data analysis, calculations, and running Python scripts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "The Python code to execute. Can be multiple lines."
                        }
                    },
                    "required": ["code"]
                }
            }
        }
