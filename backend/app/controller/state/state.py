"""
State management for OpenReplica matching OpenHands exactly
"""
from __future__ import annotations

import base64
import os
import pickle
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import app
from app.core.logging import get_logger
from app.core.schema import AgentState
from app.events.action import (
    MessageAction,
)
from app.events.action.agent import AgentFinishAction
from app.events.event import Event, EventSource
from app.llm.metrics import Metrics
from app.memory.view import View
from app.storage.files import FileStore
from app.storage.locations import get_conversation_agent_state_filename

logger = get_logger(__name__)


class TrafficControlState(str, Enum):
    # default state, no rate limiting
    NORMAL = 'normal'

    # task paused due to traffic control
    THROTTLING = 'throttling'

    # traffic control is temporarily paused
    PAUSED = 'paused'


RESUMABLE_STATES = [
    AgentState.RUNNING,
    AgentState.PAUSED,
    AgentState.AWAITING_USER_INPUT,
    AgentState.FINISHED,
]


@dataclass
class State:
    """
    Represents the running state of an agent in the OpenReplica system, saving data of its operation and memory.

    - Multi-agent/delegate state:
      - store the task (conversation between the agent and the user)
      - the subtask (conversation between an agent and the user or another agent)
      - global and local iterations
      - delegate levels for multi-agent interactions
      - almost stuck state

    - Running state of an agent:
      - current agent state (e.g., LOADING, RUNNING, PAUSED)
      - traffic control state for rate limiting
      - confirmation mode
      - the last error encountered

    - Data for saving and restoring the agent:
      - save to and restore from a session
      - serialize with pickle and base64

    - Save / restore data about message history
      - start and end IDs for events in agent's history
      - summaries and delegate summaries

    - Metrics:
      - global metrics for the current task
      - local metrics for the current subtask

    - Extra data:
      - additional task-specific data
    """

    session_id: str = ''
    # global iteration for the current task
    iteration: int = 0
    # local iteration for the current subtask
    local_iteration: int = 0
    # max number of iterations for the current task
    max_iterations: int = 100
    confirmation_mode: bool = False
    history: list[Event] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    agent_state: AgentState = AgentState.LOADING
    resume_state: AgentState | None = None
    traffic_control_state: TrafficControlState = TrafficControlState.NORMAL
    # global metrics for the current task
    metrics: Metrics = field(default_factory=Metrics)
    # local metrics for the current subtask
    local_metrics: Metrics = field(default_factory=Metrics)
    # root agent has level 0, and every delegate increases the level by one
    delegate_level: int = 0
    # start_id and end_id track the range of events in history
    start_id: int = -1
    end_id: int = -1
    # a delegate can be stuck while trying to complete a task
    almost_stuck: int = 0
    # the last error encountered, if any
    last_error: str | None = None
    # the total budget used for the current task
    budget_used: float = 0.0
    # the maximum budget allowed for the current task
    max_budget_per_task: float | None = None
    # saving information about the task's completed status
    task_completed: bool = False
    # save the summary of the current task for the case of delegate
    summary: dict[str, Any] = field(default_factory=dict)
    # saving information about the subtask's completed status for the case of delegate
    subtask_completed: bool = False
    # save the delegate summary of the current subtask for the case of delegate
    delegate_summary: dict[str, Any] = field(default_factory=dict)
    # extra data that can be used by different agents
    extra_data: dict[str, Any] = field(default_factory=dict)

    def save_to_session(
        self, file_store: FileStore, session_id: str | None = None
    ) -> None:
        """Save the current state to a session file.

        Args:
            file_store: The file store to save to.
            session_id: The session ID to save to. If None, uses the current session_id.
        """
        if session_id is None:
            session_id = self.session_id

        try:
            # Serialize the state
            state_data = self.serialize()
            
            # Save to file store
            filename = get_conversation_agent_state_filename(session_id)
            file_store.write(filename, state_data)
            
            logger.info(f'Saved agent state to session {session_id}')
            
        except Exception as e:
            logger.error(f'Failed to save agent state: {e}')
            raise

    @classmethod
    def restore_from_session(
        cls, file_store: FileStore, session_id: str
    ) -> 'State | None':
        """Restore state from a session file.

        Args:
            file_store: The file store to restore from.
            session_id: The session ID to restore from.

        Returns:
            The restored state, or None if not found.
        """
        try:
            filename = get_conversation_agent_state_filename(session_id)
            
            if not file_store.exists(filename):
                logger.warning(f'No agent state found for session {session_id}')
                return None
            
            # Load from file store
            state_data = file_store.read(filename)
            
            # Deserialize the state
            state = cls.deserialize(state_data)
            state.session_id = session_id
            
            logger.info(f'Restored agent state from session {session_id}')
            return state
            
        except Exception as e:
            logger.error(f'Failed to restore agent state: {e}')
            return None

    def serialize(self) -> str:
        """Serialize the state to a string.

        Returns:
            Base64 encoded pickle data.
        """
        try:
            # Create a copy without unpickleable objects
            state_dict = {}
            for key, value in self.__dict__.items():
                try:
                    # Test if the value is pickleable
                    pickle.dumps(value)
                    state_dict[key] = value
                except (pickle.PicklingError, TypeError):
                    logger.warning(f'Skipping unpickleable field: {key}')
            
            # Serialize to bytes
            pickled_data = pickle.dumps(state_dict)
            
            # Encode to base64 string
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            
            return encoded_data
            
        except Exception as e:
            logger.error(f'Failed to serialize state: {e}')
            raise

    @classmethod
    def deserialize(cls, data: str) -> 'State':
        """Deserialize state from a string.

        Args:
            data: Base64 encoded pickle data.

        Returns:
            The deserialized state.
        """
        try:
            # Decode from base64
            pickled_data = base64.b64decode(data.encode('utf-8'))
            
            # Deserialize from bytes
            state_dict = pickle.loads(pickled_data)
            
            # Create new state instance
            state = cls()
            
            # Set attributes
            for key, value in state_dict.items():
                setattr(state, key, value)
            
            return state
            
        except Exception as e:
            logger.error(f'Failed to deserialize state: {e}')
            raise

    def get_current_user_intent(self) -> str:
        """Get the current user intent from the conversation history.

        Returns:
            The latest user message content, or empty string if none found.
        """
        for event in reversed(self.history):
            if (isinstance(event, MessageAction) and 
                event.source == EventSource.USER and 
                event.content):
                return event.content
        
        return ""

    def get_completed_subtasks(self) -> list[str]:
        """Get list of completed subtasks.

        Returns:
            List of completed subtask descriptions.
        """
        completed = []
        
        for event in self.history:
            if isinstance(event, AgentFinishAction):
                if hasattr(event, 'summary') and event.summary:
                    completed.append(event.summary)
                elif hasattr(event, 'thought') and event.thought:
                    completed.append(event.thought)
        
        return completed

    def get_task_state(self) -> dict[str, Any]:
        """Get the current task state summary.

        Returns:
            Dictionary containing task state information.
        """
        return {
            'session_id': self.session_id,
            'iteration': self.iteration,
            'local_iteration': self.local_iteration,
            'max_iterations': self.max_iterations,
            'agent_state': self.agent_state.value,
            'traffic_control_state': self.traffic_control_state.value,
            'confirmation_mode': self.confirmation_mode,
            'delegate_level': self.delegate_level,
            'budget_used': self.budget_used,
            'max_budget_per_task': self.max_budget_per_task,
            'task_completed': self.task_completed,
            'subtask_completed': self.subtask_completed,
            'almost_stuck': self.almost_stuck,
            'last_error': self.last_error,
            'history_length': len(self.history),
            'start_id': self.start_id,
            'end_id': self.end_id,
        }

    def is_budget_exceeded(self) -> bool:
        """Check if the budget has been exceeded.

        Returns:
            True if budget is exceeded, False otherwise.
        """
        if self.max_budget_per_task is None:
            return False
        
        return self.budget_used >= self.max_budget_per_task

    def is_stuck(self, threshold: int = 3) -> bool:
        """Check if the agent is stuck.

        Args:
            threshold: Number of stuck iterations before considering stuck.

        Returns:
            True if agent is stuck, False otherwise.
        """
        return self.almost_stuck >= threshold

    def can_continue(self) -> bool:
        """Check if the agent can continue execution.

        Returns:
            True if agent can continue, False otherwise.
        """
        if self.task_completed or self.subtask_completed:
            return False
        
        if self.agent_state in [AgentState.FINISHED, AgentState.ERROR, AgentState.STOPPED]:
            return False
        
        if self.iteration >= self.max_iterations:
            return False
        
        if self.is_budget_exceeded():
            return False
        
        if self.traffic_control_state == TrafficControlState.THROTTLING:
            return False
        
        return True

    def reset_for_new_task(self) -> None:
        """Reset state for a new task while preserving session info."""
        self.iteration = 0
        self.local_iteration = 0
        self.history.clear()
        self.inputs.clear()
        self.outputs.clear()
        self.agent_state = AgentState.LOADING
        self.resume_state = None
        self.traffic_control_state = TrafficControlState.NORMAL
        self.almost_stuck = 0
        self.last_error = None
        self.budget_used = 0.0
        self.task_completed = False
        self.summary.clear()
        self.subtask_completed = False
        self.delegate_summary.clear()
        self.extra_data.clear()
        self.start_id = -1
        self.end_id = -1
        
        # Reset metrics but keep references
        self.metrics.reset()
        self.local_metrics.reset()

    def update_metrics(self, cost: float = 0.0) -> None:
        """Update both global and local metrics.

        Args:
            cost: The cost to add to the budget.
        """
        self.budget_used += cost
        
        # Metrics are updated by the LLM classes directly
        # This method is for any additional state-specific updates

    def __repr__(self) -> str:
        return (
            f"State(session_id='{self.session_id}', "
            f"iteration={self.iteration}, "
            f"agent_state={self.agent_state.value}, "
            f"delegate_level={self.delegate_level})"
        )
