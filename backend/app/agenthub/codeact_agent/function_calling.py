"""
Function calling utilities for CodeAct agent matching OpenHands
"""
from typing import TYPE_CHECKING, List
import json

if TYPE_CHECKING:
    from app.llm.llm import ModelResponse
    from app.controller.agent import Agent
    from app.controller.state.state import State
    from app.events.action import Action

from app.core.logging import get_logger
from app.events.action import (
    CmdRunAction,
    IPythonRunCellAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    BrowseURLAction,
    BrowseInteractiveAction,
    MessageAction,
    AgentFinishAction,
    AgentThinkAction
)

logger = get_logger(__name__)


def response_to_actions(
    response: 'ModelResponse',
    agent: 'Agent',
    state: 'State'
) -> List['Action']:
    """Convert LLM response to a list of actions"""
    actions = []
    
    try:
        choice = response.choices[0] if response.choices else None
        if not choice:
            return [MessageAction("No response from LLM")]
        
        message = choice.message
        
        # Handle function/tool calls
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                action = _tool_call_to_action(tool_call)
                if action:
                    actions.append(action)
        
        # Handle regular message content
        if message.content and message.content.strip():
            actions.append(MessageAction(message.content.strip()))
        
        # If no actions were created, create a default message action
        if not actions:
            actions.append(MessageAction("I need to think about this..."))
            
    except Exception as e:
        logger.error(f"Error converting response to actions: {e}")
        actions.append(MessageAction(f"Error processing response: {str(e)}"))
    
    return actions


def _tool_call_to_action(tool_call) -> 'Action':
    """Convert a tool call to an action"""
    try:
        function_name = tool_call.function.name
        arguments_str = tool_call.function.arguments
        
        # Parse arguments
        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            return MessageAction(f"Invalid arguments for {function_name}: {arguments_str}")
        
        # Map function names to actions
        if function_name == "str_replace_editor":
            return _handle_str_replace_editor(arguments)
        elif function_name == "bash":
            return _handle_bash(arguments)
        elif function_name == "ipython":
            return _handle_ipython(arguments)
        elif function_name == "browser":
            return _handle_browser(arguments)
        elif function_name == "think":
            return _handle_think(arguments)
        elif function_name == "finish":
            return _handle_finish(arguments)
        else:
            return MessageAction(f"Unknown function: {function_name}")
            
    except Exception as e:
        logger.error(f"Error converting tool call to action: {e}")
        return MessageAction(f"Error processing tool call: {str(e)}")


def _handle_str_replace_editor(arguments: dict) -> 'Action':
    """Handle str_replace_editor tool calls"""
    command = arguments.get("command")
    path = arguments.get("path", "")
    
    if command == "view":
        return FileReadAction(path=path)
    elif command == "create":
        content = arguments.get("file_text", "")
        return FileWriteAction(path=path, content=content)
    elif command == "str_replace":
        old_str = arguments.get("old_str", "")
        new_str = arguments.get("new_str", "")
        return FileEditAction(path=path, old_str=old_str, new_str=new_str)
    else:
        return MessageAction(f"Unknown str_replace_editor command: {command}")


def _handle_bash(arguments: dict) -> 'Action':
    """Handle bash tool calls"""
    command = arguments.get("command", "")
    return CmdRunAction(command=command)


def _handle_ipython(arguments: dict) -> 'Action':
    """Handle ipython tool calls"""
    code = arguments.get("code", "")
    return IPythonRunCellAction(code=code)


def _handle_browser(arguments: dict) -> 'Action':
    """Handle browser tool calls"""
    action = arguments.get("action")
    
    if action == "navigate":
        url = arguments.get("url", "")
        return BrowseURLAction(url=url)
    elif action == "interact":
        coordinate = arguments.get("coordinate", [0, 0])
        return BrowseInteractiveAction(coordinate=coordinate)
    else:
        return MessageAction(f"Unknown browser action: {action}")


def _handle_think(arguments: dict) -> 'Action':
    """Handle think tool calls"""
    thought = arguments.get("thought", "")
    return AgentThinkAction(thought=thought)


def _handle_finish(arguments: dict) -> 'Action':
    """Handle finish tool calls"""
    outputs = arguments.get("outputs", {})
    summary = arguments.get("summary", "Task completed")
    return AgentFinishAction(outputs=outputs, summary=summary)
