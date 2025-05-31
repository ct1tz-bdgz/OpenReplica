"""
Bash tool for CodeAct agent matching OpenHands exactly
"""
from litellm import ChatCompletionToolParam


def create_cmd_run_tool() -> ChatCompletionToolParam:
    """Create bash command execution tool"""
    return {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command in the terminal.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute. Make sure to escape special characters."
                    }
                },
                "required": ["command"]
            }
        }
    }
