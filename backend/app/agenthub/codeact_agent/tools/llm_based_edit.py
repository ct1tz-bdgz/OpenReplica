"""
LLM-based file edit tool for CodeAct agent matching OpenHands exactly
"""
from litellm import ChatCompletionToolParam


class LLMBasedFileEditTool:
    """Tool for LLM-based file editing"""
    
    def to_tool_param(self) -> ChatCompletionToolParam:
        """Convert to tool parameter format"""
        return {
            "type": "function",
            "function": {
                "name": "llm_file_edit",
                "description": "Use an LLM to edit files intelligently. This tool can make complex edits, refactoring, and improvements to code files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to edit"
                        },
                        "instruction": {
                            "type": "string",
                            "description": "Instruction for how to edit the file"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "Starting line number for partial edits (optional)"
                        },
                        "end_line": {
                            "type": "integer", 
                            "description": "Ending line number for partial edits (optional)"
                        }
                    },
                    "required": ["path", "instruction"]
                }
            }
        }
