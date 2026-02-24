"""
base_capability.py

Defines interface for all capabilities.

Capabilities represent atomic skills Rotom can execute.
"""

from abc import ABC, abstractmethod


class BaseCapability(ABC):
    """
    All capabilities must implement execute().
    """

    @abstractmethod
    def execute(self, user_input: str):
        pass