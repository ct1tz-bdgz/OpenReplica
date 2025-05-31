"""
Agent base class for OpenReplica matching OpenHands exactly
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.controller.state.state import State
    from app.core.config import AgentConfig
    from app.events.action import Action
    from app.events.action.message import SystemMessageAction
    from app.utils.prompt import PromptManager
from litellm import ChatCompletionToolParam

from app.core.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotRegisteredError,
)
from app.core.logging import get_logger
from app.events.event import EventSource
from app.llm.llm import LLM
from app.runtime.plugins import PluginRequirement

logger = get_logger(__name__)


class Agent(ABC):
    DEPRECATED = False
    """
    This abstract base class is an general interface for an agent dedicated to
    executing a specific instruction and allowing human interaction with the
    agent during execution.
    It tracks the execution status and maintains a history of interactions.
    """

    _registry: dict[str, type['Agent']] = {}
    sandbox_plugins: list[PluginRequirement] = []

    def __init__(
        self,
        llm: LLM,
        config: 'AgentConfig',
    ):
        self.llm = llm
        self.config = config
        self._complete = False
        self._prompt_manager: 'PromptManager' | None = None
        self.mcp_tools: dict[str, ChatCompletionToolParam] = {}
        self.tools: list = []

    @property
    def name(self) -> str:
        """Get the agent name"""
        return self.__class__.__name__

    @property
    def prompt_manager(self) -> 'PromptManager':
        if self._prompt_manager is None:
            raise ValueError(f'Prompt manager not initialized for agent {self.name}')
        return self._prompt_manager

    def get_system_message(self) -> 'SystemMessageAction | None':
        """
        Returns a SystemMessageAction containing the system message and tools.
        This will be added to the event stream as the first message.

        Returns:
            SystemMessageAction: The system message action with content and tools
            None: If there was an error generating the system message
        """
        # Import here to avoid circular imports
        from app.events.action.message import SystemMessageAction

        try:
            if not self.prompt_manager:
                logger.warning(
                    f'[{self.name}] Prompt manager not initialized before getting system message'
                )
                return None

            system_message = self.prompt_manager.get_system_message()

            # Get tools if available
            tools = getattr(self, 'tools', None)

            system_message_action = SystemMessageAction(
                content=system_message, tools=tools, agent_class=self.name
            )
            # Set the source attribute
            system_message_action._source = EventSource.AGENT  # type: ignore

            return system_message_action
        except Exception as e:
            logger.warning(f'[{self.name}] Failed to generate system message: {e}')
            return None

    @property
    def complete(self) -> bool:
        """Indicates whether the current instruction execution is complete.

        Returns:
        - complete (bool): True if execution is complete; False otherwise.
        """
        return self._complete

    @abstractmethod
    def step(self, state: 'State') -> 'Action':
        """Starts the execution of the assigned instruction. This method should
        be implemented by subclasses to define the specific execution logic.

        Parameters:
        - state (State): The current state of the agent.

        Returns:
        - Action: The action to be executed by the agent.
        """
        pass

    @classmethod
    def register(cls, name: str, agent_cls: type['Agent']) -> None:
        """Register an agent class.

        Args:
            name: The name to register the agent under.
            agent_cls: The agent class to register.

        Raises:
            AgentAlreadyRegisteredError: If an agent with the same name is already registered.
        """
        if name in cls._registry:
            raise AgentAlreadyRegisteredError(f'Agent {name} already registered')
        
        cls._registry[name] = agent_cls
        logger.info(f'Registered agent: {name}')

    @classmethod
    def get_cls(cls, name: str) -> type['Agent']:
        """Get an agent class by name.

        Args:
            name: The name of the agent class to retrieve.

        Returns:
            The agent class.

        Raises:
            AgentNotRegisteredError: If no agent with the given name is registered.
        """
        if name not in cls._registry:
            raise AgentNotRegisteredError(f'Agent {name} not registered')
        
        return cls._registry[name]

    @classmethod
    def list_agents(cls) -> list[str]:
        """List all registered agent names.

        Returns:
            A list of registered agent names.
        """
        return list(cls._registry.keys())

    @classmethod
    def get_agent_cls_by_name(cls, name: str) -> type['Agent']:
        """Get agent class by name (alias for get_cls for compatibility)"""
        return cls.get_cls(name)

    def set_prompt_manager(self, prompt_manager: 'PromptManager') -> None:
        """Set the prompt manager for this agent"""
        self._prompt_manager = prompt_manager

    def get_action_and_observation_sets(self) -> tuple[set[type], set[type]]:
        """
        Get the action and observation sets for this agent.
        This can be used to filter relevant events for the agent.
        
        Returns:
            tuple: (action_types, observation_types) that this agent can handle
        """
        # Default implementation - subclasses should override if they need specific filtering
        from app.events.action import Action
        from app.events.observation import Observation
        
        return {Action}, {Observation}

    def reset(self) -> None:
        """Reset the agent to its initial state"""
        self._complete = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(complete={self._complete})"
