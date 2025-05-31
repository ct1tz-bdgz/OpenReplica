"""
Plugin requirements for OpenReplica runtime matching OpenHands exactly
"""
from abc import abstractmethod
from dataclasses import dataclass

from app.events.action import Action
from app.events.observation import Observation


class Plugin:
    """Base class for a plugin.

    This will be initialized by the runtime client, which will run inside docker.
    """

    name: str

    @abstractmethod
    async def initialize(self, username: str) -> None:
        """Initialize the plugin."""
        pass

    @abstractmethod
    async def run(self, action: Action) -> Observation:
        """Run the plugin for a given action."""
        pass


@dataclass
class PluginRequirement:
    """Requirement for a plugin."""

    name: str
    version: str = "latest"
    config: dict = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}
