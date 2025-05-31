"""
Browsing agent for OpenReplica
Agent specialized for web browsing and interaction
"""
from typing import Dict, Any, List, Optional

from app.agents.base import LLMAgent, AgentConfig
from app.events.action import Action, create_action, ActionType
from app.events.observation import Observation, ObservationType


class BrowsingAgent(LLMAgent):
    """
    Browsing agent that can navigate and interact with web pages.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.current_url: Optional[str] = None
        self.page_content: str = ""
        self.system_prompt = self._get_system_prompt()
        self.add_message("system", self.system_prompt)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the Browsing agent"""
        return """You are a web browsing AI assistant that can navigate and interact with web pages.

You have access to the following actions:
- browse: Navigate to a URL
- click: Click on an element on the page
- type: Type text into an input field
- scroll: Scroll the page
- search: Search for content on the current page
- think: Express your thoughts about the current situation
- finish: Complete the current task

You should:
1. Understand what the user wants to accomplish on the web
2. Navigate to appropriate websites
3. Interact with page elements to complete tasks
4. Extract and provide relevant information
5. Finish when the task is complete

Always describe what you see on the page and explain your actions.
"""
    
    async def step(self, observation: Observation) -> Action:
        """Take a step based on the observation"""
        
        # Update internal state based on observation
        if observation.observation_type == ObservationType.BROWSER_PAGE_LOADED:
            if hasattr(observation, 'url'):
                self.current_url = observation.url
            if hasattr(observation, 'content'):
                self.page_content = observation.content
        
        # Add observation to conversation
        if observation.observation_type != ObservationType.NULL:
            obs_content = f"Browser observation ({observation.observation_type}): {observation.content}"
            if hasattr(observation, 'url'):
                obs_content += f"\nCurrent URL: {observation.url}"
            
            self.add_message("user", obs_content)
        
        # Get LLM response
        response = await self.call_llm(self.conversation_history)
        
        # Parse the response to determine the action
        action = self._parse_response(response)
        
        # Add action to conversation
        action_content = f"Browser action: {action.action_type}"
        if hasattr(action, 'thought') and action.thought:
            action_content += f" - {action.thought}"
        
        self.add_message("assistant", action_content)
        
        return action
    
    def _parse_response(self, response: str) -> Action:
        """
        Parse LLM response to extract browser action.
        """
        response_lower = response.lower()
        
        # Simple keyword-based action detection
        if "browse" in response_lower or "navigate" in response_lower or "go to" in response_lower:
            # Extract URL (simplified)
            url = "https://www.google.com"  # Default for demo
            if "github" in response_lower:
                url = "https://github.com"
            elif "stackoverflow" in response_lower:
                url = "https://stackoverflow.com"
            
            return create_action(
                ActionType.BROWSE,
                url=url,
                thought="Navigating to website to gather information"
            )
        
        elif "click" in response_lower:
            return create_action(
                ActionType.CLICK,
                # In a real implementation, this would extract the selector from the response
                thought="Clicking on an element on the page"
            )
        
        elif "type" in response_lower or "enter" in response_lower:
            return create_action(
                ActionType.TYPE,
                thought="Typing text into an input field"
            )
        
        elif "scroll" in response_lower:
            return create_action(
                ActionType.SCROLL,
                thought="Scrolling the page to see more content"
            )
        
        elif "search" in response_lower and ("page" in response_lower or "content" in response_lower):
            return create_action(
                ActionType.SEARCH,
                query="search term",
                thought="Searching for content on the current page"
            )
        
        elif "finish" in response_lower or "complete" in response_lower:
            return create_action(
                ActionType.FINISH,
                thought="Web browsing task completed successfully",
                success=True,
                message="Browsing agent has finished the task"
            )
        
        else:
            # Default to thinking
            return create_action(
                ActionType.THINK,
                thought=response,
                content=response
            )
    
    async def reset(self) -> None:
        """Reset the Browsing agent"""
        await super().reset()
        
        self.current_url = None
        self.page_content = ""
        
        # Reset conversation but keep system prompt
        self.clear_history()
        self.add_message("system", self.system_prompt)
        
        self.logger.info("Browsing agent reset")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Browsing agent statistics"""
        stats = super().get_stats()
        stats.update({
            "agent_type": "browsing",
            "current_url": self.current_url,
            "page_content_length": len(self.page_content),
            "conversation_length": len(self.conversation_history)
        })
        return stats


class BrowsingAgentConfig(AgentConfig):
    """Specialized configuration for Browsing agent"""
    
    # Browser settings
    headless: bool = True
    page_timeout: int = 30
    element_timeout: int = 10
    
    # Screenshot settings
    take_screenshots: bool = True
    screenshot_dir: str = "/tmp/screenshots"
    
    # Content extraction
    extract_text: bool = True
    extract_links: bool = True
    max_page_content_length: int = 50000
    
    class Config:
        extra = "allow"
