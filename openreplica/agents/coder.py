"""Coder agent for OpenReplica."""

import re
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from openreplica.agents.base import Agent
from openreplica.events.base import EventType, CodeExecutionEvent, CodeResultEvent, FileChangeEvent
from openreplica.runtime.manager import runtime_manager
from openreplica.core.logger import logger


class CoderAgent(Agent):
    """AI agent specialized for coding tasks."""
    
    def __init__(self, session_id: str, config: Dict[str, Any]):
        super().__init__(session_id, config)
        self.workspace_path = config.get("workspace_path", f"./workspaces/{session_id}")
        
    def get_system_prompt(self) -> str:
        """Get the system prompt for the coder agent."""
        return """You are an expert AI coding assistant. You help users write, debug, and improve code.

You have access to the following capabilities:
1. **Code Execution**: You can run Python, JavaScript, and other code in a secure environment
2. **File Operations**: You can read, write, and modify files in the workspace
3. **Analysis**: You can analyze code, explain concepts, and provide suggestions

When you want to execute code, use this format:
```execute:python
# Your Python code here
print("Hello, World!")
```

When you want to create or modify files, use this format:
```file:filename.py
# File content here
def hello():
    print("Hello from file!")
```

When you want to read a file, use this format:
```read:filename.py```

Always explain what you're doing and why. Be helpful, clear, and educational in your responses.
"""

    async def process_message(self, message: str, **kwargs) -> AsyncGenerator[str, None]:
        """Process a user message and generate responses."""
        await self._emit_event(EventType.AGENT_THINKING, {"message": "Processing your request..."})
        
        # Add user message to history
        self.add_to_history("user", message)
        
        # Prepare messages for LLM
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            *self.conversation_history
        ]
        
        # Generate response
        full_response = ""
        async for chunk in self._generate_response(messages):
            full_response += chunk
            yield chunk
            
        # Add assistant response to history
        self.add_to_history("assistant", full_response)
        
        # Process any code execution or file operations
        await self._process_actions(full_response)
        
    async def _process_actions(self, response: str):
        """Process code execution and file operations from the response."""
        # Find code execution blocks
        execute_pattern = r'```execute:(\w+)\n(.*?)\n```'
        for match in re.finditer(execute_pattern, response, re.DOTALL):
            language = match.group(1)
            code = match.group(2)
            await self._execute_code(code, language)
            
        # Find file creation/modification blocks
        file_pattern = r'```file:([\w\./]+)\n(.*?)\n```'
        for match in re.finditer(file_pattern, response, re.DOTALL):
            filename = match.group(1)
            content = match.group(2)
            await self._write_file(filename, content)
            
        # Find file read requests
        read_pattern = r'```read:([\w\./]+)```'
        for match in re.finditer(read_pattern, response):
            filename = match.group(1)
            await self._read_file(filename)
            
    async def _execute_code(self, code: str, language: str = "python"):
        """Execute code in the runtime environment."""
        try:
            await self._emit_event(EventType.CODE_EXECUTION, {
                "code": code,
                "language": language
            })
            
            result = await runtime_manager.execute_code(
                self.session_id,
                code,
                language=language,
                workspace_path=self.workspace_path
            )
            
            await self._emit_event(EventType.CODE_RESULT, {
                "result": result["output"],
                "success": result["success"],
                "execution_time": result.get("execution_time")
            })
            
        except Exception as e:
            logger.error("Code execution failed", error=str(e))
            await self._emit_event(EventType.CODE_RESULT, {
                "result": f"Error: {str(e)}",
                "success": False
            })
            
    async def _write_file(self, filename: str, content: str):
        """Write content to a file."""
        try:
            filepath = f"{self.workspace_path}/{filename}"
            await runtime_manager.write_file(self.session_id, filepath, content)
            
            await self._emit_event(EventType.FILE_CHANGE, {
                "filepath": filename,
                "action": "write",
                "content": content
            })
            
        except Exception as e:
            logger.error("File write failed", error=str(e))
            
    async def _read_file(self, filename: str):
        """Read content from a file."""
        try:
            filepath = f"{self.workspace_path}/{filename}"
            content = await runtime_manager.read_file(self.session_id, filepath)
            
            await self._emit_event(EventType.FILE_CHANGE, {
                "filepath": filename,
                "action": "read",
                "content": content
            })
            
        except Exception as e:
            logger.error("File read failed", error=str(e))
