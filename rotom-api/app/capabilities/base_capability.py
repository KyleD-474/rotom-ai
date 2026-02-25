"""
base_capability.py — Interface for all capabilities

A capability is a single, atomic action Rotom can perform (e.g. echo a message,
summarize text). Each one has a name, description, and argument_schema so the
LLM and RotomCore know how to call it. Capabilities are stateless: they get
only the arguments for this call and return a CapabilityResult. They do not
see session, memory, or the registry—they just execute.
"""

from abc import ABC, abstractmethod


class BaseCapability(ABC):
    """
    Subclasses must set name, description, and argument_schema (used for
    validation and for building the LLM prompt), and implement execute(arguments).
    """

    name: str
    description: str
    argument_schema: dict[str, str]

    @abstractmethod
    def execute(self, arguments: dict):
        """Run the capability with the given arguments; return a CapabilityResult."""
        pass