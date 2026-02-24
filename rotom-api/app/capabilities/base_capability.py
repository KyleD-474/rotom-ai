"""
base_capability.py

Defines interface for all capabilities.

Capabilities represent atomic skills Rotom can execute.
"""

from abc import ABC, abstractmethod


class BaseCapability(ABC):
    """
    All capabilities must implement execute().
    
    Capabilities receive structured arguments.
    They are stateless and deterministic.
    """
    # Metadata descriptors
    name: str
    description: str
    argument_schema: dict[str, str]

    @abstractmethod
    def execute(self, arguments: dict):
        pass