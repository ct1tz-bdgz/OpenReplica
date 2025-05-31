"""
CodeAct Agent for OpenReplica matching OpenHands exactly
"""
import os
import sys
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from litellm import ChatCompletionToolParam

    from app.events.action import Action
    from app.llm.llm import ModelResponse

import app.agenthub.codeact_agent.function_calling as codeact_function_calling
from app.agenthub.codeact_agent.tools.bash import create_cmd_run_tool
from app.agenthub.codeact_agent.tools.browser import BrowserTool
from app.agenthub.codeact_agent.tools.finish import FinishTool
from app.agenthub.codeact_agent.tools.ipython import IPythonTool
from app.agenthub.codeact_agent.tools.llm_based_edit import LLMBasedFileEditTool
from app.agenthub.codeact_agent.tools.str_replace_editor import (
    create_str_replace_editor_tool,
)
from app.agenthub.codeact_agent.tools.think import ThinkTool
from app.controller.agent import Agent
from app.controller.state.state import State
from app.core.config import AgentConfig
from app.core.logging import get_logger
from app.core.message import Message
from app.events.action import AgentFinishAction, MessageAction
from app.events.event import Event
from app.llm.llm import LLM
from app.llm.llm_utils import check_tools
from app.memory.condenser import Condenser
from app.memory.condenser.condenser import Condensation, View
from app.memory.conversation_memory import ConversationMemory
from app.runtime.plugins import (
    AgentSkillsRequirement,
    JupyterRequirement,
    PluginRequirement,
)
from app.utils.prompt import PromptManager

logger = get_logger(__name__)


