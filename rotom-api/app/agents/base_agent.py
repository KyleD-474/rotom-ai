"""
base_agent.py

Defines the interface that all agents must implement.

This enforces architectural consistency as the system scales.
"""

from abc import ABC, abstractmethod


# Abstract base class for all agents.
class BaseAgent(ABC):

    # Process a user input string and return a result.
    @abstractmethod
    def handle(self, user_input: str):
        pass