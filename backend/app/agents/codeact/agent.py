"""
CodeAct agent for OpenReplica
The main coding agent that can read, write, and execute code
"""
import os
from typing import Dict, Any, List

from app.agents.base import LLMAgent, AgentConfig
from app.events.action import Action, create_action, ActionType
from app.events.observation import Observation, ObservationType


class CodeActAgent(LLMAgent):
    """
    CodeAct agent that can perform code-related actions.
    This is the primary agent for coding tasks.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.system_prompt = self._get_system_prompt()
        self.add_message("system", self.system_prompt)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the CodeAct agent"""
        return """You are a helpful AI assistant that can help users with coding tasks.

You have access to the following actions:
- write: Write content to a file
- read: Read content from a file
- edit: Edit a file by replacing old content with new content
- run: Execute shell commands
- search: Search for files or content
- create_file: Create a new file
- create_directory: Create a new directory
- think: Express your thoughts about the current situation
- finish: Complete the current task

You should:
1. Understand the user's request
2. Break down complex tasks into smaller steps
3. Use appropriate actions to accomplish the task
4. Provide clear thoughts about what you're doing
5. Finish when the task is complete

Always think step by step and explain your reasoning.
"""
    
    async def step(self, observation: Observation) -> Action:
        """Take a step based on the observation"""
        
        # Add observation to conversation
        if observation.observation_type != ObservationType.NULL:
            obs_content = f"Observation ({observation.observation_type}): {observation.content}"
            if hasattr(observation, 'success') and not observation.success:
                obs_content += f" (Failed: {getattr(observation, 'error_message', 'Unknown error')})"
            
            self.add_message("user", obs_content)
        
        # Get LLM response
        response = await self.call_llm(self.conversation_history)
        
        # Parse the response to determine the action
        action = self._parse_response(response)
        
        # Add action to conversation
        action_content = f"Action: {action.action_type}"
        if hasattr(action, 'thought') and action.thought:
            action_content += f" - {action.thought}"
        
        self.add_message("assistant", action_content)
        
        return action
    
    def _parse_response(self, response: str) -> Action:
        """
        Parse LLM response to extract action.
        This is a simplified parser - in a real implementation,
        you'd want more sophisticated parsing.
        """
        response_lower = response.lower()
        
        # Simple keyword-based action detection
        if "write" in response_lower and "file" in response_lower:
            return create_action(
                ActionType.WRITE,
                path="/tmp/example.txt",
                content="# Example file content\nprint('Hello, World!')\n",
                thought="Creating an example file"
            )
        
        elif "read" in response_lower and "file" in response_lower:
            return create_action(
                ActionType.READ,
                path="/tmp/example.txt",
                thought="Reading file to understand current state"
            )
        
        elif "run" in response_lower or "execute" in response_lower:
            return create_action(
                ActionType.RUN,
                command="ls -la",
                thought="Checking current directory contents"
            )
        
        elif "search" in response_lower:
            return create_action(
                ActionType.SEARCH,
                query="*.py",
                thought="Searching for Python files"
            )
        
        elif "finish" in response_lower or "complete" in response_lower:
            return create_action(
                ActionType.FINISH,
                thought="Task completed successfully",
                success=True,
                message="CodeAct agent has finished the task"
            )
        
        else:
            # Default to thinking
            return create_action(
                ActionType.THINK,
                thought=response,
                content=response
            )
    
    async def reset(self) -> None:
        """Reset the CodeAct agent"""
        await super().reset()
        
        # Reset conversation but keep system prompt
        self.clear_history()
        self.add_message("system", self.system_prompt)
        
        self.logger.info("CodeAct agent reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get CodeAct agent statistics"""
        stats = super().get_stats()
        stats.update({
            "agent_type": "codeact",
            "conversation_length": len(self.conversation_history),
            "workspace_dir": self.workspace_dir
        })
        return stats


class CodeActAgentConfig(AgentConfig):
    """Specialized configuration for CodeAct agent"""
    
    # Code-specific settings
    enable_shell_commands: bool = True
    allowed_file_extensions: List[str] = [
        ".py", ".js", ".ts", ".html", ".css", ".json", ".md", ".txt", ".sh"
    ]
    max_file_size_mb: int = 10
    
    # Execution settings
    command_timeout: int = 30
    enable_web_browsing: bool = False
    
    class Config:
        extra = "allow"