class CodeActAgent(Agent):
    VERSION = '2.2'
    """
    The Code Act Agent is a minimalist agent.
    The agent works by passing the model a list of action-observation pairs and prompting the model to take the next step.

    ### Overview

    This agent implements the CodeAct idea ([paper](https://arxiv.org/abs/2402.01030), [tweet](https://twitter.com/xingyaow_/status/1754556835703751087)) that consolidates LLM agents' **act**ions into a unified **code** action space for both *simplicity* and *performance* (see paper for more details).

    The conceptual idea is illustrated below. At each turn, the agent can:

    1. **Converse**: Communicate with humans in natural language to ask for clarification, confirmation, etc.
    2. **CodeAct**: Choose to perform the task by executing code
    - Execute any valid Linux `bash` command
    - Execute any valid `Python` code with [an interactive Python interpreter](https://ipython.org/). This is simulated through `bash` command, see plugin system below for more details.

    ![image](https://github.com/All-Hands-AI/OpenHands/assets/38853559/92b622e3-72ad-4a61-8f41-8c040b6d5fb3)

    """

    sandbox_plugins: list[PluginRequirement] = [
        # NOTE: AgentSkillsRequirement need to go before JupyterRequirement, since
        # AgentSkillsRequirement provides a lot of Python functions,
        # and it needs to be initialized before Jupyter for Jupyter to use those functions.
        AgentSkillsRequirement(),
        JupyterRequirement(),
    ]

    def __init__(
        self,
        llm: LLM,
        config: AgentConfig,
    ) -> None:
        """Initializes a new instance of the CodeActAgent class.

        Parameters:
        - llm (LLM): The llm to be used by this agent
        - config (AgentConfig): The configuration for this agent
        """
        super().__init__(llm, config)
        self.pending_actions: deque['Action'] = deque()
        self.reset()
        self.tools = self._get_tools()

        # Create a ConversationMemory instance
        self.conversation_memory = ConversationMemory(self.config, self.prompt_manager)

        self.condenser = Condenser.from_config(self.config.condenser)
        logger.debug(f'Using condenser: {type(self.condenser)}')

    @property
    def prompt_manager(self) -> PromptManager:
        if self._prompt_manager is None:
            self._prompt_manager = PromptManager(
                prompt_dir=os.path.join(os.path.dirname(__file__), 'prompts'),
            )

        return self._prompt_manager

    def _get_tools(self) -> list['ChatCompletionToolParam']:
        """Get the list of tools available to the agent"""
        tools = []
        
        # Add core tools
        tools.append(ThinkTool().to_tool_param())
        tools.append(create_cmd_run_tool())
        tools.append(IPythonTool().to_tool_param())
        tools.append(create_str_replace_editor_tool())
        tools.append(LLMBasedFileEditTool().to_tool_param())
        tools.append(BrowserTool().to_tool_param())
        tools.append(FinishTool().to_tool_param())
        
        # Add MCP tools if available
        if hasattr(self, 'mcp_tools') and self.mcp_tools:
            tools.extend(self.mcp_tools.values())
        
        return tools

    def reset(self) -> None:
        """Reset the agent state"""
        super().reset()
        self.pending_actions.clear()

    def step(self, state: State) -> 'Action':
        """
        Performs one step using the CodeAct agent.
        This includes gathering info on previous steps and prompting the model to make a command to execute.
        """
        # Check if there are pending actions to execute
        if self.pending_actions:
            return self.pending_actions.popleft()

        # Handle special cases
        if state.agent_state.value == 'paused':
            return MessageAction('I am paused. Please provide further instructions.')

        # Get conversation history and create messages
        messages = self._get_messages(state)
        
        # Add system message if this is the first step
        if state.iteration == 0:
            system_message_action = self.get_system_message()
            if system_message_action:
                # The system message is already added to the event stream
                pass

        # Check tools compatibility
        tools = check_tools(self.tools, self.llm.model_name)
        
        try:
            # Get response from LLM
            response = self._query_llm(messages, tools)
            
            # Process the response and convert to action
            action = self._response_to_action(response, state)
            
            return action
            
        except Exception as e:
            logger.error(f'Error in CodeActAgent.step: {e}')
            return MessageAction(f'I encountered an error: {str(e)}')

    def _get_messages(self, state: State) -> list[Message]:
        """Get conversation messages from state"""
        messages = []
        
        # Convert events to messages
        for event in state.history:
            if isinstance(event, MessageAction):
                messages.append(Message(
                    role=event.source.value,
                    content=event.content
                ))
        
        # Apply memory condensation if needed
        if len(messages) > self.config.max_iterations:
            messages = self._condense_messages(messages, state)
        
        return messages

    def _condense_messages(self, messages: list[Message], state: State) -> list[Message]:
        """Apply memory condensation to reduce message count"""
        try:
            # Use the condenser to reduce message count
            condensation = self.condenser.condense(
                messages=messages,
                max_tokens=self.llm.get_model_info().get('max_tokens', 4096) // 2
            )
            
            return condensation.messages
            
        except Exception as e:
            logger.warning(f'Error in message condensation: {e}')
            # Fallback: keep only recent messages
            return messages[-self.config.max_iterations:]

    def _query_llm(self, messages: list[Message], tools: list) -> 'ModelResponse':
        """Query the LLM with messages and tools"""
        return self.llm.completion(
            messages=messages,
            tools=tools if tools else None,
            temperature=0.1,
            max_tokens=4096
        )

    def _response_to_action(self, response: 'ModelResponse', state: State) -> 'Action':
        """Convert LLM response to action"""
        try:
            return codeact_function_calling.response_to_actions(
                response=response,
                agent=self,
                state=state
            )[0]  # Get the first action
            
        except Exception as e:
            logger.error(f'Error converting response to action: {e}')
            # Fallback to message action
            choice = response.choices[0] if response.choices else None
            message = choice.message if choice else None
            content = message.content if message else str(e)
            
            return MessageAction(content)

    def search_memory(self, query: str) -> list[str]:
        """Search agent's memory for relevant information"""
        try:
            return self.conversation_memory.search(query)
        except Exception as e:
            logger.warning(f'Error searching memory: {e}')
            return []

    def add_to_memory(self, content: str, metadata: dict = None) -> None:
        """Add content to agent's memory"""
        try:
            self.conversation_memory.add(content, metadata or {})
        except Exception as e:
            logger.warning(f'Error adding to memory: {e}')

    def get_action_and_observation_sets(self) -> tuple[set[type], set[type]]:
        """Get the action and observation sets for this agent"""
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
        from app.events.observation import (
            CmdOutputObservation,
            IPythonRunCellObservation,
            FileReadObservation,
            FileWriteObservation,
            FileEditObservation,
            BrowserObservation,
            ErrorObservation,
            NullObservation
        )
        
        action_types = {
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
        }
        
        observation_types = {
            CmdOutputObservation,
            IPythonRunCellObservation,
            FileReadObservation,
            FileWriteObservation,
            FileEditObservation,
            BrowserObservation,
            ErrorObservation,
            NullObservation
        }
        
        return action_types, observation_types

    def __repr__(self) -> str:
        return f"CodeActAgent(version={self.VERSION}, complete={self._complete})"
