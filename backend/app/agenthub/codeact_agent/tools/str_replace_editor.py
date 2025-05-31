"""
String replace editor tool for CodeAct agent matching OpenHands exactly
"""
from litellm import ChatCompletionToolParam


def create_str_replace_editor_tool() -> ChatCompletionToolParam:
    """Create string replace editor tool"""
    return {
        "type": "function",
        "function": {
            "name": "str_replace_editor",
            "description": "Custom editing tool for viewing, creating and editing files\n- Use str_replace_based_edit_tool for viewing, creating and editing files\n- This tool supports line-based editing with precise string replacements\n- Create files by using the 'create' command\n- View files by using the 'view' command  \n- Edit files by using the 'str_replace' command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["view", "create", "str_replace"],
                        "description": "The command to execute"
                    },
                    "path": {
                        "type": "string",
                        "description": "Absolute path to file"
                    },
                    "file_text": {
                        "type": "string",
                        "description": "Required parameter of str_replace_based_edit_tool function - Only used when command is 'create'"
                    },
                    "old_str": {
                        "type": "string",
                        "description": "Required parameter of str_replace_based_edit_tool function - Only used when command is 'str_replace'"
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Required parameter of str_replace_based_edit_tool function - Only used when command is 'str_replace'"
                    }
                },
                "required": ["command", "path"]
            }
        }
    }
