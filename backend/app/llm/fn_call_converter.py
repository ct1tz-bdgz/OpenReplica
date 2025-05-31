"""
Function calling converter for OpenReplica matching OpenHands
Converts between function calling and non-function calling formats
"""
import json
import re
from typing import Any, Dict, List

from app.core.logging import get_logger

logger = get_logger(__name__)

# Stop words for models that support them
STOP_WORDS = [
    '</execute_ipython>',
    '</execute_bash>',
    '</execute_browse>',
    '</execute_str_replace_editor>',
    '</function_calls>',
    '</invoke>',
    '</finish>',
    '<|im_end|>',
    '<|endoftext|>',
    '<|end|>',
    '<|stop|>',
    'Human:',
    'Assistant:',
    'User:',
    'System:',
]


def convert_fncall_messages_to_non_fncall_messages(
    messages: List[Dict[str, Any]], 
    tools: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Convert function calling messages to non-function calling format.
    
    This is used for models that don't support native function calling.
    """
    if not tools:
        return messages
    
    converted_messages = []
    tools_description = _format_tools_description(tools)
    
    # Add tools description to system message or create one
    system_message_added = False
    
    for message in messages:
        if message.get('role') == 'system' and not system_message_added:
            # Add tools to existing system message
            content = message.get('content', '')
            content += f"\n\n{tools_description}"
            converted_messages.append({
                'role': 'system',
                'content': content
            })
            system_message_added = True
        elif message.get('role') == 'assistant' and 'tool_calls' in message:
            # Convert tool calls to text format
            content = message.get('content', '')
            if content:
                content += '\n\n'
            
            content += _format_tool_calls_as_text(message['tool_calls'])
            converted_messages.append({
                'role': 'assistant', 
                'content': content
            })
        elif message.get('role') == 'tool':
            # Convert tool response to user message
            tool_name = message.get('name', 'unknown_tool')
            tool_content = message.get('content', '')
            
            converted_messages.append({
                'role': 'user',
                'content': f"Tool '{tool_name}' returned:\n{tool_content}"
            })
        else:
            # Regular message
            converted_messages.append(message)
    
    # Add tools description as system message if not added yet
    if not system_message_added and tools_description:
        converted_messages.insert(0, {
            'role': 'system',
            'content': tools_description
        })
    
    return converted_messages


def convert_non_fncall_messages_to_fncall_messages(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Convert non-function calling messages to function calling format.
    
    This attempts to parse text-based tool calls and convert them to structured format.
    """
    if not tools:
        return messages
    
    converted_messages = []
    tool_names = {tool['function']['name'] for tool in tools}
    
    for message in messages:
        if message.get('role') == 'assistant':
            content = message.get('content', '')
            tool_calls, remaining_content = _extract_tool_calls_from_text(content, tool_names)
            
            if tool_calls:
                # Create assistant message with tool calls
                assistant_msg = {
                    'role': 'assistant',
                    'content': remaining_content.strip() if remaining_content.strip() else None
                }
                if tool_calls:
                    assistant_msg['tool_calls'] = tool_calls
                converted_messages.append(assistant_msg)
            else:
                converted_messages.append(message)
        else:
            converted_messages.append(message)
    
    return converted_messages


def _format_tools_description(tools: List[Dict[str, Any]]) -> str:
    """Format tools description for non-function calling models"""
    if not tools:
        return ""
    
    description = "You have access to the following tools:\n\n"
    
    for tool in tools:
        func_info = tool.get('function', {})
        name = func_info.get('name', 'unknown')
        desc = func_info.get('description', 'No description')
        params = func_info.get('parameters', {})
        
        description += f"Tool: {name}\n"
        description += f"Description: {desc}\n"
        
        if params and 'properties' in params:
            description += "Parameters:\n"
            for param_name, param_info in params['properties'].items():
                param_type = param_info.get('type', 'unknown')
                param_desc = param_info.get('description', 'No description')
                required = param_name in params.get('required', [])
                req_str = " (required)" if required else " (optional)"
                description += f"  - {param_name} ({param_type}){req_str}: {param_desc}\n"
        
        description += "\n"
    
    description += """To use a tool, format your response as:
<function_calls>
<invoke name="tool_name">
<parameter name="param1">value1</parameter>
<parameter name="param2">value2</parameter>
</invoke>
</function_calls>"""
    
    return description


def _format_tool_calls_as_text(tool_calls: List[Dict[str, Any]]) -> str:
    """Format tool calls as text for non-function calling models"""
    if not tool_calls:
        return ""
    
    text = "<function_calls>\n"
    
    for tool_call in tool_calls:
        function = tool_call.get('function', {})
        name = function.get('name', 'unknown')
        arguments = function.get('arguments', '{}')
        
        # Parse arguments
        try:
            if isinstance(arguments, str):
                args_dict = json.loads(arguments)
            else:
                args_dict = arguments
        except json.JSONDecodeError:
            args_dict = {}
        
        text += f'<invoke name="{name}">\n'
        for param_name, param_value in args_dict.items():
            # Escape XML special characters
            escaped_value = str(param_value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            text += f'<parameter name="{param_name}">{escaped_value}</parameter>\n'
        text += '</invoke>\n'
    
    text += "</function_calls>"
    return text


def _extract_tool_calls_from_text(
    text: str, 
    tool_names: set[str]
) -> tuple[List[Dict[str, Any]], str]:
    """Extract tool calls from text format"""
    tool_calls = []
    remaining_text = text
    
    # Pattern to match function calls
    function_calls_pattern = r'<function_calls>(.*?)</function_calls>'
    invoke_pattern = r'<invoke name="([^"]+)">(.*?)</invoke>'
    param_pattern = r'<parameter name="([^"]+)">([^<]*)</parameter>'
    
    # Find all function_calls blocks
    function_calls_matches = re.finditer(function_calls_pattern, text, re.DOTALL)
    
    for match in function_calls_matches:
        function_calls_content = match.group(1)
        
        # Find all invoke blocks within this function_calls block
        invoke_matches = re.finditer(invoke_pattern, function_calls_content, re.DOTALL)
        
        for invoke_match in invoke_matches:
            tool_name = invoke_match.group(1)
            invoke_content = invoke_match.group(2)
            
            # Only process if it's a known tool
            if tool_name in tool_names:
                # Extract parameters
                param_matches = re.finditer(param_pattern, invoke_content)
                arguments = {}
                
                for param_match in param_matches:
                    param_name = param_match.group(1)
                    param_value = param_match.group(2)
                    # Unescape XML special characters
                    param_value = param_value.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
                    arguments[param_name] = param_value
                
                # Create tool call
                tool_call = {
                    'id': f"call_{len(tool_calls)}",
                    'type': 'function',
                    'function': {
                        'name': tool_name,
                        'arguments': json.dumps(arguments)
                    }
                }
                tool_calls.append(tool_call)
        
        # Remove the function_calls block from remaining text
        remaining_text = remaining_text.replace(match.group(0), '', 1)
    
    return tool_calls, remaining_text


def is_function_calling_supported(model_name: str) -> bool:
    """Check if a model supports native function calling"""
    from app.llm.llm import FUNCTION_CALLING_SUPPORTED_MODELS
    return model_name in FUNCTION_CALLING_SUPPORTED_MODELS


def should_convert_to_non_fncall(model_name: str, has_tools: bool) -> bool:
    """Determine if we should convert to non-function calling format"""
    return has_tools and not is_function_calling_supported(model_name)


def preprocess_messages_for_model(
    messages: List[Dict[str, Any]],
    model_name: str,
    tools: List[Dict[str, Any]] = None
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Preprocess messages for a specific model.
    
    Returns:
        tuple: (processed_messages, modified_kwargs)
    """
    modified_kwargs = {}
    
    if tools and should_convert_to_non_fncall(model_name, True):
        # Convert to non-function calling format
        processed_messages = convert_fncall_messages_to_non_fncall_messages(messages, tools)
        # Remove tools from kwargs since model doesn't support them
        modified_kwargs['tools'] = None
        modified_kwargs['tool_choice'] = None
    else:
        processed_messages = messages
    
    return processed_messages, modified_kwargs


def postprocess_response_for_model(
    response: Dict[str, Any],
    model_name: str,
    tools: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Postprocess response from a specific model.
    """
    if tools and should_convert_to_non_fncall(model_name, True):
        # Try to extract tool calls from text response
        choice = response.get('choices', [{}])[0]
        message = choice.get('message', {})
        content = message.get('content', '')
        
        if content:
            tool_names = {tool['function']['name'] for tool in tools}
            tool_calls, remaining_content = _extract_tool_calls_from_text(content, tool_names)
            
            if tool_calls:
                # Update the message with extracted tool calls
                message['tool_calls'] = tool_calls
                message['content'] = remaining_content.strip() if remaining_content.strip() else None
    
    return response
